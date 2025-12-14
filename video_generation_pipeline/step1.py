"""
Image Classification Framework using Vision-Language Models
Automatically classifies and organizes images into predefined categories.
"""

import os
import shutil
import json
import argparse
import logging
from pathlib import Path
from typing import List, Set, Dict, Optional, Tuple
from PIL import Image
from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
import torch
import warnings

# Suppress specific warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", message=".*video processor config.*")
warnings.filterwarnings("ignore", message=".*fast processor by default.*")


class ImageClassifier:
    """
    A flexible image classification framework using vision-language models.
    Supports batch processing, progress tracking, and automatic organization.
    """
    
    DEFAULT_CATEGORIES = [
        "public_roads_transportation",
        "enclosed_indoor_premises",
        "commercial_entertainment",
        "industrial_construction",
        "outdoor_natural_environments",
        "critical_infrastructure",
        "other"
    ]
    
    DEFAULT_PROMPT = (
        "Please categorize the image into one of the following categories: "
        "{categories_list}. "
        "Output ONLY the exact category name in lowercase with underscores, "
        "without any explanation or extra text."
    )
    
    def __init__(
        self,
        model_path: str,
        source_dir: str,
        target_dir: str,
        categories: Optional[List[str]] = None,
        prompt_template: Optional[str] = None,
        batch_size: int = 100,
        log_level: str = "INFO"
    ):
        """
        Initialize the image classifier.
        
        Args:
            model_path: Path to the vision-language model
            source_dir: Directory containing images to classify
            target_dir: Root directory for classified images
            categories: List of classification categories (uses defaults if None)
            prompt_template: Custom prompt template (uses default if None)
            batch_size: Number of images to process before saving progress
            log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
        """
        self.model_path = model_path
        self.source_dir = Path(source_dir)
        self.target_dir = Path(target_dir)
        self.categories = categories or self.DEFAULT_CATEGORIES
        self.prompt_template = prompt_template or self.DEFAULT_PROMPT
        self.batch_size = batch_size
        
        # Setup logging
        self._setup_logging(log_level)
        
        # Create target directory if it doesn't exist
        self.target_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Target directory ready: {self.target_dir}")
        
        # Progress file path
        self.progress_file = self.target_dir / "progress.json"
        
        # Model components (loaded lazily)
        self.model = None
        self.processor = None
        
    def _setup_logging(self, log_level: str):
        """Configure logging system."""
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)
    
    def load_model(self):
        """Load the vision-language model and processor."""
        self.logger.info(f"Loading model from: {self.model_path}")
        
        try:
            self.processor = AutoProcessor.from_pretrained(
                self.model_path,
                trust_remote_code=True
            )
            
            # Determine optimal dtype based on GPU capability
            if torch.cuda.is_available():
                capability = torch.cuda.get_device_capability()[0]
                dtype = torch.bfloat16 if capability >= 8 else torch.float16
            else:
                dtype = torch.float16
            
            self.model = Qwen2_5_VLForConditionalGeneration.from_pretrained(
                self.model_path,
                torch_dtype=dtype,
                device_map="auto",
                trust_remote_code=True
            )
            self.model.eval()
            
            self.logger.info("Model loaded successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to load model: {e}")
            raise
    
    def _create_directories(self):
        """Create all necessary output directories."""
        self.logger.info(f"Creating directory structure in: {self.target_dir}")
        
        # Create main category folders (first 6 categories)
        for category in self.categories[:6]:
            (self.target_dir / category).mkdir(parents=True, exist_ok=True)
        
        # Create other folder (for everything else including failed processing)
        other_dir = self.target_dir / "other"
        other_dir.mkdir(parents=True, exist_ok=True)
    
    def _load_progress(self) -> Set[str]:
        """Load progress log of processed images."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
            except Exception as e:
                self.logger.warning(f"Failed to load progress, starting fresh: {e}")
        return set()
    
    def _save_progress(self, processed_files: Set[str]):
        """Save progress log of processed images."""
        try:
            self.target_dir.mkdir(parents=True, exist_ok=True)
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(list(processed_files), f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Failed to save progress: {e}")
    
    def _get_image_files(self) -> List[str]:
        """Get list of image files from source directory."""
        extensions = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif'}
        return [
            f.name for f in self.source_dir.iterdir()
            if f.suffix.lower() in extensions and f.is_file()
        ]
    
    def _classify_image(self, image_path: Path) -> Tuple[str, str]:
        """
        Classify a single image.
        
        Args:
            image_path: Path to the image file
            
        Returns:
            Tuple of (raw_response, extracted_category)
        """
        # Load image
        image = Image.open(image_path).convert("RGB")
        
        # Prepare prompt
        categories_str = ", ".join(self.categories)
        prompt = self.prompt_template.format(categories_list=categories_str)
        
        # Construct model input
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": image},
                    {"type": "text", "text": prompt},
                ],
            }
        ]
        
        # Process and generate
        text = self.processor.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.processor(
            text=[text], images=[image], padding=True, return_tensors="pt"
        ).to(self.model.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=50,
                do_sample=False,
                temperature=0.0,
            )
        
        # Decode response
        response = self.processor.decode(outputs[0], skip_special_tokens=True)
        
        # Extract category (take last line, remove punctuation)
        predicted = response.strip().split("\n")[-1].split(".")[0].strip()
        
        return response, predicted
    
    def _match_category(self, predicted: str) -> Optional[str]:
        """
        Match predicted category to predefined categories.
        Uses fuzzy matching (substring matching).
        
        Note: Only matches first 6 main categories. 
        "other" and unmatched results return None.
        
        Args:
            predicted: Predicted category string (should be lowercase with underscores)
            
        Returns:
            Matched category name or None (None triggers "other" folder)
        """
        predicted_lower = predicted.lower()
        
        # Only match first 6 main categories
        for category in self.categories[:6]:
            category_lower = category.lower()
            if predicted_lower in category_lower or category_lower in predicted_lower:
                return category
        
        return None
    
    def _move_file(self, source: Path, target_category: Optional[str], filename: str):
        """
        Move file to appropriate category folder.
        
        Args:
            source: Source file path
            target_category: Target category name (None for unknown)
            filename: Original filename
        """
        # If no match or matches "other", put in Other folder
        if target_category is None or target_category == "other":
            target_path = self.target_dir / "other" / filename
            self.logger.info(f"  → other")
        else:
            target_path = self.target_dir / target_category / filename
            self.logger.info(f"  → {target_category}")
        
        shutil.move(str(source), str(target_path))
    
    def process_images(self):
        """
        Main processing loop: classify and organize all images.
        """
        # Ensure model is loaded
        if self.model is None or self.processor is None:
            self.load_model()
        
        # Setup directories
        self._create_directories()
        
        # Get images to process
        all_images = self._get_image_files()
        total_images = len(all_images)
        self.logger.info(f"Found {total_images} images to classify")
        
        # Load progress
        processed_files = self._load_progress()
        if processed_files:
            self.logger.info(f"Resuming: {len(processed_files)} images already processed")
            all_images = [f for f in all_images if f not in processed_files]
            self.logger.info(f"Remaining: {len(all_images)} images to process")
        
        # Process each image
        for idx, filename in enumerate(all_images, 1):
            current = idx + len(processed_files)
            self.logger.info(f"[{current}/{total_images}] Processing: {filename}")
            
            image_path = self.source_dir / filename
            
            try:
                # Check if file still exists
                if not image_path.exists():
                    self.logger.warning(f"  File not found, skipping: {filename}")
                    processed_files.add(filename)
                    continue
                
                # Classify image
                raw_response, predicted = self._classify_image(image_path)
                self.logger.debug(f"  Raw response: {raw_response}")
                self.logger.debug(f"  Predicted: {predicted}")
                
                # Match to category
                matched_category = self._match_category(predicted)
                
                # Move file
                self._move_file(image_path, matched_category, filename)
                
                # Mark as processed
                processed_files.add(filename)
                
                # Periodic cleanup and save
                if idx % self.batch_size == 0:
                    if torch.cuda.is_available():
                        torch.cuda.empty_cache()
                        self.logger.info(f"  Cleared GPU cache after {idx} images")
                    
                    self._save_progress(processed_files)
                    self.logger.info(f"  Progress saved: {len(processed_files)}/{total_images}")
                
            except Exception as e:
                self.logger.error(f"  Failed to process {filename}: {e}")
                
                # Move to other folder (includes processing failures)
                try:
                    other_path = self.target_dir / "other" / filename
                    if image_path.exists():
                        shutil.move(str(image_path), str(other_path))
                        self.logger.info(f"  Moved to other folder (processing failed)")
                    processed_files.add(filename)
                except Exception as move_error:
                    self.logger.error(f"  Failed to move file: {move_error}")
        
        # Final save
        self._save_progress(processed_files)
        self.logger.info(f"\nCompleted: {len(processed_files)}/{total_images} images processed")
    
    def generate_report(self) -> Dict[str, int]:
        """
        Generate a summary report of classification results.
        
        Returns:
            Dictionary with category counts
        """
        report = {}
        
        # Count main categories (first 6)
        for category in self.categories[:6]:
            category_dir = self.target_dir / category
            if category_dir.exists():
                count = len(list(category_dir.glob("*")))
                report[category] = count
        
        # Count other folder (includes uncategorized and failed processing)
        other_dir = self.target_dir / "other"
        if other_dir.exists():
            report["other"] = len(list(other_dir.glob("*")))
        
        return report


def main():
    """Command-line interface for the image classifier."""
    parser = argparse.ArgumentParser(
        description="Classify and organize images using vision-language models"
    )
    
    parser.add_argument(
        "--model-path",
        required=True,
        help="Path to the vision-language model"
    )
    parser.add_argument(
        "--source-dir",
        required=True,
        help="Directory containing images to classify"
    )
    parser.add_argument(
        "--target-dir",
        required=True,
        help="Root directory for classified images"
    )
    parser.add_argument(
        "--categories",
        nargs="+",
        help="Custom classification categories (space-separated)"
    )
    parser.add_argument(
        "--prompt",
        help="Custom classification prompt template (use {categories_list})"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Images to process before saving progress (default: 100)"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level (default: INFO)"
    )
    parser.add_argument(
        "--report",
        action="store_true",
        help="Generate classification report after processing"
    )
    
    args = parser.parse_args()
    
    # Initialize classifier
    classifier = ImageClassifier(
        model_path=args.model_path,
        source_dir=args.source_dir,
        target_dir=args.target_dir,
        categories=args.categories,
        prompt_template=args.prompt,
        batch_size=args.batch_size,
        log_level=args.log_level
    )
    
    # Process images
    classifier.process_images()
    
    # Generate report if requested
    if args.report:
        print("\n" + "="*50)
        print("CLASSIFICATION REPORT")
        print("="*50)
        report = classifier.generate_report()
        for category, count in sorted(report.items(), key=lambda x: x[1], reverse=True):
            print(f"{category:40s}: {count:5d} images")
        print("="*50)


if __name__ == "__main__":
    main()