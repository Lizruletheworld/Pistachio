import os
import random

import numpy as np
import torch


def process_feat(feat, length, is_random=False):
    new_feat = np.zeros((length, feat.shape[1])).astype(np.float32)
    r = np.linspace(0, len(feat), length + 1, dtype=np.int32)
    for i in range(length):
        if r[i] != r[i + 1]:
            new_feat[i, :] = np.mean(feat[r[i]:r[i + 1], :], 0)
        else:
            idx = min(r[i], len(feat) - 1)
            new_feat[i, :] = feat[idx, :]
    return new_feat


def random_perturb(length, num_segments):
    if length <= num_segments:
        return np.linspace(0, length - 1, num_segments, dtype=np.int32)
    return np.sort(np.random.choice(length, num_segments, replace=False))


def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def save_best_record(test_info, file_path):
    os.makedirs(os.path.dirname(file_path) or '.', exist_ok=True)
    with open(file_path, 'w') as handle:
        for key, values in test_info.items():
            handle.write(f'{key}: {values}\n')


class Visualizer:
    def __init__(self, *args, **kwargs):
        pass

    def plot_lines(self, *args, **kwargs):
        pass

    def lines(self, *args, **kwargs):
        pass
