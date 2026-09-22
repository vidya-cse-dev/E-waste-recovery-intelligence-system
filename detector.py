"""Stage 1: identify the component with YOLO.

If trained weights are found at config.DETECTOR_WEIGHTS they are used. Otherwise the
detector runs in DEMO mode (component guessed from the file name or image contents),
so the rest of the system can still be run and shown. The UI labels demo mode clearly.
"""
import hashlib
from pathlib import Path

import cv2

import config
from components import COMPONENTS, canonical_name

DEMO_ORDER = list(COMPONENTS)


class Detector:
    def __init__(self, weights=None):
        self.model = None
        self.mode = "demo"
        self.load_error = None
        weights = Path(weights or config.DETECTOR_WEIGHTS)
        if weights.exists():
            try:
                from ultralytics import YOLO
                self.model = YOLO(str(weights))
                self.mode = "model"
            except Exception as exc:  # missing package, bad file, etc.
                self.load_error = str(exc)
                print(f"[detector] could not load {weights}: {exc}. Falling back to demo mode.")

    def detect(self, img, filename=""):
        return self._detect_model(img) if self.model is not None else self._detect_demo(img, filename)

    def _detect_model(self, img):
        result = self.model.predict(img, conf=config.DETECTION_CONF, verbose=False)[0]
        found = []
        for box in result.boxes:
            raw = result.names[int(box.cls[0])]
            x1, y1, x2, y2 = [int(v) for v in box.xyxy[0].tolist()]
            found.append({"component": canonical_name(raw), "raw_label": raw,
                          "confidence": float(box.conf[0]), "box": [x1, y1, x2, y2]})
        found.sort(key=lambda d: d["confidence"] * max(1, (d["box"][2] - d["box"][0]) * (d["box"][3] - d["box"][1])),
                   reverse=True)
        return found

    def _detect_demo(self, img, filename):
        h, w = img.shape[:2]
        name = canonical_name(Path(filename).stem)
        digest = int(hashlib.md5(cv2.resize(img, (16, 16)).tobytes()).hexdigest(), 16)
        key = name if name in COMPONENTS else DEMO_ORDER[digest % len(DEMO_ORDER)]
        conf = 0.55 + (digest % 40) / 100
        return [{"component": key, "raw_label": key, "confidence": round(conf, 2),
                 "box": [int(w * 0.1), int(h * 0.1), int(w * 0.9), int(h * 0.9)]}]
