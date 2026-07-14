from collections import OrderedDict

import numpy as np
import torch
import torch.nn.functional as F
from torch import nn
from utils.clip import clip
from utils.prompt_net import PromptLearner


class LayerNorm(nn.LayerNorm):
    def forward(self, x: torch.Tensor):
        orig_type = x.dtype
        ret = super().forward(x.type(torch.float32))
        return ret.type(orig_type)


class QuickGELU(nn.Module):
    def forward(self, x: torch.Tensor):
        return x * torch.sigmoid(1.702 * x)


class ResidualAttentionBlock(nn.Module):
    def __init__(self, d_model: int, n_head: int, dropout: float, attn_mask: torch.Tensor = None):
        super().__init__()

        self.attn = nn.MultiheadAttention(d_model, n_head, dropout=dropout)
        self.ln_1 = LayerNorm(d_model)

        self.mlp = nn.Sequential(OrderedDict([
            ("c_fc", nn.Linear(d_model, d_model * 4)),
            ("gelu", QuickGELU()),
            ("c_proj", nn.Linear(d_model * 4, d_model))
        ]))
        self.ln_2 = LayerNorm(d_model)
        self.attn_mask = attn_mask

    def attention(self, x: torch.Tensor):
        self.attn_mask = self.attn_mask.to(dtype=x.dtype, device=x.device) if self.attn_mask is not None else None
        return self.attn(x, x, x, need_weights=False, attn_mask=self.attn_mask)[0]

    def forward(self, x: torch.Tensor):
        x = x + self.attention(self.ln_1(x))
        x = x + self.mlp(self.ln_2(x))
        return x


# transformer encoder
class TransformerEncoder(nn.Module):
    def __init__(self, width: int, layers: int, heads: int, dropout: float = 0, attn_mask: torch.Tensor = None, ):
        super(TransformerEncoder, self).__init__()
        self.width = width
        self.layers = layers
        self.resblocks = nn.Sequential(
            *[ResidualAttentionBlock(width, heads, dropout, attn_mask) for _ in range(layers)])

    def forward(self, x: torch.Tensor):
        return self.resblocks(x)


class Model(nn.Module):
    def __init__(self,
                 embed_dim: int,
                 visual_length: int,
                 prompt_prefix: int,
                 prompt_postfix: int,
                 visual_width: int,
                 visual_layers: int,
                 visual_head: int,
                 attn_window: int,
                 device):
        super().__init__()

        self.visual_length = visual_length
        self.embed_dim = embed_dim
        self.prompt_prefix = prompt_prefix
        self.prompt_postfix = prompt_postfix
        self.attn_window = attn_window
        self.device = device

        self.clipmodel, _ = clip.load("ViT-B/16", device)
        for clip_param in self.clipmodel.parameters():
            clip_param.requires_grad = False

        self.temporal = TransformerEncoder(
            width=visual_width,
            layers=visual_layers,
            heads=visual_head,
        )

        self.prompt_learner = PromptLearner()

        self.frame_position_embeddings = nn.Embedding(visual_length, visual_width)
        self.global_text_prompt_embeddings = nn.Embedding(77, self.embed_dim)
        self.dtype = self.clipmodel.dtype
        self.initialize_parameters()

    def initialize_parameters(self):
        nn.init.normal_(self.frame_position_embeddings.weight, std=0.01)

    def encode_video(self, images):
        images = images.to(torch.float)
        position_ids = torch.arange(self.visual_length, device=self.device)
        position_ids = position_ids.unsqueeze(0).expand(images.shape[0], -1)
        frame_position_embeddings = self.frame_position_embeddings(position_ids)
        frame_position_embeddings = frame_position_embeddings.permute(1, 0, 2)
        images = images.permute(1, 0, 2) + frame_position_embeddings

        x = self.temporal(images)
        x = x.permute(1, 0, 2)
        return x

    def get_tokenized_classnames(self, classes):
        prompts = [" ".join(["X"] * 4) + " " + name + "." for name in classes]

        tokenized_prompts = torch.cat([clip.tokenize(p) for p in prompts])
        with torch.no_grad():
            embedding = self.clipmodel.token_embedding(tokenized_prompts.to(self.device)).type(self.dtype)

        return embedding, tokenized_prompts

    def encode_text_prompt(self, text, visual):
        classes = [name.replace("_", " ") for name in text]
        class_tokens = torch.cat([clip.tokenize(p) for p in classes])
        class_tokens = class_tokens.to(self.device)
        with torch.no_grad():
            class_features = self.clipmodel.encode_text_original(class_tokens)
            class_features = class_features / class_features.norm(dim=-1, keepdim=True)

        context_embedding = class_features
        prompt_vectors, tokenized_prompts = self.get_tokenized_classnames(classes)

        context = self.prompt_learner(context_embedding, visual)
        prompt_vectors = torch.cat(
            [
                prompt_vectors[:, :1],
                context[0].unsqueeze(0).expand(prompt_vectors.shape[0], -1, -1),
                prompt_vectors[:, 1 + context.shape[1]:],
            ],
            dim=1,
        )

        text_features = self.clipmodel.encode_text(prompt_vectors, tokenized_prompts)
        return text_features

    def forward(self, visual, text, lengths):
        visual_features = self.encode_video(visual)
        text_features = self.encode_text_prompt(text, visual_features)

        text_features = text_features.unsqueeze(0)
        text_features = text_features.expand(
            visual_features.shape[0], text_features.shape[1], text_features.shape[2])

        visual_features_norm = visual_features / visual_features.norm(dim=-1, keepdim=True)
        text_features_norm = text_features / text_features.norm(dim=-1, keepdim=True)
        text_features_norm = text_features_norm.permute(0, 2, 1)

        logits = visual_features_norm @ text_features_norm.type(visual_features_norm.dtype)
        logits = logits * self.clipmodel.logit_scale.exp()
        return logits
