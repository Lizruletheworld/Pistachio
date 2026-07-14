import copy
from collections import OrderedDict
import torch
from torch.optim.lr_scheduler import MultiStepLR
from utils.tools import get_batch_label, get_prompt_text, CLASM

class FedAvgClient:
    def __init__(self,
                 model,
                 learning_rate: float,
                 train_loaders: tuple,
                 dataset: str,
                 local_epochs: int,
                 label_map,
                 scheduler_milestones,
                 scheduler_rate,
                 device: str,
                 ):
        super().__init__()
        self.model = copy.deepcopy(model)
        self.learning_rate = learning_rate
        self.train_loaders = train_loaders
        self.dataset = dataset
        self.local_epochs = local_epochs
        self.label_map = label_map
        self.device = device
        self.optimizer = torch.optim.AdamW(self.model.parameters(), lr=self.learning_rate)
        self.scheduler = MultiStepLR(self.optimizer, scheduler_milestones, scheduler_rate)

    def set_parameters(self, new_params):
        state_dict = self.model.state_dict()
        for key, value in new_params.items():
            state_dict[key] = value.data.clone()
        self.model.load_state_dict(state_dict)

    def get_global_parameters(self):
        new_parameters = OrderedDict()
        for name, p in self.model.named_parameters():
            if p.requires_grad:
                new_parameters[name] = p.data.clone()

        return new_parameters

    def train(self):
        self.model.train()
        prompt_text = get_prompt_text(self.label_map)

        if self.dataset == 'ucf':

            loss_total2 = 0

            for epoch in range(self.local_epochs):
                normal_iter = iter(self.train_loaders[0])
                anomaly_iter = iter(self.train_loaders[1])

                loss_per_epoch2 = 0

                iters = 0

                for i in range(min(len(self.train_loaders[0]), len(self.train_loaders[1]))):

                    normal_features, normal_label, normal_lengths = next(normal_iter)
                    anomaly_features, anomaly_label, anomaly_lengths = next(anomaly_iter)

                    visual_features = torch.cat([normal_features, anomaly_features], dim=0).to(self.device)

                    text_labels = list(normal_label) + list(anomaly_label)

                    feat_lengths = torch.cat([normal_lengths, anomaly_lengths], dim=0).to(self.device)

                    text_labels = get_batch_label(text_labels, prompt_text, self.label_map, self.dataset).to(
                        self.device)
                    logits = self.model(visual_features,
                                        prompt_text,
                                        feat_lengths)

                    loss2 = CLASM(logits, text_labels, feat_lengths, self.device)
                    loss_per_epoch2 += loss2.item()

                    loss = loss2

                    self.optimizer.zero_grad()
                    loss.backward()
                    self.optimizer.step()

                    iters += 1
                loss_total2 += loss_per_epoch2 / iters

            return (self.get_global_parameters(), loss_total2,
                    len(self.train_loaders[0]) + len(self.train_loaders[1]))
        elif self.dataset == 'me':

            loss_total2 = 0

            for epoch in range(self.local_epochs):
                normal_iter = iter(self.train_loaders[0])
                anomaly_iter = iter(self.train_loaders[1])

                loss_per_epoch2 = 0

                iters = 0

                for i in range(min(len(self.train_loaders[0]), len(self.train_loaders[1]))):

                    normal_features, normal_label, normal_lengths = next(normal_iter)
                    anomaly_features, anomaly_label, anomaly_lengths = next(anomaly_iter)

                    visual_features = torch.cat([normal_features, anomaly_features], dim=0).to(self.device)

                    text_labels = list(normal_label) + list(anomaly_label)

                    feat_lengths = torch.cat([normal_lengths, anomaly_lengths], dim=0).to(self.device)

                    text_labels = get_batch_label(text_labels, prompt_text, self.label_map, self.dataset).to(
                        self.device)
                    logits = self.model(visual_features,
                                        prompt_text,
                                        feat_lengths)

                    loss2 = CLASM(logits, text_labels, feat_lengths, self.device)
                    loss_per_epoch2 += loss2.item()

                    loss = loss2

                    self.optimizer.zero_grad()
                    loss.backward()
                    self.optimizer.step()

                    iters += 1
                loss_total2 += loss_per_epoch2 / iters

            return (self.get_global_parameters(), loss_total2,
                    len(self.train_loaders[0]) + len(self.train_loaders[1]))

        elif self.dataset == 'xd':

            loss_total2 = 0

            for epoch in range(self.local_epochs):

                loss_per_epoch2 = 0
                iters = 0

                for i, item in enumerate(self.train_loaders):

                    visual_feat, text_labels, feat_lengths = item
                    visual_feat = visual_feat.to(self.device)
                    feat_lengths = feat_lengths.to(self.device)

                    text_labels = get_batch_label(text_labels, prompt_text, self.label_map, self.dataset).to(
                        self.device)

                    logits = self.model(visual_feat,
                                        prompt_text,
                                        feat_lengths)

                    loss2 = CLASM(logits, text_labels, feat_lengths, self.device)
                    loss_per_epoch2 += loss2.item()

                    loss = loss2

                    self.optimizer.zero_grad()
                    loss.backward()
                    self.optimizer.step()

                    iters += 1

                loss_total2 += loss_per_epoch2 / iters

            return (self.get_global_parameters(), loss_total2,
                    len(self.train_loaders))