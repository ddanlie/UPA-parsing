  # This script  parses the vehicles page and extracts the URLs of the individual vehicle pages of chosen brands
import os
from sys import stderr
import sys
import time
from bs4 import BeautifulSoup
import requests
from dotenv import load_dotenv

load_dotenv()

VEHICLES_PAGE_URL     = os.getenv("VEHICLES_PAGE_URL", "")
BRANDS_TO_PARRSE      = [brand.lower() for brand in os.getenv("XDOMRA00_BRANDS", "").split(",")]
ITEM_COLS             = os.getenv("ITEM_COLS", "").split(",")
CATEGORY_IDS_TO_PARSE = [int(catid) for catid in os.getenv("CATEGORY_IDS_TO_PARSE", "").split(",")]
USER_AGENT            = "student-project-script/1.0"
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
DEFAULT_PAGE_COUNT = 11

def _get_and_print_items_links(soup:BeautifulSoup):
    # Find all items with given brands and category ids
    items_links = [
        link
        for link in soup.find_all("a")
        if (
            (brand := link.get("data-brand"))
            and str(brand).lower() in BRANDS_TO_PARRSE
            and (category := link.get("data-category"))
            and any(
                str(catid).lower() in str(category).lower()
                for catid in CATEGORY_IDS_TO_PARSE
            )
        )
    ]

    printed_urls = set()
    for link in items_links:
        url = link.get("href")
        if url and url not in printed_urls:
            printed_urls.add(url)
            print(url)
            sys.stdout.flush()

def _get_html_doc_for_page(pagenum:int, timeout:int=20, attempts=1) -> str:
    for attempt in range(attempts):
        try:
            response = requests.get(
                VEHICLES_PAGE_URL.format(pagenum),
                headers={ "User-Agent": USER_AGENT },
                timeout=timeout,
                allow_redirects=True,
            )
            response.raise_for_status()
            html_doc = response.content.decode("utf-8")
            return html_doc
        except Exception as e:
            if attempt == attempts - 1:
                raise e
            time.sleep(1)
    raise Exception(f"Failed to fetch page {pagenum} after {attempts} attempts.")

def get_urls(): 
    # Get 1st page by url and page number)
    try: 
        if DEBUG:
            html_doc = open("file.html", "r", encoding="utf-16").read()
        else:
            html_doc = _get_html_doc_for_page(1, timeout=30, attempts=3)

        soup = BeautifulSoup(html_doc, 'html.parser')
        
        pages_count = max(int(a.get_text()) for a in soup.find("div", id="pagination").find_all("a", class_="pagenumber"))

        _get_and_print_items_links(soup)
    except Exception as e: 
        print(f"Error occurred while fetching the page and pages count: {e}", file=stderr)
        pages_count = DEFAULT_PAGE_COUNT


    for pagenum in range(2, pages_count + 1):
        try:
            time.sleep(1)  # Be respectful to the server
            html_doc = _get_html_doc_for_page(pagenum)
            soup = BeautifulSoup(html_doc, 'html.parser')
            
            _get_and_print_items_links(soup)
        except Exception as e: 
            print(f"Error occurred while fetching the page: {e}", file=stderr)

if __name__ == "__main__":
    get_urls()
