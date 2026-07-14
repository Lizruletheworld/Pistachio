import torch
import torch.utils.data as data
import os
import numpy as np
import utils 
from pathlib import Path


_METHOD_ROOT = Path(__file__).resolve().parent


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
def _resolve_pistachio_path(path_str: str) -> str:
    dataset_root = _find_dataset_root()
    path = Path(path_str)

    if path.is_absolute():
        return str(path)

    current = path.as_posix()
    if current.startswith('Pistachio/VAD/'):
        return str(dataset_root / current.split('Pistachio/', 1)[1])
    if current.startswith('Pistachio_dataset/'):
        return str(dataset_root.parent / current)
    if current.startswith('VAD/'):
        return str(dataset_root / current)
    return str(path)


class UCF_crime(data.DataLoader):
    def __init__(self, root_dir, modal, mode, num_segments, len_feature, seed=-1, is_normal=None):
        if seed >= 0:
            utils.set_seed(seed)
        self.mode = mode
        self.modal = modal
        self.num_segments = num_segments
        self.len_feature = len_feature
        split_path = os.path.join('list','UCF_{}.list'.format(self.mode))
        split_file = open(split_path, 'r')
        self.vid_list = []
        for line in split_file:
            self.vid_list.append(line.split())
        split_file.close()
        if self.mode == "Train":
            if is_normal is True:
                self.vid_list = self.vid_list[8100:]
            elif is_normal is False:
                self.vid_list = self.vid_list[:8100]
            else:
                assert (is_normal == None)
                print("Please sure is_normal=[True/False]")
                self.vid_list=[]
    def __len__(self):
        return len(self.vid_list)

    def __getitem__(self, index):
        
        if self.mode == "Test":
            data,label,name = self.get_data(index)
            return data,label,name
        else:
            data,label = self.get_data(index)
            return data,label

    def get_data(self, index):
        vid_info = self.vid_list[index][0]  
        name = vid_info.split("/")[-1].split("_x264")[0]
        video_feature = np.load(vid_info).astype(np.float32)   

        if "Normal" in vid_info.split("/")[-1]:
            label = 0
        else:
            label = 1
        if self.mode == "Train":
            new_feat = np.zeros((self.num_segments, video_feature.shape[1])).astype(np.float32)
            r = np.linspace(0, len(video_feature), self.num_segments + 1, dtype = np.int)
            for i in range(self.num_segments):
                if r[i] != r[i+1]:
                    new_feat[i,:] = np.mean(video_feature[r[i]:r[i+1],:], 0)
                else:
                    new_feat[i:i+1,:] = video_feature[r[i]:r[i]+1,:]
            video_feature = new_feat
        if self.mode == "Test":
            return video_feature, label, name      
        else:
            return video_feature, label      

class XDVideo(data.DataLoader):
    def __init__(self, root_dir, mode, modal, num_segments, len_feature, seed=-1, is_normal=None):
        if seed >= 0:
            utils.set_seed(seed)
        self.data_path=root_dir
        self.mode=mode
        self.modal=modal
        self.num_segments = num_segments
        self.len_feature = len_feature
        if self.modal == 'all':
            self.feature_path = []
            if self.mode == "Train":
                for _modal in ['RGB', 'Flow']:
                    self.feature_path.append(os.path.join(self.data_path, "i3d-features",_modal))
            else:
                for _modal in ['RGBTest', 'FlowTest']:
                    self.feature_path.append(os.path.join(self.data_path, "i3d-features",_modal))
        else:
            self.feature_path = os.path.join(self.data_path, modal)
        split_path = os.path.join("list",'XD_{}.list'.format(self.mode))
        split_file = open(split_path, 'r',encoding="utf-8")
        self.vid_list = []
        for line in split_file:
            self.vid_list.append(line.split())
        split_file.close()
        if self.mode == "Train":
            if is_normal is True:
                self.vid_list = self.vid_list[9525:]
            elif is_normal is False:
                self.vid_list = self.vid_list[:9525]
            else:
                assert (is_normal == None)
                print("Please sure is_normal = [True/False]")
                self.vid_list=[]
        
    def __len__(self):
        return len(self.vid_list)

    def __getitem__(self, index):
        data,label = self.get_data(index)
        return data, label

    def get_data(self, index):
        vid_name = self.vid_list[index][0]
        label=0
        if "_label_A" not in vid_name:
            label=1  
        video_feature = np.load(os.path.join(self.feature_path[0],
                                vid_name )).astype(np.float32)
        if self.mode == "Train":
            new_feature = np.zeros((self.num_segments,self.len_feature)).astype(np.float32)
            sample_index = utils.random_perturb(video_feature.shape[0],self.num_segments)
            for i in range(len(sample_index)-1):
                if sample_index[i] == sample_index[i+1]:
                    new_feature[i,:] = video_feature[sample_index[i],:]
                else:
                    new_feature[i,:] = video_feature[sample_index[i]:sample_index[i+1],:].mean(0)
                    
            video_feature = new_feature
        return video_feature, label    


