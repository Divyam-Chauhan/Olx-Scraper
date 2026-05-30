"""OLX Rental Scraper"""

import time
import winsound
import eel
import urllib.parse
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout

from config import (
    HEADLESS,
    PAGE_LOAD_TIMEOUT,
    CAPTCHA_INDICATORS,
    BEEP_FREQUENCY,
    BEEP_DURATION_MS,
)
from db import init_db, listing_exists, insert_listing, get_listing_count

# Threading state variables
stop_requested = False
captcha_solved = False


def log(msg, msg_type="system"):
    """Helper to both print and send logs to Eel UI."""
    print(msg)
    try:
        eel.log_message(msg, msg_type)
    except Exception:
        pass


def update_ui_stats(processed, saved, duplicates):
    """Helper to update stats in Eel UI."""
    try:
        eel.update_stats(processed, saved, duplicates)
    except Exception:
        pass


def build_url(base_geo_url, bhk_config):
    """Build the robust OLX URL dynamically using the geographic base URL."""
    rooms = []
    for bhk in bhk_config.keys():
        rooms.append(bhk)
    
    rooms.sort()
    room_param = "_and_".join(rooms)
    
    # Apply the BHK filters to the geographic node URL
    return f"{base_geo_url}?filter=bachelors_eq_yes%2Crooms_eq_{room_param}"


def alert_and_pause():
    """Trigger system beep and wait for user input from UI."""
    global captcha_solved
    captcha_solved = False
    
    log("CAPTCHA / BLOCK DETECTED! Waiting for manual resolution.", "warning")
    
    try:
        eel.trigger_captcha_modal()
    except Exception:
        pass

    for _ in range(3):
        winsound.Beep(BEEP_FREQUENCY, BEEP_DURATION_MS)
        time.sleep(0.3)

    # Wait until the UI sets captcha_solved to True or stop is requested
    while not captcha_solved and not stop_requested:
        time.sleep(1)

    captcha_solved = False # reset for next time


def is_captcha_present(page):
    """Detect Cloudflare or CAPTCHA blocks."""
    try:
        title = page.title().lower()
        if "just a moment" in title or "attention required" in title or "cloudflare" in title or "access denied" in title:
            return True

        content = page.inner_text("body").lower()
        if "verify you are human" in content and ("cloudflare" in content or "challenge" in content):
            return True
            
        if "enable javascript and cookies to continue" in content:
            return True
            
    except Exception:
        pass

    return False


def handle_captcha_if_present(page):
    """Pause execution if CAPTCHA is detected."""
    while is_captcha_present(page):
        if stop_requested:
            return
        alert_and_pause()
        time.sleep(2)  # Give the DOM a tiny moment to settle after manual solve


def safe_navigate(page, url):
    """Navigate to URL and handle potential CAPTCHAs."""
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
    except Exception as e:
        log(f"Navigation error for {url}: {str(e)}", "warning")
        raise e  # re-raise so calling code knows navigation failed

    time.sleep(3)
    handle_captcha_if_present(page)


