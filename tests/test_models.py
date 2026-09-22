"""Check that the trained-model code paths read Ultralytics-style results correctly.

Fake result objects mimic the parts of the Ultralytics API the app uses, so these
tests run without torch or real weights.
"""
import numpy as np

from condition import ConditionAI, map_class
from detector import Detector


class T(list):
    """Behaves like a 1-D tensor for the calls we make."""
    def tolist(self):
        return list(self)


class FakeBox:
    def __init__(self, cls, conf, xyxy):
        self.cls, self.conf, self.xyxy = [cls], [conf], [T(xyxy)]


class FakeResult:
    def __init__(self, names, boxes=None, probs=None):
        self.names, self.boxes = names, boxes or []
        self.probs = type("P", (), {"data": T(probs)})() if probs is not None else None


class FakeModel:
    def __init__(self, result):
        self.result = result

    def predict(self, *_, **__):
        return [self.result]


IMG = np.zeros((200, 300, 3), np.uint8)


def test_detector_reads_yolo_boxes_and_maps_names():
    d = Detector(weights="/nonexistent.pt")
    d.model = FakeModel(FakeResult({0: "Arduino_Uno", 1: "capacitor"},
                                   [FakeBox(1, 0.4, [10, 10, 40, 40]), FakeBox(0, 0.9, [20, 20, 250, 180])]))
    out = d._detect_model(IMG)
    assert [o["component"] for o in out] == ["arduino", "capacitor"]     # biggest confident box first
    assert out[0]["box"] == [20, 20, 250, 180]


def test_condition_classifier_weights():
    c = ConditionAI(weights="/nonexistent.pt")
    c.model = FakeModel(FakeResult({0: "good", 1: "burnt", 2: "cracked"}, probs=[0.1, 0.8, 0.1]))
    r = c._assess_model(IMG)
    assert r["mode"] == "model" and r["findings"] == {"burn": 0.8}
    assert r["severity"] == 0.72 and r["confidence"] == 0.8


def test_condition_detector_weights():
    c = ConditionAI(weights="/nonexistent.pt")
    c.model = FakeModel(FakeResult({0: "corrosion", 1: "crack"}, [FakeBox(0, 0.7, [0, 0, 5, 5])]))
    r = c._assess_model(IMG)
    assert r["findings"] == {"corrosion": 0.7} and r["label"] == "Minor visible damage"


def test_class_name_mapping():
    assert map_class("Battery_Leakage") == "leakage"
    assert map_class("Burnt") == "burn"
    assert map_class("cracked_casing") == "crack"
    assert map_class("good_condition") == "good"
    assert map_class("no_damage") == "good"
    assert map_class("undamaged") == "good"
    assert map_class("not_working") == "broken"
    assert map_class("broken") == "broken"          # must not be mistaken for "ok"
    assert map_class("something_else") is None
