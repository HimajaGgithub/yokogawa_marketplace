from src.entities.db_model import User
from src.tests.config import fleet, refurb, manufacturer, recycler, ess
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
    }
    fetch("/listing/negotiate", payload, "post")


def make_counter_offer(price):
    payload = {
        "listing_id": listing_id,
        "replying_to_user": other_user_id,
        "action": "counter_offer",
        "price": price,
        "message": "No, your quote is way too low, I need more."
    }
    fetch("/listing/negotiate", payload, "post")


def reject_offer():
    payload = {
        "listing_id": listing_id,
        "replying_to_user": other_user_id,
        "action": "reject",
        "message": "Nope."
    }
    fetch("/listing/negotiate", payload, "post")


def get_listing_details():
    fetch(f"/listing/view-listing/{listing_id}", method="get")


if __name__ == "__main__":
    # Scenario 1: Fleet (buyer) and Refurb (seller)
    listing_owner = fleet
    other_user = refurb

    other_user_id = str(User.get(User.email_id == other_user).user_id)
    with login(other_user):
        demand_message = """
        I have a demand for 300 units of refurbished batteries, around bengaluru, 
        in a really good working condition with 75% state of health. I'm up for negotiations.
        """
        x = generate_listing_preview(demand_message)
        create_listing(x)

    with login(listing_owner):
        supply_message = """
        I have a supply for 500 units of refurbished batteries, in chennai.
        The state of health is 75%, and the output rate is 12 watt-hours.
        I'm up for negotiations. My listing price must be 3000, and target price is 2700.
        """
        x = generate_listing_preview(supply_message)
        listing = create_listing(x)
        listing_id = listing['listing_id']

    with login(other_user):
        make_an_offer(900)
        get_listing_details()

    with login(listing_owner):
        make_counter_offer(1200)
        get_listing_details()

    with login(other_user):
        make_an_offer(1200)
        get_listing_details()

    with login(listing_owner):
        reject_offer()
        get_listing_details()

    with login(other_user):
        make_an_offer(1200)
        get_listing_details()

    # Scenario 2: Recycler (seller) and Manufacturer (buyer)
    listing_owner = recycler
    other_user = manufacturer

    other_user_id = str(User.get(User.email_id == other_user).user_id)
    with login(other_user):
        demand_message = """
        Looking to purchase 1500 kg of recycled Lithium for new battery production in Surat.
        Require cells with at least 65% state of health. Open to negotiation for bulk pricing.
        """
        x = generate_listing_preview(demand_message)
        create_listing(x)

    with login(listing_owner):
        supply_message = """
        Supplying 2000 kg of recycled Lithium, processed and ready for reuse.
        Located in Surat. Negotiable for large orders.
        """
        x = generate_listing_preview(supply_message)
        listing = create_listing(x)
        listing_id = listing['listing_id']

    with login(other_user):
        make_an_offer(300000)
        get_listing_details()

    with login(listing_owner):
        make_counter_offer(325000)
        get_listing_details()

    with login(other_user):
        make_an_offer(325000)
        get_listing_details()

    with login(listing_owner):
        reject_offer()
        get_listing_details()

    with login(other_user):
        make_an_offer(330000)
        get_listing_details()

    # Scenario 3: ESS (seller) and recycler (buyer)
    listing_owner = ess
    other_user = recycler

    other_user_id = str(User.get(User.email_id == other_user).user_id)
    with login(other_user):
        demand_message = """
        Need 80 MWh of used NMC batteries for EV fleet expansion in Kolkata.
        Must have at least 70% state of health. Willing to negotiate for best price.
        """
        x = generate_listing_preview(demand_message)
        create_listing(x)

    with login(listing_owner):
        supply_message = """
        Offering 100 MWh of used NMC batteries, located in Kolkata.
        State of health is 72%, voltage is 3.6V. Open to negotiation.
        """
        x = generate_listing_preview(supply_message)
        listing = create_listing(x)
        listing_id = listing['listing_id']

    with login(other_user):
        make_an_offer(950000)
        get_listing_details()

    with login(listing_owner):
        make_counter_offer(1_100_000)
        get_listing_details()

    with login(other_user):
        make_an_offer(1_100_000)
        get_listing_details()

    with login(listing_owner):
        reject_offer()
        get_listing_details()

    with login(other_user):
        make_an_offer(1_150_000)
        get_listing_details()
