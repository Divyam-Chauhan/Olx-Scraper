import sys
import eel
import threading
import scraper

# Initialize eel with the web directory
eel.init('web')

scraper_thread = None

@eel.expose
def start_scraping(config):
    global scraper_thread
    bhk_config = config.get("bhk_config", {})
    max_pages = config.get("max_pages", 50)
    
    # Reset state
    scraper.stop_requested = False
    scraper.captcha_solved = False
    
    # Run in a background thread to keep UI responsive
    scraper_thread = threading.Thread(
        target=scraper.run_scraper, 
        args=(bhk_config, max_pages), 
        daemon=True
    )
    scraper_thread.start()

@eel.expose
def stop_scraping():
    scraper.stop_requested = True

@eel.expose
def resume_scraping():
    scraper.captcha_solved = True

if __name__ == '__main__':
    try:
        # Start the app. port=0 picks an available random port to avoid conflicts.
        eel.start('index.html', size=(1100, 750), port=0)
    except (SystemExit, KeyboardInterrupt):
        print("Application closed.")
        sys.exit(0)
