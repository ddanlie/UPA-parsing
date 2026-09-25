import sys
import os
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()
ITEM_COLS = os.getenv("ITEM_COLS", "").split(",")


def setup_browser(playwright_instance):
    # Initialize browser
    browser = playwright_instance.chromium.launch(headless=True)
    page = browser.new_page()

    # Set headers to prevent blocking script as a bot
    page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"})
    return browser, page


def get_table_value(page, key_name):
    try:
        # Find items with key_name
        row = page.locator('#Description table tr').filter(has_text=key_name).first
        raw_text = row.locator('td').nth(1).inner_text().strip()

        # If there are data for more table cells in one cell
        if ":" in raw_text:
            for line in raw_text.split('\n'):
                # Find key in any line inside a cell
                if key_name.lower() in line.lower() and ":" in line:
                    # Return part after found key
                    return line.split(":", 1)[1].strip()

        # Return text if there is only text
        return raw_text

    except Exception:
        return "-"


def extract_product_data(page, url):
    # Extraction
    try:
        name = page.locator("h1").first.inner_text().strip()
    except Exception:
        name = "-"

    try:
        price = page.locator(".price, #saleprice, .sale-price").first.inner_text().strip()
    except Exception:
        price = "-"

    brand = get_table_value(page, "Brand")
    colors = get_table_value(page, "Color")
    motor_power = get_table_value(page, "Power")
    battery = get_table_value(page, "Capacity")
    range_val = get_table_value(page, "Range")
    speed = get_table_value(page, "Speed")

    data_dict = {
        "url": url, "name": name, "price": price, "brand": brand, "colors": colors,
        "motor_power": motor_power, "battery": battery, "range": range_val, "speed": speed
    }
    raw_data = [data_dict.get(col, "-") for col in ITEM_COLS]

    # Remove \n, \r and \t from collected data
    cleaned_data = [str(val).replace('\n', ' ').replace('\r', '').replace('\t', ' ').strip() for val in raw_data]
    return cleaned_data

def main():
    # Read urls
    urls = [line.strip() for line in sys.stdin if line.strip()]

    if not urls:
        print("There are no urls in stdin.", file=sys.stderr)
        return

    with sync_playwright() as p:
        # Browser initialization
        browser, page = setup_browser(p)

        for url in urls:
            try:
                # Extract data from 1 url
                page.goto(url, timeout=60000)
                page.wait_for_selector('h1', state="attached", timeout=15000)
                data = extract_product_data(page, url)
                print("\t".join(data))
                sys.stdout.flush()

            except Exception as e:
                print(f"Error with parsing {url}: {e}", file=sys.stderr)
        browser.close()


if __name__ == "__main__":
    main()
