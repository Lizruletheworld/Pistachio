# Pistachio VAD adapters

This directory contains Pistachio adapters for nine VAD methods. The adapters are intended to be copied into fresh clones of the original method repositories.

## Dataset setup

Download the dataset first from Hugging Face:

https://huggingface.co/datasets/lizirulestheworld/Pistachio

Extract the archives you need into one directory. After extraction, that directory should contain paths such as `VAD/i3d-features`, `VAD/vit-features`, and `VAD/video` depending on which archives you downloaded. Download `VAD/video` as well when running VADTree.

Set the dataset root before running any method:

```bash
export PISTACHIO_DATASET_ROOT=/path/to/Pistachio_dataset
```

The code also checks `PISTACHIO_ROOT/Pistachio_dataset` and a `Pistachio_dataset` directory next to this repository.

## Environment

Do not use project-internal server environments for open-source reproduction. Start from a clean Python environment, install the original method repository's requirements when it provides them, then install the common adapter dependencies:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r /path/to/Pistachio/vad/requirements.txt
```

Use a PyTorch build that matches your CUDA driver. For CPU-only smoke tests, the standard CPU PyTorch wheel is sufficient. Some original training scripts optionally use Visdom; it is listed in `vad/requirements.txt`, but the Pistachio dataset adapters do not require a running Visdom server for data loading.

## Regenerate lists

Run this once after downloading or moving the dataset:

```bash
cd /path/to/Pistachio
python vad/prepare_pistachio_lists.py --dataset-root "$PISTACHIO_DATASET_ROOT"
```

Expected list sizes:

| Feature | Train | Test |
|:--|--:|--:|
| i3d | 4562 | 402 |
| vit | 45620 | 402 |
| MULDE normal-only train | 3404 | 402 |

If an i3d feature cannot be loaded, regenerate that single feature from the matching video with the I3D extraction script before running `prepare_pistachio_lists.py`. The released lists expect all 4562 i3d train features to be readable.

## Fresh clone workflow

Clone the upstream method repository, then copy the matching adapter into it. Examples assume the Pistachio repository is at `/path/to/Pistachio`.

| Method | Clone command | Adapter copy command |
|:--|:--|:--|
| CLIP-TSA i3d | `git clone https://github.com/joos2010kj/CLIP-TSA.git CLIP-TSA-i3d` | `cp -a /path/to/Pistachio/vad/i3d/CLIP-TSA/. CLIP-TSA-i3d/` |
| CLIP-TSA vit | `git clone https://github.com/joos2010kj/CLIP-TSA.git CLIP-TSA-vit` | `cp -a /path/to/Pistachio/vad/vit/CLIP-TSA/. CLIP-TSA-vit/` |
| MGFN | `git clone https://github.com/carolchenyx/MGFN.git` | `cp -a /path/to/Pistachio/vad/i3d/MGFN.-main/. MGFN/` |
| RTFM | `git clone https://github.com/tianyu0207/RTFM.git` | `cp -a /path/to/Pistachio/vad/i3d/RTFM/. RTFM/` |
| UR-DMU | `git clone https://github.com/henrryzh1/UR-DMU.git` | `cp -a /path/to/Pistachio/vad/i3d/UR-DMU-master/. UR-DMU/` |
| PEL4VAD | `git clone https://github.com/yujiangpu20/PEL4VAD.git` | `cp -a /path/to/Pistachio/vad/vit/PEL4VAD/. PEL4VAD/` |
| VadCLIP | `git clone https://github.com/nwpu-zxr/VadCLIP.git` | `cp -a /path/to/Pistachio/vad/vit/VadCLIP/. VadCLIP/` |
| Fed-WSVAD | `git clone https://github.com/wbfwonderful/Fed-WSVAD.git` | `cp -a /path/to/Pistachio/vad/vit/Fed-WSVAD/. Fed-WSVAD/` |
| VADTree | `git clone https://github.com/wenlongli10/VADTree.git` | `cp -a /path/to/Pistachio/vad/training-free/VADTree/. VADTree/` |
| MULDE | `git clone https://github.com/divyanshm21/MULDE--Video-Anomaly-detection.git MULDE` | `cp -a /path/to/Pistachio/vad/i3d/MULDE/. MULDE/` |

After copying, run each method from the cloned upstream repository directory. The adapters provide Pistachio list files, dataset path resolution through `PISTACHIO_DATASET_ROOT`, and small compatibility fixes needed for current Python/NumPy/PyTorch environments.


## Fed-WSVAD

Fed-WSVAD uses Pistachio VIT/CLIP features. The adapter includes normalized CSV files for `event`, `scene`, and `random` federated splits under `vad/vit/Fed-WSVAD/data/list`. Run from the fresh Fed-WSVAD clone after copying the adapter:

```bash
cd Fed-WSVAD
python train.py --dataset me --split_mode event --batch_size 64 --clients_num 32
```

## VADTree

VADTree is included as a lightweight overlay under `vad/training-free/VADTree`. It does not include external VLM repositories, model checkpoints, generated captions, similarity pickles, or historical result directories. After copying into a fresh VADTree clone, follow the original VADTree setup for GEBD, LLaVA-NeXT, DeepSeek-R1, and ImageBind, then set `PISTACHIO_DATASET_ROOT` before running Pistachio commands.

The adapter provides:

- `dataset_info/Pistachio/annotations/*` with 402 test records
- `pistachio_paths.py` for nested `VAD/video/test` path resolution
- patched GEBD, LLaVA, DeepSeek, ImageBind, refinement, and correlation scripts without internal server paths

## MULDE preprocessing

MULDE uses generated arrays under `preprocessed_for_MULDE/`. These arrays are intentionally not committed because they are large. Rebuild them after copying the adapter:

```bash
cd MULDE
python prepare_preprocessed.py --dataset-root "$PISTACHIO_DATASET_ROOT"
python main.py
```

For a quick preprocessing check without building the train array:

```bash
python prepare_preprocessed.py --dataset-root "$PISTACHIO_DATASET_ROOT" --skip-train
```

## Verified smoke test scope

The fresh-clone workflow above was tested by cloning the upstream GitHub repositories for the original seven adapters, applying the adapters, regenerating lists, and loading the first train/test samples. MULDE was additionally tested with a small preprocessing run. Fed-WSVAD was tested for CSV path resolution, train/test batch loading, and one CPU model forward pass. VADTree was tested for syntax, 402-record annotation coverage, nested video path resolution, and frame-label expansion. Full training or full VLM inference to final benchmark metrics was not run as part of this smoke test.
