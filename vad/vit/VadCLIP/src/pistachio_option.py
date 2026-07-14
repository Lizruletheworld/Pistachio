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
_SRC_ROOT = Path(__file__).resolve().parent
_PROJECT_ROOT = _SRC_ROOT.parent
_DATASET_ROOT = _find_dataset_root()

parser = argparse.ArgumentParser(description='VadCLIP')
parser.add_argument('--seed', default=234, type=int)

parser.add_argument('--embed-dim', default=512, type=int)
parser.add_argument('--visual-length', default=256, type=int)
parser.add_argument('--visual-width', default=512, type=int)
parser.add_argument('--visual-head', default=1, type=int)
parser.add_argument('--visual-layers', default=2, type=int)
parser.add_argument('--attn-window', default=8, type=int)
parser.add_argument('--prompt-prefix', default=10, type=int)
parser.add_argument('--prompt-postfix', default=10, type=int)
parser.add_argument('--classes-num', default=32, type=int)

parser.add_argument('--max-epoch', default=10, type=int)
parser.add_argument('--model-path', default=str(_PROJECT_ROOT / 'model' / 'model_me.pth'))
parser.add_argument('--use-checkpoint', default=False, type=bool)
parser.add_argument('--checkpoint-path', default=str(_PROJECT_ROOT / 'model' / 'checkpoint.pth'))
parser.add_argument('--batch-size', default=256, type=int)
parser.add_argument('--train-list', default=str(_DATASET_ROOT / 'VAD' / 'vit-features' / 'train-list.txt'))
parser.add_argument('--test-list', default=str(_DATASET_ROOT / 'VAD' / 'vit-features' / 'test-list.txt'))
parser.add_argument('--gt-path', default=str(_DATASET_ROOT / 'VAD' / 'vit-features' / 'gt_vit.npy'))
parser.add_argument('--gt-segment-path', default=None)
parser.add_argument('--gt-label-path', default=None)

parser.add_argument('--lr', default=2e-5)
parser.add_argument('--scheduler-rate', default=0.1)
parser.add_argument('--scheduler-milestones', default=[4, 8])
