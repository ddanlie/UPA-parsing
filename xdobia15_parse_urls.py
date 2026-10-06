import argparse
import csv
import hashlib
import re
import sys
from collections import Counter
from pathlib import Path
from typing import Iterable, Sequence
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag
from playwright.sync_api import Locator, Page, sync_playwright


PAGE_LOAD_TIMEOUT_MS = 10_000
POST_LOAD_WAIT_MS = 5_000
CACHE_DIR = Path("cache")
TABLES_DIR = Path("tables")


def parse_arguments() -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description="Load product URLs from standard input.")
    parser.add_argument(
        "--get-params",
        action="store_true",
        help="print how many times each table parameter occurs across all URLs",
    )
    parser.add_argument(
        "--soup",
        action="store_true",
        help="use MechanicalSoup instead of the default Playwright browser",
    )
    return parser.parse_args()


def get_tables(page: Page, url: str) -> list[Locator]:
    """Return all tables in ``#Description`` and report unexpected table counts."""
    tables = page.locator("div#Description table")
    table_count = tables.count()
    if table_count == 0:
        print(f"{url}: found no <table> elements in div#Description", file=sys.stderr)
    if table_count > 1:
        print(f"{url}: found {table_count} <table> elements", file=sys.stderr)
    return tables.all()


def get_params(tables: Iterable[Locator]) -> Counter[str]:
    """Return parameter-name occurrences from all rows with exactly two cells."""
    parameters: Counter[str] = Counter()
    for table in tables:
        parameters.update(
            table.locator("tr").evaluate_all(
                """rows => rows.flatMap(row => {
                    const cells = [...row.querySelectorAll(':scope > td')];
                    return cells.length === 2 && cells[0].textContent.trim()
                        ? [cells[0].textContent.trim()]
                        : [];
                })"""
            )
        )
    return parameters


def get_playwright_table_rows(table: Locator) -> list[list[str]]:
    """Extract the displayed text of each non-empty row from one table."""
    return table.evaluate(
        """table => [...table.rows]
            .map(row => [...row.cells].map(cell => cell.innerText.trim()
                .replace(/[ \\t\\f\\v]+/g, ' ')))
            .filter(row => row.length)"""
    )


def get_playwright_product_name(page: Page, url: str) -> str:
    """Return the page product name, with a URL-derived fallback."""
    name = page.locator("#productName h1, h1").first.text_content()
    return name.strip() if name else get_product_name_from_url(url)

def get_soup_tables(soup: Tag, url: str) -> list[Tag]:
    """Return all ``#Description`` tables from a BeautifulSoup document."""
    description = soup.find("div", id="Description")
    tables = description.find_all("table") if description else []
    if not tables:
        print(f"{url}: found no <table> elements in div#Description", file=sys.stderr)
    if len(tables) > 1:
        print(f"{url}: found {len(tables)} <table> elements", file=sys.stderr)
    return list(tables)


def get_soup_params(tables: Iterable[Tag]) -> Counter[str]:
    """Return parameter-name occurrences from all MechanicalSoup result tables."""
    parameters: Counter[str] = Counter()
    for table in tables:
        for row in table.find_all("tr"):
            cells = row.find_all("td", recursive=False)
            if len(cells) == 2 and (parameter := cells[0].get_text(strip=True)):
                parameters.update([parameter])
    return parameters


def get_soup_table_rows(table: Tag) -> list[list[str]]:
    """Extract rows belonging to ``table``, excluding rows from nested tables."""
    rows: list[list[str]] = []
    for row in table.find_all("tr"):
        if row.find_parent("table") is not table:
            continue
        cells = row.find_all(("td", "th"), recursive=False)
        if cells:
            rows.append([cell.get_text("\n", strip=True) for cell in cells])
    return rows


def get_soup_product_name(soup: Tag, url: str) -> str:
    """Return the product heading from a BeautifulSoup document."""
    name = soup.select_one("#productName h1, h1")
    return name.get_text(" ", strip=True) if name else get_product_name_from_url(url)


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
    """Turn compound two-cell specification rows into one row per parameter."""
    return [entry for row in table for entry in split_compound_parameter_row(row)]


