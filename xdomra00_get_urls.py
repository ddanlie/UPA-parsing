  # This script  parses the vehicles page and extracts the URLs of the individual vehicle pages of chosen brands
import os
from sys import stderr
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


def _get_and_print_items_links(pagenum:int, soup:BeautifulSoup):
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

def _get_html_doc_for_page(pagenum:int) -> str:
    response = requests.get(
        VEHICLES_PAGE_URL.format(pagenum),
        headers={ "User-Agent": USER_AGENT }
    )
    response.raise_for_status()
    html_doc = response.content.decode("utf-8")
    return html_doc

def get_urls(): 
    # Get 1st page by url and page number)
    html_doc = _get_html_doc_for_page(1)
    #html_doc = open("file.html", "r", encoding="utf-16").read()

    soup = BeautifulSoup(html_doc, 'html.parser')
    
    pages_count = max(int(a.get_text()) for a in soup.find("div", id="pagination").find_all("a", class_="pagenumber"))

    _get_and_print_items_links(1, soup)

    for pagenum in range(2, pages_count + 1):
        time.sleep(1)  # Be respectful to the server
        html_doc = _get_html_doc_for_page(pagenum)
        soup = BeautifulSoup(html_doc, 'html.parser')
        
        _get_and_print_items_links(pagenum, soup)




try: 
    get_urls()
except Exception as e: 
    print(f"Error occurred while fetching the page: {e}", file=stderr)
