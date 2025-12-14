"""
Universal Event Labeling Framework for Multi-Scene Anomaly Detection
Supports both scene-specific and unified labeling modes.
Organizes labeled images into event-specific folders.
"""

import os
import shutil
import re
import json
import argparse
import logging
from pathlib import Path
from typing import List, Dict, Set, Optional, Tuple
from PIL import Image
from transformers import AutoProcessor, Qwen2_5_VLForConditionalGeneration
import torch
import warnings

warnings.filterwarnings("ignore", category=FutureWarning)


class SceneEventConfig:
    """Configuration for scene-specific abnormal events."""
    
    SCENE_EVENTS = {
        "public_roads_transportation": [
            "Traffic Accident", "Wild Large Animal Intrusion", "Robbery",
            "Theft", "Fighting & Physical Conflict", "Weapons Incident",
            "Vandalism", "Slip & Fall Accident", "Ground Collapse",
            "Fire", "Explosion", "Other"
        ],
        "enclosed_indoor_premises": [
            "Theft", "Robbery", "Fighting & Physical Conflict",
            "Animal Abuse", "Weapons Incident", "Vandalism",
            "Slip & Fall Accident", "Sudden Illness & Seizure", "Fire",
            "Explosion", "Infrastructure Failure", "Falling Object & Collapse",
            "Animal Attack or Fight", "Wild Large Animal Intrusion", "Other"
        ],
        "commercial_entertainment": [
            "Theft", "Fighting & Physical Conflict", "Weapons Incident",
            "Robbery", "Animal Abuse", "Slip & Fall Accident",
            "Pushing Conflict", "Sudden Illness & Seizure", "Fire",
            "Vandalism", "Explosion", "Falling Object & Collapse",
            "Animal Attack or Fight", "Wild Large Animal Intrusion", "Other"
        ],
        "industrial_construction": [
            "Falling Object & Collapse", "Slip & Fall Accident",
            "Safety Violations", "Medical Emergency", "Extreme Weather Events",
            "Equipment Breakdown", "Traffic Accident", "Fire",
            "Explosion", "Structural Failure", "Ground Collapse",
            "Leakage", "Wild Large Animal Intrusion", "Other"
        ],
        "outdoor_natural": [
            "Animal Predation", "Animal Fight", "Animal Fall & Injury",
            "Animal Abuse", "Slip & Fall Accident", "Fighting & Physical Conflict",
            "Weapons Incident", "Person Drowning", "Fire",
            "Explosion", "Falling Object & Collapse", "Ground Collapse",
            "Landslide", "Extreme Weather Events", "Other"
        ],
        "critical_infrastructure": [
            "Natural Disasters", "Weapons Incident", "Vandalism",
            "Extreme Weather Events", "Equipment Breakdown", "Fire",
            "Construction Accident", "Structural Failure", "Falling Object & Collapse",
            "Explosion", "Leakage", "Other"
        ]
    }
    
    SCENE_DESCRIPTIONS = {
        "public_roads_transportation": "Public Roads & Transportation Areas",
        "enclosed_indoor_premises": "Enclosed & Indoor Premises",
        "commercial_entertainment": "Commercial & Entertainment Gathering Points",
        "industrial_construction": "Industrial & Construction Zones",
        "outdoor_natural": "Outdoor & Natural Environments",
        "critical_infrastructure": "Critical Infrastructure"
    }
    
    @classmethod
    def get_all_events(cls) -> List[str]:
        """Get unified list of all unique events across all scenes."""
        all_events = set()
        for events in cls.SCENE_EVENTS.values():
            all_events.update(events)
        return sorted(list(all_events))
    
    @classmethod
    def get_scene_events(cls, scene_key: str) -> List[str]:
        """Get events for a specific scene."""
        return cls.SCENE_EVENTS.get(scene_key, cls.get_all_events())