def save_tables(product_name: str, tables: Sequence[Sequence[Sequence[str]]]) -> list[Path]:
    """Save page tables, merging them only when all have the same width."""
    non_empty_tables = [
        expand_compound_parameter_rows(table) for table in tables if table
    ]
    if not non_empty_tables:
        return []

    TABLES_DIR.mkdir(parents=True, exist_ok=True)
    stem = get_file_stem(product_name)
    widths = [max(len(row) for row in table) for table in non_empty_tables]
    if len(set(widths)) == 1:
        output_paths = [TABLES_DIR / f"{stem}_TABLE.csv"]
        tables_to_write = [[row for table in non_empty_tables for row in table]]
    else:
        output_paths = [
            TABLES_DIR / f"{stem}_TABLE_{index}.csv"
            for index in range(1, len(non_empty_tables) + 1)
        ]
        tables_to_write = non_empty_tables

    for path, rows in zip(output_paths, tables_to_write):
        write_csv(path, rows)
    return output_paths


def get_cache_path(url: str) -> Path:
    """Return the cache-file path for a URL without putting the URL in its name."""
    url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()
    return CACHE_DIR / f"{url_hash}.html"


def get_cached_soup(browser, url: str) -> BeautifulSoup:
    """Return cached page HTML, or load and cache the MechanicalSoup DOM."""
    cache_path = get_cache_path(url)
    if cache_path.is_file():
        return BeautifulSoup(cache_path.read_text(encoding="utf-8"), "html.parser")

    browser.open(url)
    soup = browser.get_current_page()
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(str(soup), encoding="utf-8")
    return soup


def process_with_playwright(
    urls: Iterable[str], get_parameters: bool
) -> Counter[str]:
    """Load URLs using the default headless Playwright browser."""
    parameter_counts: Counter[str] = Counter()

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        try:
            page = browser.new_page()

            for url in urls:
                try:
                    page.goto(url, wait_until="commit", timeout=PAGE_LOAD_TIMEOUT_MS)
                    page.wait_for_timeout(POST_LOAD_WAIT_MS)

                    tables = get_tables(page, url)
                    if get_parameters:
                        parameter_counts.update(get_params(tables))
                    else:
                        output_paths = save_tables(
                            get_playwright_product_name(page, url),
                            [get_playwright_table_rows(table) for table in tables],
                        )
                        for output_path in output_paths:
                            print(output_path)
                except Exception as error:
                    print(f"Could not load {url}: {error}", file=sys.stderr)
        finally:
            browser.close()
    return parameter_counts


def process_with_soup(urls: Iterable[str], get_parameters: bool) -> Counter[str]:
    """Load URLs using MechanicalSoup without executing page JavaScript."""
    try:
        import mechanicalsoup
    except ModuleNotFoundError as error:
        raise RuntimeError(
            "MechanicalSoup is not installed. Run: ./.venv/bin/pip install -r requirements.txt"
        ) from error

    parameter_counts: Counter[str] = Counter()
    browser = mechanicalsoup.StatefulBrowser()
    try:
        for url in urls:
            try:
                soup = get_cached_soup(browser, url)
                tables = get_soup_tables(soup, url)
                if get_parameters:
                    parameter_counts.update(get_soup_params(tables))
                else:
                    output_paths = save_tables(
                        get_soup_product_name(soup, url),
                        [get_soup_table_rows(table) for table in tables],
                    )
                    for output_path in output_paths:
                        print(output_path)
            except Exception as error:
                print(f"Could not load {url}: {error}", file=sys.stderr)
    finally:
        browser.session.close()
    return parameter_counts


def main() -> None:
    """Load every non-empty URL received on standard input in one browser session."""
    arguments = parse_arguments()
    urls = (line.strip() for line in sys.stdin if line.strip())

    if arguments.soup:
        parameter_counts = process_with_soup(urls, arguments.get_params)
    else:
        parameter_counts = process_with_playwright(urls, arguments.get_params)

    if arguments.get_params:
        for parameter, count in sorted(parameter_counts.items()):
            print(f"{parameter}\t{count}")


if __name__ == "__main__":
    main()
