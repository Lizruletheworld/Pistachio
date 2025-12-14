import torch
import torchvision
from PIL import Image
import os.path as osp
import random
import numpy as np
from torchvision.io import write_video
from moviepy import VideoFileClip, concatenate_videoclips
import tempfile
import shutil
import time
import os
import sys
import logging
import torch.distributed as dist
from datetime import datetime
from pathlib import Path
import argparse
import warnings

warnings.filterwarnings('ignore')
wan_path = os.path.join(os.path.dirname(__file__), 'Wan2.2')
sys.path.insert(0, wan_path)
import wan
from wan.configs import MAX_AREA_CONFIGS, SIZE_CONFIGS, SUPPORTED_SIZES, WAN_CONFIGS
from wan.distributed.util import init_distributed_group
from wan.utils.utils import save_video, str2bool

# Resiliency constants
MAX_RETRIES = 1000
INITIAL_BACKOFF_SECONDS = 60

EXAMPLE_PROMPT = {
    "t2v-A14B": {
        "prompt": "Two anthropomorphic cats in comfy boxing gear and bright gloves fight intensely on a spotlighted stage.",
    },
    "i2v-A14B": {
        "prompt": "Summer beach vacation style, a white cat wearing sunglasses sits on a surfboard.",
    },
    "ti2v-5B": {
        "prompt": "Two anthropomorphic cats in comfy boxing gear and bright gloves fight intensely on a spotlighted stage.",
    },
}

def _validate_args(args):
    """Validate command line arguments"""
    assert args.ckpt_dir is not None, "Please specify checkpoint directory with --ckpt_dir"
    assert args.task in WAN_CONFIGS, f"Unsupported task: {args.task}"
    assert args.path_list_file is not None, "Please specify path list file with --path_list_file"
    
    if args.prompt is None:
        args.prompt = EXAMPLE_PROMPT[args.task]["prompt"]

    cfg = WAN_CONFIGS[args.task]

    if args.sample_steps is None:
        args.sample_steps = cfg.sample_steps
    if args.sample_shift is None:
        args.sample_shift = cfg.sample_shift
    if args.sample_guide_scale is None:
        args.sample_guide_scale = cfg.sample_guide_scale
    if args.frame_num is None:
        args.frame_num = cfg.frame_num

    args.base_seed = args.base_seed if args.base_seed >= 0 else random.randint(0, sys.maxsize)
    
    assert args.size in SUPPORTED_SIZES[args.task], \
        f"Unsupported size {args.size} for task {args.task}. Supported: {', '.join(SUPPORTED_SIZES[args.task])}"

def _parse_args():
    parser = argparse.ArgumentParser(
        description="Batch video generation from image-prompt pairs with auto-merge"
    )
    parser.add_argument(
        '--path_list_file', 
        type=str, 
        required=True,
        help="Path to TXT file containing (image_path,prompt_path) pairs"
    )
    parser.add_argument(
        '--output_dir', 
        type=str, 
        default="output_videos",
        help="Output directory for generated videos"
    )
    parser.add_argument(
        '--merged_output_dir',
        type=str,
        default="merged_videos",
        help="Output directory for merged videos"
    )
    parser.add_argument(
        '--keep_segments',
        action='store_true',
        help="Keep individual segment videos after merging"
    )
    parser.add_argument(
        "--task",
        type=str,
        default="i2v-A14B",
        choices=list(WAN_CONFIGS.keys()),
        help="Generation task type"
    )
    parser.add_argument(
        "--size",
        type=str,
        default="1280*720",
        choices=list(SIZE_CONFIGS.keys()),
        help="Video resolution (width*height)"
    )
    parser.add_argument(
        "--frame_num",
        type=int,
        default=None,
        help="Number of frames to generate (should be 4n+1)"
    )
    parser.add_argument(
        "--ckpt_dir",
        type=str,
        required=True,
        help="Path to model checkpoint directory"
    )
    parser.add_argument(
        "--offload_model",
        type=str2bool,
        default=None,
        help="Offload model to CPU after forward pass to save GPU memory"
    )
    parser.add_argument(
        "--ulysses_size",
        type=int,
        default=1,
        help="Ulysses parallelism size for DiT"
    )
    parser.add_argument(
        "--t5_fsdp",
        action="store_true",
        help="Use FSDP for T5 model"
    )
    parser.add_argument(
        "--t5_cpu",
        action="store_true",
        help="Place T5 model on CPU"
    )
    parser.add_argument(
        "--dit_fsdp",
        action="store_true",
        help="Use FSDP for DiT model"
    )
    parser.add_argument(
        "--prompt",
        type=str,
        default=None,
        help="Default prompt (uses example prompt if not specified)"
    )
    parser.add_argument(
        "--base_seed",
        type=int,
        default=-1,
        help="Base random seed (-1 for random)"
    )
    parser.add_argument(
        "--sample_solver",
        type=str,
        default='unipc',
        choices=['unipc', 'dpm++'],
        help="Sampling solver"
    )
    parser.add_argument(
        "--sample_steps",
        type=int,
        default=None,
        help="Number of sampling steps"
    )
    parser.add_argument(
        "--sample_shift",
        type=float,
        default=None,
        help="Sampling shift factor"
    )
    parser.add_argument(
        "--sample_guide_scale",
        type=float,
        default=None,
        help="Classifier-free guidance scale"
    )
    parser.add_argument(
        "--convert_model_dtype",
        action="store_true",
        help="Convert model parameter dtype"
    )

    args = parser.parse_args()
    _validate_args(args)
    return args

