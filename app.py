import sys
import eel
import threading
import scraper
import db

# Force Windows console to use UTF-8 to prevent charmap errors on Rupee symbols (only if console exists)
if sys.stdout is not None:
    sys.stdout.reconfigure(encoding='utf-8')

import os

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
        # Fix Playwright looking for browsers inside the frozen _internal folder
        os.environ.setdefault("PLAYWRIGHT_BROWSERS_PATH", os.path.join(os.path.expanduser("~"), "AppData", "Local", "ms-playwright"))
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# Initialize eel with the dynamically resolved web directory path
eel.init(resource_path('web'))

scraper_thread = None

@eel.expose
def start_scraping(config):
    global scraper_thread
    geo_url = config.get("geo_url", "")
    bhk_config = config.get("bhk_config", {})
    max_pages = config.get("max_pages", 50)

    # --- NEW SAFETY CHECK ---
    if scraper_thread and scraper_thread.is_alive():
        print("Scraper is already running or shutting down!")
        try:
            eel.on_scraping_finished("Error: Scraper is still shutting down. Please wait 5 seconds and try again.")
        except Exception:
            pass
        return
    # ------------------------

    # Reset state
    scraper.stop_requested = False
    scraper.captcha_solved = False
    
    # Run in a background thread to keep UI responsive
    scraper_thread = threading.Thread(
        target=scraper.run_scraper,
        args=(geo_url, bhk_config, max_pages),
        daemon=True
    )
    scraper_thread.start()

@eel.expose
def stop_scraping():
    scraper.stop_requested = True

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
        sys.exit(0)

if __name__ == '__main__':
    try:
        # Start the app. port=0 picks an available random port to avoid conflicts.
        eel.start('index.html', size=(1100, 750), port=0, close_callback=close_callback)
    except (SystemExit, KeyboardInterrupt):
        print("Application closed.")
        sys.exit(0)
