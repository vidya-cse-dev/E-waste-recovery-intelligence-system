"""Generate sample records so the dashboard and Power BI have something to show.

    python seed_data.py            writes powerbi/ewaste_sample_records.csv
    python seed_data.py --insert   also adds the rows to the app database

The rows are SYNTHETIC. They are produced by running the real decision and value
code on random-but-plausible inputs, and they are flagged is_sample = 1.
Never present them as results from real photos.
"""
import argparse
import csv
import json
import random
from datetime import datetime, timedelta

import database
from components import COMPONENTS, display_name
from decision import BAND_LABEL, decide, severity_band
from condition import DAMAGE_WEIGHTS
from questions import get_questions
from value import estimate

COMPONENT_WEIGHTS = {"battery": 30, "arduino": 18, "motor": 20, "sensor": 20, "capacitor": 12}
SIGNAL_WEIGHTS = {"good": 50, "partial": 20, "bad": 12, "unknown": 13, "hazard": 5}


def make_row(rng, when):
    component = rng.choices(list(COMPONENT_WEIGHTS), weights=list(COMPONENT_WEIGHTS.values()))[0]
    findings = {}
    if rng.random() > 0.45:
        allowed = [k for k in DAMAGE_WEIGHTS if k != "leakage" or component in ("battery", "capacitor")]
        for kind in rng.sample(allowed, k=rng.choice([1, 1, 2])):
            findings[kind] = round(rng.uniform(0.25, 1.0), 2)
    severity = round(max([DAMAGE_WEIGHTS[k] * v for k, v in findings.items()] or [0.0]), 2)
    cond = {"severity": severity, "confidence": round(rng.uniform(0.55, 0.88), 2), "findings": findings}
    det_conf = round(rng.uniform(0.45, 0.97), 2)

    answers = {}
    if cond["confidence"] < 0.75 or severity_band(severity) == "moderate" or COMPONENTS[component]["safety_critical"] \
            or rng.random() < 0.3:
        for q in get_questions(component):
            if rng.random() < 0.85:
                weights = [SIGNAL_WEIGHTS.get(o.get("signal", "unknown"), 25) for o in q["options"]]
                answers[q["id"]] = rng.choices(q["options"], weights=weights)[0]["value"]

    d = decide(component, cond, answers, det_conf)
    v = estimate(component, d["code"], severity, d["age_factor"], d["hazard"])
    return {
        "created_at": when.isoformat(timespec="seconds"), "component": component,
        "component_display": display_name(component), "det_conf": det_conf, "detector_mode": "sample",
        "condition_label": BAND_LABEL[severity_band(severity)], "severity": severity, "cond_conf": cond["confidence"],
        "condition_mode": "sample", "findings": findings, "ask_reasons": [], "answers": answers,
        "decision": d["code"], "decision_label": d["label"], "reasons": d["reasons"], "certainty": d["certainty"],
        "value_low": v["low"], "value_high": v["high"], "value_estimate": v["estimate"],
        "status": "final", "is_sample": 1,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=150)
    ap.add_argument("--insert", action="store_true", help="also insert into the app database")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    rng = random.Random(args.seed)
    now = datetime.now().replace(microsecond=0)
    rows = [make_row(rng, now - timedelta(days=rng.randint(0, 60), hours=rng.randint(0, 23))) for _ in range(args.n)]
    rows.sort(key=lambda r: r["created_at"])

    with open("powerbi/ewaste_sample_records.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(database.CSV_COLUMNS)
        for i, r in enumerate(rows, 1):
            w.writerow([i, r["created_at"][:10], r["component_display"], r["condition_label"], r["severity"],
                        r["cond_conf"], r["det_conf"], ", ".join(r["findings"]), r["decision_label"],
                        r["certainty"], r["value_estimate"], r["value_low"], r["value_high"], 1])
    print(f"Wrote {len(rows)} sample rows to powerbi/ewaste_sample_records.csv")

    if args.insert:
        database.init()
        for r in rows:
            database.insert_final(r)
        print("Inserted the same rows into the app database (flagged is_sample = 1).")


if __name__ == "__main__":
    main()
