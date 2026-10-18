import sys
import os
import signal
import time
import re
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

if hasattr(signal, "SIGPIPE"):
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

load_dotenv()

MERLIN = os.getenv("MERLIN", "false") == "true"
BASE_URL = "https://www.geekbuying.com"
CATEGORY_IDS = os.getenv("CATEGORY_IDS_TO_PARSE", "").split(",")
CATEGORY_MAP = {
    "2080": "Electric-Scooters-2080",
    "2082": "Bikes-2082"
}
CATEGORIES = [CATEGORY_MAP.get(cat_id.strip(), cat_id.strip()) for cat_id in CATEGORY_IDS if cat_id.strip()]
BRAND_IDS = os.getenv("XBLAZE38_BRANDS_IDS", "").split(",")


def setup_browser(playwright_instance):
    # Initialize browser
    browser = playwright_instance.chromium.launch(headless=True, **({"executable_path":"/usr/local/bin/chrome"} if MERLIN else {}))
    page = browser.new_page()
    
    # Set headers to prevent blocking script as a bot
    page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"})
    return browser, page


def build_page_url(category, brand_id, page_num):
    # Create url according to category, page number and brand id
    return f"{BASE_URL}/category/{category}/{page_num}-40-3-0-0-0-grid-0-all-b-{brand_id}.html"


def extract_urls_from_page(page):
    urls = set()

    # Find detail pages with "/item/" in url
    hrefs = page.locator('a[href*="/item/"]').evaluate_all("elements => elements.map(el => el.getAttribute('href'))")

    for href in hrefs:
        if href:
            # Add BASE_URL for relative links
            if href.startswith("//"):
                full_url = "https:" + href
            elif href.startswith("/"):
                full_url = BASE_URL + href
            else:
                full_url = href
            match = re.fullmatch(
                r"https?://www\.geekbuying\.com(/[^?#]*)(?:\?([^#]*))?(?:#.*)?",
                full_url, re.IGNORECASE,
            )
            if not match:
                continue
            path = match.group(1).lower()
            query = match.group(2) or ""

            # Ignore suggested and excluded items
            if "pmrm=" in query.lower():
                continue
            if not path.startswith("/item/") or not path.endswith(".html"):
                continue
            if not re.search(r"(?:^|[-/])(?:bike|bicycle|ebike|scooter)(?:-|\.)", path):
                continue
            if re.search(r"(?:^|[-/])(?:for|motorcycle)(?:-|\.)", path):
                continue

            # Add url to set
            urls.add(BASE_URL + match.group(1))
    return urls


def main():
    urls = set()
    with sync_playwright() as p:
        # Browser initialization
        browser, page = setup_browser(p)

        for category in CATEGORIES:
            for brand_id in BRAND_IDS:
                # Search up to 2 pages for each brand
                for page_num in range(1, 3):
                    target_url = build_page_url(category, brand_id, page_num)

                    try:
                        # Load page
                        page.goto(target_url, timeout=20000, wait_until="domcontentloaded")

                        # Wait for products
                        page.wait_for_selector('a[href*="/item/"]', state="attached", timeout=5000)

                    except Exception as e:
                        # Continue if brand doesn't have more pages
                        print(f"Could not load {target_url}: {e}", file=sys.stderr, flush=True)
                        continue

                    # Extract products urls
                    page_urls = extract_urls_from_page(page)
                    urls.update(page_urls)

                    # Wait to prevent too many requests
                    time.sleep(1)

        browser.close()

    # Print urls
    for url in sorted(urls):
        print(url, flush=True)


if __name__ == "__main__":
    main()
