from functools import lru_cache
import os
from pathlib import Path


_METHOD_ROOT = Path(__file__).resolve().parent


def pistachio_dataset_root():
    env_root = os.environ.get("PISTACHIO_DATASET_ROOT")
    candidates = []
    if env_root:
        candidates.append(Path(env_root).expanduser())
    candidates.extend([
        _METHOD_ROOT.parents[3] / "Pistachio_dataset",
        _METHOD_ROOT.parents[2] / "Pistachio_dataset",
        Path.cwd() / "Pistachio_dataset",
        Path.cwd().parent / "Pistachio_dataset",
    ])
    for candidate in candidates:
        if (candidate / "VAD").exists():
            return candidate.resolve()
    raise FileNotFoundError(
        "Cannot find Pistachio_dataset. Set PISTACHIO_DATASET_ROOT to the extracted dataset directory."
    )


def pistachio_video_test_root():
    return pistachio_dataset_root() / "VAD" / "video" / "test"


@lru_cache(maxsize=4)
def _video_index(video_root):
    root = Path(video_root)
    index = {}
    if not root.exists():
        return index
    for path in root.rglob("*.mp4"):
        index.setdefault(path.name, path)
        index.setdefault(path.stem, path)
    return index


def resolve_pistachio_video_path(video_root, name):
    root = Path(video_root) if video_root else pistachio_video_test_root()
    candidate = Path(name)
    if candidate.is_absolute() and candidate.exists():
        return str(candidate)
    direct = root / candidate
    if direct.exists():
        return str(direct)
    if direct.suffix != ".mp4":
        with_suffix = direct.with_suffix(".mp4")
        if with_suffix.exists():
            return str(with_suffix)
    key = candidate.name
    index = _video_index(str(root))
    if key in index:
        return str(index[key])
    stem = candidate.stem if candidate.suffix else candidate.name
    if stem in index:
        return str(index[stem])
    raise FileNotFoundError(f"Cannot resolve Pistachio video {name!r} under {root}")
