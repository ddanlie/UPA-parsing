import csv
import hashlib
import re
import sys
import os
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Iterable, Sequence
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag
from llm_parse import llm_resolve_cols
from playwright.sync_api import Page, sync_playwright

from dotenv import load_dotenv
load_dotenv()


CACHE_DIR = Path("cache")
TABLES_DIR = Path("tables")
RESPONSES_DIR = Path("responses")
ITEM_COLS = os.getenv("ITEM_COLS", "").split(",")
MAX_LLM_THREADS = 3
PAGE_LOAD_TIMEOUT_MS = 30_000
POST_LOAD_WAIT_MS = 5_000
PRICE_SELECTOR = "span#saleprice"
MERLIN = os.getenv("MERLIN", "false") == "true"


def get_description_tables(document: Tag, url: str) -> list[Tag]:
    """Return all ``#Description`` tables from a BeautifulSoup document."""
    description = document.find("div", id="Description")
    tables = description.find_all("table") if description else []
    if not tables:
        print(f"{url}: found no <table> elements in div#Description", file=sys.stderr)
    if len(tables) > 1:
        print(f"{url}: found {len(tables)} <table> elements", file=sys.stderr)
    return list(tables)


def get_table_rows(table: Tag) -> list[list[str]]:
    """Extract rows belonging to ``table``, excluding rows from nested tables."""
    rows: list[list[str]] = []
    for row in table.find_all("tr"):
        if row.find_parent("table") is not table:
            continue
        cells = row.find_all(("td", "th"), recursive=False)
        if cells:
            rows.append([cell.get_text("\n", strip=True) for cell in cells])
    return rows


def get_product_name(document: Tag, url: str) -> str:
    name = document.select_one("#productName h1, h1")
    return name.get_text(" ", strip=True) if name else get_product_name_from_url(url)


def get_product_price(document: Tag) -> tuple[str, str]:
    sale_price = document.select_one("span#saleprice")
    currency = document.select_one("span#currencyF")
    return (
        sale_price.get_text(" ", strip=True) if sale_price else "",
        currency.get_text(" ", strip=True) if currency else "",
    )


def get_product_name_from_url(url: str) -> str:
    """Make a readable fallback name when the page has no product heading."""
    return Path(urlparse(url).path).stem or "product"


def get_file_stem(product_name: str) -> str:
    """Return a portable filename stem derived from a product name."""
    stem = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", product_name)
    stem = re.sub(r"\s+", " ", stem).strip(" .")
    return (stem or "product")[:200]


def write_csv(path: Path, rows: Sequence[Sequence[str]]) -> None:
    """Write a rectangular UTF-8 CSV file without adding a synthetic header."""
    width = max(len(row) for row in rows)
    with path.open("w", newline="", encoding="utf-8") as output:
        writer = csv.writer(output)
        writer.writerows([list(row) + [""] * (width - len(row)) for row in rows])


def split_compound_parameter_row(row: Sequence[str]) -> list[list[str]]:
    """Split ``Param: Value`` lines stored together in the second table cell."""
    if len(row) != 2 or row[1].count(":") < 2:
        return [list(row)]

    entries = []
    for line in row[1].splitlines():
        parameter, separator, value = line.partition(":")
        if not separator or not parameter.strip() or not value.strip():
            return [list(row)]
        entries.append([parameter.strip(), value.strip()])
    return entries if len(entries) > 1 else [list(row)]


def expand_compound_parameter_rows(table: Sequence[Sequence[str]]) -> list[list[str]]:
    """Some table cells contain multiple Key: Value pairs, this splits such cells into multiple KV pairs in the table"""
    return [entry for row in table for entry in split_compound_parameter_row(row)]


