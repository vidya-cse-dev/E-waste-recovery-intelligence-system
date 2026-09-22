"""End-to-end flow: detect -> inspect -> (ask) -> decide -> value -> log."""
import uuid

import cv2

import config
import database
from components import COMPONENTS, canonical_name, display_name, get_component
from condition import ConditionAI
from decision import decide, severity_band
from detector import Detector
from questions import public_questions
from value import estimate

detector = Detector()
condition_ai = ConditionAI()


def ask_reasons(component, det_conf, cond):
    """Why (if at all) the photo alone is not enough."""
    reasons = []
    band = severity_band(cond["severity"])
    if det_conf < config.LOW_DETECTION_CONF:
        reasons.append("We are not fully sure which component this is.")
    if cond["confidence"] < config.LOW_CONDITION_CONF:
        reasons.append("The photo does not show enough detail to judge the condition confidently.")
    if get_component(component)["safety_critical"] and band == "none":
        reasons.append(f"{display_name(component)} faults are often internal and cannot be seen in a photo.")
    if band == "moderate":
        reasons.append("The visible damage may or may not affect how it works.")
    return reasons


def _annotate(img, detections, primary, out_path):
    vis = img.copy()
    scale = max(1, round(max(vis.shape[:2]) / 700))
    for d in detections:
        x1, y1, x2, y2 = d["box"]
        colour = (58, 75, 30) if d is primary else (160, 160, 160)
        cv2.rectangle(vis, (x1, y1), (x2, y2), colour, 2 * scale)
        text = f"{d['component']} {int(d['confidence'] * 100)}%"
        (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6 * scale, scale)
        cv2.rectangle(vis, (x1, max(0, y1 - th - 10 * scale)), (x1 + tw + 8 * scale, y1), colour, -1)
        cv2.putText(vis, text, (x1 + 4 * scale, y1 - 5 * scale), cv2.FONT_HERSHEY_SIMPLEX,
                    0.6 * scale, (255, 255, 255), scale, cv2.LINE_AA)
    cv2.imwrite(str(out_path), vis)


def _decision_payload(rec_id, component, cond, answers, det_conf):
    decision = decide(component, cond, answers, det_conf)
    val = estimate(component, decision["code"], cond["severity"], decision["age_factor"], decision["hazard"])
    database.finalize(rec_id, answers, decision, val)
    return {
        "code": decision["code"], "label": decision["label"], "reasons": decision["reasons"],
        "next_step": decision["next_step"], "certainty": decision["certainty"],
        "certainty_label": decision["certainty_label"], "value": val,
    }


def analyze(image_path, filename, override=None):
    img = cv2.imread(str(image_path))
    if img is None:
        raise ValueError("That file could not be read as an image.")
    h, w = img.shape[:2]

    if override:
        key = canonical_name(override)
        detections = [{"component": key, "raw_label": override, "confidence": 1.0, "box": [0, 0, w, h]}]
        det_mode = "manual"
    else:
        detections = detector.detect(img, filename)
        det_mode = detector.mode
    if not detections:
        return {"detected": False,
                "message": "We could not recognise a component in this photo. Try a closer, well-lit photo, "
                           "or choose the component from the list."}

    primary = detections[0]
    component, det_conf = primary["component"], primary["confidence"]
    x1, y1, x2, y2 = primary["box"]
    padx, pady = int((x2 - x1) * 0.08), int((y2 - y1) * 0.08)
    crop = img[max(0, y1 - pady):min(h, y2 + pady), max(0, x1 - padx):min(w, x2 + padx)]
    if crop.size == 0:
        crop = img
    cond = condition_ai.assess(crop, component)

    stem = uuid.uuid4().hex
    annotated_name = f"{stem}.jpg"
    _annotate(img, detections, primary, config.ANNOTATED_DIR / annotated_name)

    reasons = ask_reasons(component, det_conf, cond)
    others = [{"component": d["component"], "confidence": round(d["confidence"], 2)} for d in detections[1:]]
    rec_id = database.insert_analysis({
        "image_file": image_path.name, "annotated_file": annotated_name, "component": component,
        "component_display": display_name(component), "det_conf": round(det_conf, 2), "detector_mode": det_mode,
        "condition_label": cond["label"], "severity": cond["severity"], "cond_conf": cond["confidence"],
        "condition_mode": cond["mode"], "findings": cond["findings"], "other_detections": others,
        "ask_reasons": reasons,
    })

    payload = {
        "detected": True, "id": rec_id,
        "annotated_url": f"/media/annotated/{annotated_name}",
        "component": component, "component_display": display_name(component),
        "det_conf": round(det_conf, 2), "detector_mode": det_mode, "other_detections": others,
        "condition": {"label": cond["label"], "severity": cond["severity"], "confidence": cond["confidence"],
                      "findings": cond["findings"], "mode": cond["mode"], "notes": cond["notes"]},
        "ask_reasons": reasons, "questions": public_questions(component),
    }
    if not reasons:
        payload["decision"] = _decision_payload(rec_id, component, cond, {}, det_conf)
    return payload


def decide_record(rec_id, answers):
    rec = database.get(rec_id)
    if rec is None:
        raise KeyError("Unknown analysis id.")
    cond = {"severity": rec["severity"], "confidence": rec["cond_conf"],
            "findings": rec["findings"] or {}, "label": rec["condition_label"]}
    return _decision_payload(rec_id, rec["component"], cond, answers or {}, rec["det_conf"])


def component_choices():
    return [{"key": k, "name": v["display"]} for k, v in COMPONENTS.items()]
