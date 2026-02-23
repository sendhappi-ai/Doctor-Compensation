from __future__ import annotations

import re
import uuid
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from threading import Lock
from typing import Any

from flask import Flask, jsonify, render_template, request, send_file

from automation import STEPS, run_report_automation

app = Flask(__name__)

DOWNLOADS_DIR = Path("downloads")
ARTIFACTS_DIR = Path("artifacts")
DOWNLOADS_DIR.mkdir(exist_ok=True)
ARTIFACTS_DIR.mkdir(exist_ok=True)

DATE_PATTERN = re.compile(r"^(0[1-9]|1[0-2])/(0[1-9]|[12]\d|3[01])/(\d{4})$")

jobs: dict[str, dict[str, Any]] = {}
jobs_lock = Lock()
executor = ThreadPoolExecutor(max_workers=3)


def initial_steps() -> list[dict[str, Any]]:
    return [{"id": s["id"], "label": s["label"], "state": "pending"} for s in STEPS]


def build_job() -> dict[str, Any]:
    return {
        "percent": 0,
        "current_step_id": 1,
        "steps": initial_steps(),
        "done": False,
        "download_ready": False,
        "error": None,
        "file_name": None,
        "file_path": None,
    }


def get_job(job_id: str) -> dict[str, Any] | None:
    with jobs_lock:
        return jobs.get(job_id)


def update_job(job_id: str, **patch: Any) -> None:
    with jobs_lock:
        if job_id in jobs:
            jobs[job_id].update(patch)


def update_step(job_id: str, step_id: int, state: str) -> None:
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            return

        for step in job["steps"]:
            if step["id"] < step_id and step["state"] in {"pending", "active"}:
                step["state"] = "done"
            if step["id"] == step_id:
                step["state"] = state
            elif step["id"] > step_id and step["state"] == "active":
                step["state"] = "pending"

        max_index = len(job["steps"]) - 1
        progress_index = min(step_id - 1, max_index)
        base_percent = int((progress_index / max_index) * 100) if max_index else 100
        if state == "done":
            base_percent = int((min(step_id, len(job["steps"])) / len(job["steps"])) * 100)
        job["current_step_id"] = step_id
        job["percent"] = max(0, min(base_percent, 100))


def validate_payload(payload: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or ""
    start_date = (payload.get("start_date") or "").strip()
    end_date = (payload.get("end_date") or "").strip()

    if not username:
        errors.append("Username is required.")
    if not password:
        errors.append("Password is required.")
    if not DATE_PATTERN.match(start_date):
        errors.append("Start date must be in MM/DD/YYYY format.")
    if not DATE_PATTERN.match(end_date):
        errors.append("End date must be in MM/DD/YYYY format.")

    if not errors:
        parsed_start = datetime.strptime(start_date, "%m/%d/%Y")
        parsed_end = datetime.strptime(end_date, "%m/%d/%Y")
        if parsed_start > parsed_end:
            errors.append("Start date must be on or before end date.")

    return errors


def run_job(job_id: str, payload: dict[str, Any]) -> None:
    def on_step(step_id: int, state: str) -> None:
        update_step(job_id, step_id, state)

    try:
        result = run_report_automation(
            job_id=job_id,
            username=payload["username"],
            password=payload["password"],
            start_date=payload["start_date"],
            end_date=payload["end_date"],
            debug=bool(payload.get("debug")),
            step_callback=on_step,
            downloads_dir=DOWNLOADS_DIR,
            artifacts_dir=ARTIFACTS_DIR,
        )
        update_job(
            job_id,
            done=True,
            download_ready=True,
            percent=100,
            current_step_id=len(STEPS),
            file_name=result["file_name"],
            file_path=result["file_path"],
        )
    except Exception as exc:  # noqa: BLE001
        message = str(exc) or "Unexpected automation error."
        with jobs_lock:
            job = jobs.get(job_id)
            if job:
                active_step = next((s for s in job["steps"] if s["state"] == "active"), None)
                if active_step:
                    active_step["state"] = "error"
                elif job["steps"]:
                    job["steps"][max(job["current_step_id"] - 1, 0)]["state"] = "error"
                job["done"] = True
                job["error"] = f"Report retrieval failed: {message}"


@app.get("/")
def index() -> str:
    return render_template("index.html", steps=STEPS)


@app.post("/run")
def run():
    payload = request.get_json(silent=True) or request.form.to_dict(flat=True)
    errors = validate_payload(payload)
    if errors:
        return jsonify({"errors": errors}), 400

    job_id = uuid.uuid4().hex
    with jobs_lock:
        jobs[job_id] = build_job()

    executor.submit(run_job, job_id, payload)
    return jsonify({"job_id": job_id})


@app.get("/status/<job_id>")
def status(job_id: str):
    job = get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    return jsonify(deepcopy(job))


@app.get("/download/<job_id>")
def download(job_id: str):
    job = get_job(job_id)
    if not job:
        return jsonify({"error": "Job not found"}), 404
    if not job.get("download_ready") or not job.get("file_path"):
        return jsonify({"error": "File is not ready"}), 400

    file_path = Path(job["file_path"])
    if not file_path.exists():
        return jsonify({"error": "Downloaded file is missing"}), 404

    return send_file(file_path, as_attachment=True, download_name=job.get("file_name") or file_path.name)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
