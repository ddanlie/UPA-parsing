from sys import stderr, stdin
from bs4 import BeautifulSoup
import requests
import os
from dotenv import load_dotenv
from llm_parse import llm_resolve_cols
import time

load_dotenv()

ITEM_COLS = os.getenv("ITEM_COLS", "").split(",")

EMPTY_COLS = ["" for i in range(len(ITEM_COLS))]

# links exmaple
# links = """https://www.geekbuying.com/item/Magicycle-CT-1-Torque-Sensor-Electric-Bike-Red-528350.html
# https://www.geekbuying.com/item/Magicycle-Deer-2-0-Step-thru-Torque-Sensor-Electric-Bike-Blue-Grey-528346.html
# https://www.geekbuying.com/item/TWOFISH-V2-MAX-Electric-Scooter-600W-48V-17Ah-53km-h-530811.html
# https://www.geekbuying.com/item/Magicycle-Jaguarundi-2-0-Torque-Sensor-Folding-Electric-Bike-White-528325.html
# https://www.geekbuying.com/item/TWOFISH-M5-PRO-S-Electric-Scooter-500W-48V-13Ah-25km-h-531100.html
# https://www.geekbuying.com/item/Magicycle-CT-1-Torque-Sensor-Electric-Bike-Blue-528351.html
# https://www.geekbuying.com/item/TWOFISH-M5-ELITE-Electric-Scooter-500W-48V-13Ah-45km-h-531099.html
# https://www.geekbuying.com/item/Magicycle-Ocelot-Pro-2-0-Electric-Bike-Green-528323.html
# https://www.geekbuying.com/item/Magicycle-Cruiser-Pro-Step-thru-Electric-Bike-White-528314.html
# https://www.geekbuying.com/item/TWOFISH-TW4-PRO-Electric-Scooter-60V-23Ah-72km-h-530807.html
# https://www.geekbuying.com/item/Magicycle-Ocelot-Pro-Electric-Bike-White-528317.html
# """


def parse_urls():
    #for url in links.splitlines():
    for url in stdin:
        #time.sleep(1)  # Be respectful to the server
        url = url.strip()
        if not url:
            continue
        response = requests.get(url)
        response.raise_for_status()
        soup = BeautifulSoup(response.content.decode("utf-8"), "html.parser")

        name = ""
        name_element = soup.find("div", id="productName")
        if name_element:
            name = name_element.h1.get_text(strip=True).replace("\t", " ")

        price = 0.0
        price_element = soup.find(
            "meta",
            attrs={"property": "og:price:amount"}
        )
        if price_element:
            price = price_element.get("content", "").strip()

        description_text = str(soup.find("table", class_="jbEidtTable") or "")
        cols = [""] * len(ITEM_COLS)
        if description_text:
            cols = llm_resolve_cols(description_text)
            cols[ITEM_COLS.index("name")] = name
            cols[ITEM_COLS.index("price")] = price
            cols[ITEM_COLS.index("url")] = url
            print("\t".join(map(str, cols)))
        else:
            print("\t".join(EMPTY_COLS))

if __name__ == "__main__":
    try:
        parse_urls()
    except Exception as e:
        print(f"Error: {e}", file=stderr)