def extract_listing_cards(page):
    """Extract property cards from search results."""
    cards = []

    try:
        page.wait_for_selector('[data-aut-id="itemPrice"]', timeout=10000)
    except Exception:
        log("Timeout waiting for itemPrice elements. (Page may be empty or blocked)", "warning")

    time.sleep(2)

    card_elements = page.query_selector_all('li[data-aut-id="itemBox"]')
    if not card_elements:
        card_elements = page.query_selector_all('[data-aut-id="itemBox"]')

    if not card_elements:
        all_links = page.query_selector_all('a[href*="/item/"]')
        card_elements = [link for link in all_links if link.query_selector('[data-aut-id="itemPrice"]')]

    for card in card_elements:
        if stop_requested:
            break
            
        try:
            link_el = card.query_selector("a")
            if not link_el:
                link_el = card if card.get_attribute("href") else None

            if not link_el:
                continue

            href = link_el.get_attribute("href")
            if not href:
                continue

            listing_url = href if href.startswith("http") else urljoin("https://www.olx.in", href)

            title_el = card.query_selector('[data-aut-id="itemTitle"]')
            title = title_el.inner_text().strip() if title_el else "Untitled"

            price_el = card.query_selector('[data-aut-id="itemPrice"]')
            price = price_el.inner_text().strip() if price_el else ""

            details_el = card.query_selector('[data-aut-id="itemDetails"]')
            bhk_info = details_el.inner_text().strip() if details_el else ""
            bhk = bhk_info.split("-")[0].strip() if "-" in bhk_info else bhk_info

            subtitle_el = card.query_selector('[data-aut-id="itemSubTitle"]')
            location = ""
            posted_date = ""
            if subtitle_el:
                spans = subtitle_el.query_selector_all("span")
                if len(spans) >= 2:
                    location = spans[0].inner_text().strip()
                    posted_date = spans[1].inner_text().strip()
                elif len(spans) == 1:
                    text = spans[0].inner_text().strip()
                    if "Today" in text or "Yesterday" in text or text.split(" ")[0] in ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]:
                        posted_date = text
                    else:
                        location = text

            cards.append({
                "title": title,
                "price": price,
                "url": listing_url,
                "location": location,
                "posted_date": posted_date,
                "bhk": bhk
            })
        except Exception:
            continue

    return cards


def scrape_detail_page(page, url):
    """Extract seller type and furnishing from detail page."""
    try:
        safe_navigate(page, url)
        
        try:
            page.wait_for_selector('h1', timeout=6000)
        except Exception:
            pass
            
        time.sleep(3)

        seller_type = "Unknown"
        try:
            seller_el = page.query_selector('div[data-aut-id="seller-info"] span')
            if not seller_el:
                seller_el = page.query_selector('div:has-text("Listed by") + div')
            
            if seller_el:
                seller_text = seller_el.inner_text().strip()
                if seller_text:
                    seller_type = seller_text
        except Exception:
            pass

        full_text = page.inner_text("body").lower()

        if seller_type == "Unknown":
            if "dealer" in full_text or "broker" in full_text:
                seller_type = "Dealer"
            elif "owner" in full_text:
                seller_type = "Owner"


        furnishing = "Unknown"
        if "fully furnished" in full_text or ("furnished" in full_text and "semi" not in full_text and "un" not in full_text):
            furnishing = "Furnished"
        elif "semi-furnished" in full_text or "semi furnished" in full_text:
            furnishing = "Semi-Furnished"
        elif "unfurnished" in full_text:
            furnishing = "Unfurnished"

        return {
            "seller_type": seller_type,
            "furnishing": furnishing,
        }
    except Exception as e:
        log(f"Detail scrape failed for {url}: {str(e)}", "error")
        return None


def go_to_next_page(page):
    """Click next page button."""
    try:
        next_btn = page.query_selector('button[data-aut-id="btnLoadMore"]')
        if next_btn and next_btn.is_visible():
            next_btn.click()
            time.sleep(3)
            handle_captcha_if_present(page)
            return True

        next_link = page.query_selector('a[data-aut-id="nextPageLink"]')
        if not next_link:
            next_link = page.query_selector('a:has-text("›")')
        if not next_link:
            next_link = page.query_selector('a:has-text("Next")')

        if next_link and next_link.is_visible():
            next_link.click()
            page.wait_for_load_state("domcontentloaded", timeout=PAGE_LOAD_TIMEOUT)
            time.sleep(3)
            handle_captcha_if_present(page)
            return True

    except Exception:
        pass

    return False


