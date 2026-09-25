import sys
import os
import time
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()
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
    browser = playwright_instance.chromium.launch(headless=True)
    page = browser.new_page()
    
    # Set headers to prevent blocking script as a bot
    page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"})
    return browser, page


def build_page_url(category, brand_id, page_num):
    # Create url according to category, page number and brand id
    return f"{BASE_URL}/category/{category}/{page_num}-40-3-0-0-0-grid-0-all-b-{brand_id}.html"


def extract_urls_from_page(page):
    urls = set()

    EXCLUDED_WORDS = [
        "bag", "charger", "battery", "tire", "helmet", "display", "seat", "accessories",
        "motor", "printer", "laser", "monitor", "projector", "smartwatch", "purifier",
        "camera", "vacuum", "pc", "starter", "station"
    ]
    
    # Find detail pages with "/item/" in url
    product_links = page.locator('a[href*="/item/"]')

    # Go through locators and get links
    for i in range(product_links.count()):
        href = product_links.nth(i).get_attribute("href")
        if href:
            # Add BASE_URL for relative links
            full_url = href if href.startswith("http") else BASE_URL + href

            # Ignore suggested items
            if "?pmrm=" in full_url:
                continue

            # Ignore excluded items
            if any(word in full_url.lower() for word in EXCLUDED_WORDS):
                continue

            # Add url to set
            urls.add(full_url)
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
                        page.goto(target_url, timeout=60000)

                        # Wait for products
                        page.wait_for_selector('a[href*="/item/"]', state="attached", timeout=15000)

                    except Exception as e:
                        # Continue if brand doesn't have more pages
                        print(f"Error with loading a page {target_url}: {e}", file=sys.stderr)
                        continue

                    # Extract products urls
                    page_urls = extract_urls_from_page(page)
                    urls.update(page_urls)

                    # Wait to prevent too many requests
                    time.sleep(2)

        browser.close()

    # Print urls
    for url in urls:
        print(url)


if __name__ == "__main__":
    main()
