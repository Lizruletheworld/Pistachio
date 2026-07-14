import argparse
import json
import os
from pathlib import Path

from pistachio_paths import pistachio_dataset_root


def get_category(path):
    parts = Path(path).parts
    if "normal" in parts:
        return "Normal"
    if "anomaly" in parts:
        idx = parts.index("anomaly")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    return "Unknown"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset-root", default=None)
    parser.add_argument("--annotation-json", default=None)
    parser.add_argument("--test-list", default=None)
    parser.add_argument("--output", default="Pistachio/annotations/Temporal_Anomaly_Annotation_for_Testing_Videos.txt")
    args = parser.parse_args()

    dataset_root = Path(args.dataset_root) if args.dataset_root else pistachio_dataset_root()
    annotation_json = Path(args.annotation_json) if args.annotation_json else dataset_root / "VAD" / "annotation_updated.json"
    test_list = Path(args.test_list) if args.test_list else dataset_root / "VAD" / "video" / "test-list.txt"
    output = Path(args.output)
    if not output.is_absolute():
        output = Path(__file__).resolve().parent / output
    output.parent.mkdir(parents=True, exist_ok=True)

    with annotation_json.open("r", encoding="utf-8") as f:
        annotations = json.load(f)
    anno_dict = {os.path.basename(item["path"]): item for item in annotations}

    lines = []
    for video_path in test_list.read_text(encoding="utf-8").splitlines():
        if not video_path.strip():
            continue
        video_name = os.path.basename(video_path.strip())
        video_key = os.path.splitext(video_name)[0]
        category = get_category(video_path)
        anno = anno_dict.get(video_key, {})
        s1, e1 = anno.get("start1", -1), anno.get("end1", -1)
        s2, e2 = anno.get("start2", -1), anno.get("end2", -1)
        lines.append(f"{video_name}  {category}  {s1}  {e1}  {s2}  {e2}")

    output.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {len(lines)} records to {output}")


if __name__ == "__main__":
    main()
