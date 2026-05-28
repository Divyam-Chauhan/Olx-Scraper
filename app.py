import sys
import eel
import threading
import time
from playwright.sync_api import sync_playwright
import scraper
import db

# Force Windows console to use UTF-8 to prevent charmap errors on Rupee symbols
sys.stdout.reconfigure(encoding='utf-8')

# Initialize eel with the web directory
eel.init('web')

scraper_thread = None

@eel.expose
def start_scraping(config):
    global scraper_thread
    location_query = config.get("location_query", "")
    bhk_config = config.get("bhk_config", {})
    max_pages = config.get("max_pages", 50)

    # Reset state
    scraper.stop_requested = False
    scraper.captcha_solved = False
    
    # Run in a background thread to keep UI responsive
    scraper_thread = threading.Thread(
        target=scraper.run_scraper,
        args=(location_query, bhk_config, max_pages),
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
