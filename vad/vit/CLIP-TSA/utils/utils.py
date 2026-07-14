import os

import numpy as np
import torch


def process_feat(feat, length):
    if isinstance(feat, torch.Tensor):
        new_feat = torch.zeros((length, feat.shape[1]), dtype=torch.float32, device=feat.device)
        r = torch.linspace(0, len(feat), length + 1, dtype=torch.int64, device=feat.device)
        for i in range(length):
            if r[i] != r[i + 1]:
                new_feat[i, :] = torch.mean(feat[r[i]:r[i + 1], :], 0)
            else:
                idx = min(int(r[i].item()), len(feat) - 1)
                new_feat[i, :] = feat[idx, :]
        return new_feat

    new_feat = np.zeros((length, feat.shape[1])).astype(np.float32)
    r = np.linspace(0, len(feat), length + 1, dtype=np.int32)
    for i in range(length):
        if r[i] != r[i + 1]:
            new_feat[i, :] = np.mean(feat[r[i]:r[i + 1], :], 0)
        else:
            idx = min(r[i], len(feat) - 1)
            new_feat[i, :] = feat[idx, :]
    return new_feat


def save_best_record(test_info, file_path):
    os.makedirs(os.path.dirname(file_path) or '.', exist_ok=True)
    with open(file_path, 'w') as handle:
        if 'epoch' in test_info and test_info['epoch']:
            handle.write('epoch: {}\n'.format(test_info['epoch'][-1]))
        if 'test_AUC' in test_info and test_info['test_AUC']:
            handle.write(str(test_info['test_AUC'][-1]))
