"""SQLite storage. Every analysis is logged; Power BI and the dashboard read from it."""
import csv
import io
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    image_file TEXT,
    annotated_file TEXT,
    component TEXT,
    component_display TEXT,
    det_conf REAL,
    detector_mode TEXT,
    condition_label TEXT,
    severity REAL,
    cond_conf REAL,
    condition_mode TEXT,
    findings TEXT,
    other_detections TEXT,
    ask_reasons TEXT,
    answers TEXT,
    decision TEXT,
    decision_label TEXT,
    reasons TEXT,
    certainty REAL,
    value_low INTEGER,
    value_high INTEGER,
    value_estimate INTEGER,
    status TEXT NOT NULL DEFAULT 'pending',
    is_sample INTEGER NOT NULL DEFAULT 0
);
"""

JSON_FIELDS = ("findings", "other_detections", "ask_reasons", "answers", "reasons")


@contextmanager
def connect():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init():
    with connect() as c:
        c.executescript(SCHEMA)


def _row(r):
    if r is None:
        return None
    d = dict(r)
    for f in JSON_FIELDS:
        if d.get(f):
            d[f] = json.loads(d[f])
    return d


def insert_analysis(d):
    cols = ["created_at", "image_file", "annotated_file", "component", "component_display", "det_conf",
            "detector_mode", "condition_label", "severity", "cond_conf", "condition_mode", "findings",
            "other_detections", "ask_reasons", "status", "is_sample"]
    row = {"created_at": datetime.now().isoformat(timespec="seconds"), "status": "pending", "is_sample": 0}
    row.update(d)
    for f in JSON_FIELDS:
        if f in row and not isinstance(row[f], str):
            row[f] = json.dumps(row[f])
    with connect() as c:
        cur = c.execute(f"INSERT INTO records ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                        [row.get(k) for k in cols])
        return cur.lastrowid


def insert_final(d):
    """Insert a complete record in one go (used by the sample-data script)."""
    cols = ["created_at", "component", "component_display", "det_conf", "detector_mode", "condition_label",
            "severity", "cond_conf", "condition_mode", "findings", "ask_reasons", "answers", "decision",
            "decision_label", "reasons", "certainty", "value_low", "value_high", "value_estimate",
            "status", "is_sample"]
    row = dict(d)
    for f in JSON_FIELDS:
        if f in row and not isinstance(row[f], str):
            row[f] = json.dumps(row[f])
    with connect() as c:
        c.execute(f"INSERT INTO records ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                  [row.get(k) for k in cols])


def finalize(rec_id, answers, decision, value):
    with connect() as c:
        c.execute(
            "UPDATE records SET answers=?, decision=?, decision_label=?, reasons=?, certainty=?, "
            "value_low=?, value_high=?, value_estimate=?, status='final' WHERE id=?",
            (json.dumps(answers), decision["code"], decision["label"], json.dumps(decision["reasons"]),
             decision["certainty"], value["low"], value["high"], value["estimate"], rec_id))


def get(rec_id):
    with connect() as c:
        return _row(c.execute("SELECT * FROM records WHERE id=?", (rec_id,)).fetchone())


def list_records(limit=50):
    with connect() as c:
        rows = c.execute("SELECT * FROM records WHERE status='final' ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    return [_row(r) for r in rows]


def stats():
    with connect() as c:
        q = lambda sql: [dict(r) for r in c.execute(sql).fetchall()]
        totals = dict(c.execute(
            "SELECT COUNT(*) n, COALESCE(SUM(value_estimate),0) v, COALESCE(AVG(certainty),0) cert, "
            "COALESCE(SUM(is_sample),0) samples FROM records WHERE status='final'").fetchone())
        by_component = q("SELECT component_display name, COUNT(*) count, SUM(value_estimate) value "
                         "FROM records WHERE status='final' GROUP BY component_display ORDER BY count DESC")
        by_condition = q("SELECT condition_label name, COUNT(*) count FROM records WHERE status='final' "
                         "GROUP BY condition_label ORDER BY count DESC")
        by_decision = q("SELECT decision code, decision_label name, COUNT(*) count, SUM(value_estimate) value "
                        "FROM records WHERE status='final' GROUP BY decision ORDER BY count DESC")
    reusable = next((d["count"] for d in by_decision if d["code"] == "reusable"), 0)
    return {
        "total": totals["n"], "total_value": totals["v"], "avg_certainty": round(totals["cert"], 2),
        "sample_rows": totals["samples"],
        "reuse_rate": round(reusable / totals["n"], 3) if totals["n"] else 0,
        "by_component": by_component, "by_condition": by_condition, "by_decision": by_decision,
    }


CSV_COLUMNS = ["id", "date", "component", "condition", "damage_severity", "condition_confidence",
               "detection_confidence", "damage_found", "decision", "certainty",
               "estimated_value_inr", "value_low_inr", "value_high_inr", "is_sample"]


def export_csv():
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(CSV_COLUMNS)
    with connect() as c:
        rows = c.execute("SELECT * FROM records WHERE status='final' ORDER BY id").fetchall()
    for r in rows:
        d = _row(r)
        w.writerow([d["id"], d["created_at"][:10], d["component_display"], d["condition_label"], d["severity"],
                    d["cond_conf"], d["det_conf"], ", ".join((d["findings"] or {}).keys()) if d["findings"] else "",
                    d["decision_label"], d["certainty"], d["value_estimate"], d["value_low"], d["value_high"],
                    d["is_sample"]])
    return out.getvalue()
