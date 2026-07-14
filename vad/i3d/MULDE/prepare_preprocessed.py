#!/usr/bin/env python3
"""Build MULDE preprocessed arrays from Pistachio feature and label lists."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

import numpy as np
from tqdm import tqdm


def default_dataset_root(method_root: Path) -> Path:
    env_root = os.getenv("PISTACHIO_DATASET_ROOT")
    if env_root:
        return Path(env_root).expanduser()
    env_repo_root = os.getenv("PISTACHIO_ROOT")
    if env_repo_root:
        return Path(env_repo_root).expanduser() / "Pistachio_dataset"
    for parent in method_root.parents:
        candidate = parent / "Pistachio_dataset"
        if candidate.exists():
            return candidate
    return method_root.parents[3] / "Pistachio_dataset"


def resolve_path(raw_path: str, dataset_root: Path, list_file: Path) -> Path:
    value = raw_path.strip()
    path = Path(value)
    if path.is_absolute():
        return path
    if value.startswith("Pistachio/VAD/"):
        return dataset_root / value.split("Pistachio/", 1)[1]
    if value.startswith("VAD/"):
        return dataset_root / value
    if value.startswith("Pistachio_dataset/"):
        return dataset_root.parent / value
    return list_file.parent / path


def load_list(list_file: Path, dataset_root: Path, is_label: bool) -> np.ndarray:
    entries = [line.strip() for line in list_file.read_text().splitlines() if line.strip().endswith(".npy")]
    arrays = []
    skipped = 0
    for entry in tqdm(entries, desc=list_file.name):
        path = resolve_path(entry, dataset_root, list_file)
        try:
            data = np.load(path, allow_pickle=True)
        except Exception as exc:
            skipped += 1
            print(f"skip {path}: {exc}")
            continue

        if is_label:
            arrays.append(data.reshape(-1))
            continue

        if data.ndim == 3:
            arrays.append(data.reshape(-1, data.shape[-1]))
        elif data.ndim == 2:
            arrays.append(data)
        else:
            skipped += 1
            print(f"skip {path}: unsupported feature ndim {data.ndim}")

    if not arrays:
        raise RuntimeError(f"No arrays loaded from {list_file}")
    merged = np.concatenate(arrays, axis=0)
    print(f"loaded {len(arrays)} entries from {list_file}; skipped {skipped}; shape={merged.shape}")
    return merged


def main() -> None:
    method_root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset-root", type=Path, default=None)
    parser.add_argument("--train-list", type=Path, default=method_root / "train.list")
    parser.add_argument("--test-list", type=Path, default=method_root / "test.list")
    parser.add_argument("--label-list", type=Path, default=method_root / "test_labels.list")
    parser.add_argument("--output-dir", type=Path, default=method_root / "preprocessed_for_MULDE")
    parser.add_argument("--skip-train", action="store_true")
    parser.add_argument("--skip-test", action="store_true")
    args = parser.parse_args()

    dataset_root = (args.dataset_root or default_dataset_root(method_root)).resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    if not args.skip_train:
        train_data = load_list(args.train_list, dataset_root, is_label=False)
        np.save(args.output_dir / "my_train_features.npy", train_data)

    if not args.skip_test:
        test_data = load_list(args.test_list, dataset_root, is_label=False)
        test_labels = load_list(args.label_list, dataset_root, is_label=True)
        if test_data.shape[0] != test_labels.shape[0]:
            raise RuntimeError(f"test feature/label length mismatch: {test_data.shape[0]} vs {test_labels.shape[0]}")
        np.save(args.output_dir / "my_test_features.npy", test_data)
        np.save(args.output_dir / "my_test_labels.npy", test_labels)

    print(f"wrote MULDE preprocessed arrays to {args.output_dir}")


if __name__ == "__main__":
    main()
