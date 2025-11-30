import os
import argparse
import logging
import sys
import glob
from PIL import Image

from utils.prompt_extend import DashScopePromptExpander, QwenPromptExpander

def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate extended text prompts from images"
    )
    parser.add_argument("--task", type=str, default="i2v-A14B", 
                       help="Task type")
    parser.add_argument("--prompt", type=str, default=None, 
                       help="Base prompt (optional)")
    parser.add_argument("--category", type=str, default=None, 
                       help="Category name for system prompts")
    parser.add_argument("--use_prompt_extend", action="store_true", 
                       help="Enable prompt extension")
    parser.add_argument("--prompt_extend_method", type=str, default="local_qwen",
                       choices=["dashscope", "local_qwen"])
    parser.add_argument("--prompt_extend_model", type=str, default=None,
                       help="Model path (e.g., /path/to/Qwen2.5-VL-32B-Instruct)")
    parser.add_argument("--prompt_extend_target_lang", type=str, default="en",
                       choices=["zh", "en"])
    parser.add_argument("--base_seed", type=int, default=-1)
    parser.add_argument("--image_dir", type=str, required=True,
                       help="Directory containing images")
    parser.add_argument("--prompt_dir", type=str, default="saved_prompts",
                       help="Directory to save prompts")
    parser.add_argument("--image_extension", type=str, default="jpg")
    parser.add_argument("--device", type=int, default=0)
    parser.add_argument("--skip_existing", action="store_true", default=True)
    return parser.parse_args()

def init_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(asctime)s] %(levelname)s: %(message)s",
        handlers=[logging.StreamHandler(stream=sys.stdout)])

def main():
    args = parse_args()
    init_logging()
    
    if not args.use_prompt_extend:
        logging.info("Prompt extension not enabled. Use --use_prompt_extend")
        return

    if not os.path.exists(args.image_dir):
        logging.error(f"Image directory not found: {args.image_dir}")
        return

    # Initialize model
    prompt_expander = None
    try:
        if args.prompt_extend_method == "dashscope":
            logging.info(f"Initializing DashScope model")
            prompt_expander = DashScopePromptExpander(
                model_name=args.prompt_extend_model,
                task=args.task,
                is_vl=True)
        elif args.prompt_extend_method == "local_qwen":
            logging.info(f"Loading Qwen model: {args.prompt_extend_model or 'default'}")
            prompt_expander = QwenPromptExpander(
                model_name=args.prompt_extend_model,
                task=args.task,
                is_vl=True,
                device=args.device,
                category=args.category)
    except Exception as e:
        logging.error(f"Failed to initialize model: {e}")
        return
    
    if prompt_expander is None:
        logging.error("Model initialization failed")
        return
    
    os.makedirs(args.prompt_dir, exist_ok=True)

    # Find images
    image_pattern = os.path.join(args.image_dir, f"*.{args.image_extension}")
    image_paths = sorted(glob.glob(image_pattern))
    
    if not image_paths:
        logging.warning(f"No .{args.image_extension} files found in {args.image_dir}")
        return

    logging.info(f"Found {len(image_paths)} images")

    processed = 0
    skipped = 0
    failed = 0

    # Process each image
    for image_path in image_paths:
        filename = os.path.basename(image_path)
        prompt_filename = f"{filename}_prompt.txt"
        prompt_path = os.path.join(args.prompt_dir, prompt_filename)

        if args.skip_existing and os.path.exists(prompt_path):
            logging.info(f"[SKIP] {filename}")
            skipped += 1
            continue
        
        logging.info(f"Processing: {filename}")

        try:
            img = Image.open(image_path).convert("RGB")
            
            prompt_output = prompt_expander(
                args.prompt or "",
                image=img,
                tar_lang=args.prompt_extend_target_lang,
                seed=args.base_seed)

            if not prompt_output.status:
                logging.error(f"Failed: {prompt_output.message}")
                extended_prompt = args.prompt or f"Image: {filename}"
                failed += 1
            else:
                extended_prompt = prompt_output.prompt
                processed += 1

            preview = extended_prompt[:100] + "..." if len(extended_prompt) > 100 else extended_prompt
            logging.info(f"Prompt: {preview}")
            
            with open(prompt_path, "w", encoding="utf-8") as f:
                f.write(extended_prompt)
            
            logging.info(f"Saved: {prompt_path}")
            
        except Exception as e:
            logging.error(f"Error: {e}")
            failed += 1
        
        logging.info("-" * 50)

    # Summary
    logging.info("=" * 50)
    logging.info(f"Total: {len(image_paths)}")
    logging.info(f"Processed: {processed}")
    logging.info(f"Skipped: {skipped}")
    logging.info(f"Failed: {failed}")
    logging.info("=" * 50)

if __name__ == "__main__":
    main()