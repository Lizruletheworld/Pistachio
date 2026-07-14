import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import torch
import torch.utils.data as data
from torch.utils.data import DataLoader

# sys.path.append(os.path.dirname(__file__))
from utils.tools import process_feat, process_split

_METHOD_ROOT = Path(__file__).resolve().parents[1]
_REPO_ROOT = Path(__file__).resolve().parents[4]


def _pistachio_dataset_root():
    env_root = os.environ.get("PISTACHIO_DATASET_ROOT")
    candidates = []
    if env_root:
        candidates.append(Path(env_root).expanduser())
    candidates.extend([
        _REPO_ROOT.parent / "Pistachio_dataset",
        _REPO_ROOT / "Pistachio_dataset",
        Path.cwd() / "Pistachio_dataset",
        Path.cwd().parent / "Pistachio_dataset",
    ])
    for candidate in candidates:
        if (candidate / "VAD").exists():
            return candidate
    raise FileNotFoundError(
        "Cannot find Pistachio_dataset. Set PISTACHIO_DATASET_ROOT to the extracted dataset directory."
    )


def resolve_feature_path(path):
    feature_path = Path(path)
    if feature_path.is_absolute():
        return feature_path
    parts = feature_path.parts
    if parts and parts[0] == "Pistachio":
        return _pistachio_dataset_root() / Path(*parts[1:])
    return (_METHOD_ROOT / feature_path).resolve()



class UCFDataset(data.Dataset):
    def __init__(self, clip_dim: int, file_path: str, test_mode: bool, normal: bool = False):
        self.df = pd.read_csv(file_path)
        self.clip_dim = clip_dim
        self.test_mode = test_mode
        self.normal = normal
        if normal == True and test_mode == False:
            self.df = self.df.loc[self.df['label'] == 'Normal']
            self.df = self.df.reset_index()

        elif test_mode == False:
            self.df = self.df.loc[self.df['label'] != 'Normal']
            self.df = self.df.reset_index()

    def __len__(self):
        return self.df.shape[0]

    def __getitem__(self, index):
        clip_feature = np.load(resolve_feature_path(self.df.loc[index]['path']))
        if self.test_mode == False:
            clip_feature, clip_length = process_feat(clip_feature, self.clip_dim)
        else:
            clip_feature, clip_length = process_split(clip_feature, self.clip_dim)

        clip_feature = torch.tensor(clip_feature)
        clip_label = self.df.loc[index]['label']
        return clip_feature, clip_label, clip_length


class MEDataset(data.Dataset):
    def __init__(self, clip_dim: int, file_path: str, test_mode: bool, normal: bool = False):
        self.df = pd.read_csv(file_path)
        self.clip_dim = clip_dim
        self.test_mode = test_mode
        self.normal = normal
        if normal == True and test_mode == False:
            self.df = self.df.loc[self.df['label'] == 'Normal']
            self.df = self.df.reset_index()

        elif test_mode == False:
            self.df = self.df.loc[self.df['label'] != 'Normal']
            self.df = self.df.reset_index()

    def __len__(self):
        return self.df.shape[0]

    def __getitem__(self, index):
        clip_feature = np.load(resolve_feature_path(self.df.loc[index]['path']))
        if self.test_mode == False:
            clip_feature, clip_length = process_feat(clip_feature, self.clip_dim)
        else:
            clip_feature, clip_length = process_split(clip_feature, self.clip_dim)

        clip_feature = torch.tensor(clip_feature)
        clip_label = self.df.loc[index]['label']
        return clip_feature, clip_label, clip_length


class XDDataset(data.Dataset):
    def __init__(self, clip_dim: int, file_path: str, test_mode: bool):
        self.df = pd.read_csv(file_path)
        self.clip_dim = clip_dim
        self.test_mode = test_mode

    def __len__(self):
        return self.df.shape[0]

    def __getitem__(self, index):
        clip_feature = np.load(resolve_feature_path(self.df.loc[index]['path']))
        if not self.test_mode:
            clip_feature, clip_length = process_feat(clip_feature, self.clip_dim)
        else:
            clip_feature, clip_length = process_split(clip_feature, self.clip_dim)

        clip_feature = torch.tensor(clip_feature)
        clip_label = self.df.loc[index]['label']
        return clip_feature, clip_label, clip_length

