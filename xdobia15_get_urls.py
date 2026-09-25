import argparse
from urllib.parse import urljoin

from playwright.sync_api import Page, sync_playwright


URL = "https://www.geekbuying.com/category/Electric-Scooters-2080"


def parse_arguments() -> str:
    """Return the browser engine selected on the command line."""
    parser = argparse.ArgumentParser(description="Launch a Playwright browser.")
    browsers = parser.add_mutually_exclusive_group(required=True)
    browsers.add_argument(
        "-c", "--chromium", action="store_true", help="launch Chromium"
    )
    browsers.add_argument("-f", "--firefox", action="store_true", help="launch Firefox")
    arguments = parser.parse_args()
    return "chromium" if arguments.chromium else "firefox"


def get_brands(page: Page) -> list[tuple[str, str]]:
    """Return ``(brand_id, redirect)`` pairs from the page's brand filter."""
    brands: list[tuple[str, str]] = []

    for brand in page.locator("li.filter_brands_li").all():
        brand_id = brand.get_attribute("id")
        redirect = brand.locator("a").first.get_attribute("href")

        if brand_id is not None and redirect is not None:
            brands.append((brand_id, redirect))

    return brands


def get_product_links(page: Page) -> list[str]:
    """Return product URLs from the currently loaded brand-results page."""
    links: list[str] = []

    for product in page.locator("li.searchResultItem > div > div > a").all():
        redirect = product.get_attribute("href")
        if redirect is not None:
            links.append(redirect)

    return links


def main() -> None:
    engine_name = parse_arguments()

    # `pw` is the conventional short alias for Playwright's runtime instance.
    with sync_playwright() as pw:
        browser = getattr(pw, engine_name).launch(args=[
                "--disable-blink-features=AutomationControlled",\
                "--no-sandbox",\
                "--disable-infobars"
            ])
        try:
            page = browser.new_page()
            page.goto(URL, wait_until="commit", timeout=45000)
            page.wait_for_timeout(5000)

            title = page.title()
            print(f"loaded {title}")
            brands = get_brands(page)

            for brand_id, redirect in brands:
                brand_url = urljoin(page.url, redirect)
                page.goto(brand_url, wait_until="commit", timeout=45000)
                page.wait_for_timeout(5000)

                for product_link in get_product_links(page):
                    print(product_link)
        finally:
            browser.close()


if __name__ == "__main__":
    main()
