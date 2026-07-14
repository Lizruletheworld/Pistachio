import torch.utils.data as data
import numpy as np
from utils import process_feat
import torch
from torch.utils.data import DataLoader
import os
from pathlib import Path
torch.set_default_tensor_type('torch.FloatTensor')




def _find_dataset_root() -> Path:
    candidates = []
    env_root = os.getenv('PISTACHIO_DATASET_ROOT')
    if env_root:
        candidates.append(Path(env_root).expanduser())

    env_repo_root = os.getenv('PISTACHIO_ROOT')
    if env_repo_root:
        candidates.append(Path(env_repo_root).expanduser() / 'Pistachio_dataset')

    file_path = Path(__file__).resolve()
    for parent in file_path.parents:
        candidates.append(parent / 'Pistachio_dataset')

    for candidate in candidates:
        if candidate.exists():
            return candidate

    if candidates:
        return candidates[0]
    return Path('Pistachio_dataset')
class Dataset(data.Dataset):
    def __init__(self, args, is_normal=True, transform=None, test_mode=False):
        self.modality = args.modality
        self.is_normal = is_normal
        self.dataset = args.dataset
        self.dataset_root = _find_dataset_root()
        if self.dataset == 'shanghai':
            if test_mode:
                self.rgb_list_file = 'list/shanghai-i3d-test-10crop.list'
            else:
                self.rgb_list_file = 'list/shanghai-i3d-train-10crop.list'
        else:
            if test_mode:
                self.rgb_list_file = args.test_rgb_list
            else:
                self.rgb_list_file = args.rgb_list

        self.tranform = transform
        self.test_mode = test_mode
        self._parse_list()
        self.num_frame = 0
        self.labels = None

    def _resolve_feature_path(self, raw_path):
        path_str = raw_path.strip()
        if not path_str:
            return path_str

        path = Path(path_str)
        if path.is_absolute():
            return str(path)

        current = path.as_posix()
        if current.startswith('Pistachio/VAD/'):
            return str(self.dataset_root / current.split('Pistachio/', 1)[1])
        if current.startswith('Pistachio_dataset/'):
            return str(self.dataset_root.parent / current)
        if current.startswith('VAD/'):
            return str(self.dataset_root / current)

        return str((Path(self.rgb_list_file).resolve().parent / path).resolve())

    def _parse_list(self):
        with open(self.rgb_list_file, 'r') as handle:
            self.list = [self._resolve_feature_path(line) for line in handle if line.strip()]

        if self.test_mode is False:
            if self.dataset == 'shanghai':
                if self.is_normal:
                    self.list = self.list[63:]
                    print('normal list for shanghai tech')
                    print(self.list)
                else:
                    self.list = self.list[:63]
                    print('abnormal list for shanghai tech')
                    print(self.list)

            elif self.dataset == 'ucf':
                if self.is_normal:
                    self.list = self.list[810:]
                    print('normal list for ucf')
                    print(self.list)
                else:
                    self.list = self.list[:810]
                    print('abnormal list for ucf')
                    print(self.list)
            elif self.dataset == 'pistachio':
                if self.is_normal:
                    self.list = [item for item in self.list if '/normal/' in item.replace('\\', '/')]
                else:
                    self.list = [item for item in self.list if '/anomaly/' in item.replace('\\', '/')]
            

    def __getitem__(self, index):

        label = self.get_label()  # get video level label 0/1
        features = np.load(self.list[index].strip('\n'), allow_pickle=True)
        features = np.array(features, dtype=np.float32)

        if self.tranform is not None:
            features = self.tranform(features)
        if self.test_mode:
            return features
        else:
            # process 10-cropped snippet feature
            features = features.transpose(1, 0, 2)  # [10, B, T, F]
            divided_features = []
            for feature in features:
                feature = process_feat(feature, 32)  # divide a video into 32 segments
                divided_features.append(feature)
            divided_features = np.array(divided_features, dtype=np.float32)

            return divided_features, label

    def get_label(self):

        if self.is_normal:
            label = torch.tensor(0.0)
        else:
            label = torch.tensor(1.0)

        return label

    def __len__(self):
        return len(self.list)

    def get_num_frames(self):
        return self.num_frame
