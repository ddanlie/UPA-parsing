import argparse
import csv
import hashlib
import re
import signal
import sys
import os
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Iterable, Sequence
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag
from llm_parse import llm_resolve_cols
from playwright.sync_api import Page, sync_playwright
import requests

from dotenv import load_dotenv

if hasattr(signal, "SIGPIPE"):
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

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


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Parse product URLs from standard input.")
    parser.add_argument(
        "-p",
        "--playwright",
        action="store_true",
        help="render pages with Playwright before parsing them",
    )
    parser.add_argument(
        "--save-responses",
        action="store_true",
        help="save LLM responses to ./responses",
    )
    return parser.parse_args()


def get_tables(document: Tag, url: str) -> list[Tag]:
    """Div with ID description is the main body of the page containing the tables"""
    description = document.find("div", id="Description")
    tables = description.find_all("table") if description else []
    if not tables:
        print(f"{url}: found no <table> elements in div#Description", file=sys.stderr)
    if len(tables) > 1:
        print(f"{url}: found {len(tables)} <table> elements", file=sys.stderr)
    return list(tables)


def get_table_rows(table: Tag) -> list[list[str]]:
    """Sometimes table cells may contain another table, in that case just return the entire table as a cells value"""
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


def get_product_price(document: Tag, use_playwright: bool) -> tuple[str, str]:
    """Prices are unfortunately rendered dynamically but for some reason are also contained in <meta> property after a normal get request."""
    if use_playwright:
        sale_price = document.select_one(PRICE_SELECTOR)
        price = sale_price.get_text(" ", strip=True) if sale_price else ""
    else:
        price_meta = document.select_one('meta[property="og:price:amount"]')
        price = price_meta.get("content", "").strip() if price_meta else ""

    currency = document.select_one("span#currencyF")
    return (
        price,
        currency.get_text(" ", strip=True) if currency else "",
    )


def get_product_name_from_url(url: str) -> str:
    """return last part of url path or "product" on failure."""
    return Path(urlparse(url).path).stem or "product"


def get_file_stem(product_name: str) -> str:
    """Create filename from product name"""
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


def split_compound_values(table: Sequence[Sequence[str]]) -> list[list[str]]:
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
        split_compound_values(table) for table in tables if table
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
    save_response: bool,
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

    response = "\t".join(llm_resolve_cols(table_content))
    if save_response:
        RESPONSES_DIR.mkdir(parents=True, exist_ok=True)
        response_path = RESPONSES_DIR / f"{get_file_stem(product_name)}.out"
        response_path.write_text(response + "\n", encoding="utf-8")
    return response


def get_cache_path(url: str) -> Path:
    url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{url_hash}.html"


def get_cached_page(url: str) -> BeautifulSoup:
    """Pure beautiful soup"""
    cache_path = get_cache_path(url)
    if not cache_path.is_file():
        response = requests.get(url, timeout=PAGE_LOAD_TIMEOUT_MS / 1_000)
        response.raise_for_status()
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_path.write_text(response.text, encoding="utf-8")
    return BeautifulSoup(cache_path.read_text(encoding="utf-8"), "html.parser")


def get_rendered_cached_page(page: Page, url: str) -> BeautifulSoup:
    """Playwright to load dynamic content -> Beautiful soup"""
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


def queue_url(
    url: str,
    document: Tag,
    use_playwright: bool,
    save_responses: bool,
    executor: ThreadPoolExecutor,
    response_futures: list[tuple[str, Future[str | None]]],
) -> None:
    """Parse product and feed it to the llm. """
    tables = get_tables(document, url)
    product_name = get_product_name(document, url)
    sale_price, currency = get_product_price(document, use_playwright)
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
                save_responses,
            ),
        )
    )


def process_urls(
    urls: Iterable[str], use_playwright: bool, save_responses: bool
) -> None:
    """Core of URL processing: Uses beautiful soup for parsing and playwright if enabled for dynamic content loading. Only feeds tables to LLM to save on tokens. """
    executor = ThreadPoolExecutor(max_workers=MAX_LLM_THREADS)
    try:
        response_futures: list[tuple[str, Future[str | None]]] = []
        if use_playwright:
            with sync_playwright() as playwright:
                browser = playwright.chromium.launch(
                    headless=True,
                    **({"executable_path": "/usr/local/bin/chrome"} if MERLIN else {}),
                )
                try:
                    page = browser.new_page()
                    for url in urls:
                        try:
                            queue_url(
                                url,
                                get_rendered_cached_page(page, url),
                                use_playwright,
                                save_responses,
                                executor,
                                response_futures,
                            )
                        except Exception as error:
                            print(f"Could not load {url}: {error}", file=sys.stderr)
                finally:
                    browser.close()
        else:
            for url in urls:
                try:
                    queue_url(
                        url,
                        get_cached_page(url),
                        use_playwright,
                        save_responses,
                        executor,
                        response_futures,
                    )
                except Exception as error:
                    print(f"Could not load {url}: {error}", file=sys.stderr)

        for url, response_future in response_futures:
            try:
                if response := response_future.result():
                    print(response, flush=True)
            except Exception as error:
                print(f"Could not process {url} with the LLM: {error}", file=sys.stderr)
    except KeyboardInterrupt:
        """Cancels the future tasks, the currently running tasks will crash on an unhandled exception."""
        executor.shutdown(wait=False, cancel_futures=True)
        print("Interrupted: cancelled pending LLM jobs.", file=sys.stderr)
        return
    else:
        executor.shutdown(wait=True)


def main() -> None:
    arguments = parse_arguments()
    urls = (line.strip() for line in sys.stdin if line.strip()) # creates list of strings
    #print("\t".join(ITEM_COLS))
    process_urls(urls, arguments.playwright, arguments.save_responses)


if __name__ == "__main__":
    main()
