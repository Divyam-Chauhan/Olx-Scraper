"""
Comprehensive verification test for BYOU (Bring Your Own URL) feature.
Tests: URL parsing, build_url, scraper args, frontend-backend contract.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8')

print("=" * 60)
print("BYOU VERIFICATION TEST SUITE")
print("=" * 60)

# ===== TEST 1: URL Validator (mirrors the JS regex) =====
import re

def validate_olx_url(url):
    """Python mirror of the JS validateOlxUrl function."""
    if not url:
        return None
    match = re.search(r'/([a-z0-9-]+_g\d+)/', url, re.IGNORECASE)
    if not match:
        return None
    geo_slug = match.group(1)
    location_name = geo_slug.split('_g')[0].replace('-', ' ').title()
    clean_url = f"https://www.olx.in/en-in/{geo_slug}/for-rent-houses-apartments_c1723"
    return {"location": location_name, "clean_url": clean_url}

print("\n--- TEST 1: URL Validator ---")
test_urls = [
    ("https://www.olx.in/en-in/sundarpur_g5343637/for-rent-houses-apartments_c1723", True, "Sundarpur"),
    ("https://www.olx.in/en-in/hiranmagri_g5334685/for-rent-houses-apartments_c1723", True, "Hiranmagri"),
    ("https://www.olx.in/en-in/hiran-magri_g5334685/for-rent-houses-apartments_c1723", True, "Hiran Magri"),
    ("olx.in/en-in/sundarpur_g5343637/for-rent-houses-apartments_c1723", True, "Sundarpur"),
    ("https://www.olx.in/en-in/for-rent-houses-apartments_c1723/q-hiranmagri%2C-udaipur", False, None),
    ("https://www.olx.in/en-in/for-rent-houses-apartments_c1723", False, None),
    ("random garbage text", False, None),
    ("", False, None),
]

all_pass = True
for url, should_pass, expected_loc in test_urls:
    result = validate_olx_url(url)
    passed = (result is not None) == should_pass
    if passed and result and expected_loc:
        passed = result["location"] == expected_loc
    
    status = "PASS" if passed else "FAIL"
    if not passed:
        all_pass = False
    loc_str = result["location"] if result else "None"
    print(f"  [{status}] {url[:60]}... -> {loc_str}")

# ===== TEST 2: build_url function =====
print("\n--- TEST 2: build_url() ---")
sys.path.insert(0, '.')
from scraper import build_url

geo_url = "https://www.olx.in/en-in/sundarpur_g5343637/for-rent-houses-apartments_c1723"
bhk_config = {"2": {"min": 0, "max": 15000}, "3": {"min": 0, "max": 20000}}
result_url = build_url(geo_url, bhk_config)
expected = f"{geo_url}?filter=bachelors_eq_yes%2Crooms_eq_2_and_3"

if result_url == expected:
    print(f"  [PASS] build_url correctly appends filters")
    print(f"         {result_url}")
else:
    all_pass = False
    print(f"  [FAIL] Expected: {expected}")
    print(f"         Got:      {result_url}")

# ===== TEST 3: run_scraper signature =====
print("\n--- TEST 3: run_scraper() signature ---")
import inspect
sig = inspect.signature(build_url)
params = list(sig.parameters.keys())
print(f"  build_url params: {params}")

from scraper import run_scraper
sig2 = inspect.signature(run_scraper)
params2 = list(sig2.parameters.keys())
print(f"  run_scraper params: {params2}")

if params2[0] == "geo_url":
    print("  [PASS] run_scraper accepts geo_url as first param")
else:
    all_pass = False
    print(f"  [FAIL] run_scraper first param is '{params2[0]}', expected 'geo_url'")

# ===== TEST 4: app.py config key =====
print("\n--- TEST 4: app.py frontend-backend contract ---")
with open("app.py", "r") as f:
    app_code = f.read()

if 'config.get("geo_url"' in app_code:
    print("  [PASS] app.py reads 'geo_url' from config")
else:
    all_pass = False
    print("  [FAIL] app.py does not read 'geo_url' from config")

if 'auto_resolve_location' not in app_code:
    print("  [PASS] app.py has no auto_resolve_location remnants")
else:
    all_pass = False
    print("  [FAIL] app.py still references auto_resolve_location")

# ===== TEST 5: script.js config key =====
print("\n--- TEST 5: script.js frontend contract ---")
with open("web/script.js", "r") as f:
    js_code = f.read()

if "geo_url:" in js_code:
    print("  [PASS] script.js sends 'geo_url' in config")
else:
    all_pass = False
    print("  [FAIL] script.js does not send 'geo_url' in config")

if "location_query" not in js_code:
    print("  [PASS] script.js has no old 'location_query' remnants")
else:
    all_pass = False
    print("  [FAIL] script.js still references 'location_query'")

if "validateOlxUrl" in js_code:
    print("  [PASS] script.js has URL validator function")
else:
    all_pass = False
    print("  [FAIL] script.js missing validateOlxUrl function")

# ===== TEST 6: scraper.py no auto_resolve remnants =====
print("\n--- TEST 6: scraper.py cleanup ---")
with open("scraper.py", "r") as f:
    scraper_code = f.read()

if "auto_resolve_location" not in scraper_code:
    print("  [PASS] scraper.py has no auto_resolve_location remnants")
else:
    all_pass = False
    print("  [FAIL] scraper.py still has auto_resolve_location")

# ===== TEST 7: Guide images exist =====
print("\n--- TEST 7: Guide screenshots ---")
import os
for img in ["web/guide_step1.png", "web/guide_step2.png", "web/guide_step3.png"]:
    if os.path.exists(img) and os.path.getsize(img) > 1000:
        size_kb = os.path.getsize(img) // 1024
        print(f"  [PASS] {img} exists ({size_kb}KB)")
    else:
        all_pass = False
        print(f"  [FAIL] {img} missing or empty")

# ===== TEST 8: index.html has guide modal =====
print("\n--- TEST 8: index.html structure ---")
with open("web/index.html", "r") as f:
    html_code = f.read()

checks = [
    ("location-url", "URL input element"),
    ("how-to-btn", "How-to button"),
    ("guide-modal", "Guide modal"),
    ("guide_step1.png", "Step 1 screenshot ref"),
    ("guide_step2.png", "Step 2 screenshot ref"),
    ("guide_step3.png", "Step 3 screenshot ref"),
    ("url-status", "URL status indicator"),
]
for check_id, desc in checks:
    if check_id in html_code:
        print(f"  [PASS] {desc} ({check_id})")
    else:
        all_pass = False
        print(f"  [FAIL] Missing {desc} ({check_id})")

# ===== FINAL RESULT =====
print("\n" + "=" * 60)
if all_pass:
    print("ALL TESTS PASSED! The BYOU feature is ready to ship.")
else:
    print("SOME TESTS FAILED. Review the output above.")
print("=" * 60)
