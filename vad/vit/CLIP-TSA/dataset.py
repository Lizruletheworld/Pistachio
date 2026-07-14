import torch.utils.data as data
import numpy as np
from utils.utils import process_feat
import torch
from torch.utils.data import DataLoader
import os
# torch.set_default_tensor_type('torch.cuda.FloatTensor')

from pathlib import Path
import pickle



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
    def __init__(self, args, is_normal=True, transform=None, test_mode=False, normal_only=False):
        self.is_normal = is_normal
        self.dataset = args.dataset
        self.args = args
        self.dataset_root = _find_dataset_root()

        if self.dataset in ['shanghai', "sh"]:
            if test_mode:
                self.rgb_list_file = f'list/{args.visual.lower()}/shanghai-{args.visual}-test-10crop.list'
                ds = "sh_test"
            else:
                self.rgb_list_file = f'list/{args.visual.lower()}/shanghai-{args.visual}-train-10crop.list'
                ds = "sh_train"
        elif self.dataset == "ucf":
            if test_mode:
                self.rgb_list_file = f'list/{args.visual.lower()}/ucf-{args.visual}-test.list'
                ds = "ucf_test"
            else:
                self.rgb_list_file = f'list/{args.visual.lower()}/ucf-{args.visual}.list'
                ds = "ucf_train"
        elif self.dataset == "xd":
            if test_mode:
                self.rgb_list_file = f'list/{args.visual.lower()}/xd-{args.visual}-test.list'
                ds = "xd_test"
            else:
                self.rgb_list_file = f'list/{args.visual.lower()}/xd-{args.visual}-train.list'
                ds = "xd_train"
        elif self.dataset == "pistachio":
            if test_mode:
                self.rgb_list_file = f'list/{args.visual.lower()}/pistachio-{args.visual}-test.list'
                ds = "pistachio_test"
            else:
                self.rgb_list_file = f'list/{args.visual.lower()}/pistachio-{args.visual}.list'
                ds = "pistachio_train"
        elif self.dataset == "pistachio_i3d":
            if test_mode:
                self.rgb_list_file = f'list/{args.visual.lower()}/pistachio_i3d-{args.visual}-test.list'
                ds = "pistachio_i3d_test"
            else:
                self.rgb_list_file = f'list/{args.visual.lower()}/pistachio_i3d-{args.visual}.list'
                ds = "pistachio_i3d_train"
        else:
            raise SystemError("Check main.py --dataset")

        if not Path(self.rgb_list_file).is_absolute():
            self.rgb_list_file = str((Path(__file__).resolve().parent / self.rgb_list_file).resolve())

        self.tranform = transform
        self.test_mode = test_mode
        self._parse_list()
        self.num_frame = 0
        self.labels = None

        self.file_management = {
            "sh": 63,
            "shanghai": 63,
            "ucf": 8100,
            "pistachio":11580,
            "pistachio_i3d":1158,
            "xd": 19050
        }

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
            if self.dataset in ["sh", 'shanghai']:
                if self.is_normal:
                    self.list = self.list[63:]
                    assert len(self.list) == 175
                    # print(self.list)
                else:
                    self.list = self.list[:63]
                    assert len(self.list) == 63
                    # print(self.list)

            elif self.dataset == 'ucf':
                if self.is_normal:
                    self.list = self.list[8100:]
                    assert len(self.list) == 8000
                    # print(self.list)
                else:
                    self.list = self.list[:8100]
                    assert len(self.list) == 8100
                    # print(self.list)

            elif self.dataset == 'xd':
                if self.is_normal:
                    self.list = self.list[19050:]
                    print(len(self.list))
                    assert len(self.list) == 20480

                else:
                    self.list = self.list[:19050]
                    assert len(self.list) == 19050
            elif self.dataset == 'pistachio':
                if self.is_normal:
                    self.list = self.list[11580:]
                    print(len(self.list))
                    if not self.list:
                        raise RuntimeError('Empty normal split for Pistachio.')
                    # print(self.list)
                else:
                    self.list = self.list[:11580]
                    print(len(self.list))
                    if not self.list:
                        raise RuntimeError('Empty anomaly split for Pistachio.')
                    # print(self.list)
            elif self.dataset == 'pistachio_i3d':
                if self.is_normal:
                    self.list = self.list[1158:]
                    print(len(self.list))
                    if not self.list:
                        raise RuntimeError('Empty normal split for Pistachio I3D.')
                    # print(self.list)
                else:
                    self.list = self.list[:1158]
                    print(len(self.list))
                    if not self.list:
                        raise RuntimeError('Empty anomaly split for Pistachio I3D.')
                    # print(self.list)

    def __getitem__(self, index):
        path = self.list[index].strip('\n')

        label = self.get_label()  # get video level label 0/1

        features = np.load(path, allow_pickle=True)
        features = np.array(features, dtype=np.float32)

        # Instead of 10-crop snippet feature, let one image represent all
        # If it enters, it doesn't do tencrop
        if self.args.visual.lower() not in ["i3d", "c3d"] and len(features.shape) != 3:
            features = features.reshape((*features.shape[:-1],1,features.shape[-1]))

        if self.tranform is not None:
            features = self.tranform(features)
        if self.test_mode:
            return features
        else:
            # currently: (31, 10, 2048)
            # process 10-cropped snippet feature
            features = features.transpose(1, 0, 2)  # [10, B, T, F] -> (10, 31, 2048)
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
        
