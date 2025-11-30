#!/bin/bash

# Batch Image-to-Text Prompt Generation Script with Category Mapping

# ========== Configuration ==========
IMAGE_DIR="/data/images"              # Root image directory with subdirectories
PROMPT_DIR="/data/prompts"            # Output prompt directory
MODEL_PATH="/models/Qwen2.5-VL-32B"   # Vision-language model path
CATEGORY_MAP_FILE="category_map.txt"  # Category mapping file

# ========== Parse Arguments ==========
MODE="run"  # Default mode

if [ "$1" == "init" ]; then
    MODE="init"
elif [ "$1" == "run" ]; then
    MODE="run"
elif [ -n "$1" ]; then
    echo "Usage: $0 [init|run]"
    echo "  init - Generate category mapping file for customization"
    echo "  run  - Process images with category mappings (default)"
    exit 1
fi

# ========== Basic Checks ==========
[ ! -d "$IMAGE_DIR" ] && echo "Error: Image directory not found" && exit 1

# ========== Auto-init if needed ==========
if [ "$MODE" == "run" ] && [ ! -f "$CATEGORY_MAP_FILE" ]; then
    echo "======================================"
    echo "Category mapping file not found!"
    echo "======================================"
    echo ""
    echo "This is your first time running this script."
    echo "You need to generate category mapping first."
    echo ""
    read -p "Generate now? (y/n): " confirm
    
    if [[ "$confirm" == "y" ]]; then
        MODE="init"
        echo ""
    else
        echo ""
        echo "Please run: $0 init"
        exit 1
    fi
fi

# ========== INIT Mode: Generate Category Mapping ==========
if [ "$MODE" == "init" ]; then
    if [ -f "$CATEGORY_MAP_FILE" ] && [ "$1" == "init" ]; then
        echo "Warning: $CATEGORY_MAP_FILE already exists"
        read -p "Overwrite? (y/n): " confirm
        [[ "$confirm" != "y" ]] && echo "Cancelled" && exit 0
    fi
    
    echo "Generating category mapping file: $CATEGORY_MAP_FILE"
    echo "# Category Mapping Configuration" > "$CATEGORY_MAP_FILE"
    echo "# Format: folder_name=category_name" >> "$CATEGORY_MAP_FILE"
    echo "# Examples:" >> "$CATEGORY_MAP_FILE"
    echo "#   theft=theft,theft_Short              # Mixed (both long and short)" >> "$CATEGORY_MAP_FILE"
    echo "#   fire=fire                            # Long video only" >> "$CATEGORY_MAP_FILE"
    echo "#   accident=accident_Short              # Short video only" >> "$CATEGORY_MAP_FILE"
    echo "#   other=normal,normal_Short            # Custom names (mixed)" >> "$CATEGORY_MAP_FILE"
    echo "" >> "$CATEGORY_MAP_FILE"
    
    # Auto-generate default mappings (all mixed by default)
    find "$IMAGE_DIR" -maxdepth 1 -type d | tail -n +2 | sort | while read CATEGORY_DIR; do
        FOLDER_NAME=$(basename "$CATEGORY_DIR")
        
        # Special handling for "other" folder → map to "normal"
        if [ "$FOLDER_NAME" == "other" ]; then
            echo "$FOLDER_NAME=normal,normal_Short" >> "$CATEGORY_MAP_FILE"
        else
            # Default: all folders generate both long and short versions
            echo "$FOLDER_NAME=${FOLDER_NAME},${FOLDER_NAME}_Short" >> "$CATEGORY_MAP_FILE"
        fi
    done
    
    echo ""
    echo "======================================"
    echo "✓ Category mapping file generated!"
    echo "  File: $CATEGORY_MAP_FILE"
    echo ""
    echo "Next steps:"
    echo "  1. Edit '$CATEGORY_MAP_FILE' to customize categories"
    echo "  2. Run: $0"
    echo "======================================"
    echo ""
    exit 0
fi

# ========== RUN Mode: Process Images ==========
[ ! -f "step3.py" ] && echo "Error: step3.py not found" && exit 1

mkdir -p "$PROMPT_DIR" logs

# Load Category Mappings
declare -A CATEGORY_MAP

