# Fed-WSVAD on Pistachio

This directory contains the Pistachio adapter for Fed-WSVAD using VIT/CLIP features.

## Data

Download and extract the Pistachio dataset first. The expected feature root is:

```text
Pistachio_dataset/VAD/vit-features
```

If `Pistachio_dataset` is not a sibling of the `Pistachio` code repository, set:

```bash
export PISTACHIO_DATASET_ROOT=/path/to/Pistachio_dataset
```

The CSV files under `data/list/me_*` use paths relative to the dataset root and contain:

- train: 45,620 VIT feature clips
- test: 402 VIT feature clips
- split modes: `event`, `scene`, and `random`

## Run

Install dependencies from the shared VAD requirements or this method's `requirements.txt`, then run from this directory:

```bash
python train.py --dataset me --split_mode event --batch_size 64 --clients_num 32
```

For quick smoke checks, reduce the number of rounds and epochs:

```bash
python train.py --dataset me --split_mode event --batch_size 2 --global_rounds 1 --local_epochs 1
```

For inference, provide a trained checkpoint:

```bash
python inference.py --dataset me --checkpoint /path/to/model.pth
```
