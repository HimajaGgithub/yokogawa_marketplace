from src.entities.db_model import User
from src.tests.config import fleet_2, refurb_1, ess, oem_2, manufacturer
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


def accept_offer():
    payload = {
        "listing_id": listing_id,
        "replying_to_user": other_user_id,
        "action": "accept",
        "message": "Ok! Sold!"
    }
    fetch("/listing/negotiate", payload, "post")


def get_listing_details():
    fetch(f"/listing/view-listing/{listing_id}", method="get")


if __name__ == "__main__":

    listing_owner = fleet_2
    other_user = refurb_1

    other_user_id = str(User.get(User.email_id == other_user).user_id)
    with login(other_user):
        demand_message = """
        I have a demand for 300 units of waste batteries, around bengaluru, 
        in a really good working condition with 75% state of health. I'm up for negotiations.
        """
        x = generate_listing_preview(demand_message)
        create_listing(x)

    with login(listing_owner):
        supply_message = """
        I have a supply for 300 units of waste batteries, in chennai.
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
        # accept_offer()
        get_listing_details()


    # Scenario 1: ESS and Refurbisher negotiation
    listing_owner = ess
    other_user = refurb_1

    other_user_id = str(User.get(User.email_id == other_user).user_id)
    with login(other_user):
        demand_message = """
        Seeking 100 MWh of used NMC batteries for storage utilization, preferably from Mumbai region.
        Must have at least 80% state of health. Willing to negotiate on price.
        """
        x = generate_listing_preview(demand_message)
        create_listing(x)

    with login(listing_owner):
        supply_message = """
        Offering 100 MWh of used NMC batteries, located in Mumbai.
        State of health is 85%, voltage is 3.7V.
        Open to negotiation.
        """
        x = generate_listing_preview(supply_message)
        listing = create_listing(x)
        listing_id = listing['listing_id']

    with login(other_user):
        make_an_offer(120000)
        get_listing_details()

    with login(listing_owner):
        make_counter_offer(135000)
        get_listing_details()

    with login(other_user):
        make_an_offer(140000)
        get_listing_details()

    with login(listing_owner):
        accept_offer()
        get_listing_details()

    # Scenario 2: OEM and Manufacturer negotiation
    listing_owner = oem_2
    other_user = manufacturer

    other_user_id = str(User.get(User.email_id == other_user).user_id)
    with login(listing_owner):
        demand_message = """
        Need 500 units of fresh LFP battery packs for EV manufacturing in Pune.
        Minimum 80% state of health required. Ready to negotiate for bulk purchase.
        """
        x = generate_listing_preview(demand_message)
        create_listing(x)

    with login(other_user):
        supply_message = """
        Supplying 500 fresh LFP battery packs, Pune warehouse.
        Each pack has 82% state of health, 48V output. 
        Negotiation welcome for large orders.
        """
        x = generate_listing_preview(supply_message)
        listing = create_listing(x)
        listing_id = listing['listing_id']

    with login(other_user):
        make_an_offer(450000)
        get_listing_details()

    with login(listing_owner):
        make_counter_offer(470000)
        get_listing_details()

    with login(other_user):
        make_an_offer(480000)
        get_listing_details()

    with login(listing_owner):
        accept_offer()
        get_listing_details()