class Pistachio(data.DataLoader):
    def __init__(self, root_dir, modal, mode, num_segments, len_feature, seed=-1, is_normal=None):
        if seed >= 0:
            utils.set_seed(seed)
        self.mode = mode
        self.modal = modal
        self.num_segments = num_segments
        self.len_feature = len_feature
        
        if self.mode == 'Train':
            split_path = _METHOD_ROOT / 'list' / 'pistachio_Train.list'
        else:
            split_path = _METHOD_ROOT / 'list' / 'pistachio_Test.list'
        split_file = open(split_path, 'r')
        self.vid_list = []
        for line in split_file:
            self.vid_list.append(line.split())
        split_file.close()
        
        # Filter training data based on is_normal parameter
        if self.mode == "Train":
            if is_normal is True:
                original_size = len(self.vid_list)
                self.vid_list = [item for item in self.vid_list if self.is_normal_video(item[0])]
                print(f"Filtered normal samples: {len(self.vid_list)}/{original_size}")
            elif is_normal is False:
                original_size = len(self.vid_list)
                self.vid_list = [item for item in self.vid_list if not self.is_normal_video(item[0])]
                print(f"Filtered anomaly samples: {len(self.vid_list)}/{original_size}")
            else:
                assert (is_normal == None)
                print("Please sure is_normal=[True/False]")
                self.vid_list = []
        
        # Check final dataset size
        if len(self.vid_list) == 0:
            print(f"Warning: {mode} dataset is empty after filtering!")
            print(f"is_normal parameter: {is_normal}")
        
        # Count normal and anomaly samples
        normal_count = sum(1 for item in self.vid_list if self.is_normal_video(item[0]))
        anomaly_count = len(self.vid_list) - normal_count
        print(f"Total samples: {len(self.vid_list)}, Normal: {normal_count}, Anomaly: {anomaly_count}")

    def __len__(self):
        return len(self.vid_list)

    def __getitem__(self, index):
        if self.mode == "Test":
            data, label, name = self.get_data(index)
            return data, label, name
        else:
            data, label = self.get_data(index)
            return data, label

    def get_data(self, index):
        vid_info = self.vid_list[index][0]  
        name = self.parse_video_name(vid_info)
        video_feature = np.load(_resolve_pistachio_path(vid_info)).astype(np.float32)  

        # Step 1: Handle 10-crop averaging
        # Check if features are 3D (T, C, D) and average across crop dimension
        if video_feature.ndim == 3:
            # axis=1 is the 'C' (crop) dimension
            video_feature = np.mean(video_feature, axis=1) 
        
        # Now video_feature.shape should be (T, D) e.g., (40, 2048)

        # Step 2: Get label
        label = self.get_label(vid_info)
        
        # Step 3: Temporal resampling for both Train and Test modes
        # This ensures output always has self.num_segments segments
        original_num_segments = video_feature.shape[0]  # T
        target_num_segments = self.num_segments  # e.g., 200 (Train) or 10 (Test)
        
        # video_feature.shape[1] is now the feature dimension (e.g., 2048)
        new_feat = np.zeros((target_num_segments, video_feature.shape[1])).astype(np.float32)
        
        r = np.linspace(0, original_num_segments, target_num_segments + 1, dtype=int)
        
        for i in range(target_num_segments):
            if r[i] != r[i+1]:
                # Average pooling
                new_feat[i,:] = np.mean(video_feature[r[i]:r[i+1],:], 0)
            else:
                # Copy sampling (when T < target_num_segments)
                # Ensure r[i] doesn't go out of bounds
                idx = min(r[i], original_num_segments - 1)
                new_feat[i,:] = video_feature[idx, :]
                
        video_feature = new_feat  # Now shape is (target_num_segments, 2048)
        
        # Step 4: Return based on mode
        if self.mode == "Test":
            return video_feature, label, name       
        else:  # Train mode
            return video_feature, label

    def is_normal_video(self, video_path):
        """Determine if video is normal based on Pistachio dataset rules"""
        path_parts = Path(video_path).as_posix().split('/')
        lowered = [part.lower() for part in path_parts]
        if 'normal' in lowered:
            return True
        if 'anomaly' in lowered:
            return False
        return False

    def parse_video_name(self, video_path):
        """Parse video name from Pistachio dataset path"""
        # Extract filename without extension
        file_name = os.path.basename(video_path)
        if file_name.endswith('.npy'):
            file_name = file_name[:-4]
        return file_name

    def get_label(self, video_path):
        """Get label for Pistachio dataset"""
        if self.is_normal_video(video_path):
            return 0  # Normal video
        else:
            return 1  # Anomaly video
