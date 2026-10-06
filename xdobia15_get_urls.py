import argparse
import os
from sys import stderr
from urllib.parse import urljoin

from dotenv import load_dotenv
from playwright.sync_api import Page, sync_playwright


URL = "https://www.geekbuying.com/category/Electric-Scooters-2080"
PAGE_LOAD_TIMEOUT_MS = 20_000
DEFAULT_RETRIES = 3

load_dotenv()


def parse_arguments() -> tuple[str, bool, int]:
    """Argument parsing, Added chrome for merlin, firefox for my workstation."""
    parser = argparse.ArgumentParser(description="Launch a Playwright browser.")
    browsers = parser.add_mutually_exclusive_group(required=True)
    browsers.add_argument(
        "-c", "--chromium", action="store_true", help="launch Chromium"
    )
    browsers.add_argument("-f", "--firefox", action="store_true", help="launch Firefox")
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="print progress messages to stderr"
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help=f"retry failed page loads this many times (default: {DEFAULT_RETRIES})",
    )
    arguments = parser.parse_args()
    if arguments.retries < 1:
        parser.error("--retries must be at least 1")
    return (
        "chromium" if arguments.chromium else "firefox",
        arguments.verbose,
        arguments.retries,
    )


def verbose_print(enabled: bool, message: str) -> None:
    if enabled:
        print(message, file=stderr, flush=True)


def get_brand_url(brand_id: str) -> str:
    return f"{URL}/1-40-3-0-0-0-grid-0-all-b-{brand_id}.html"


def get_brand_ids() -> list[str]:
    """Gets brand IDs which we distributed among team members"""
    brand_ids = [
        brand_id.strip()
        for brand_id in os.getenv("XDOBIA15_BRANDS_IDS", "").split(",")
        if brand_id.strip()
    ]
    if not brand_ids:
        raise ValueError("XDOBIA15_BRANDS_IDS must contain at least one brand ID")
    if any(not brand_id.isdecimal() for brand_id in brand_ids):
        raise ValueError("XDOBIA15_BRANDS_IDS must contain comma-separated numeric IDs")
    return brand_ids


def get_product_links(page: Page) -> list[str]:
    """Return product URLs from the currently loaded brand-results page."""
    links: list[str] = []

    for product in page.locator("li.searchResultItem > div > div > a").all():
        redirect = product.get_attribute("href")
        if redirect is not None:
            links.append(redirect)

    return links


def load_page(page: Page, url: str, retries: int) -> bool:
    """Load a page and print to stderr on failure"""
    for attempt in range(1, retries + 1):
        try:
            page.goto(url, wait_until="commit", timeout=PAGE_LOAD_TIMEOUT_MS)
            page.wait_for_timeout(5000)
            return True
        except Exception as error:
            print(
                f"Could not load {url} (attempt {attempt}/{retries}): {error}",
                file=stderr,
                flush=True,
            )
    return False


def main() -> None:
    engine_name, verbose, retries = parse_arguments()
    brand_ids = get_brand_ids()
    verbose_print(verbose, f"Configured brand IDs ({len(brand_ids)}): {', '.join(brand_ids)}")

    with sync_playwright() as pw:
        verbose_print(verbose, f"Launching {engine_name}")
        browser = getattr(pw, engine_name).launch(args=[
                "--disable-blink-features=AutomationControlled",\
                "--no-sandbox",\
                "--disable-infobars"
            ])
        try:
            page = browser.new_page()
            for number, brand_id in enumerate(brand_ids, start=1):
                brand_url = get_brand_url(brand_id)
                verbose_print(
                    verbose,
                    f"[{number}/{len(brand_ids)}] Loading brand {brand_id}: {brand_url}",
                )
                if not load_page(page, brand_url, retries):
                    print(
                        f"Skipping brand {brand_id} after {retries} failed load attempts",
                        file=stderr,
                        flush=True,
                    )
                    continue

                product_links = get_product_links(page)
                verbose_print(
                    verbose,
                    f"[{number}/{len(brand_ids)}] Found {len(product_links)} product URLs for brand {brand_id}",
                )
                for product_link in product_links:
                    print(urljoin(page.url, product_link))
        finally:
            verbose_print(verbose, "Closing browser")
            browser.close()


if __name__ == "__main__":
    main()
