from src.entities.db_model import User
from src.tests.config import fleet, refurb, manufacturer, manu_1, recycler, oem_1
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


def accept_offer():
    payload = {
        "listing_id": listing_id,
        "replying_to_user": other_user_id,
        "action": "accept",
        "message": "Ok, Thanks!"
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


if __name__ == '__main__':

    listing_owner = refurb
    other_user = fleet
    other_user_id = str(User.get(User.email_id == other_user).user_id)

    with login(listing_owner):
        supply_message = """
        I can supply 300 MWh of refurbished LCO batteries, around bengaluru, 
        in a really good working condition with 60% state of health. I'm up for negotiations.
        """
        x = generate_listing_preview(supply_message)
        listing = create_listing(x)
        listing_id = listing['listing_id']

    with login(other_user):
        make_an_offer(900)
        get_listing_details()

    with login(listing_owner):
        reject_offer()
        get_listing_details()

    with login(other_user):
        make_an_offer(1000)
        get_listing_details()

    with login(listing_owner):
        accept_offer()
        get_listing_details()


    # Scenario 1: Recycler and OEM negotiation
    listing_owner = recycler
    other_user = manu_1
    other_user_id = str(User.get(User.email_id == other_user).user_id)

    with login(listing_owner):
        supply_message = """
        Offering 2 tons of recycled Cobalt, processed and ready for reuse.
        Located in Hyderabad. Minimum order 500 kg. Open to negotiation for bulk deals.
        """
        x = generate_listing_preview(supply_message)
        listing = create_listing(x)
        listing_id = listing['listing_id']

    with login(other_user):
        make_an_offer(250000)
        get_listing_details()

    with login(listing_owner):
        reject_offer()
        get_listing_details()

    with login(other_user):
        make_an_offer(270000)
        get_listing_details()

    with login(listing_owner):
        reject_offer()
        get_listing_details()

    # Scenario 2: Manufacturer and Refurbisher negotiation
    listing_owner = manufacturer
    other_user = oem_1
    other_user_id = str(User.get(User.email_id == other_user).user_id)

    with login(listing_owner):
        supply_message = """
        Supplying 300MWh new NMC battery modules, 48V, available in Delhi.
        Bulk purchase discounts available. Open to negotiation.
        """
        x = generate_listing_preview(supply_message)
        listing = create_listing(x)
        listing_id = listing['listing_id']

    with login(other_user):
        make_an_offer(600000)
        get_listing_details()

    with login(listing_owner):
        reject_offer()
        get_listing_details()

    with login(other_user):
        make_an_offer(650000)
        get_listing_details()

    with login(listing_owner):
        accept_offer()
        get_listing_details()