class EventLabeler:
    """
    Universal event labeling system for anomaly detection.
    Supports both scene-specific and unified labeling modes.
    Organizes images into event-specific folders.
    """
    
    PROMPT_TEMPLATE = """
You are an expert in multi-image analysis and event inference for "{scene_description}".
You will receive a set of image files.

Your task is to assign the most likely and specific anomalous events that will happen in the future for each image according to the following priorities:
1. First, identify the most probable anomalous events
2. Second, ensure that the types of events are relatively evenly distributed across the entire image set

Abnormal Event Categories (must be strictly used - {num_events} specific events):
{event_list}

Output Requirements:
1. Output must be a strict numbered list
2. Numbering must correspond EXACTLY to the input image file order
3. For each image, output ONLY the event category name in lowercase with underscores
4. Format: "number. event_name" (e.g., "1. theft", "2. fire", "3. slip_and_fall_accident")
5. The event_name must match the category names with spaces and special characters replaced by underscores (_)
   Examples: "Slip & Fall Accident" -> slip_and_fall_accident; "Theft" -> theft; "Fire" -> fire
6. STRICT REQUIREMENT: Do not output any text before the numbered list begins
7. Do not output explanations, descriptions, or any other text
8. Output Language: English

Example (for 5 images):
Input images:
1. 000000000234.jpg
2. 000028938042.png
3. 000002380003.jpeg
4. 000000000456.jpg
5. 000000000789.webp

Expected Output:
1. theft
2. fighting_and_physical_conflict
3. weapons_incident
4. robbery
5. slip_and_fall_accident

Now classify the following images:
"""
    
    def __init__(
        self,
        model_path: str,
        source_dir: str,
        target_dir: str,
        scene_mode: Optional[str] = None,
        batch_size: int = 10,
        log_level: str = "INFO"
    ):
        """
        Initialize the event labeler.
        
        Args:
            model_path: Path to the vision-language model
            source_dir: Directory containing images to label
            target_dir: Output directory for labeled images (will create subfolders)
            scene_mode: Scene type key (None for unified mode)
            batch_size: Number of images per batch
            log_level: Logging level
        """
        self.model_path = model_path
        self.source_dir = Path(source_dir)
        self.target_dir = Path(target_dir)
        self.scene_mode = scene_mode
        self.batch_size = batch_size
        
        # Setup logging
        self._setup_logging(log_level)
        
        # Determine event categories
        if scene_mode:
            self.events = SceneEventConfig.get_scene_events(scene_mode)
            self.scene_desc = SceneEventConfig.SCENE_DESCRIPTIONS.get(
                scene_mode, "General Scenes"
            )
        else:
            self.events = SceneEventConfig.get_all_events()
            self.scene_desc = "All Scene Types (Unified Mode)"
        
        self.logger.info(f"Scene Mode: {self.scene_desc}")
        self.logger.info(f"Event Categories: {len(self.events)} types")
        
        # Create target directory if it doesn't exist
        self.target_dir.mkdir(parents=True, exist_ok=True)
        self.logger.info(f"Target directory ready: {self.target_dir}")
        
        # Model components (event folders will be created on-demand)
        self.model = None
        self.processor = None
    
    def _setup_logging(self, log_level: str):
        """Configure logging."""
        logging.basicConfig(
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)
    

    def load_model(self):
        """Load the vision-language model."""
        self.logger.info(f"Loading model: {self.model_path}")
        
        try:
            self.processor = AutoProcessor.from_pretrained(
                self.model_path,
                trust_remote_code=True
            )
            
            dtype = torch.bfloat16 if (
                torch.cuda.is_available() and 
                torch.cuda.get_device_capability()[0] >= 8
            ) else torch.float16
            
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
    
    def _build_prompt(self, image_list: List[str]) -> str:
        """Build the inference prompt."""
        event_list_str = "\n".join([f"- {event}" for event in self.events])
        
        prompt = self.PROMPT_TEMPLATE.format(
            scene_description=self.scene_desc,
            num_events=len(self.events),
            event_list=event_list_str
        )
        
        # Add image list
        image_lines = [f"{i+1}. {fname}" for i, fname in enumerate(image_list)]
        prompt += "\n" + "\n".join(image_lines)
        
        return prompt
    
    def _get_image_files(self) -> List[str]:
        """Get sorted list of image files."""
        extensions = {'.png', '.jpg', '.jpeg', '.webp', '.bmp', '.gif'}
        files = [
            f.name for f in self.source_dir.iterdir()
            if f.suffix.lower() in extensions and f.is_file()
        ]
        return sorted(files)
    
    def _validate_event_name(self, event_name: str) -> bool:
        """
        Validate the event name.
        
        Checks:
        1. Contains only lowercase, numbers, and underscores
        2. Not empty
        """
        if not event_name:
            self.logger.warning("Validation failed: Empty event name")
            return False
        
        # Check if contains only valid characters
        if not re.match(r'^[a-z0-9_]+$', event_name):
            self.logger.warning(f"Validation failed: Invalid characters in event: {event_name}")
            return False
        
        return True
    
    def _parse_model_output(
        self, 
        response: str, 
        file_map: Dict[int, str]
    ) -> List[Tuple[str, str]]:
        """
        Parse model output and extract event labels.
        
        Returns:
            List of (original_filename, event_name) tuples
        """
        # Match: "number. event_name" (simple format)
        pattern = r'^(\d+)\.\s*([a-z0-9_]+)\s*$'
        matches = re.findall(pattern, response, re.MULTILINE | re.IGNORECASE)
        
        self.logger.debug(f"Found {len(matches)} potential matches in output")
        
        results = []
        for match in matches:
            index_str, event_name = match
            index = int(index_str)
            
            # Get original filename
            original_filename = file_map.get(index)
            if not original_filename:
                self.logger.warning(f"Invalid index {index} in model output")
                continue
            
            # Validate event name
            if not self._validate_event_name(event_name.lower()):
                self.logger.warning(f"Invalid event: {event_name} for {original_filename}")
                continue
            
            results.append((original_filename, event_name.lower()))
        
        return results
    
    def process_batch(self, batch_files: List[str]) -> Dict[str, str]:
        """
        Process a batch of images.
        
        Returns:
            Dictionary mapping original filename -> (event_folder, filename)
        """
        self.logger.info(f"Processing batch of {len(batch_files)} images")
        
        # Load images
        batch_images = []
        file_map = {}
        
        for i, filename in enumerate(batch_files):
            file_path = self.source_dir / filename
            try:
                image = Image.open(file_path).convert("RGB")
                batch_images.append(image)
                file_map[i + 1] = filename
            except Exception as e:
                self.logger.error(f"Failed to load {filename}: {e}")
        
        if not batch_images:
            self.logger.warning("No valid images in batch")
            return {}
        
        # Build prompt
        prompt = self._build_prompt(list(file_map.values()))
        
        # Prepare model input
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "image": img} for img in batch_images
                ] + [
                    {"type": "text", "text": prompt}
                ],
            }
        ]
        
        # Run inference
        try:
            text = self.processor.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True
            )
            inputs = self.processor(
                text=[text], 
                images=batch_images, 
                padding=True, 
                return_tensors="pt"
            ).to(self.model.device)
            
            max_tokens = len(batch_images) * 50
            
            with torch.no_grad():
                outputs = self.model.generate(
                    **inputs,
                    max_new_tokens=max_tokens,
                    do_sample=False,
                )
            
            response = self.processor.decode(outputs[0], skip_special_tokens=True)
            self.logger.debug(f"Model output:\n{response[:500]}...")
            
        except RuntimeError as e:
            if "out of memory" in str(e).lower():
                self.logger.error(f"OOM error! Try reducing batch_size (current: {self.batch_size})")
            else:
                self.logger.error(f"Inference failed: {e}")
            return {}
        except Exception as e:
            self.logger.error(f"Inference error: {e}")
            return {}
        
        # Parse output to get (filename, event_name) pairs
        event_pairs = self._parse_model_output(response, file_map)
        
        if event_pairs:
            self.logger.debug("Parsed event assignments:")
            for orig, event in event_pairs:
                self.logger.debug(f"  {orig} -> {event}")
        
        # Build final move mapping (original_filename -> target_path)
        move_map = {}
        for original_filename, event_name in event_pairs:
            # Keep original filename, just move to event folder
            target_path = self.target_dir / event_name / original_filename
            move_map[original_filename] = target_path
        
        return move_map
    
    def process_images(self):
        """Main processing loop."""
        # Load model
        if self.model is None:
            self.load_model()
        
        # Get images
        image_files = self._get_image_files()
        total = len(image_files)
        
        if total == 0:
            self.logger.warning(f"No images found in {self.source_dir}")
            return
        
        self.logger.info(f"Found {total} images to process")
        
        # Process in batches
        processed = 0
        for i in range(0, total, self.batch_size):
            batch = image_files[i:i + self.batch_size]
            batch_num = i // self.batch_size + 1
            
            self.logger.info(f"\n{'='*60}")
            self.logger.info(f"Batch {batch_num}: {len(batch)} images")
            self.logger.info(f"{'='*60}")
            
            # Process batch
            move_map = self.process_batch(batch)
            
            # Move files to event folders
            for orig, target_path in move_map.items():
                src = self.source_dir / orig
                
                # Extract event name from target path
                event_name = target_path.parent.name
                
                try:
                    if src.exists():
                        # Ensure target folder exists
                        target_path.parent.mkdir(parents=True, exist_ok=True)
                        
                        # Move file
                        shutil.move(str(src), str(target_path))
                        self.logger.info(f"✓ {orig} -> /{event_name}/{orig}")
                        processed += 1
                    else:
                        self.logger.warning(f"File not found: {orig}")
                except Exception as e:
                    self.logger.error(f"Failed to move {orig}: {e}")
            
            # GPU cleanup
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        
        self.logger.info(f"\nCompleted: {processed}/{total} images processed")
    
    def generate_summary(self) -> Dict[str, int]:
        """Generate event distribution summary."""
        summary = {}
        
        # Iterate through event folders
        for event_folder in self.target_dir.iterdir():
            if event_folder.is_dir():
                # Count images in this folder
                count = len([f for f in event_folder.iterdir() if f.is_file()])
                if count > 0:
                    # Convert folder name back to readable format
                    event_display = event_folder.name.replace('_', ' ').title()
                    summary[event_display] = count
        
        return summary


