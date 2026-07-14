#!/usr/bin/env python3
"""Generate Pistachio VAD list files for the release adapters."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

BAD_I3D_FEATURES = set()


def default_dataset_root(repo_root: Path) -> Path:
    env_root = os.getenv("PISTACHIO_DATASET_ROOT")
    if env_root:
        return Path(env_root).expanduser()
    env_repo_root = os.getenv("PISTACHIO_ROOT")
    if env_repo_root:
        return Path(env_repo_root).expanduser() / "Pistachio_dataset"
    return repo_root.parent / "Pistachio_dataset"


def normalize_line(raw: str, dataset_root: Path) -> str:
    value = raw.strip()
    if not value:
        return value

    dataset_prefix = dataset_root.resolve().as_posix() + "/"
    for prefix in [dataset_prefix]:
        if value.startswith(prefix):
            value = "Pistachio/" + value[len(prefix):]
            break
    if value.startswith("VAD/"):
        value = "Pistachio/" + value
    return value


def read_dataset_list(dataset_root: Path, rel_path: str) -> list[str]:
    list_path = dataset_root / rel_path
    if not list_path.exists():
        raise FileNotFoundError(f"Missing dataset list: {list_path}")
    return [normalize_line(line, dataset_root) for line in list_path.read_text().splitlines() if line.strip()]


def validate_i3d(lines: list[str], dataset_root: Path) -> list[str]:
    import numpy as np

    valid = []
    for line in lines:
        if line in BAD_I3D_FEATURES:
            continue
        feature_path = dataset_root / line.split("Pistachio/", 1)[1]
        try:
            arr = np.load(feature_path, allow_pickle=True)
        except Exception as exc:
            print(f"skip unreadable i3d feature: {line} ({exc})")
            continue
        if arr.ndim == 3 and arr.shape[1:] == (10, 2048):
            valid.append(line)
        else:
            print(f"skip malformed i3d feature: {line} shape={arr.shape}")
    return valid


def write_list(path: Path, lines: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")
    print(f"{path}: {len(lines)}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--dataset-root", type=Path, default=None)
    parser.add_argument("--validate-i3d", action="store_true", help="Load i3d train features and skip unreadable/malformed files.")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    dataset_root = (args.dataset_root or default_dataset_root(repo_root)).resolve()

    i3d_train = read_dataset_list(dataset_root, "VAD/i3d-features/train-list.txt")
    i3d_test = read_dataset_list(dataset_root, "VAD/i3d-features/test-list.txt")
    vit_train = read_dataset_list(dataset_root, "VAD/vit-features/train-list.txt")
    vit_test = read_dataset_list(dataset_root, "VAD/vit-features/test-list.txt")

    if args.validate_i3d:
        i3d_train = validate_i3d(i3d_train, dataset_root)
    else:
        i3d_train = [line for line in i3d_train if line not in BAD_I3D_FEATURES]

    for clip in [repo_root / "vad/i3d/CLIP-TSA", repo_root / "vad/vit/CLIP-TSA"]:
        write_list(clip / "list/i3d/pistachio_i3d-i3d.list", i3d_train)
        write_list(clip / "list/i3d/pistachio_i3d-i3d-test.list", i3d_test)
        write_list(clip / "list/vit/pistachio-vit.list", vit_train)
        write_list(clip / "list/vit/pistachio-vit-test.list", vit_test)

    for method in [repo_root / "vad/i3d/MGFN.-main", repo_root / "vad/i3d/RTFM"]:
        write_list(method / "list/i3d/pistachio_i3d-i3d.list", i3d_train)
        write_list(method / "list/i3d/pistachio_i3d-i3d-test.list", i3d_test)

    write_list(repo_root / "vad/i3d/UR-DMU-master/list/pistachio_Train.list", i3d_train)
    write_list(repo_root / "vad/i3d/UR-DMU-master/list/pistachio_Test.list", i3d_test)

    write_list(repo_root / "vad/vit/PEL4VAD/list/pistachio/train.list", vit_train)
    write_list(repo_root / "vad/vit/PEL4VAD/list/pistachio/test.list", vit_test)

    mulde = repo_root / "vad/i3d/MULDE"
    mulde_train = [line for line in i3d_train if "/train/normal/" in line]
    write_list(mulde / "train.list", mulde_train)
    write_list(mulde / "test.list", i3d_test)
    write_list(mulde / "test_anomaly.txt", [line for line in i3d_test if "/test/anomaly/" in line])
    write_list(mulde / "test_normal.txt", [line for line in i3d_test if "/test/normal/" in line])
    write_list(mulde / "test_labels.list", [f"test_label/{Path(line).stem}_LABEL.npy" for line in i3d_test])


if __name__ == "__main__":
    main()
