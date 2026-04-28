import json

from src.tests.config import recycler, manufacturer, oem
from pathlib import Path
from src.utils.fetch_utils import  fetch, login


def generate_listing_preview(message):
    payload = {"message": message}
    return fetch("/listing/generate-preview", payload, "POST")


def create_listing(x):
    return fetch("/listing/create-listing", x['response'], "POST")


if __name__ == "__main__":
    user = oem
    message = """
    I have a demand for 500 MWh NMC batteries (SoH 100), around bengaluru. The category is new 
    batteries. I need it by 30th October 2025.
    """
    # user = manufacturer
    # supply_message = """
    # I have a demand for 50 tons of Cobalt raw material, around bengaluru, with 75% purity.
    # I need it by 5th October 2025.
    # """

    # user = recycler
    # supply_message = """
    #     I have a demand for 30 MWh of NMC waste batteries, around bengaluru.
    #     The batteries have a state of health (SoH) 80%. I need it by 25th October 2025.
    # """

    with login(user):
        x = generate_listing_preview(message)
        y = create_listing(x)
        Path("last_run_id.txt").write_text(json.dumps({"listing_id": y['listing_id']}), encoding="utf-8")