def save_tables(
    product_name: str,
    url: str,
    sale_price: str,
    currency: str,
    tables: Sequence[Sequence[Sequence[str]]],
) -> list[Path]:
    """create csv tables for double checking and merge tables found on the website into one large table if number of columns matches."""
    non_empty_tables = [
        expand_compound_parameter_rows(table) for table in tables if table
    ]
    if not non_empty_tables:
        return []

    metadata_rows = [["URL", url], ["Price", sale_price], ["Currency", currency]]
    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    stem = get_file_stem(product_name)
    widths = [max(len(row) for row in table) for table in non_empty_tables]
    if len(set(widths)) == 1:
        output_paths = [TABLES_DIR / f"{stem}_TABLE.csv"]
        tables_to_write = [
            metadata_rows + [row for table in non_empty_tables for row in table]
        ]
    else:
        output_paths = [
            TABLES_DIR / f"{stem}_TABLE_{index}.csv"
            for index in range(1, len(non_empty_tables) + 1)
        ]
        tables_to_write = [metadata_rows + table for table in non_empty_tables]

    for path, rows in zip(output_paths, tables_to_write):
        write_csv(path, rows)
    return output_paths


def save_llm_thread(
    product_name: str,
    url: str,
    sale_price: str,
    currency: str,
    tables: Sequence[Tag],
) -> str | None:
    """Resolve product columns from all tables and save the LLM response."""
    if not tables:
        return None

    table_content = "\n".join(
        [
            f"URL: {url}",
            f"Price: {sale_price} {currency}".strip(),
            "Tables:",
            *(str(table) for table in tables),
        ]
    )

    RESPONSES_DIR.mkdir(parents=True, exist_ok=True)
    response_path = RESPONSES_DIR / f"{get_file_stem(product_name)}.out"
    response = "\t".join(llm_resolve_cols(table_content))
    response_path.write_text(response + "\n", encoding="utf-8")
    return response


def get_cache_path(url: str) -> Path:
    url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{url_hash}.html"


def get_cached_page(page: Page, url: str) -> BeautifulSoup:
    """Get page from cache then construct beautiful soup"""
    cache_path = get_cache_path(url)
    if cache_path.is_file():
        cached_page = BeautifulSoup(
            cache_path.read_text(encoding="utf-8"), "html.parser"
        )
        cached_price = cached_page.select_one(PRICE_SELECTOR)
        if cached_price and cached_price.get_text(strip=True):
            return cached_page

    page.goto(url, wait_until="domcontentloaded", timeout=PAGE_LOAD_TIMEOUT_MS)
    page.wait_for_timeout(POST_LOAD_WAIT_MS)
    html = page.content()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(html, encoding="utf-8")
    return BeautifulSoup(cache_path.read_text(encoding="utf-8"), "html.parser")


def process_urls(urls: Iterable[str]) -> None:
    """ Create playwright -> use playwright to load website content along with dynamically loaded elements (Prices were dynamically loaded) ->
     save DOM and load it using beautifulSoup -> get tables and price -> send it over to LLM -> LLM returns all the necessary data."""
    executor = ThreadPoolExecutor(max_workers=MAX_LLM_THREADS)
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, **({"executable_path":"/usr/local/bin/chrome"} if MERLIN else {}))
            try:
                page = browser.new_page()
                response_futures: list[tuple[str, Future[str | None]]] = []
                for url in urls:
                    try:
                        document = get_cached_page(page, url)
                        tables = get_description_tables(document, url)
                        product_name = get_product_name(document, url)
                        sale_price, currency = get_product_price(document)
                        save_tables(
                            product_name,
                            url,
                            sale_price,
                            currency,
                            [get_table_rows(table) for table in tables],
                        )
                        response_futures.append(
                            (
                                url,
                                executor.submit(
                                    save_llm_thread,
                                    product_name,
                                    url,
                                    sale_price,
                                    currency,
                                    tables,
                                ),
                            )
                        )
                    except Exception as error:
                        print(f"Could not load {url}: {error}", file=sys.stderr)

                for url, response_future in response_futures:
                    try:
                        if response := response_future.result():
                            print(response)
                    except Exception as error:
                        print(f"Could not process {url} with the LLM: {error}", file=sys.stderr)
            finally:
                browser.close()
    except KeyboardInterrupt:
        executor.shutdown(wait=False, cancel_futures=True)
        print("Interrupted: cancelled pending LLM jobs.", file=sys.stderr)
        return
    else:
        executor.shutdown(wait=True)


def main() -> None:
    urls = (line.strip() for line in sys.stdin if line.strip())
    #print("\t".join(ITEM_COLS))
    process_urls(urls)


if __name__ == "__main__":
    main()
