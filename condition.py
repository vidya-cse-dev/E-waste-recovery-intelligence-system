"""Stage 2: Condition AI - look for visible damage.

Two modes:
  model     - your trained condition model at config.CONDITION_WEIGHTS
              (Ultralytics classification or detection weights)
  heuristic - an OpenCV colour and edge analysis used when no model is present

Both return the same structure: findings (0-1 per damage type), a severity score,
a confidence, and a short label.
"""
import re
from pathlib import Path

import cv2
import numpy as np

import config
from decision import BAND_LABEL, severity_band

DAMAGE_WEIGHTS = {"crack": 0.6, "burn": 0.9, "corrosion": 0.6, "leakage": 0.85, "broken": 0.8}

_GOOD_TOKENS = {"good", "ok", "okay", "normal", "intact", "healthy", "clean", "undamaged", "working", "fine"}
_DAMAGE_PREFIXES = [
    ("crack", ("crack", "fractur")),
    ("burn", ("burn", "char", "scorch")),
    ("corrosion", ("corro", "rust", "oxid")),
    ("leakage", ("leak", "bulg", "swell", "stain")),
    ("broken", ("broken", "missing", "snap", "damag")),
]


def map_class(name):
    """Map a class label from your model ('Burnt', 'no_damage', 'battery_leak') to a damage type.

    Returns 'good', one of the damage keys, or None if the label is not recognised.
    """
    tokens = [t for t in re.split(r"[^a-z]+", str(name).lower()) if t]
    if "undamaged" in tokens or ("no" in tokens and any(t.startswith("damag") for t in tokens)):
        return "good"
    if "not" in tokens or "non" in tokens:
        return "broken"
    for key, prefixes in _DAMAGE_PREFIXES:
        if any(t.startswith(p) for t in tokens for p in prefixes):
            return key
    if any(t in _GOOD_TOKENS for t in tokens):
        return "good"
    return None


def _finish(findings, confidence, mode, notes=None):
    findings = {k: round(float(v), 2) for k, v in findings.items() if v >= 0.15}
    severity = max([DAMAGE_WEIGHTS.get(k, 0.7) * v for k, v in findings.items()] or [0.0])
    severity = round(min(1.0, severity), 2)
    return {"findings": findings, "severity": severity, "confidence": round(float(confidence), 2),
            "label": BAND_LABEL[severity_band(severity)], "mode": mode, "notes": notes or []}


class ConditionAI:
    def __init__(self, weights=None):
        self.model = None
        self.mode = "heuristic"
        self.load_error = None
        weights = Path(weights or config.CONDITION_WEIGHTS)
        if weights.exists():
            try:
                from ultralytics import YOLO
                self.model = YOLO(str(weights))
                self.mode = "model"
            except Exception as exc:
                self.load_error = str(exc)
                print(f"[condition] could not load {weights}: {exc}. Using the OpenCV heuristic instead.")

    def assess(self, crop, component=""):
        if self.model is not None:
            return self._assess_model(crop)
        return self._assess_heuristic(crop, component)

    # ---- trained model -------------------------------------------------
    def _assess_model(self, crop):
        res = self.model.predict(crop, verbose=False)[0]
        findings = {}
        if getattr(res, "probs", None) is not None:          # classification weights
            probs = res.probs.data.tolist()
            for i, p in enumerate(probs):
                key = map_class(res.names[i])
                if key and key != "good":
                    findings[key] = max(findings.get(key, 0.0), p)
            confidence = max(probs)
        else:                                                 # detection weights
            best = 0.0
            for box in res.boxes:
                key = map_class(res.names[int(box.cls[0])])
                conf = float(box.conf[0])
                best = max(best, conf)
                if key and key != "good":
                    findings[key] = max(findings.get(key, 0.0), conf)
            confidence = best if best else 0.7
        return _finish(findings, confidence, "model")

    # ---- OpenCV fallback -----------------------------------------------
    def _assess_heuristic(self, crop, component):
        h0, w0 = crop.shape[:2]
        scale = 320.0 / max(h0, w0)
        img = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA) if scale < 1 else crop
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        H, S, V = [c.astype(np.int16) for c in cv2.split(hsv)]
        total = float(H.size)

        def frac(mask):
            return float(np.count_nonzero(mask)) / total

        def scaled(fraction, full, floor=0.004):
            return 0.0 if fraction < floor else min(1.0, fraction / full)

        burn = scaled(frac((H >= 5) & (H <= 22) & (S >= 60) & (V >= 25) & (V <= 110)), 0.05)
        verdigris = frac((H >= 75) & (H <= 100) & (S >= 40) & (S <= 150) & (V >= 120))
        rust = frac((H >= 6) & (H <= 20) & (S >= 130) & (V > 110) & (V <= 200))
        corrosion = scaled(verdigris + rust, 0.08)
        leakage = 0.0
        if component in ("battery", "capacitor"):
            leakage = scaled(frac((H >= 15) & (H <= 35) & (S >= 70) & (S <= 190) & (V >= 90) & (V <= 210)), 0.06)

        gray_raw = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        gray = cv2.GaussianBlur(gray_raw, (3, 3), 0)
        blackhat = cv2.morphologyEx(gray, cv2.MORPH_BLACKHAT,
                                    cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9)))
        thin = (blackhat > max(20, 0.5 * blackhat.max())).astype(np.uint8)
        n, _, stats, _ = cv2.connectedComponentsWithStats(cv2.dilate(thin, np.ones((3, 3), np.uint8)))
        side = min(gray.shape)
        length = 0.0
        for i in range(1, n):
            w, h, area = stats[i, cv2.CC_STAT_WIDTH], stats[i, cv2.CC_STAT_HEIGHT], stats[i, cv2.CC_STAT_AREA]
            long_side, short_side = max(w, h), max(1, min(w, h))
            if long_side > 0.18 * side and long_side / short_side > 4 and area / (w * h) < 0.35:
                length += long_side
        crack = min(1.0, length / (0.9 * side)) * 0.8
        if component == "arduino":       # PCB traces and silkscreen look like thin lines
            crack *= 0.5

        findings = {"burn": burn, "corrosion": corrosion, "leakage": leakage, "crack": crack}

        sharp = min(1.0, cv2.Laplacian(gray_raw, cv2.CV_64F).var() / 80.0)
        size_q = min(1.0, min(h0, w0) / 160.0)
        quality = min(sharp, size_q)   # the weakest link decides
        provisional = max([DAMAGE_WEIGHTS[k] * v for k, v in findings.items() if v >= 0.15] or [0.0])
        margin = min(1.0, min(abs(provisional - t) for t in (0.2, 0.5, 0.75)) / 0.15)
        confidence = min(0.85, 0.35 + 0.30 * quality + 0.20 * margin)

        notes = ["Checked with the OpenCV fallback (no trained condition model found). "
                 "Broken or missing parts cannot be judged this way, so the questions cover them."]
        if quality < 0.5:
            notes.append("The photo is small or blurry, which lowers confidence.")
        return _finish(findings, confidence, "heuristic", notes)
