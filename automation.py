from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

BASE_URL = "https://intoview-radportal.medvet.com/"
WORKFLOW_URL = "https://intoview-radportal.medvet.com/?workflow#!"

STEPS = [
    {"id": 1, "label": "Validating input"},
    {"id": 2, "label": "Launching browser"},
    {"id": 3, "label": "Opening login page"},
    {"id": 4, "label": "Submitting credentials"},
    {"id": 5, "label": "Opening workflow and toolbar"},
    {"id": 6, "label": "Opening Analytics popup"},
    {"id": 7, "label": "Opening Reports"},
    {"id": 8, "label": "Selecting Physician Productivity Report"},
    {"id": 9, "label": "Selecting Radiologist Report"},
    {"id": 10, "label": "Configuring absolute date range"},
    {"id": 11, "label": "Running report"},
    {"id": 12, "label": "Waiting for report download"},
    {"id": 13, "label": "Saving .xls file"},
    {"id": 14, "label": "Done"},
]


def _mark(step_callback: Callable[[int, str], None], step: int, state: str) -> None:
    step_callback(step, state)


def run_report_automation(
    *,
    job_id: str,
    username: str,
    password: str,
    start_date: str,
    end_date: str,
    debug: bool,
    step_callback: Callable[[int, str], None],
    downloads_dir: Path,
    artifacts_dir: Path,
) -> dict[str, str]:
    _mark(step_callback, 1, "active")
    if not username or not password:
        raise RuntimeError("Missing credentials.")
    _mark(step_callback, 1, "done")

    downloads_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    start_slug = start_date.replace("/", "-")
    end_slug = end_date.replace("/", "-")
    final_name = f"medvet_radiologist_report_{start_slug}_{end_slug}_{timestamp}.xls"
    final_path = downloads_dir / final_name

    with sync_playwright() as playwright:
        _mark(step_callback, 2, "active")
        browser = playwright.chromium.launch(headless=not debug, slow_mo=200 if debug else 0)
        context = browser.new_context(accept_downloads=True)
        if debug:
            context.tracing.start(screenshots=True, snapshots=True, sources=True)
        page = context.new_page()
        _mark(step_callback, 2, "done")

        try:
            _mark(step_callback, 3, "active")
            page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
            _mark(step_callback, 3, "done")

            _mark(step_callback, 4, "active")
            page.get_by_placeholder("Username").click(timeout=20000)
            page.get_by_placeholder("Username").fill(username)
            page.get_by_placeholder("Username").press("Tab")
            page.get_by_placeholder("Password").fill(password)
            page.get_by_role("button", name="Login", exact=True).click()
            _mark(step_callback, 4, "done")

            _mark(step_callback, 5, "active")
            page.goto(WORKFLOW_URL, wait_until="domcontentloaded", timeout=60000)
            page.locator("#tool-3559-toolEl").click(timeout=20000)
            page.locator("#button-3541").click(timeout=20000)
            _mark(step_callback, 5, "done")

            _mark(step_callback, 6, "active")
            with page.expect_popup(timeout=20000) as popup_info:
                page.get_by_role("button", name="Analytics").click(timeout=20000)
            page1 = popup_info.value
            page1.wait_for_load_state("domcontentloaded")
            _mark(step_callback, 6, "done")

            _mark(step_callback, 7, "active")
            page1.get_by_role("button", name="Reports").click(timeout=20000)
            _mark(step_callback, 7, "done")

            _mark(step_callback, 8, "active")
            page1.locator("#treeview-1850-record-ext-record-65").get_by_text(
                "Physician Productivity Report"
            ).click(timeout=20000)
            _mark(step_callback, 8, "done")

            _mark(step_callback, 9, "active")
            page1.locator("#treeview-1858-record-ext-record-76").get_by_text("Radiologist Report").click(
                timeout=20000
            )
            _mark(step_callback, 9, "done")

            _mark(step_callback, 10, "active")
            page1.locator("#ext-gen6648").click(timeout=20000)
            page1.locator("#ext-gen6648").click(timeout=20000)
            page1.get_by_role("cell", name="Dates Relative to Today").get_by_label("").click(timeout=20000)
            page1.get_by_role("option", name="Absolute Dates").click(timeout=20000)
            page1.locator("#datefield-2635-inputEl").click(timeout=20000)
            page1.locator("#datefield-2635-inputEl").fill(start_date)
            page1.locator("#datefield-2636-inputEl").click(timeout=20000)
            page1.locator("#datefield-2636-inputEl").fill(end_date)
            page1.get_by_role("textbox", name="Radiologist:").click(timeout=20000)
            _mark(step_callback, 10, "done")

            _mark(step_callback, 11, "active")
            page1.get_by_role("button", name="Create Report").click(timeout=20000)
            _mark(step_callback, 11, "done")

            _mark(step_callback, 12, "active")
            with page1.expect_download(timeout=120000) as download_info:
                page1.get_by_role("link", name=".xls", exact=False).first.click(timeout=120000)
            download = download_info.value
            _mark(step_callback, 12, "done")

            _mark(step_callback, 13, "active")
            download.save_as(str(final_path))
            _mark(step_callback, 13, "done")

            _mark(step_callback, 14, "active")
            _mark(step_callback, 14, "done")

            if debug:
                context.tracing.stop(path=str(artifacts_dir / f"trace_{job_id}.zip"))

            return {"file_name": final_name, "file_path": str(final_path.resolve())}
        except Exception:
            try:
                page.screenshot(path=str(artifacts_dir / f"failure_{job_id}.png"), full_page=True)
                (artifacts_dir / f"failure_{job_id}.html").write_text(page.content(), encoding="utf-8")
            except Exception:
                pass
            if debug:
                try:
                    context.tracing.stop(path=str(artifacts_dir / f"trace_{job_id}.zip"))
                except Exception:
                    pass
            raise
        finally:
            context.close()
            browser.close()
