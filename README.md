# MedVet Report Retriever (Local Only)

This app is **for local use only**. It runs on `127.0.0.1` and automates generating/downloading a MedVet radiologist report.

## Features
- Single-page Flask UI with:
  - Username/password/date inputs
  - Live progress bar (0-100)
  - Live step checklist
  - Friendly error area
  - Download button enabled only when report is ready
- Background automation job polling (`/run`, `/status/<job_id>`, `/download/<job_id>`)
- Playwright Chromium automation that mirrors the provided MedVet Playwright flow (login → workflow → analytics popup → reports → radiologist report download) with artifacts on failure
- Optional debug mode (headed browser + trace capture)

## Setup
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m playwright install chromium
```

## Run
```bash
python app.py
```

Then open: <http://127.0.0.1:5000>

## Troubleshooting
- Enable **Debug mode (show browser)** to observe the workflow.
- If the portal UI changes, update the Playwright interactions in `automation.py`.
- Failure artifacts are saved under `./artifacts`:
  - `failure_<job_id>.png`
  - `failure_<job_id>.html`
  - `trace_<job_id>.zip` (debug mode)
- Downloads are stored under `./downloads` with unique filenames.

## Security notes
- Credentials are only used in-memory per run.
- Credentials are not written to disk.
- Passwords are never logged.
