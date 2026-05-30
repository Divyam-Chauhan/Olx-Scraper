import os
import re
import subprocess
import sys
import threading
import time

DEFAULT_PLAYWRIGHT_BROWSERS_PATH = os.path.join(
    os.path.expanduser("~"),
    "AppData",
    "Local",
    "ms-playwright",
)
os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", DEFAULT_PLAYWRIGHT_BROWSERS_PATH)

import eel
import scraper
import db

if sys.stdout is not None:
    sys.stdout.reconfigure(encoding="utf-8")


scraper_thread = None
installer_process = None
thread_state_lock = threading.Lock()


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)


def call_frontend(callback_name, *args):
    """Call an Eel callback if the web UI is ready."""
    try:
        getattr(eel, callback_name)(*args)
    except Exception:
        pass


def log_to_ui(message, msg_type="system"):
    """Print and send a message to the activity log."""
    print(message)
    call_frontend("log_message", message, msg_type)


def clean_installer_line(line):
    """Remove ANSI terminal formatting from Playwright installer output."""
    return re.sub(r"\x1b\[[0-9;]*m", "", line).strip()


def get_chromium_executable_path():
    """Return the Playwright-managed Chromium executable path."""
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        return playwright.chromium.executable_path


def read_installer_output(process):
    """Forward Playwright installer output to the UI log."""
    if process.stdout is None:
        return

    for raw_line in process.stdout:
        line = clean_installer_line(raw_line)
        if line:
            call_frontend("on_browser_setup_progress", line)


def stop_installer_process():
    """Terminate the active Playwright installer process if one is running."""
    global installer_process

    with thread_state_lock:
        process = installer_process

    if process and process.poll() is None:
        try:
            process.terminate()
            process.wait(timeout=5)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass


def install_chromium_browser():
    """Install Chromium using Playwright's bundled Node driver."""
    global installer_process

    from playwright._impl._driver import compute_driver_executable, get_driver_env

    os.makedirs(os.environ["PLAYWRIGHT_BROWSERS_PATH"], exist_ok=True)
    node_executable, cli_path = compute_driver_executable()
    env = get_driver_env()
    env["PLAYWRIGHT_BROWSERS_PATH"] = os.environ["PLAYWRIGHT_BROWSERS_PATH"]

    creation_flags = 0
    if hasattr(subprocess, "CREATE_NO_WINDOW"):
        creation_flags = subprocess.CREATE_NO_WINDOW

    try:
        process = subprocess.Popen(
            [node_executable, cli_path, "install", "chromium"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            text=True,
            encoding="utf-8",
            errors="replace",
            env=env,
            creationflags=creation_flags,
        )
    except Exception as exc:
        call_frontend("on_browser_setup_failed", f"Could not start browser download: {exc}")
        return False

    with thread_state_lock:
        installer_process = process

    output_thread = threading.Thread(
        target=read_installer_output,
        args=(process,),
        daemon=True,
    )
    output_thread.start()

    try:
        while process.poll() is None:
            if scraper.stop_requested:
                stop_installer_process()
                call_frontend("on_browser_setup_failed", "Browser download cancelled.")
                return False
            time.sleep(0.2)

        output_thread.join(timeout=1)
        if scraper.stop_requested:
            call_frontend("on_browser_setup_failed", "Browser download cancelled.")
            return False

        if process.returncode == 0:
            return True

        call_frontend(
            "on_browser_setup_failed",
            f"Browser download failed with exit code {process.returncode}. Check your internet connection and try again.",
        )
        return False
    finally:
        with thread_state_lock:
            if installer_process is process:
                installer_process = None


def ensure_chromium_ready():
    """Ensure the Chromium browser exists before scraping starts."""
    call_frontend("on_browser_setup_started")
    call_frontend("on_browser_setup_progress", "Checking Chromium browser...")

    try:
        chromium_path = get_chromium_executable_path()
    except Exception as exc:
        call_frontend("on_browser_setup_failed", f"Could not check Playwright browser status: {exc}")
        return False

    if os.path.exists(chromium_path):
        call_frontend("on_browser_setup_progress", "Chromium browser is ready.")
        call_frontend("on_browser_setup_finished")
        return True

    call_frontend(
        "on_browser_setup_progress",
        "Chromium browser is missing. Downloading it now, about 300 MB...",
    )

    if not install_chromium_browser():
        return False

    if scraper.stop_requested:
        call_frontend("on_browser_setup_failed", "Browser setup cancelled.")
        return False

    try:
        chromium_path = get_chromium_executable_path()
    except Exception as exc:
        call_frontend("on_browser_setup_failed", f"Could not verify Chromium after download: {exc}")
        return False

    if not os.path.exists(chromium_path):
        call_frontend("on_browser_setup_failed", "Chromium download finished, but the browser executable was not found.")
        return False

    call_frontend("on_browser_setup_progress", "Chromium browser download complete.")
    call_frontend("on_browser_setup_finished")
    return True


def run_scraper_after_browser_setup(geo_url, bhk_config, max_pages):
    """Prepare Playwright's browser and then run the scraper."""
    try:
        if not ensure_chromium_ready():
            return

        if scraper.stop_requested:
            call_frontend("on_browser_setup_failed", "Scraping cancelled before browser launch.")
            return

        call_frontend("on_scraper_started")
        scraper.run_scraper(geo_url, bhk_config, max_pages)
    except Exception as exc:
        log_to_ui(f"CRITICAL ERROR: Browser setup failed: {exc}", "error")
        call_frontend("on_browser_setup_failed", f"Browser setup failed: {exc}")

@eel.expose
def start_scraping(config):
    global scraper_thread
    geo_url = config.get("geo_url", "")
    bhk_config = config.get("bhk_config", {})
    max_pages = config.get("max_pages", 50)

    with thread_state_lock:
        if scraper_thread and scraper_thread.is_alive():
            print("Scraper is already running or shutting down!")
            call_frontend("on_scraping_finished", "Error: Scraper is still shutting down. Please wait 5 seconds and try again.")
            return

        scraper.stop_requested = False
        scraper.captcha_solved = False

        scraper_thread = threading.Thread(
            target=run_scraper_after_browser_setup,
            args=(geo_url, bhk_config, max_pages),
            daemon=True,
        )
        scraper_thread.start()

@eel.expose
def stop_scraping():
    scraper.stop_requested = True
    stop_installer_process()

@eel.expose
def resume_scraping():
    scraper.captcha_solved = True

@eel.expose
def fetch_database():
    """Fetch all listings from the database and send to frontend."""
    return db.get_all_listings()

@eel.expose
def delete_selected_listings(ids):
    """Delete selected listings and return success."""
    db.delete_listings(ids)
    return True

def close_callback(route, websockets):
    if not websockets:
        print("UI window closed. Shutting down cleanly...")
        scraper.stop_requested = True
        stop_installer_process()
        sys.exit(0)

eel.init(resource_path("web"))

if __name__ == '__main__':
    try:
        eel.start('index.html', size=(1100, 750), port=0, close_callback=close_callback)
    except (SystemExit, KeyboardInterrupt):
        print("Application closed.")
        sys.exit(0)
