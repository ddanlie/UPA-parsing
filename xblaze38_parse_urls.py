import sys
import os
import re
from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

load_dotenv()

MERLIN = os.getenv("MERLIN", "false") == "true"
ITEM_COLS = os.getenv("ITEM_COLS", "").split(",")


def setup_browser(playwright_instance):
    # Initialize browser
    browser = playwright_instance.chromium.launch(headless=True, **({"executable_path":"/usr/local/bin/chrome"} if MERLIN else {}))
    page = browser.new_page()

    # Set headers to prevent blocking script as a bot
    page.set_extra_http_headers({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36"})
    return browser, page


def get_table_value(page, key_names):
    for key_name in key_names:
        try:
            # Find items with key_name
            rows = page.locator('#Description table tr').filter(has_text=key_name).all()

            for row in rows:
                cells = row.locator('td, th')
                cell_count = cells.count()
                if cell_count == 0:
                    continue

                target_cell_index = 1 if cell_count >= 2 else 0
                raw_text = cells.nth(target_cell_index).inner_text(timeout=2000).strip()

                # If there are data for more table cells in one cell
                if ":" in raw_text:
                    for line in raw_text.split('\n'):
                        # Find key in any line inside a cell
                        if key_name.lower() in line.lower() and ":" in line:
                            val = line.split(":", 1)[1].strip()
                            if val and len(val) < 60:
                                # Return part after found key and ": " if exists and is shorter than 60 characters
                                return val

                if cell_count >= 2:
                    first_cell_text = cells.nth(0).inner_text(timeout=2000).strip()
                    if key_name.lower() in first_cell_text.lower():
                        val = raw_text.split('\n')[0].strip()
                        # Return text shorter than 60 characters
                        if len(val) < 60:
                            return val

        except Exception:
            continue
    return "-"


def shorten_product_name(name):
    if not name:
        return "-"

    # Find "Electric" in name and 1 next word
    match = re.search(r"(?i)\bElectric\s+([A-Za-z0-9-]+)", name)
    if match:
        # Shorten name to "Electric" and 1 word only
        return name[:match.end()].strip()
    return name.strip()


def extract_product_data(page, url):
    # Extraction
    try:
        name = page.locator("h1").first.inner_text().strip()
        name = shorten_product_name(name)
    except Exception:
        name = "-"

    try:
        price = page.locator(".price, #saleprice, .sale-price").first.inner_text().strip()
    except Exception:
        price = "-"

    brand = get_table_value(page, ["Brand"])
    if brand == "-":
        try:
            brand_text = page.locator(".brand_name").first.inner_text(timeout=1000).strip()
            brand = brand_text.replace("Brand:", "").strip()
            if not brand:
                brand = "-"
        except Exception:
            pass

    colors = get_table_value(page, ["Color", "Colour"])
    motor_power = get_table_value(page, ["Rated Power", "Motor Power", "Motor", "Power"])
    battery = get_table_value(page, ["Battery Capacity", "Capacity & Voltage", "Battery", "Capacity", "Voltage"])
    range_val = get_table_value(page, ["Max Range", "Range", "Millage", "Mileage", "Distance"])
    speed = get_table_value(page, ["Max Speed", "Top Speed", "Speed"])

    data_dict = {
        "url": url, "name": name, "price": price, "brand": brand, "colors": colors,
        "motor power": motor_power, "battery power capacity": battery, "range": range_val, "speed": speed
    }
    raw_data = [data_dict.get(col, "-") for col in ITEM_COLS]

    # Remove \n, \r and \t from collected data
    cleaned_data = [str(val).replace('\n', ' ').replace('\r', '').replace('\t', ' ').strip() for val in raw_data]
    return cleaned_data

def main():
    # Read urls
    # DEBUG START:
    if len(sys.argv) > 1:
        input_path = sys.argv[1]
        try:
            with open(input_path, "r", encoding="utf-8") as f:
                urls = [line.strip() for line in f if line.strip()]
        except OSError as e:
            print(f"Failed to read input file '{input_path}': {e}", file=sys.stderr)
            return
    else:
        urls = [line.strip() for line in sys.stdin if line.strip()]
    # DEBUG END: urls = [line.strip() for line in sys.stdin if line.strip()]

    if not urls:
        print("There are no urls in stdin.", file=sys.stderr)
        return

    with sync_playwright() as p:
        # Browser initialization
        browser, page = setup_browser(p)

        for url in urls:
            try:
                # Extract data from 1 url
                page.goto(url, timeout=20000, wait_until="domcontentloaded")
                page.wait_for_selector('h1', state="attached", timeout=10000)
                data = extract_product_data(page, url)
                print("\t".join(data), flush=True)

            except Exception as e:
                print(f"Error with parsing {url}: {e}", file=sys.stderr)
        browser.close()


if __name__ == "__main__":
    main()
