import sys
import os
import signal
import time
import re
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

if hasattr(signal, "SIGPIPE"):
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

load_dotenv()

BASE_URL = "https://www.geekbuying.com"
CATEGORY_IDS = os.getenv("CATEGORY_IDS_TO_PARSE", "").split(",")
CATEGORY_MAP = {
    "2080": "Electric-Scooters-2080",
    "2082": "Bikes-2082"
}
CATEGORIES = [CATEGORY_MAP.get(cat_id.strip(), cat_id.strip()) for cat_id in CATEGORY_IDS if cat_id.strip()]
BRAND_IDS = os.getenv("XBLAZE38_BRANDS_IDS", "").split(",")


def build_page_url(category, brand_id, page_num):
    # Create url according to category, page number and brand id
    return f"{BASE_URL}/category/{category}/{page_num}-40-3-0-0-0-grid-0-all-b-{brand_id}.html"


def extract_urls_from_page(page):
    urls = set()

    # Find detail pages with "/item/" in url
    hrefs = [link.get("href") for link in page.select('a[href*="/item/"]')]

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
    with requests.Session() as session:
        for category in CATEGORIES:
            for brand_id in BRAND_IDS:
                # Search up to 2 pages for each brand
                for page_num in range(1, 3):
                    target_url = build_page_url(category, brand_id, page_num)

                    try:
                        # Load page
                        time.sleep(1)
                        response = session.get(target_url, timeout=20)
                        response.raise_for_status()
                        page = BeautifulSoup(response.text, "html.parser")
                        if "system update in progress" in page.get_text().lower():
                            raise RuntimeError("Site temporarily unavailable")

                    except Exception as e:
                        # Continue if brand doesn't have more pages
                        print(f"Could not load {target_url}: {e}", file=sys.stderr, flush=True)
                        continue

                    # Extract products urls
                    page_urls = extract_urls_from_page(page)
                    urls.update(page_urls)

                    # Wait to prevent too many requests
                    time.sleep(1)

    # Print urls
    for url in sorted(urls):
        print(url, flush=True)


if __name__ == "__main__":
    main()
