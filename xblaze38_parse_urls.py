import sys
import os
import signal
import re
import time
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

if hasattr(signal, "SIGPIPE"):
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

load_dotenv()

ITEM_COLS = os.getenv("ITEM_COLS", "").split(",")


def get_table_value(page, key_names):
    def matches_key(text, key):
        return text.strip().rstrip(":").strip().casefold() == key.casefold()

    for key_name in key_names:
        try:
            # Find items with key_name
            rows = [[cell.get_text("\n", strip=True) for cell in row.select('td, th')]
                    for row in page.select('#Description table tr')]

            for cells in rows:
                cell_count = len(cells)
                if cell_count == 0:
                    continue

                target_cell_index = 1 if cell_count >= 2 else 0
                raw_text = cells[target_cell_index]

                # If there are data for more table cells in one cell
                if ":" in raw_text:
                    for line in raw_text.split('\n'):
                        # Find key in any line inside a cell
                        if ":" in line and matches_key(line.split(":", 1)[0], key_name):
                            val = line.split(":", 1)[1].strip()
                            if val and len(val) < 60:
                                # Return part after found key and ": " if exists and is shorter than 60 characters
                                return val

                if cell_count >= 2:
                    first_cell_text = cells[0]
                    if matches_key(first_cell_text, key_name):
                        val = raw_text.split('\n')[0].strip()
                        # Return text shorter than 60 characters
                        if len(val) < 60:
                            return val

        except Exception:
            continue
    return ""


def shorten_product_name(name):
    if not name:
        return ""

    # Find "Electric" in name and 1 next word
    match = re.search(r"(?i)\bElectric\s+([A-Za-z0-9-]+)", name)
    if match:
        # Shorten name to "Electric" and 1 word only
        return name[:match.end()].strip()
    return name.strip()


def extract_product_data(page: BeautifulSoup, url):
    # Extraction
    try:
        heading = page.select_one("h1")
        name = heading.get_text(" ", strip=True) if heading else ""
        name = shorten_product_name(name)
    except Exception:
        name = ""

    try:
        price_meta = page.select_one('meta[property="og:price:amount"]')
        price = str(price_meta.get("content", "")).strip() if price_meta else ""
        if not price:
            price_node = page.select_one("#saleprice, .price, .sale-price")
            price = price_node.get_text(" ", strip=True) if price_node else ""
    except Exception:
        price = ""

    brand = get_table_value(page, ["Brand"])
    if brand == "":
        try:
            brand_node = page.select_one(".brand_name")
            brand_text = brand_node.get_text(" ", strip=True) if brand_node else ""
            brand = brand_text.replace("Brand:", "").strip()
            if not brand:
                brand = ""
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
    raw_data = [data_dict.get(col, "") for col in ITEM_COLS]

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

    with requests.Session() as session:
        for url in urls:
            try:
                # Extract data from 1 url
                time.sleep(3)
                response = session.get(url, timeout=20)
                response.raise_for_status()
                page = BeautifulSoup(response.text, "html.parser")
                if "system update in progress" in page.get_text().lower():
                    raise RuntimeError("Site temporarily unavailable")
                if page.select_one("h1") is None:
                    raise ValueError("Product heading not found")
                data = extract_product_data(page, url)
                print("\t".join(data), flush=True)

            except Exception as e:
                print(f"Error with parsing {url}: {e}", file=sys.stderr)


if __name__ == "__main__":
    main()
