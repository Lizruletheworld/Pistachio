# Pistachio: Towards Synthetic, Balanced, and Long-Form Video Anomaly Benchmarks

[![arXiv](https://img.shields.io/badge/arXiv-2511.19474-b31b1b.svg)](https://arxiv.org/abs/2511.19474)
[![Project Page](https://img.shields.io/badge/Project-Page-green.svg)](https://pistachio-video.github.io )
[![Dataset](https://img.shields.io/badge/Dataset-HuggingFace-yellow.svg)](https://huggingface.co/datasets/lizirulestheworld/Pistachio)

## 📋 Installation
Clone the repo:
```sh
git clone https://github.com/Pistachio.git
cd Pistachio
git clone https://github.com/Wan-Video/Wan2.2.git
```

Install dependencies:
```sh
# Ensure torch >= 2.4.0
# If the installation of `flash_attn` fails, try installing the other packages first and install `flash_attn` last
pip install -r requirements.txt
```

📥 Download models using huggingface-cli:
``` sh
pip install "huggingface_hub[cli]"
huggingface-cli download Wan-AI/Wan2.2-T2V-A14B --local-dir ./Wan2.2-T2V-A14B
```

📥 Download models using modelscope-cli:
``` sh
pip install modelscope
modelscope download Wan-AI/Wan2.2-T2V-A14B --local_dir ./Wan2.2-T2V-A14B
```


## Pipeline Overview

This pipeline consists of 4 sequential steps:

1. **Step 1**: Scene-AwareClassification - Categorize images into predefined scene types.
2. **Step 2**: AnomalyTypeSpecification - Assign anomaly event labels to images.
3. **Step 3**: Multi-step Storyline Generation - Generate detailed text prompts from images.
4. **Step 4**: Temporally consistent long-form video synthesis. - Synthesize videos from image-prompt pairs.
5. **Step 5**: Event-level to Video-level Annotation Generation - Generate video-level summaries from event annotations.
---
## Complete Pipeline Example

```bash
# Step 1: Classify images into scene categories
python step1.py \
  --model-path /path/to/model \
  --source-dir ./raw_images \
  --target-dir ./classified_images \
  --report

# Step 2: Label images with event categories
python step2.py \
  --model-path /path/to/model \
  --source-dir ./classified_images/public_roads_transportation \
  --target-dir ./labeled_images \
  --scene-mode public_roads_transportation \
  --summary

# Step 3: Generate prompts
# First time: initialize category mapping
./step3.sh init
# Edit category_map.txt as needed
# Then run prompt generation
./step3.sh

# Step 4: Generate videos (multi-GPU)
export CUDA_VISIBLE_DEVICES=0,1,2,3
torchrun --nproc_per_node=4 step4.py \
  --task i2v-A14B \
  --size 1280*720 \
  --ckpt_dir /path/to/Wan2.2-I2V-A14B \
  --path_list_file ./prompts/global_data_list.txt \
  --output_dir ./video_segments \
  --merged_output_dir ./final_videos \
  --dit_fsdp \
  --t5_fsdp \
  --ulysses_size 4
  
# Step 5: Generate video-level annotations
python step5.py \
  --input_dir ./final_videos \
  --model_path /path/to/Qwen3-8B \
  --skip_existing true
```
---

## Step 1: Scene-AwareClassification.

Automatically classifies and organizes images into predefined categories using vision-language models.

### Usage

```bash
python step1.py \
  --model-path /path/to/model \
  --source-dir /path/to/images \
  --target-dir /path/to/output \
  [OPTIONS]
```

**Note**: `--model-path` supports **Qwen2.5-VL series** models (e.g., Qwen2.5-VL-7B-Instruct, Qwen2.5-VL-32B-Instruct). Other models require manual code modifications.


### Output Structure

```
target_dir/
├── public_roads_transportation/
├── enclosed_indoor_premises/
├── commercial_entertainment/
├── industrial_construction/
├── outdoor_natural_environments/
├── critical_infrastructure/
├── other/
└── progress.json
```

### Examples

**Basic usage:**
```bash
python step1.py \
  --model-path /path/to/model \
  --source-dir /path/to/images \
  --target-dir /path/to/output
```

**With custom categories and report:**
```bash
python step1.py \
  --model-path /path/to/model \
  --source-dir /path/to/images \
  --target-dir /path/to/output \
  --categories "Urban" "Rural" "Nature" "Indoor" \
  --report
```
---

## Step 2: Anomaly Type Specification.

Assigns anomaly event labels to images based on scene-specific or unified event categories.

### Usage

```bash
python step2.py \
  --model-path /path/to/model \
  --source-dir /path/to/images \
  --target-dir /path/to/output \
  [OPTIONS]
```
**Note**: `--model-path` supports **Qwen2.5-VL series** models (e.g., Qwen2.5-VL-7B-Instruct, Qwen2.5-VL-32B-Instruct). Other models require manual code modifications.

### Optional Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--scene-mode` | None (unified mode) | Scene-specific mode (see options below) |
| `--batch-size` | 10 | Number of images to process per batch |
| `--log-level` | INFO | Logging level: DEBUG, INFO, WARNING, ERROR |
| `--summary` | False | Generate event distribution summary after processing |

### Scene Modes

| Mode | Description | Event Categories |
|------|-------------|------------------|
| `public_roads_transportation` | Public roads and transportation areas | 12 specific events |
| `enclosed_indoor_premises` | Enclosed and indoor premises | 15 specific events |
| `commercial_entertainment` | Commercial and entertainment venues | 15 specific events |
| `industrial_construction` | Industrial and construction zones | 14 specific events |
| `outdoor_natural` | Outdoor and natural environments | 15 specific events |
| `critical_infrastructure` | Critical infrastructure | 12 specific events |
| None (omit parameter) | Unified mode - all scene types | All unique events combined |

### Output Structure

Images are organized into event-specific folders:

```
target_dir/
├── traffic_accident/
│   ├── image001.jpg
│   └── image002.jpg
├── fire/
│   ├── image003.jpg
│   └── image004.jpg
├── theft/
└── [other_event_folders]/
```

### Examples

**Scene-specific mode (Indoor premises):**
```bash
python step2.py \
  --model-path /path/to/model \
  --source-dir ./indoor_images \
  --target-dir ./labeled_indoor \
  --scene-mode enclosed_indoor_premises \
  --batch-size 10 \
  --summary
```

**Unified mode (All event types):**
```bash
python step2.py \
  --model-path /path/to/model \
  --source-dir ./mixed_images \
  --target-dir ./labeled_unified \
  --batch-size 10 \
  --log-level DEBUG \
  --summary
```
---

## Step 3: Multi-step Storyline Generation.

Generates extended text prompts from images using vision-language models, with category-based organization.


### Usage

The script supports two modes:

**Mode 1: Default Mode (Paper-based Mixed Long/Short Video)**
```bash
./step3.sh
```
This mode uses the default category mapping based on the paper's configuration, where each folder generates both long and short video prompts (mixed mode). The `other` folder is automatically mapped to `normal` and `normal_Short`.

**Mode 2: Custom Mode (Manual Configuration)**
```bash
./step3.sh init
nano category_map.txt
./step3.sh run
```

**Note**: `--prompt_extend_model` supports **Qwen2.5-VL series** models. Other models require manual code modifications.


**Category Mapping Format:**

```
# Format: folder_name=category_name[,category_name_Short]

# Examples:
theft=theft,theft_Short              # Generate both long and short versions
fire=fire                            # Long video only
accident=accident_Short              # Short video only
other=normal,normal_Short            # Map "other" folder to "normal"
```

**Edit the generated file to customize:**
- Which folders generate long videos (`category`)
- Which folders generate short videos (`category_Short`)
- Which folders generate both (comma-separated)

### Output Structure

```
prompts/
├── theft/
│   ├── image001.jpg_prompt.txt
│   └── image002.jpg_prompt.txt
├── theft_Short/
│   ├── image001.jpg_prompt.txt
│   └── image002.jpg_prompt.txt
├── fire/
├── normal/
├── normal_Short/
└── global_data_list.txt
```

**`global_data_list.txt` format:**
```
/path/to/image001.jpg,/path/to/prompts/theft/image001.jpg_prompt.txt
/path/to/image002.jpg,/path/to/prompts/theft_Short/image002.jpg_prompt.txt
```

## Step 4: Temporally consistent long-form video synthesis.

Synthesizes videos from image-prompt pairs with automatic multi-segment merging.

### Single GPU Usage

```bash
python step4.py \
  --task i2v-A14B \
  --size 1280*720 \
  --ckpt_dir /path/to/Wan2.2-I2V-A14B \
  --path_list_file /path/to/global_data_list.txt \
  --output_dir /path/to/video_segments \
  --merged_output_dir /path/to/merged_videos
```

### Multi-GPU Usage (Recommended)

```bash
export CUDA_VISIBLE_DEVICES=0,1,2,3
torchrun --nproc_per_node=4 step4.py \
  --task i2v-A14B \
  --size 1280*720 \
  --ckpt_dir /path/to/Wan2.2-I2V-A14B \
  --path_list_file /path/to/global_data_list.txt \
  --output_dir /path/to/video_segments \
  --merged_output_dir /path/to/merged_videos \
  --dit_fsdp \
  --t5_fsdp \
  --ulysses_size 4
```

### Core Parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--task` | `i2v-A14B` | Generation task type: `i2v-A14B`, `t2v-A14B`, `ti2v-5B` |
| `--size` | `1280*720` | Video resolution (width*height) |
| `--frame_num` | Task default | Number of frames to generate (must be 4n+1) |
| `--output_dir` | `output_videos` | Directory for individual segment videos |
| `--merged_output_dir` | `merged_videos` | Directory for final merged videos |
| `--keep_segments` | False | Keep individual segments after merging |


### Output Structure

**Segment videos (temporary):**
```
output_videos/
└── image001/
    ├── i2v-A14B_image001_seq1.mp4
    ├── i2v-A14B_image001_seq1_last_frame.jpg
    ├── i2v-A14B_image001_seq2.mp4
    └── i2v-A14B_image001_seq2_last_frame.jpg
```

**Merged videos (final output):**
```
merged_videos/
├── theft/
│   ├── image001_all.mp4
│   └── image002_all.mp4
├── fire/
│   └── image003_all.mp4
└── [other_category_folders]/
```
---

## Step 5: Event-level to Video-level Annotation Generation

Generates comprehensive video-level summaries from event-level annotations using language models. This step processes all generated videos and creates concise textual summaries for each video.

### Usage
```bash
python step5.py \
  --input_dir /path/to/videos \
  --model_path /path/to/Qwen3-8B
```

**Note**: `--model_path` supports **Qwen3 series** models (e.g., Qwen3-8B-Instruct). Other models require manual code modifications.

### Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--input_dir` | Yes | - | Input directory containing video files (recursively processes all .txt files) |
| `--model_path` | No | `/home/intern/lijie/Qwen3-8B` | Path to the Qwen3 model |

### How It Works

1. **Scans directory**: Recursively finds all `.txt` files containing event-level annotations
2. **Generates summaries**: Uses Qwen3 model to create 2-3 sentence summaries capturing main content and key information
3. **Saves outputs**: Creates `summary_*.txt` files alongside original annotation files
4. **Auto-skips**: Automatically skips files that already have summaries generated

### Output Structure

For each annotation file, a corresponding summary file is created:
```
input_dir/
├── theft/
│   ├── video001_annotation.txt
│   ├── summary_video001_annotation.txt    # Generated summary
│   ├── video002_annotation.txt
│   └── summary_video002_annotation.txt    # Generated summary
├── fire/
│   ├── video003_annotation.txt
│   └── summary_video003_annotation.txt    # Generated summary
└── [other_category_folders]/
```

### Example

**Basic usage:**
```bash
python step5.py \
  --input_dir ./final_videos \
  --model_path /path/to/Qwen3-8B
```

---
## Citation

If you use Pistachio in your research, please cite:
```bibtex
@misc{li2025pistachiosyntheticbalancedlongform,
      title={Pistachio: Towards Synthetic, Balanced, and Long-Form Video Anomaly Benchmarks}, 
      author={Jie Li and Hongyi Cai and Mingkang Dong and Muxin Pu and Shan You and Fei Wang and Tao Huang},
      year={2025},
      eprint={2511.19474},
      archivePrefix={arXiv},
      primaryClass={cs.CV},
      url={https://arxiv.org/abs/2511.19474}
}
```