from src.entities.db_model import User
from src.tests.config import fleet, refurb
from src.utils.fetch_utils import login, fetch


def generate_listing_preview(message):
    payload = {"message": message}
    return fetch("/listing/generate-preview", payload, "POST")


def create_listing(x):
    return fetch("/listing/create-listing", x['response'], "POST")


def make_an_offer(price):
    payload = {
        "listing_id": listing_id,
        "action": "offer",
        "price": price,
        "message": "I want to buy it now"
    }
    fetch("/listing/negotiate", payload, "post")


def accept_offer():
    payload = {
        "listing_id": listing_id,
        "replying_to_user": other_user_id,
        "action": "accept",
        "message": "Ok, sold!"
    }
    fetch("/listing/negotiate", payload, "post")

def get_listing_details():
    return fetch(f"/listing/view-listing/{listing_id}", method="get")

def get_my_listings():
    return fetch("/marketplace/view-my-listings", method="get")


if __name__ == '__main__':
    listing_owner = refurb
    other_user = fleet

    other_user_id = str(User.get(User.email_id == other_user).user_id)
    with login(other_user):
        demand_message = """
        I have a demand for 300 units of refurbished batteries, around bengaluru, 
        in a really good working condition with 75% state of health. I'm up for negotiations.
        """
        x = generate_listing_preview(demand_message)
        other_listing = create_listing(x)
        other_listing_id = other_listing['listing_id']

    with login(listing_owner):
        supply_message = """
        I have a supply for 500 units of refurbished batteries, in chennai.
        The state of health is 75%, and the output rate is 12 watt-hours.
        I'm up for negotiations. My listing price must be 3000, and target price is 2700.
        """
        x = generate_listing_preview(supply_message)
        create_listing(x)

    with login(other_user):
        listings = get_my_listings()
        other_listing_with_matches = [x for x in listings if x['listing_id'] == other_listing_id][0]
        matched_listing = other_listing_with_matches['matches'][0]
        listing_id = matched_listing['listing_id']
        price = matched_listing['payload'].get("listing_price")
        make_an_offer(price)

    with login(listing_owner):
        accept_offer()
        get_listing_details()