def main():
    parser = argparse.ArgumentParser(
        description="Universal Event Labeling Framework for Anomaly Detection (Folder Organization)"
    )
    
    parser.add_argument("--model-path", required=True, help="Path to vision-language model")
    parser.add_argument("--source-dir", required=True, help="Input directory with images")
    parser.add_argument("--target-dir", required=True, help="Output directory (will create event subfolders)")
    parser.add_argument(
        "--scene-mode",
        choices=[
            "public_roads_transportation",
            "enclosed_indoor_premises",
            "commercial_entertainment",
            "industrial_construction",
            "outdoor_natural",
            "critical_infrastructure"
        ],
        help="Scene-specific mode (omit for unified mode)"
    )
    parser.add_argument("--batch-size", type=int, default=10, help="Images per batch (default: 10)")
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Logging level"
    )
    parser.add_argument("--summary", action="store_true", help="Generate event distribution summary")
    
    args = parser.parse_args()
    
    # Initialize labeler
    labeler = EventLabeler(
        model_path=args.model_path,
        source_dir=args.source_dir,
        target_dir=args.target_dir,
        scene_mode=args.scene_mode,
        batch_size=args.batch_size,
        log_level=args.log_level
    )
    
    # Process images
    labeler.process_images()
    
    # Generate summary
    if args.summary:
        print("\n" + "="*60)
        print("EVENT DISTRIBUTION SUMMARY")
        print("="*60)
        summary = labeler.generate_summary()
        for event, count in sorted(summary.items(), key=lambda x: x[1], reverse=True):
            print(f"{event:40s}: {count:4d} images")
        print("="*60)


if __name__ == "__main__":
    main()