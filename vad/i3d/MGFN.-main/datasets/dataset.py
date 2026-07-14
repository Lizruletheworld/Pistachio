import torch.utils.data as data
import numpy as np
from utils.utils import process_feat
import torch
import os
from pathlib import Path
torch.set_default_tensor_type('torch.FloatTensor')
import option
args=option.parse_args()




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
    path = Path(raw_path.strip())

    if path.is_absolute():
        if path.exists():
            return str(path)
        current = path.as_posix()
        legacy_prefix = LEGACY_DATASET_ROOT.as_posix()
        if current.startswith(legacy_prefix):
            suffix = current[len(legacy_prefix):].lstrip('/')
            return str(dataset_root / suffix)
        return str(path)

    current = path.as_posix()
    if current.startswith('Pistachio/VAD/'):
        return str(dataset_root / current.split('Pistachio/', 1)[1])
    if current.startswith('VAD/'):
        return str(dataset_root / current)
    return str(path)



class Dataset(data.Dataset):
    def __init__(self, args, is_normal=True, transform=None, test_mode=False, is_preprocessed=False):
        self.modality = args.modality
        self.is_normal = is_normal
        if test_mode:
            self.rgb_list_file = args.test_rgb_list
        else:
            self.rgb_list_file = args.rgb_list
        self.tranform = transform
        self.test_mode = test_mode
        self._parse_list()
        self.num_frame = 0
        self.labels = None
        self.is_preprocessed = args.preprocessed

    def _parse_list(self):
        with open(self.rgb_list_file, 'r') as handle:
            self.list = [_resolve_feature_path(line) for line in handle if line.strip()]
        if self.test_mode is False:
            if args.datasetname == 'UCF':
                if self.is_normal:
                    self.list = self.list[810:]#ucf 810; sht63; xd 9525
                    print('normal list')
                    print(self.list)
                else:
                    self.list = self.list[:810]#ucf 810; sht 63; 9525
                    print('abnormal list')
                    print(self.list)
            elif args.datasetname == 'XD':
                if self.is_normal:
                    self.list = self.list[9525:]
                    print('normal list')
                    print(self.list)
                else:
                    self.list = self.list[:9525]
                    print('abnormal list')
                    print(self.list)
            elif args.datasetname.lower() == 'pistachio':
                if self.is_normal:
                    self.list = self.list[1158:]
                    print('normal list')
                    print(self.list[:5])
                else:
                    self.list = self.list[:1158]
                    print('abnormal list')
                    print(self.list[:5])



    def __getitem__(self, index):
        label = self.get_label(index)  # get video level label 0/1
        if args.datasetname in ['UCF', 'pistachio']:
            features = np.load(self.list[index].strip('\n'), allow_pickle=True)
            features = np.array(features, dtype=np.float32)
            name = self.list[index].split('/')[-1].strip('\n')[:-4]
        elif args.datasetname == 'XD':
            features = np.load(self.list[index].strip('\n'), allow_pickle=True)
            features = np.array(features, dtype=np.float32)
            name = self.list[index].split('/')[-1].strip('\n')[:-4]
        if self.tranform is not None:
            features = self.tranform(features)
        if self.test_mode:
            if args.datasetname in ['UCF', 'pistachio']:
                mag = np.linalg.norm(features, axis=2)[:,:, np.newaxis]
                features = np.concatenate((features,mag),axis = 2)
            elif args.datasetname == 'XD':
                mag = np.linalg.norm(features, axis=1)[:, np.newaxis]
                features = np.concatenate((features, mag), axis=1)
            return features, name
        else:
            if args.datasetname in ['UCF', 'pistachio']:
                if self.is_preprocessed:
                    return features, label
                features = features.transpose(1, 0, 2)  # [10, T, F]
                divided_features = []

                divided_mag = []
                for feature in features:
                    feature = process_feat(feature, args.seg_length) #ucf(32,2048)
                    divided_features.append(feature)
                    divided_mag.append(np.linalg.norm(feature, axis=1)[:, np.newaxis])
                divided_features = np.array(divided_features, dtype=np.float32)
                divided_mag = np.array(divided_mag, dtype=np.float32)
                divided_features = np.concatenate((divided_features,divided_mag),axis = 2)
                return divided_features, label

            elif args.datasetname == 'XD':
                feature = process_feat(features, 32)
                if args.add_mag_info == True:
                    feature_mag = np.linalg.norm(feature, axis=1)[:, np.newaxis]
                    feature = np.concatenate((feature,feature_mag),axis = 1)
                return feature, label


    def get_label(self, index):
        if self.is_normal:
            # label[0] = 1
            label = torch.tensor(0.0)
        else:
            label = torch.tensor(1.0)
            # label[1] = 1
        return label

    def __len__(self):

        return len(self.list)


    def get_num_frames(self):
        return self.num_frame
