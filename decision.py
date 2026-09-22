"""Decision system.

Turns (component, visible condition, user answers) into one of four outcomes.
It is rule-based on purpose: every recommendation can be explained in plain words,
and the reasons are returned with the result.

Outcomes
  reusable    - potentially reusable as it is
  repairable  - potentially repairable
  recycle     - recycling / material recovery
  testing     - needs further testing before anyone can say
"""
import config
from components import get_component
from questions import get_questions

CODES = {
    "reusable": "Potentially reusable",
    "repairable": "Potentially repairable",
    "recycle": "Recycle / material recovery",
    "testing": "Needs further testing",
}

FINDING_TEXT = {
    "crack": "cracks",
    "burn": "burn marks",
    "corrosion": "corrosion",
    "leakage": "leakage or staining",
    "broken": "broken or missing parts",
}

BAND_LABEL = {
    "none": "No visible damage",
    "minor": "Minor visible damage",
    "moderate": "Moderate visible damage",
    "severe": "Severe visible damage",
}


def severity_band(v):
    if v < 0.20:
        return "none"
    if v < 0.50:
        return "minor"
    if v < 0.75:
        return "moderate"
    return "severe"


def summarise_answers(component, answers):
    """Collapse the user's answers into a few signals the rules can use."""
    answers = answers or {}
    questions = get_questions(component)
    out = {"hazard": False, "function": "unknown", "phys_issue": False,
           "repairable_hint": False, "old": False, "age_factor": 1.0,
           "known": 0, "total": len(questions), "said": []}
    func, phys = [], []
    for q in questions:
        opt = next((o for o in q["options"] if o["value"] == answers.get(q["id"])), None)
        if opt is None:
            continue
        signal = opt.get("signal", "unknown")
        if q["kind"] == "age":
            out["age_factor"] = float(opt.get("age_factor", 1.0))
            out["old"] = bool(opt.get("old"))
            out["known"] += 1
            if opt.get("note"):
                out["said"].append(opt["note"])
            continue
        if signal != "unknown":
            out["known"] += 1
        if opt.get("repairable"):
            out["repairable_hint"] = True
        if opt.get("note"):
            out["said"].append(opt["note"])
        if signal == "hazard":
            out["hazard"] = True
        elif q["kind"] == "function":
            func.append(signal)
        else:
            phys.append(signal)

    known = [s for s in func if s != "unknown"]
    if not known:
        fn = "unknown"
    elif "bad" in known:
        fn = "fails"
    elif "partial" in known:
        fn = "partial"
    else:
        fn = "works"
    out["phys_issue"] = any(s in ("bad", "partial") for s in phys)
    if fn == "works" and out["phys_issue"]:
        fn = "partial"
    out["function"] = fn
    return out


def _visible_text(condition, band):
    if band == "none":
        return "The photo shows no visible damage."
    names = [FINDING_TEXT[k] for k, v in condition.get("findings", {}).items()
             if v >= 0.25 and k in FINDING_TEXT]
    what = ", ".join(names) if names else "damage"
    return f"The photo shows {band} damage ({what})."


def decide(component, condition, answers=None, det_conf=1.0):
    """Return the recommendation, the reasons behind it and a certainty score."""
    info = get_component(component)
    severity = float(condition.get("severity", 0.0))
    band = severity_band(severity)
    cond_conf = float(condition.get("confidence", 0.5))
    s = summarise_answers(component, answers)
    fn = s["function"]
    can_repair = info["repairable"] or s["repairable_hint"]

    reasons = [_visible_text(condition, band)]
    reasons.extend(s["said"])

    if s["hazard"]:
        code = "recycle"
        reasons.append("A safety warning sign was reported, so this part should go to recycling, not reuse.")
    elif band == "severe":
        if fn == "works":
            code = "testing"
            reasons.append("The photo shows severe damage but you say it works. Those two disagree, so it needs a supervised test.")
        else:
            code = "recycle"
            reasons.append("Severe damage makes reuse or repair unlikely, so material recovery is the best route.")
    elif band == "moderate":
        if fn in ("works", "unknown"):
            code = "testing"
            reasons.append("Moderate damage may or may not affect how it works, so it needs testing.")
        elif can_repair:
            code = "repairable"
            reasons.append("It has a fault, but this type of part can usually be repaired.")
        else:
            code = "recycle"
            reasons.append("It has a fault and this type of part is not normally repaired.")
    elif band == "minor":
        if fn == "works":
            code = "reusable"
            reasons.append("Damage is minor and it works, so it looks reusable.")
        elif fn == "unknown":
            code = "testing"
            reasons.append("Damage is minor, but nothing tells us whether it still works.")
        elif fn == "partial":
            code = "repairable" if can_repair else "testing"
            reasons.append("It partly works and has some wear." + (
                " Repair looks worthwhile." if can_repair else " A test will show whether it is still useful."))
        else:
            code = "repairable" if can_repair else "recycle"
            reasons.append("It has stopped working." + (
                " This type of part can usually be repaired." if can_repair else " It is not normally repaired."))
    else:  # no visible damage
        if fn == "works":
            code = "reusable"
            reasons.append("No visible damage and it works, so it looks reusable.")
        elif fn == "partial":
            code = "repairable" if can_repair else "testing"
            reasons.append("It looks fine but only partly works." + (
                " Repair looks worthwhile." if can_repair else " A test will show whether it is still useful."))
        elif fn == "fails":
            code = "repairable" if can_repair else "recycle"
            reasons.append("It looks fine but does not work." + (
                " This type of part can usually be repaired." if can_repair else " It is not normally repaired."))
        else:
            if not info["safety_critical"] and cond_conf >= config.LOW_CONDITION_CONF:
                code = "reusable"
                reasons.append("No visible damage, so it may be reusable once it passes a quick test.")
            else:
                code = "testing"
                reasons.append("It looks undamaged, but faults in this kind of part are often invisible, so it needs testing.")

    # Guard rails that only ever make the outcome more cautious.
    if code == "reusable" and s["old"] and info["ages_out"]:
        code = "testing"
        reasons.append("This type of part degrades with age, so test it before trusting it.")
    if code in ("reusable", "repairable") and s["known"] == 0 and det_conf < config.LOW_DETECTION_CONF:
        code = "testing"
        reasons.append("We are not fully sure what this component is, so it needs checking first.")

    base = min(det_conf, cond_conf)
    certainty = base + (1 - base) * 0.5 * (s["known"] / max(1, s["total"]))
    if code == "testing":
        certainty = min(certainty, 0.6)
    certainty = round(max(0.0, min(1.0, certainty)), 2)
    label = "High" if certainty >= 0.8 else "Medium" if certainty >= 0.6 else "Low"

    return {
        "code": code,
        "label": CODES[code],
        "reasons": reasons,
        "next_step": info["notes"][code],
        "certainty": certainty,
        "certainty_label": label,
        "severity_band": band,
        "function_signal": fn,
        "hazard": s["hazard"],
        "age_factor": s["age_factor"],
    }
