from collections import OrderedDict

import torch
from torch import nn
import torch.nn.functional as F
from einops import repeat


class PromptLearner(nn.Module):
    def __init__(self):
        super().__init__()

        n_ctx, ctx_depth = 4, 1
        self.meta_net = PromptTranslator(n_ctx, ctx_depth, depth=0)
        self.ctx_depth = ctx_depth
        self.n_ctx = n_ctx

    def forward(self, context_emb, visual):
        text_ctx = self.meta_net(context_emb.unsqueeze(0), visual)
        return text_ctx


def exists(val):
    return val is not None


class PreNorm(nn.Module):
    def __init__(self, dim, fn, context_dim=None):
        super().__init__()
        self.fn = fn
        self.norm = nn.LayerNorm(dim)
        self.norm_context = nn.LayerNorm(context_dim) if exists(context_dim) else None

    def forward(self, x_q, x_kv=None, **kwargs):
        x_q = self.norm(x_q)
        if exists(x_kv):
            x_kv = self.norm_context(x_kv)
        else:
            x_kv = x_q

        return self.fn(x_q, x_kv, x_kv, **kwargs)


class GEGLU(nn.Module):
    def forward(self, x):
        x, gates = x.chunk(2, dim=-1)
        return x * F.gelu(gates)


class FeedForward(nn.Module):
    def __init__(self, dim, mult=4):
        super().__init__()
        self.net = nn.Sequential(
            nn.LayerNorm(dim),
            nn.Linear(dim, dim * mult * 2),
            GEGLU(),
            nn.Linear(dim * mult, dim)
        )

    def forward(self, x):
        return self.net(x)


class CrossAttention(nn.Module):
    def __init__(
            self,
            latent_dim,
            kv_dim,
            cross_heads=4,
            seq_dropout_prob=0.
    ):
        super().__init__()
        self.seq_dropout_prob = seq_dropout_prob

        self.cross_attend_blocks = nn.ModuleList([
            PreNorm(latent_dim,
                    nn.MultiheadAttention(latent_dim, num_heads=cross_heads, kdim=kv_dim, vdim=kv_dim,
                                          dropout=seq_dropout_prob, batch_first=True),
                    context_dim=kv_dim),
            FeedForward(latent_dim)])

    def forward(self, data, visual_prompt, mask=None):
        b, *_, device = *data.shape, data.device
        visual_prompt = repeat(visual_prompt, 'n d -> b n d', b=b)
        cross_attn, cross_ff = self.cross_attend_blocks
        x, _ = cross_attn(visual_prompt, data, key_padding_mask=mask)
        x = cross_ff(x) + x
        return x


class SelfAttention(nn.Module):
    def __init__(
            self,
            depth,
            latent_dim,
            latent_heads=4,
    ):
        super().__init__()

        self.layers = nn.ModuleList([])

        for i in range(depth):
            self.layers.append(nn.ModuleList([
                PreNorm(latent_dim, nn.MultiheadAttention(latent_dim, num_heads=latent_heads, batch_first=True)),
                FeedForward(latent_dim)
            ]))

    def forward(self, x, mask=None):
        for self_attn, self_ff in self.layers:
            x = self_attn(x, key_padding_mask=mask)[0] + x
            x = self_ff(x) + x
        return x


class PromptTranslator(nn.Module):
    def __init__(
            self,
            prompt_len,
            prompt_depth,
            prompt_dim=512,
            depth=4,
            self_heads=4,
            cross_heads=4,
            textemb_dim=512,
            device='cuda'
    ):
        super().__init__()
        self.device = device
        self.prompt_len = prompt_len
        self.prompt_depth = prompt_depth
        prompt_dim = prompt_dim
        self.encoder = CrossAttention(
            latent_dim=prompt_dim,
            kv_dim=textemb_dim,
            cross_heads=cross_heads,
        )
        if depth > 0:
            self.transformer = SelfAttention(depth=depth, latent_dim=prompt_dim, latent_heads = self_heads)

        self.depth = depth
        self.visual_net = nn.Sequential(OrderedDict([
            ("linear1", nn.Linear(256, 32)),
            ("relu", nn.ReLU()),
            ("linear2", nn.Linear(32, prompt_len))
        ]))

    def forward(self, text_emb, visual):
        visual = visual.permute(0, 2, 1)
        visual_prompt = self.visual_net(visual)
        visual_prompt = visual_prompt.permute(0, 2, 1)
        visual_prompt_mean = torch.mean(visual_prompt, dim=0)

        prompt = self.encoder(text_emb, visual_prompt_mean)
        if self.depth > 0:
            prompt = self.transformer(prompt)
        return prompt
