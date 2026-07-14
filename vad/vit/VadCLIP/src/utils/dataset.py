import numpy as np
import torch
import torch.utils.data as data
import pandas as pd
import utils.tools as tools
import os
from pathlib import Path




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
def _resolve_feature_path(raw_path: str) -> str:
    dataset_root = _find_dataset_root()
    path = Path(raw_path)

    if path.is_absolute():
        return str(path)

    current = path.as_posix()
    if current.startswith('Pistachio/VAD/'):
        return str(dataset_root / current.split('Pistachio/', 1)[1])
    if current.startswith('Pistachio_dataset/'):
        return str(dataset_root.parent / current)
    if current.startswith('VAD/'):
        return str(dataset_root / current)
    return str(path.resolve())


def _build_dataframe(file_path: str, label_map: dict) -> pd.DataFrame:
    suffix = Path(file_path).suffix.lower()
    if suffix == '.csv':
        df = pd.read_csv(file_path)
        if 'path' in df.columns:
            df['path'] = df['path'].apply(_resolve_feature_path)
        return df

    normalized_labels = {key.lower(): key for key in label_map if key != 'Normal'}
    records = []
    with open(file_path, 'r') as handle:
        for line in handle:
            raw_path = line.strip()
            if not raw_path:
                continue

            resolved_path = _resolve_feature_path(raw_path)
            parts = [part.lower() for part in Path(resolved_path).as_posix().split('/')]
            if 'normal' in parts:
                label = 'Normal'
            else:
                label = 'Normal'
                for part in parts:
                    if part in normalized_labels:
                        label = normalized_labels[part]
                        break
            records.append({'path': resolved_path, 'label': label})
    return pd.DataFrame(records)

class UCFDataset(data.Dataset):
    def __init__(self, clip_dim: int, file_path: str, test_mode: bool, label_map: dict, normal: bool = False):
        self.df = _build_dataframe(file_path, label_map)
        self.clip_dim = clip_dim
        self.test_mode = test_mode
        self.label_map = label_map
        self.normal = normal
        if normal == True and test_mode == False:
            self.df = self.df.loc[self.df['label'] == 'Normal']
            self.df = self.df.reset_index(drop=True)
        elif test_mode == False:
            self.df = self.df.loc[self.df['label'] != 'Normal']
            self.df = self.df.reset_index(drop=True)
        
    def __len__(self):
        return self.df.shape[0]

    def __getitem__(self, index):
        clip_feature = np.load(self.df.loc[index]['path'])
        if self.test_mode == False:
            clip_feature, clip_length = tools.process_feat(clip_feature, self.clip_dim)
        else:
            clip_feature, clip_length = tools.process_split(clip_feature, self.clip_dim)

        clip_feature = torch.tensor(clip_feature)
        clip_label = self.df.loc[index]['label']
        return clip_feature, clip_label, clip_length

class PistachioDataset(data.Dataset):
    def __init__(self, clip_dim: int, file_path: str, test_mode: bool, label_map: dict, normal: bool = False):
        self.df = _build_dataframe(file_path, label_map)
        self.clip_dim = clip_dim
        self.test_mode = test_mode
        self.label_map = label_map
        self.normal = normal
        if normal == True and test_mode == False:
            self.df = self.df.loc[self.df['label'] == 'Normal']
            self.df = self.df.reset_index(drop=True)
        elif test_mode == False:
            self.df = self.df.loc[self.df['label'] != 'Normal']
            self.df = self.df.reset_index(drop=True)
        
    def __len__(self):
        return self.df.shape[0]

    def __getitem__(self, index):
        clip_feature = np.load(self.df.loc[index]['path'])
        if self.test_mode == False:
            clip_feature, clip_length = tools.process_feat(clip_feature, self.clip_dim)
        else:
            clip_feature, clip_length = tools.process_split(clip_feature, self.clip_dim)

        clip_feature = torch.tensor(clip_feature)
        clip_label = self.df.loc[index]['label']
        return clip_feature, clip_label, clip_length

class XDDataset(data.Dataset):
    def __init__(self, clip_dim: int, file_path: str, test_mode: bool, label_map: dict):
        self.df = _build_dataframe(file_path, label_map)
        self.clip_dim = clip_dim
        self.test_mode = test_mode
        self.label_map = label_map
        
    def __len__(self):
        return self.df.shape[0]

    def __getitem__(self, index):
        clip_feature = np.load(self.df.loc[index]['path'])
        if self.test_mode == False:
            clip_feature, clip_length = tools.process_feat(clip_feature, self.clip_dim)
        else:
            clip_feature, clip_length = tools.process_split(clip_feature, self.clip_dim)

        clip_feature = torch.tensor(clip_feature)
        clip_label = self.df.loc[index]['label']
        return clip_feature, clip_label, clip_length
