from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable

from playwright.sync_api import TimeoutError as PlaywrightTimeoutError
from playwright.sync_api import sync_playwright

BASE_URL = "https://intoview-radportal.medvet.com/#"

STEPS = [
    {"id": 1, "label": "Validating input"},
    {"id": 2, "label": "Launching browser"},
    {"id": 3, "label": "Opening login page"},
    {"id": 4, "label": "Logging in"},
    {"id": 5, "label": "Opening Analytics"},
    {"id": 6, "label": "Opening Reports"},
    {"id": 7, "label": "Selecting Physician Productivity Report"},
    {"id": 8, "label": "Selecting Radiologist Report"},
    {"id": 9, "label": "Setting date parameters"},
    {"id": 10, "label": "Setting radiologist = Current User"},
    {"id": 11, "label": "Creating report"},
    {"id": 12, "label": "Waiting for generated report link"},
    {"id": 13, "label": "Downloading .xls"},
    {"id": 14, "label": "Saving file"},
    {"id": 15, "label": "Done"},
]

SELECTORS = {
    "username": [
        lambda page: page.get_by_label("Username", exact=False),
        lambda page: page.locator("input[name='username'], input#username"),
    ],
    "password": [
        lambda page: page.get_by_label("Password", exact=False),
        lambda page: page.locator("input[type='password']"),
    ],
    "login_submit": [
        lambda page: page.get_by_role("button", name="Sign In", exact=False),
        lambda page: page.get_by_role("button", name="Login", exact=False),
        lambda page: page.locator("button[type='submit']"),
    ],
}


def _first_visible(page, key: str, timeout_ms: int = 10000):
    for factory in SELECTORS[key]:
        locator = factory(page).first
        try:
            locator.wait_for(state="visible", timeout=timeout_ms)
            return locator
        except PlaywrightTimeoutError:
            continue
    raise RuntimeError(f"Unable to find selector for {key}")


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

    storage_state_path = Path("storage_state.json")
    downloads_dir.mkdir(parents=True, exist_ok=True)
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    start_slug = start_date.replace("/", "-")
    end_slug = end_date.replace("/", "-")
    final_name = f"medvet_radiologist_report_{start_slug}_{end_slug}_{timestamp}.xls"
    final_path = downloads_dir / final_name

    browser = None
    context = None
    page = None

    try:
        with sync_playwright() as p:
            _mark(step_callback, 2, "active")
            browser = p.chromium.launch(headless=not debug, slow_mo=150 if debug else 0)
            context_kwargs = {"accept_downloads": True}
            if storage_state_path.exists():
                context_kwargs["storage_state"] = str(storage_state_path)
            context = browser.new_context(**context_kwargs)
            if debug:
                context.tracing.start(screenshots=True, snapshots=True, sources=True)
            page = context.new_page()
            _mark(step_callback, 2, "done")

            _mark(step_callback, 3, "active")
            page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_load_state("domcontentloaded")
            _mark(step_callback, 3, "done")

            if page.locator("input[type='password']").first.is_visible(timeout=3000):
                _mark(step_callback, 4, "active")
                _first_visible(page, "username").fill(username)
                _first_visible(page, "password").fill(password)
                _first_visible(page, "login_submit").click()
                page.wait_for_load_state("domcontentloaded")
                _mark(step_callback, 4, "done")
                context.storage_state(path=str(storage_state_path))
            else:
                _mark(step_callback, 4, "active")
                _mark(step_callback, 4, "done")

            _mark(step_callback, 5, "active")
            page.get_by_role("link", name="Analytics", exact=False).click(timeout=20000)
            page.wait_for_load_state("domcontentloaded")
            _mark(step_callback, 5, "done")

            _mark(step_callback, 6, "active")
            page.get_by_role("tab", name="Reports", exact=False).click(timeout=20000)
            _mark(step_callback, 6, "done")

            _mark(step_callback, 7, "active")
            page.get_by_text("Physician Productivity Report", exact=False).click(timeout=20000)
            _mark(step_callback, 7, "done")

            _mark(step_callback, 8, "active")
            page.get_by_text("Radiologist Report", exact=False).click(timeout=20000)
            _mark(step_callback, 8, "done")

            _mark(step_callback, 9, "active")
            page.get_by_text("Exam Date Search", exact=False).click(timeout=20000)
            page.get_by_text("Completed Between", exact=False).click(timeout=20000)
            page.get_by_text("Absolute Dates", exact=False).click(timeout=20000)
            page.get_by_label("Start Date", exact=False).fill(start_date)
            page.get_by_label("End Date", exact=False).fill(end_date)
            _mark(step_callback, 9, "done")

            _mark(step_callback, 10, "active")
            page.get_by_text("Radiologist", exact=False).click(timeout=20000)
            page.get_by_text("Current User", exact=False).click(timeout=20000)
            _mark(step_callback, 10, "done")

            _mark(step_callback, 11, "active")
            page.get_by_role("button", name="Create Report", exact=False).click(timeout=20000)
            _mark(step_callback, 11, "done")

            _mark(step_callback, 12, "active")
            report_link = page.get_by_role("link", name=".xls", exact=False)
            report_link.wait_for(state="visible", timeout=120000)
            _mark(step_callback, 12, "done")

            _mark(step_callback, 13, "active")
            with page.expect_download(timeout=120000) as download_info:
                report_link.first.click()
            download = download_info.value
            _mark(step_callback, 13, "done")

            _mark(step_callback, 14, "active")
            download.save_as(str(final_path))
            _mark(step_callback, 14, "done")

            _mark(step_callback, 15, "active")
            _mark(step_callback, 15, "done")

            if debug:
                context.tracing.stop(path=str(artifacts_dir / f"trace_{job_id}.zip"))

    except Exception:
        if page:
            try:
                page.screenshot(path=str(artifacts_dir / f"failure_{job_id}.png"), full_page=True)
                (artifacts_dir / f"failure_{job_id}.html").write_text(page.content(), encoding="utf-8")
            except Exception:
                pass
        if context and debug:
            try:
                context.tracing.stop(path=str(artifacts_dir / f"trace_{job_id}.zip"))
            except Exception:
                pass
        raise
    finally:
        if context:
            context.close()
        if browser:
            browser.close()

    return {"file_name": final_name, "file_path": str(final_path.resolve())}
