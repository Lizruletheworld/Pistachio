import argparse
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
_METHOD_ROOT = Path(__file__).resolve().parent
_I3D_ROOT = _METHOD_ROOT.parent
_DATASET_ROOT = _find_dataset_root()


def _find_clip_tsa_i3d_list_root() -> Path:
    candidates = [
        _METHOD_ROOT / 'list' / 'i3d',
        _I3D_ROOT / 'CLIP-TSA-i3d' / 'list' / 'i3d',
        _I3D_ROOT / 'CLIP-TSA' / 'list' / 'i3d',
        _METHOD_ROOT.parent / 'CLIP-TSA' / 'list' / 'i3d',
        _METHOD_ROOT.parent / 'CLIP-TSA-i3d' / 'list' / 'i3d',
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


_CLIP_TSA_I3D_LIST_ROOT = _find_clip_tsa_i3d_list_root()

parser = argparse.ArgumentParser(description='RTFM')
parser.add_argument('--feat-extractor', default='i3d', choices=['i3d', 'c3d'])
parser.add_argument('--feature-size', type=int, default=2048, help='size of feature (default: 2048)')
parser.add_argument('--modality', default='RGB', help='the type of the input, RGB,AUDIO, or MIX')
parser.add_argument('--rgb-list', default=str(_CLIP_TSA_I3D_LIST_ROOT / 'pistachio_i3d-i3d.list'), help='list of rgb features ')
parser.add_argument('--test-rgb-list', default=str(_CLIP_TSA_I3D_LIST_ROOT / 'pistachio_i3d-i3d-test.list'), help='list of test rgb features ')
parser.add_argument('--gt', default=str(_DATASET_ROOT / 'VAD' / 'i3d-features' / 'gt.npy'), help='file of ground truth ')
parser.add_argument('--gpus', default=1, type=int, choices=[0], help='gpus')
parser.add_argument('--lr', type=str, default='[0.001]*15000', help='learning rates for steps(list form)')
parser.add_argument('--batch-size', type=int, default=32, help='number of instances in a batch of data (default: 16)')
parser.add_argument('--workers', default=4, help='number of workers in dataloader')
parser.add_argument('--model-name', default='rtfm', help='name to save model')
parser.add_argument('--pretrained-ckpt', default=None, help='ckpt for pretrained model')
parser.add_argument('--num-classes', type=int, default=1, help='number of class')
parser.add_argument('--dataset', default='pistachio', help='dataset to train on (default: )')
parser.add_argument('--plot-freq', type=int, default=10, help='frequency of plotting (default: 10)')
parser.add_argument('--max-epoch', type=int, default=15000, help='maximum iteration to train (default: 100)')
