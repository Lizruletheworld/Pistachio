import argparse
from pathlib import Path

import cv2

from pistachio_paths import pistachio_video_test_root


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--video-root", default=None, help="Pistachio VAD test video root. Defaults to PISTACHIO_DATASET_ROOT/VAD/video/test.")
    parser.add_argument("--output", default="annotations/pistachio_anomaly_test.txt")
    args = parser.parse_args()

    video_root = Path(args.video_root) if args.video_root else pistachio_video_test_root()
    output = Path(args.output)
    if not output.is_absolute():
        output = Path(__file__).resolve().parent / output
    output.parent.mkdir(parents=True, exist_ok=True)

    videos = sorted(video_root.rglob("*.mp4"))
    with output.open("w") as f:
        for path in videos:
            cap = cv2.VideoCapture(str(path))
            frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            cap.release()
            label = 0 if "normal" in path.parts else 1
            segments = 0 if label == 0 else 1
            f.write(f"{path.stem} {label} {frame_count} {segments}\n")
    print(f"Wrote {len(videos)} records to {output}")


if __name__ == "__main__":
    main()
