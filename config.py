"""Script configurations."""


BASE_URL = "https://www.olx.in/en-in/jagatpura_g5333216/for-rent-houses-apartments_c1723?filter=bachelors_eq_yes%2Crooms_eq_1_and_2_and_3"

BACHELOR_KEYWORDS = [
    "bachelor",
    "bachelors",
    "boys",
    "anyone",
    "bachelor friendly",
    "bachelors allowed",
    "all",
]

SALE_KEYWORDS = [
    "for sale",
    "sell",
    "selling",
    "buy",
    "purchase",
]

MAX_BUDGET_PER_BHK = {
    "1": 10000,
    "2": 15000,
    "3": 20000
}

import os
import pathlib

# Get the user's Documents folder dynamically so the .exe can save data reliably
DOCUMENTS_DIR = os.path.join(pathlib.Path.home(), "Documents", "OLX_Scraper")
os.makedirs(DOCUMENTS_DIR, exist_ok=True)

DB_PATH = os.path.join(DOCUMENTS_DIR, "olx_rentals.db")

HEADLESS = False

PAGE_LOAD_TIMEOUT = 60000

MAX_PAGES = 50

CAPTCHA_INDICATORS = [
    "captcha",
    "verify you are human",
    "are you a robot",
    "blocked",
    "access denied",
    "challenge-platform",
    "cf-browser-verification",
    "just a moment",
]

BEEP_FREQUENCY = 1000
BEEP_DURATION_MS = 2000
