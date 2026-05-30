import sys
import eel
import threading
import scraper
import db

# Force Windows console to use UTF-8 to prevent charmap errors on Rupee symbols
sys.stdout.reconfigure(encoding='utf-8')

import os

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
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

if __name__ == '__main__':
    try:
        # Start the app. port=0 picks an available random port to avoid conflicts.
        eel.start('index.html', size=(1100, 750), port=0)
    except (SystemExit, KeyboardInterrupt):
        print("Application closed.")
        sys.exit(0)
