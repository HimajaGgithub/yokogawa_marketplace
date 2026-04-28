import asyncio

from src.entities.db_model import User
from src.entities.common_schema import MessageType
from src.tests.config import manufacturer, fleet, recycler
from src.utils.fetch_utils import login, fetch
from src.utils.service_bus_utils import receiver_context


class Material:
    material: str
    quantity: float
    unit: str

    def __init__(self, material, quantity, unit):
        self.material = material
        self.quantity = quantity
        self.unit = unit


def generate_listing_preview(message):
    payload = {"message": message}
    return fetch("/listing/generate-preview", payload, "POST")


def create_listing(x):
    return fetch("/listing/create-listing", x['response'], "POST")


def make_an_offer(listing_id, price):
    payload = {
        "listing_id": listing_id,
        "action": "offer",
        "price": price,
    }
    fetch("/listing/negotiate", payload, "post")


def make_counter_offer(listing_id, price, other_user):
    payload = {
        "listing_id": listing_id,
        "replying_to_user": other_user,
        "action": "counter_offer",
        "price": price,
        "message": "No, your quote is way too low, I need more."
    }
    fetch("/listing/negotiate", payload, "post")


def accept_offer(listing_id, other_user):
    payload = {
        "listing_id": listing_id,
        "replying_to_user": other_user,
        "action": "accept",
        "message": "Ok! Sold!"
    }
    fetch("/listing/negotiate", payload, "post")


def get_listing_details(listing_id):
    return fetch(f"/listing/view-listing/{listing_id}", method="get")


async def main():
    # todo: expand this to multiple users per biz_type
    manufacturer_user = User.get(User.email_id == manufacturer)
    fleet_user = User.get(User.email_id == fleet)
    recycler_user = User.get(User.email_id == recycler)

    to_procure = []
    for order in manufacturer_config['initial_orders']: # where status is active
        materials_required_per_unit = manufacturer_config['demand_supply_mapping'][order.material]
        for unit in materials_required_per_unit.values():
            unit: Material
            if (unit.quantity * order.quantity) > manufacturer_config['initial_stock'][unit.material].quantity:
                quantity = (unit.quantity * order.quantity) - manufacturer_config['initial_stock'][
                    unit.material].quantity
                to_procure.append(Material(unit.material, quantity, unit.unit))

    if to_procure:
        with login(manufacturer):
            for material in to_procure:
                demand_message = f"""
                I have a demand for {material.quantity} {material.unit} of {material.material}, 
                around bengaluru. Listing category must be "raw material".
                """
                x = generate_listing_preview(demand_message)
                create_listing(x)

    recycler_config = {
        "max_production_capacity": {
            "Cobalt": Material("NMC_battery", 12, "MWh"),
        },
        "initial_stock": {
            "Nickel": Material("Nickel", 0, "tons"),
            "Lithium": Material("Lithium", 0, "tons"),
            "Manganese": Material("Manganese", 0, "tons"),
            "Cobalt": Material("Cobalt", 0, "tons"),
            "Graphite": Material("Graphite", 0, "tons")
        },
        "supply_demand_mapping": {
            "Cobalt": {
                "NMC": Material("NMC", 1, "tons")
            }
        },
        "initial_orders": [
        ],
    }
    with receiver_context(recycler_user) as messages:
        for m in messages:
            if m['message_type'] == "market_listing_announcement":
                with login(recycler):
                    listing = get_listing_details(m['listing_id'])
                    # todo: check which type of listing it is
                    if listing['quantity'] < recycler_config['max_production_capacity'][listing['material_code']].quantity:
                        make_an_offer(listing['listing_id'], 1000)
                    # todo: make an entry in the orders table with status acknowledged

    with receiver_context(recycler_user) as messages:
        for m in messages:
            if m['message_type'] == MessageType.negotiation_offer.value:
                with login(manufacturer):
                    accept_offer(m['listing_id'], m['sender_id'])

    # when recycler puts a demand to fleet (creating a new listing)
    # the listing payload must specify
    # {"parent_listing_id": Orders.listing_id}
    """
    manufacturer_listing = { "listing_id": "manu-1" }
    recycler = { "order-id": "manu-1" }
    recycler_listing = { "listing-id": "recy-1", "payload": {"parent_listing_id:"manu-1"} }
    logistics_message = { "listing-id": "recy-1", "payload": {"parent_listing_id:"manu-1"}, "status": "delivered"}
    """

    # with login(listing_owner):
    #     supply_message = """
    #     I have a supply for 300 units of waste batteries, in chennai.
    #     The state of health is 75%, and the output rate is 12 watt-hours.
    #     I'm up for negotiations. My listing price must be 3000, and target price is 2700.
    #     """
    #     x = generate_listing_preview(supply_message)
    #     listing = create_listing(x)
    #     listing_id = listing['listing_id']
    #
    # with login(other_user):
    #     make_an_offer(900)
    #     get_listing_details()
    #
    # with login(listing_owner):
    #     make_counter_offer(1200)
    #     get_listing_details()
    #
    # with login(other_user):
    #     make_an_offer(1200)
    #     get_listing_details()
    #
    # with login(listing_owner):
    #     # accept_offer()
    #     get_listing_details()


if __name__ == "__main__":
    asyncio.run(main())
