from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable

from playwright.sync_api import Locator
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
        lambda page: page.get_by_placeholder("Password", exact=False),
        lambda page: page.locator("input[type='password']"),
        lambda page: page.locator("input[name='password'], input#password, input[id*='pass'], input[name*='pass']"),
    ],
    "login_submit": [
        lambda page: page.get_by_role("button", name="Sign In", exact=False),
        lambda page: page.get_by_role("button", name="Login", exact=False),
        lambda page: page.locator("button[type='submit']"),
    ],
    "analytics": [
        lambda page: page.get_by_role("link", name="Analytics", exact=False),
        lambda page: page.get_by_text("Analytics", exact=False),
        lambda page: page.locator("a:has-text('Analytics'), button:has-text('Analytics')"),
    ],
}


def _first_visible(page, key: str, timeout_ms: int = 10000) -> Locator:
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


def _any_visible(page, keys: list[str], timeout_ms: int = 3000) -> bool:
    for key in keys:
        for factory in SELECTORS[key]:
            locator = factory(page).first
            try:
                locator.wait_for(state="visible", timeout=timeout_ms)
                return True
            except PlaywrightTimeoutError:
                continue
    return False


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
        browser = playwright.chromium.launch(headless=not debug, slow_mo=150 if debug else 0)
        context = browser.new_context(accept_downloads=True)
        if debug:
            context.tracing.start(screenshots=True, snapshots=True, sources=True)

        page = context.new_page()
        _mark(step_callback, 2, "done")

        try:
            _mark(step_callback, 3, "active")
            page.goto(BASE_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_load_state("domcontentloaded")
            _mark(step_callback, 3, "done")

            _mark(step_callback, 4, "active")
            if _any_visible(page, ["password"], timeout_ms=10000):
                _first_visible(page, "username", timeout_ms=20000).fill(username)
                _first_visible(page, "password", timeout_ms=20000).fill(password)
                _first_visible(page, "login_submit", timeout_ms=20000).click()
                page.wait_for_load_state("domcontentloaded")
                print("Login successful.")
            else:
                print("Login form not shown; continuing with current authenticated session.")
            _mark(step_callback, 4, "done")

            _mark(step_callback, 5, "active")
            analytics_target = _first_visible(page, "analytics", timeout_ms=20000)
            try:
                with context.expect_page(timeout=10000) as new_page_info:
                    analytics_target.click(timeout=20000)
                page = new_page_info.value
                page.wait_for_load_state("domcontentloaded")
            except PlaywrightTimeoutError:
                analytics_target.click(timeout=20000)
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