while IFS='=' read -r folder category; do
    # Skip comments and empty lines
    [[ "$folder" =~ ^#.*$ ]] && continue
    [[ -z "$folder" ]] && continue
    
    # Trim whitespace
    folder=$(echo "$folder" | xargs)
    category=$(echo "$category" | xargs)
    
    CATEGORY_MAP["$folder"]="$category"
done < "$CATEGORY_MAP_FILE"

echo "Loaded category mappings:"
for folder in "${!CATEGORY_MAP[@]}"; do
    echo "  $folder → ${CATEGORY_MAP[$folder]}"
done
echo ""

echo "Starting processing..."
echo "Image Dir: $IMAGE_DIR"
echo "Output Dir: $PROMPT_DIR"
echo ""

# ========== Process Each Category ==========
find "$IMAGE_DIR" -maxdepth 1 -type d | tail -n +2 | sort | while read CATEGORY_DIR; do
    FOLDER_NAME=$(basename "$CATEGORY_DIR")
    
    # Get category from mapping (fallback to folder name if not found)
    if [ -n "${CATEGORY_MAP[$FOLDER_NAME]}" ]; then
        CATEGORIES="${CATEGORY_MAP[$FOLDER_NAME]}"
    else
        CATEGORIES="$FOLDER_NAME"
        echo "Warning: No mapping for '$FOLDER_NAME', using folder name as category"
    fi
    
    # Split categories by comma (for mixed mode like "normal,normal_Short")
    IFS=',' read -ra CATEGORY_ARRAY <<< "$CATEGORIES"
    
    # Process each category
    for CATEGORY in "${CATEGORY_ARRAY[@]}"; do
        CATEGORY=$(echo "$CATEGORY" | xargs)  # Trim whitespace
        
        CATEGORY_PROMPT_DIR="$PROMPT_DIR/$CATEGORY"
        mkdir -p "$CATEGORY_PROMPT_DIR"
        
        # Count progress
        IMG_COUNT=$(find "$CATEGORY_DIR" -name "*.jpg" | wc -l)
        PROMPT_COUNT=$(find "$CATEGORY_PROMPT_DIR" -name "*.jpg_prompt.txt" | wc -l)
        
        echo "[$FOLDER_NAME → $CATEGORY] Images: $IMG_COUNT, Generated: $PROMPT_COUNT"
        
        # Skip conditions: no images or already completed
        [ "$IMG_COUNT" -eq 0 ] && echo "  → Skip (no images)" && continue
        [ "$PROMPT_COUNT" -ge "$IMG_COUNT" ] && echo "  → Skip (completed)" && continue
        
        # Core: call Python script to generate prompts
        echo "  → Processing..."
        python step3.py \
            --use_prompt_extend \
            --image_dir "$CATEGORY_DIR" \
            --prompt_dir "$CATEGORY_PROMPT_DIR" \
            --prompt_extend_model "$MODEL_PATH" \
            --category "$CATEGORY" \
            &>> "logs/i2t_$CATEGORY.log"
        
        [ $? -eq 0 ] && echo "  ✓ Done" || echo "  ✗ Failed (check logs/i2t_$CATEGORY.log)"
    done
done

# ========== Generate Global Index ==========
echo ""
echo "Creating global data list..."
GLOBAL_LIST="$PROMPT_DIR/global_data_list.txt"

if [ -s "$GLOBAL_LIST" ]; then
    echo "Already exists: $GLOBAL_LIST ($(wc -l < "$GLOBAL_LIST") entries)"
else
    > "$GLOBAL_LIST"
    
    find "$IMAGE_DIR" -maxdepth 1 -type d | tail -n +2 | sort | while read CATEGORY_DIR; do
        FOLDER_NAME=$(basename "$CATEGORY_DIR")
        
        # Get category from mapping
        if [ -n "${CATEGORY_MAP[$FOLDER_NAME]}" ]; then
            CATEGORIES="${CATEGORY_MAP[$FOLDER_NAME]}"
        else
            CATEGORIES="$FOLDER_NAME"
        fi
        
        # Split categories by comma
        IFS=',' read -ra CATEGORY_ARRAY <<< "$CATEGORIES"
        
        # Add entries for each category
        for CATEGORY in "${CATEGORY_ARRAY[@]}"; do
            CATEGORY=$(echo "$CATEGORY" | xargs)
            
            CATEGORY_PROMPT_DIR="$PROMPT_DIR/$CATEGORY"
            [ ! -d "$CATEGORY_PROMPT_DIR" ] && continue
            
            find "$CATEGORY_DIR" -name "*.jpg" | sort | while read IMG; do
                PROMPT="$CATEGORY_PROMPT_DIR/$(basename "$IMG")_prompt.txt"
                [ -f "$PROMPT" ] && echo "$IMG,$PROMPT" >> "$GLOBAL_LIST"
            done
        done
    done
    
    echo "Created: $GLOBAL_LIST ($(wc -l < "$GLOBAL_LIST") entries)"
fi

echo ""
echo "✓ All done!"