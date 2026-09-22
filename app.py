"""Flask web application.

Run:  python app.py      then open http://127.0.0.1:5000
"""
import os
import uuid
from pathlib import Path

from flask import Flask, Response, abort, jsonify, render_template, request, send_from_directory

import config
import database
import pipeline
from components import COMPONENTS

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = config.MAX_UPLOAD_MB * 1024 * 1024
database.init()


@app.errorhandler(413)
def too_large(_):
    return jsonify(error=f"That image is larger than {config.MAX_UPLOAD_MB} MB. Please use a smaller photo."), 413


@app.get("/")
def index():
    return render_template("index.html", detector_mode=pipeline.detector.mode,
                           condition_mode=pipeline.condition_ai.mode)


@app.get("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.get("/api/components")
def components():
    return jsonify(pipeline.component_choices())


@app.post("/api/analyze")
def analyze():
    file = request.files.get("image")
    if file is None or not file.filename:
        return jsonify(error="Choose a photo of the component first."), 400
    ext = Path(file.filename).suffix.lower()
    if ext not in config.ALLOWED_EXT:
        return jsonify(error="Use a JPG, PNG, WEBP or BMP image."), 400
    override = (request.form.get("component") or "").strip().lower()
    if override and override not in COMPONENTS:
        return jsonify(error="Unknown component choice."), 400

    saved = config.UPLOAD_DIR / f"{uuid.uuid4().hex}{ext}"
    file.save(saved)
    try:
        return jsonify(pipeline.analyze(saved, file.filename, override or None))
    except ValueError as exc:
        saved.unlink(missing_ok=True)
        return jsonify(error=str(exc)), 400


@app.post("/api/decide")
def decide():
    body = request.get_json(silent=True) or {}
    try:
        rec_id = int(body.get("id"))
    except (TypeError, ValueError):
        return jsonify(error="Missing analysis id."), 400
    answers = body.get("answers") or {}
    if not isinstance(answers, dict):
        return jsonify(error="Answers must be an object."), 400
    try:
        return jsonify(pipeline.decide_record(rec_id, answers))
    except KeyError as exc:
        return jsonify(error=str(exc)), 404


@app.get("/api/stats")
def stats():
    return jsonify(database.stats())


@app.get("/api/records")
def records():
    limit = min(200, max(1, request.args.get("limit", 15, type=int)))
    rows = database.list_records(limit)
    keep = ("id", "created_at", "component_display", "condition_label", "decision", "decision_label",
            "certainty", "value_estimate", "is_sample")
    return jsonify([{k: r[k] for k in keep} for r in rows])


@app.get("/export/records.csv")
def export_csv():
    return Response(database.export_csv(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=ewaste_records.csv"})


@app.get("/media/<kind>/<path:name>")
def media(kind, name):
    folder = {"uploads": config.UPLOAD_DIR, "annotated": config.ANNOTATED_DIR}.get(kind)
    if folder is None:
        abort(404)
    return send_from_directory(folder, name)


if __name__ == "__main__":
    print(f"Detector: {pipeline.detector.mode} | Condition AI: {pipeline.condition_ai.mode}")
    app.run(debug=False, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))