def make_me_dataloader(split_mode: str, clients_num: int, batch_size: int, visual_length: int):
    split_list = []
    if split_mode == "event":
        clients_num = 32
        split_list = [
            'animal_abuse', 
            'animal_attack_or_fight', 
            'animal_fall_and_injury', 
            'animal_fight', 
            'animal_predation', 
            'avalanche', 
            'construction_accident', 
            'equipment_breakdown', 
            'explosion', 
            'extreme_weather_events', 
            'falling_object_and_collapse', 
            'fighting_and_physical_conflict', 
            'fire', 
            'ground_collapse', 
            'infrastructure_failure', 
            'landslide', 
            'leakage', 
            'medical_emergency', 
            'natural_disasters', 
            'person_drowning', 
            'pushing_conflict', 
            'robbery', 
            'safety_violations', 
            'slip_and_fall_accident', 
            'structural_failure', 
            'sudden_illness_and_seizure', 
            'sudden_illness_seizure', 
            'theft', 
            'traffic_accident', 
            'vandalism', 
            'weapons_incident',
            'wild_large_animal_intrusion']
    elif split_mode == "scene":
        split_list = ['commercial', 'indoor', 'outdoor', 'road', 'industrial', 'infrastructure']
        clients_num = 6

    elif split_mode == "random":
        split_list = [f'{clients_num}_{i}' for i in range(clients_num)]

    train_loaders = []
    for i in range(clients_num):
        train_list = f"./data/list/me_{split_mode}/me_{split_list[i]}.csv"
        
        # 正常样本加载器
        normal_dataset = MEDataset(visual_length, train_list, False, True)
        # 🚩 修改 1: drop_last 改为 False (保证即使只有 1 条数据也能读出来)
        # 🚩 修改 2: batch_size 通常建议 // 2，因为 zip 会把正常和异常拼起来，总数就是 batch_size
        normal_dataloader = DataLoader(normal_dataset, batch_size=batch_size // 2, shuffle=True, drop_last=False)

        # 异常样本加载器
        anomaly_dataset = MEDataset(visual_length, train_list, False, False)
        # 🚩 修改 3: 同上，drop_last 改为 False
        anomaly_loader = DataLoader(anomaly_dataset, batch_size=batch_size // 2, shuffle=True, drop_last=False)

        train_loader = (normal_dataloader, anomaly_loader)
        train_loaders.append(train_loader)

    test_list = './data/list/me_test.csv'
    test_dataset = MEDataset(visual_length, test_list, True)
    test_loader = DataLoader(test_dataset, batch_size=1, shuffle=False)

    return train_loaders, test_loader



def make_ucf_dataloader(split_mode: str, clients_num: int, batch_size: int, visual_length: int):
    split_list = []
    if split_mode == "event":
        clients_num = 13
        split_list = ['Abuse', 'Arrest', 'Arson', 'Assault', 'Burglary', 'Explosion', 'Fighting', 'RoadAccidents',
                      'Robbery', 'Shooting', 'Shoplifting', 'Stealing', 'Vandalism']
    elif split_mode == "scene":
        split_list = ['Street', 'Store', 'Office', 'Parking lot', 'Room',
                      'Restaurant', 'Bank', 'Factory', 'Gas station']
        clients_num = 9

    elif split_mode == "random":
        split_list = [f'{clients_num}_{i}' for i in range(clients_num)]

    train_loaders = []
    for i in range(clients_num):
        train_list = f"./data/list/ucf_{split_mode}/ucf_{split_list[i]}.csv"
        normal_dataset = UCFDataset(visual_length, train_list, False, True)
        normal_dataloader = DataLoader(normal_dataset, batch_size=batch_size, shuffle=True, drop_last=True)

        anomaly_dataset = UCFDataset(visual_length, train_list, False, False)
        anomaly_loader = DataLoader(anomaly_dataset, batch_size=batch_size, shuffle=True, drop_last=True)

        train_loader = (normal_dataloader, anomaly_loader)
        train_loaders.append(train_loader)

    test_list = './data/list/ucf_test.csv'
    test_dataset = UCFDataset(visual_length, test_list, True)
    test_loader = DataLoader(test_dataset, batch_size=1, shuffle=False)

    return train_loaders, test_loader


def make_xd_dataloader(split_mode: str, clients_num: int, batch_size: int, visual_length: int):
    split_list = []
    if split_mode == "event":
        clients_num = 6
        split_list = ['Fighting', 'Riot', 'Abuse', 'Shooting', 'Explosion', 'Car accident']

    elif split_mode == "scene":
        split_list = ['Street', 'Park', 'Sports', 'Highway', 'Living room', 'Wild', 'Factory',
                      'Mall and Store', 'Office', 'Theater', 'Restaurant', 'Vehicle', 'Classroom']
        clients_num = 13

    elif split_mode == "random":
        split_list = [f'{clients_num}_{i}' for i in range(clients_num)]

    train_loaders = []
    for i in range(clients_num):
        train_list = f"./data/list/xd_{split_mode}/xd_{split_list[i]}.csv"
        train_dataset = XDDataset(visual_length, train_list, False)
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        train_loaders.append(train_loader)

    test_list = './data/list/xd_test.csv'
    test_dataset = XDDataset(visual_length, test_list, True)
    test_loader = DataLoader(test_dataset, batch_size=1, shuffle=False)
    return train_loaders, test_loader
