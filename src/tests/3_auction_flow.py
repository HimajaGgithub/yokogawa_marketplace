from src.entities.db_model import Scenario
from src.tests.config import fleet_1, refurb_1, refurb_2, refurb_3, admin
from src.utils.fetch_utils import fetch, login, run, run_id


def get_run(scenario_id):
    payload = {"scenario_id": str(scenario_id)}
    return fetch("/scenario/run", payload, "POST")


def generate_listing_preview(message):
    payload = {"message": message}
    return fetch("/listing/generate-preview", payload, "POST")


def create_listing(x):
    return fetch("/listing/create-listing", x['response'], "POST")


def get_recommendations_for_me():
    fetch(f"/marketplace/latest-items-for-me", method="get")


def get_supply_demand_items():
    fetch(f"/marketplace/supply-demand-items", method="get")


def get_my_listings():
    fetch("/marketplace/view-my-listings", method="get")


def view_stats():
    fetch("/home/view-stats", method="get")


def view_recent_activity():
    fetch("/home/view-recent-activity", method="get")


def place_bid(price):
    payload = {
        "listing_id": auction_id,
        "price": price,
        "message": "This is my bid."
    }
    fetch("/auction/place-bid", payload, "post")


def get_bids():
    fetch(f"/listing/view-listing/{auction_id}", method="get")


def get_purchase_history():
    fetch(f"/marketplace/purchase-history", method="get")


def close_auction():
    fetch(f"/auction/close-auction", {"listing_id": auction_id}, method="post")


if __name__ == "__main__":
    # Existing scenarios
    scenario = Scenario.get(Scenario.scenario_name== "Auction Flow")

    with login(admin):
        run_obj = get_run(scenario.scenario_id)
    run_id.set(run_obj['run_id'])

    with login(refurb_3):
        demand_message = """
        I have a demand for 30 kgs of Lithium waste batteries, around bengaluru, 
        in really good working condition with 80% state of health. I'm up for negotiations.
        """
        x = generate_listing_preview(demand_message)
        create_listing(x)

    with login(fleet_1):
        supply_message = """
        I have a supply for 30 kgs of Lithium batteries which are waste batteries.
        I want them in good working condition, the brand is everyday and the 
        state of health is 80%, the voltage is 5V. My location is bangalore. 
        I am opening this for auction with start date is 15th August and end date as 
        20th August 2025, and the reserve price as 300 INR.
        """
        x = generate_listing_preview(supply_message)
        listing = create_listing(x)

        auction_id = listing['listing_id']

    run(fleet_1, get_recommendations_for_me)
    run(refurb_3, get_recommendations_for_me)

    run(fleet_1, get_supply_demand_items)
    run(refurb_3, get_supply_demand_items)

    run(fleet_1, get_supply_demand_items)
    run(refurb_3, get_supply_demand_items)

    run(refurb_1, place_bid, 1200)
    run(refurb_2, place_bid, 1220)
    run(refurb_3, place_bid, 1240)

    run(refurb_1, place_bid, 1300)
    run(refurb_2, place_bid, 1320)
    run(refurb_3, place_bid, 1340)

    run(refurb_1, place_bid, 1400)
    run(refurb_2, place_bid, 1420)
    run(refurb_3, place_bid, 1440)

    run(fleet_1, get_my_listings)
    run(fleet_1, view_recent_activity)
    run(fleet_1, view_stats)

    run(fleet_1, get_bids)
    run(fleet_1, close_auction)
    run(refurb_1, place_bid, 1800)
    run(refurb_3, get_purchase_history)

    print("RUN id is ", run_id.get())
