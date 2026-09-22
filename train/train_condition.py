"""Train the Condition AI as an image classifier (Ultralytics YOLO classification).

Dataset layout (one folder per class; folder names should say what the class is,
for example good, cracked, burnt, corroded, leaking, broken):

    condition_data/
        train/good/*.jpg   train/burnt/*.jpg   train/cracked/*.jpg ...
        val/good/*.jpg     val/burnt/*.jpg     val/cracked/*.jpg  ...

Run:
    python train/train_condition.py --data condition_data --epochs 30

The best weights are copied to models/condition_model.pt, which the app loads
automatically. Class names are mapped to damage types by condition.map_class().
"""
import argparse
import shutil
from pathlib import Path

from ultralytics import YOLO


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True, help="folder containing train/ and val/")
    ap.add_argument("--epochs", type=int, default=30)
    ap.add_argument("--imgsz", type=int, default=224)
    ap.add_argument("--base", default="yolov8n-cls.pt", help="pretrained classification checkpoint")
    args = ap.parse_args()

    model = YOLO(args.base)
    model.train(data=args.data, epochs=args.epochs, imgsz=args.imgsz)
    metrics = model.val()
    print("Top-1 accuracy:", getattr(metrics, "top1", "n/a"))

    dest = Path(__file__).resolve().parents[1] / "models" / "condition_model.pt"
    shutil.copy(model.trainer.best, dest)
    print(f"Saved {dest}")


if __name__ == "__main__":
    main()