def run_scraper(geo_url, bhk_config, max_pages):
    """Main entry point for scraping thread."""
    global stop_requested
    stop_requested = False
    
    if not geo_url:
        log("No location URL provided. Please paste an OLX location URL.", "error")
        try:
            eel.on_scraping_finished("Failed: No location URL.")
        except Exception:
            pass
        return

    init_db()
    initial_count = get_listing_count()
    
    log(f"Database initialized. Existing listings: {initial_count}", "info")
    
    # Build the final URL with BHK filters applied to the user's geographic URL
    target_url = build_url(geo_url, bhk_config)
    log(f"Dynamic Target URL: {target_url}", "system")

    saved = 0
    duplicates = 0
    processed = 0

    try:
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=HEADLESS)
            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()
            page.set_default_timeout(PAGE_LOAD_TIMEOUT)

            log("Navigating to filtered search page...", "system")
            try:
                safe_navigate(page, target_url)
            except Exception as e:
                log(f"Failed to load the main search page: {str(e)}", "error")
                browser.close()
                return

            for page_num in range(1, max_pages + 1):
                if stop_requested:
                    log("Scraping stopped by user.", "warning")
                    break

                log(f"--- Scanning Page {page_num} ---", "info")

                cards = extract_listing_cards(page)
                log(f"Found {len(cards)} listing cards on this page.", "system")

                if not cards:
                    log("No cards found. Possibly end of results or page structure changed.", "warning")
                    break

                for card in cards:
                    if stop_requested:
                        break
                        
                    processed += 1
                    update_ui_stats(processed, saved, duplicates)
                    
                    listing_url = card["url"]
                    card_title = card["title"]

                    if listing_exists(listing_url):
                        log(f"[{processed}] SKIP (duplicate) - {card_title[:40]}...", "skip")
                        duplicates += 1
                        update_ui_stats(processed, saved, duplicates)
                        continue

                    # Strict Budget Filter
                    try:
                        clean_price = "".join(filter(str.isdigit, card["price"]))
                        if clean_price:
                            price_val = int(clean_price)
                            bhk_num = card["bhk"].replace("BHK", "").strip()
                            
                            if bhk_num in bhk_config:
                                min_allowed = bhk_config[bhk_num]["min"]
                                max_allowed = bhk_config[bhk_num]["max"]
                                
                                if price_val < min_allowed or price_val > max_allowed:
                                    log(f"[{processed}] SKIP (out of budget: {bhk_num}BHK at ₹{price_val})", "skip")
                                    continue
                            else:
                                log(f"[{processed}] SKIP (unselected BHK type: {bhk_num})", "skip")
                                continue
                    except Exception:
                        pass

                    log(f"[{processed}] Inspecting: {card_title[:40]}...", "system")

                    detail = None
                    try:
                        detail_page = context.new_page()
                        detail_page.set_default_timeout(PAGE_LOAD_TIMEOUT)
                        detail = scrape_detail_page(detail_page, listing_url)
                    except Exception as e:
                        log(f"[{processed}] Tab Error loading detail page: {str(e)}", "error")
                    finally:
                        try:
                            detail_page.close()
                        except Exception:
                            pass

                    if not detail:
                        log(f"[{processed}] -> WARNING: Using defaults due to failure loading flat details.", "warning")
                        detail = {"seller_type": "Unknown", "furnishing": "Unknown"}

                    listing_data = {
                        "title": card["title"],
                        "price": card["price"],
                        "url": listing_url,
                        "seller_type": detail.get("seller_type", "Unknown"),
                        "posted_date": card["posted_date"],
                        "bhk": card["bhk"],
                        "furnishing": detail.get("furnishing", "Unknown"),
                    }

                    insert_listing(listing_data)
                    saved += 1
                    update_ui_stats(processed, saved, duplicates)
                    log(f"[{processed}] -> SAVED | {card['bhk']} | {listing_data['price']} | {listing_data['seller_type']}", "success")

                if stop_requested:
                    break

                if not go_to_next_page(page):
                    log("No more pages available.", "info")
                    break

            browser.close()
            
    except Exception as e:
        log(f"CRITICAL ERROR: Scraper encountered an unrecoverable error: {str(e)}", "error")

    final_count = get_listing_count()
    
    msg = f"SCRAPING COMPLETE. Processed: {processed}, Saved: {saved}, Total in DB: {final_count}"
    try:
        eel.on_scraping_finished(msg)
    except Exception:
        log(msg, "success")
