# VADTree on Pistachio

This directory is a lightweight Pistachio adapter for VADTree. It is intended to be copied into a fresh clone of the upstream VADTree repository. It does not include external model checkpoints, generated result JSON files, ImageBind weights, LLaVA/DeepSeek model weights, or historical output directories.

## Data

Download and extract the Pistachio dataset first, then set:

```bash
export PISTACHIO_DATASET_ROOT=/path/to/Pistachio_dataset
```

VADTree needs the video archive because it operates on `Pistachio_dataset/VAD/video/test`. The adapter resolves videos inside the nested release layout, so a separate flattened test directory is not required.

## Install

```bash
git clone https://github.com/wenlongli10/VADTree.git
cp -a /path/to/Pistachio/vad/training-free/VADTree/. VADTree/
cd VADTree
pip install -r requirements.txt
```

Install the upstream VADTree dependencies and the dependencies required by EfficientGEBD, LLaVA-NeXT, DeepSeek-R1, and ImageBind according to their original instructions. Provide model checkpoints explicitly with command-line arguments.

## Typical Pistachio Flow

Generate GEBD splits with an explicit config and checkpoint:

```bash
python EfficientGEBD/GEBD_split100.py \
  --video_dir "$PISTACHIO_DATASET_ROOT/VAD/video/test" \
  --annotationfile_path dataset_info/Pistachio/annotations/pistachio_anomaly_test.txt \
  --config-file /path/to/baseline.yaml \
  --resume /path/to/model_best.pth
```

Run LLaVA and DeepSeek scoring with your local model paths, then run refinement/correlation on the generated JSON files. The Pistachio branches in these scripts automatically use:

```text
dataset_info/Pistachio/annotations/pistachio_anomaly_test.txt
dataset_info/Pistachio/annotations/Temporal_Anomaly_Annotation_for_Testing_Videos.txt
```

## Smoke Test Scope

Verified in the release workspace:

- all adapter Python files compile
- all 402 `pistachio_anomaly_test.txt` records resolve to actual videos under `VAD/video/test`
- temporal annotations expand into frame-level labels

Full VLM inference is not included in the smoke test because it depends on external checkpoints and generated intermediate JSON files.