def _init_logging(rank):
    """Initialize logging configuration"""
    if rank == 0:
        logging.basicConfig(
            level=logging.INFO,
            format="[%(asctime)s] %(levelname)s: %(message)s",
            handlers=[logging.StreamHandler(stream=sys.stdout)])
    else:
        logging.basicConfig(level=logging.ERROR)

def save_last_frame(tensor, save_file, nrow=8, normalize=True, value_range=(-1, 1)):
    """Extract and save the last frame from video tensor as an image."""
    tensor = tensor.clamp(min(value_range), max(value_range))
    
    tensor = torch.stack([
        torchvision.utils.make_grid(
            u, nrow=nrow, normalize=normalize, value_range=value_range)
        for u in tensor.unbind(2)
    ], dim=1).permute(1, 2, 3, 0)
    
    tensor = (tensor * 255).type(torch.uint8).cpu()

    if tensor.shape[0] > 0:
        last_frame = tensor[-1].numpy()
        img = Image.fromarray(last_frame)
        img.save(save_file)
        logging.info(f"Last frame saved to: {save_file}")
    else:
        logging.warning("No frames in tensor, cannot save image")
        img = None
    
    return img

def read_path_list_file(path_list_file_path):
    """Read image and prompt file path pairs from TXT file."""
    path_pairs = []
    try:
        with open(path_list_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and ',' in line:
                    img_path, prompt_path = line.split(',', 1)
                    path_pairs.append((img_path.strip(), prompt_path.strip()))
        return path_pairs
    except FileNotFoundError:
        logging.error(f"Path list file not found: {path_list_file_path}")
        return []
    except Exception as e:
        logging.error(f"Error reading path list file: {e}")
        return []

def read_prompts_from_file(prompt_file_path):
    """Read prompts from file, one per line."""
    try:
        with open(prompt_file_path, 'r', encoding='utf-8') as f:
            prompts = [line.strip() for line in f if line.strip()]
        return prompts
    except FileNotFoundError:
        logging.error(f"Prompt file not found: {prompt_file_path}")
        return []

def merge_videos(video_files, output_path, rank):
    """Merge multiple video files into one."""
    if rank != 0:
        return  # Only rank 0 performs merge
    
    if not video_files:
        logging.warning("No video files to merge")
        return
    
    logging.info(f"Merging {len(video_files)} videos into: {output_path}")
    
    clips = []
    try:
        for video_path in video_files:
            if os.path.exists(video_path):
                clip = VideoFileClip(video_path)
                clips.append(clip)
                logging.info(f"  Loaded: {os.path.basename(video_path)} ({clip.duration:.2f}s)")
            else:
                logging.warning(f"  Video not found, skipped: {video_path}")
        
        if not clips:
            logging.warning("No valid video clips to merge")
            return
        
        # Concatenate and save
        final_clip = concatenate_videoclips(clips)
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        final_clip.write_videofile(
            output_path,
            codec='libx264',
            audio=False,
            threads=4
        )
        
        logging.info(f"✓ Merged video saved: {output_path}")
        
    except Exception as e:
        logging.error(f"Error merging videos: {e}")
    finally:
        for clip in clips:
            clip.close()
        if 'final_clip' in locals():
            final_clip.close()

def generate(args):
    """Main generation function with integrated merge"""
    
    # Initialize distributed environment
    rank = int(os.getenv("RANK", 0))
    world_size = int(os.getenv("WORLD_SIZE", 1))
    local_rank = int(os.getenv("LOCAL_RANK", 0))
    device = local_rank
    _init_logging(rank)

    if args.offload_model is None:
        args.offload_model = False if world_size > 1 else True
        logging.info(f"offload_model set to {args.offload_model}")
    
    if world_size > 1:
        torch.cuda.set_device(local_rank)
        dist.init_process_group(
            backend="nccl",
            init_method="env://",
            rank=rank,
            world_size=world_size)
    else:
        assert not (args.t5_fsdp or args.dit_fsdp), \
            "FSDP not supported in non-distributed environments"
        assert not (args.ulysses_size > 1), \
            "Sequence parallel not supported in non-distributed environments"

    if args.ulysses_size > 1:
        assert args.ulysses_size == world_size, \
            "ulysses_size must equal world_size"
        init_distributed_group()

    # Load model config
    cfg = WAN_CONFIGS[args.task]
    if args.ulysses_size > 1:
        assert cfg.num_heads % args.ulysses_size == 0, \
            f"num_heads {cfg.num_heads} cannot be divided by ulysses_size {args.ulysses_size}"

    logging.info(f"Args: {args}")
    logging.info(f"Model config: {cfg}")

    if dist.is_initialized():
        base_seed = [args.base_seed] if rank == 0 else [None]
        dist.broadcast_object_list(base_seed, src=0)
        args.base_seed = base_seed[0]

    # Create pipeline
    logging.info("Creating Wan pipeline...")
    wan_i2v = wan.WanI2V(
        config=cfg,
        checkpoint_dir=args.ckpt_dir,
        device_id=device,
        rank=rank,
        t5_fsdp=args.t5_fsdp,
        dit_fsdp=args.dit_fsdp,
        use_sp=(args.ulysses_size > 1),
        t5_cpu=args.t5_cpu,
        convert_model_dtype=args.convert_model_dtype,
    )
    
    # Read all image-prompt pairs
    path_pairs = read_path_list_file(args.path_list_file)
    if not path_pairs:
        logging.warning("No image-prompt pairs loaded. Exiting.")
        if dist.is_initialized():
            dist.barrier()
            dist.destroy_process_group()
        return

    # Process each image sequentially
    for batch_idx, (original_image_path, prompt_file_path) in enumerate(path_pairs):
        logging.info("=" * 60)
        logging.info(f"[{batch_idx+1}/{len(path_pairs)}] Processing: {original_image_path}")

        # Read prompts for this image
        prompts = read_prompts_from_file(prompt_file_path)
        if not prompts:
            logging.warning(f"No prompts found for {original_image_path}. Skipping.")
            continue
        
        # Create output directory (rank 0 only)
        if rank == 0:
            base_name = Path(original_image_path).stem
            output_dir = Path(args.output_dir) / base_name
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # Create merged output directory with category structure
            category_name = Path(original_image_path).parent.name
            merged_category_dir = Path(args.merged_output_dir) / category_name
            merged_category_dir.mkdir(parents=True, exist_ok=True)
            
            merged_video_path = merged_category_dir / f"{base_name}_all.mp4"
            
            # Check if merged video already exists
            if merged_video_path.exists():
                logging.info(f"Merged video already exists: {merged_video_path}. Skipping entire image.")
                continue
            
            logging.info(f"Output directory: {output_dir}")
            logging.info(f"Merged video will be saved to: {merged_video_path}")
        
        # Sync skip decision
        should_skip_image = False
        if dist.is_initialized():
            should_skip_list = [merged_video_path.exists() if rank == 0 else False]
            dist.broadcast_object_list(should_skip_list, src=0)
            should_skip_image = should_skip_list[0]
            dist.barrier()
        
        if should_skip_image:
            continue
        
        # Load initial image
        try:
            current_image = Image.open(original_image_path).convert("RGB")
            logging.info(f"Loaded input image: {original_image_path}")
        except FileNotFoundError:
            logging.error(f"Image not found: {original_image_path}. Skipping.")
            continue
        
        # Track generated video files for merging
        segment_video_files = []
        
        # Generate videos for each prompt sequentially
        for seq_idx, prompt in enumerate(prompts):
            base_name = Path(original_image_path).stem
            output_dir = Path(args.output_dir) / base_name
            
            # Define output filenames
            video_file_name = f"{args.task}_{base_name}_seq{seq_idx+1}.mp4"
            save_video_file = output_dir / video_file_name
            image_file_name = f"{args.task}_{base_name}_seq{seq_idx+1}_last_frame.jpg"
            save_image_file = output_dir / image_file_name
            
            # Track for merging
            if rank == 0:
                segment_video_files.append(str(save_video_file))
            
            # Check if already generated
            should_skip = False
            if rank == 0:
                if save_video_file.exists() and save_image_file.exists():
                    logging.info(f"Already exists: {save_video_file}. Skipping.")
                    should_skip = True
                else:
                    preview = prompt[:70] + "..." if len(prompt) > 70 else prompt
                    logging.info(f"Seq {seq_idx+1}/{len(prompts)} | Prompt: {preview}")

            # Sync skip decision
            if dist.is_initialized():
                should_skip_list = [should_skip] if rank == 0 else [False]
                dist.broadcast_object_list(should_skip_list, src=0)
                should_skip = should_skip_list[0]
                dist.barrier()

            if should_skip:
                if rank == 0:
                    try:
                        current_image = Image.open(save_image_file).convert("RGB")
                        logging.info(f"Loaded existing last frame: {save_image_file}")
                    except FileNotFoundError:
                        logging.error(f"Last frame not found: {save_image_file}")
                
                if dist.is_initialized():
                    dist.barrier()
                continue

            # Generate video
            logging.info("Generating video...")
            video = wan_i2v.generate(
                prompt,
                current_image,
                max_area=MAX_AREA_CONFIGS[args.size],
                frame_num=args.frame_num,
                shift=args.sample_shift,
                sample_solver=args.sample_solver,
                sampling_steps=args.sample_steps,
                guide_scale=args.sample_guide_scale,
                seed=args.base_seed + batch_idx * 100 + seq_idx,
                offload_model=args.offload_model
            )

            # Save results (rank 0 only) with retry logic
            if rank == 0:
                retries = 0
                while retries < MAX_RETRIES:
                    try:
                        logging.info(f"Saving video to {save_video_file} (attempt {retries+1})")
                        save_video(
                            tensor=video[None],
                            save_file=str(save_video_file),
                            fps=cfg.sample_fps,
                            nrow=1,
                            normalize=True,
                            value_range=(-1, 1)
                        )

                        # Save last frame as next input
                        current_image = save_last_frame(
                            video[None],
                            save_file=str(save_image_file)
                        )
                        
                        break  # Success
                        
                    except OSError as e:
                        if e.errno == 28:  # No space left on device
                            retries += 1
                            if retries == MAX_RETRIES:
                                logging.error(f"Max retries reached. No space left. Giving up.")
                                raise
                                
                            wait_time = INITIAL_BACKOFF_SECONDS * (2 ** (retries - 1))
                            logging.error(f"No space left on device. Waiting {wait_time}s (retry {retries}/{MAX_RETRIES})")
                            time.sleep(wait_time)
                        else:
                            logging.error(f"OSError during save: {e}")
                            raise
                    except Exception as e:
                        logging.error(f"Unexpected error during save: {e}")
                        raise

            # Cleanup and sync
            del video
            if dist.is_initialized():
                torch.cuda.synchronize()
                dist.barrier()
        
        # Merge all segment videos for this image
        logging.info(f"All {len(prompts)} segments generated for {original_image_path}")
        
        if rank == 0:
            logging.info("Starting video merge...")
            merge_videos(segment_video_files, str(merged_video_path), rank)
            
            # Optionally delete segment videos
            if not args.keep_segments:
                logging.info("Cleaning up segment videos...")
                for video_file in segment_video_files:
                    try:
                        if os.path.exists(video_file):
                            os.remove(video_file)
                            # Also remove corresponding last frame
                            last_frame = video_file.replace('.mp4', '_last_frame.jpg')
                            if os.path.exists(last_frame):
                                os.remove(last_frame)
                    except Exception as e:
                        logging.warning(f"Failed to delete {video_file}: {e}")
                
                # Remove empty directory
                try:
                    output_dir = Path(args.output_dir) / Path(original_image_path).stem
                    if output_dir.exists() and not any(output_dir.iterdir()):
                        output_dir.rmdir()
                except Exception as e:
                    logging.warning(f"Failed to remove directory: {e}")
        
        if dist.is_initialized():
            dist.barrier()

    # Cleanup
    if dist.is_initialized():
        dist.barrier()
        dist.destroy_process_group()

    logging.info("Batch generation and merge complete!")

if __name__ == "__main__":
    args = _parse_args()
    generate(args)