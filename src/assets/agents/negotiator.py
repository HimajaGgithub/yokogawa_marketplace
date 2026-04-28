import datetime

from playhouse.shortcuts import model_to_dict

from src.assets.agent_db import Orders, OrderStatus, Config
from src.assets.api_utils import get_role
from src.properties.market_prices import market_prices
from src.utils.budget_calculations_utils import get_quotes


def handle_offer(m, listing, current_user_id):
    if listing['status'] in ["accepted", "completed"]:
        return {
            "instruction": "The listing has been completed, this offer was probably made at the last moment.",
            "agent_name": "Sales Agent",
            "listing_object": listing
        }

    order = Orders.get_or_none(Orders.listing_id == m['listing_id'])
    if not order:
        return {
            "instruction": "Reject the offer as no matching order found.",
            "function": "reject_offer",
            "agent_name": "Negotiator Agent",
            "args": {
                "listing_id": listing['listing_id'],
                "other_user": m['sender_id'],
                "price": m['payload']['price']
            },
            "listing_object": listing
        }

    print("Received offer for order", model_to_dict(order))
    target_user = m['sender_id'] if m['sender_id'] in listing['offers'] else m['receiver_id']
    counter_offer_idx = len(listing['offers'][target_user]) - 1
    print("n", counter_offer_idx)

    prices = get_quotes(listing, role=get_role(listing, current_user_id))

    print("GOT OFFER MESSAGE", get_role(listing, current_user_id), prices)
    print("Counter offer idx", counter_offer_idx, len(prices)-1)
    if counter_offer_idx > (len(prices) - 1):
        return {
            "instruction": "Reject offer as we have run out of counter-offers to make.",
            "function": "reject_offer",
            "agent_name": "Negotiator Agent",
            "args": {
                "listing_id": listing['listing_id'],
                "other_user": m['sender_id'],
                "price": m['payload']['price']
            },
            "listing_object": listing
        }

    if get_role(listing, current_user_id) == "seller":
        # If I am the seller and the incoming price is greater than my lowest-acceptable-offer,
        # I can accept
        print("For accepting, price vs budgets for >=", m['payload']['price'], min(prices))
        accept = m['payload']['price'] >= min(prices)
    else:
        # If I am the buyer and the incoming price is lesser than my highest-acceptable-offer,
        # I can accept
        print("For accepting, price vs budgets for <=", m['payload']['price'], max(prices))
        accept = m['payload']['price'] <= max(prices)

    if accept:
        permissions = Config.get(Config.key == "permissions").value
        if not "conclude" in permissions:
            return {
                "instruction": "We have an offer that can be accepted. However, the agent does not have permissions to conclude the transaction. Sending a message to the human.",
                "agent_name": "Negotiator Agent",
                "function": "inform_pending_approval",
                "args": {
                    "description": f"We have an offer that can be accepted. Please check {listing['item_name']}.",
                    "listing_id": listing['listing_id'],
                    "other_user": m['sender_id'],
                    "price": m['payload']['price']
                },
                "listing_object": listing
            }

        order.selling_price = m['payload']['price']
        if listing['listing_type'] == "supply":
            order.delivery_date = (datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=2)).isoformat()
            order.status = OrderStatus.ready.value
        order.save()
        return {
            "instruction": "Accept offer as it falls within our acceptable range.",
            "function": "accept_offer",
            "agent_name": "Negotiator Agent",
            "args": {
                "listing_id": listing['listing_id'],
                "other_user": m['sender_id'],
                "price": m['payload']['price']
            },
            "listing_object": listing
        }
    else:

        price = prices[counter_offer_idx]
        instruction = f"Make counter offer for {listing['material_code']} at ${price:,}."

        average_market_price = market_prices[listing['material_code']] * listing['quantity']
        deviation_from_average_market_price = ((price - average_market_price) / average_market_price) * 100
        instruction += f"Deviation from average market price (%): {deviation_from_average_market_price}%"

        return {
            "instruction": instruction,
            "function": "make_counter_offer",
            "agent_name": "Negotiator Agent",
            "args": {
                "listing_id": listing['listing_id'],
                "other_user": m['sender_id'],
                "price": price
            },
            "listing_object": listing
        }


def handle_reject_or_counter(m, listing, current_user_id):
    if listing['status'] in ["accepted", "completed"]:
        return {
            "instruction": "The listing has been completed, this offer was probably made at the last moment.",
            "agent_name": "Negotiator Agent",
            "listing_object": listing
        }
    target_user = m['sender_id'] if m['sender_id'] in listing['offers'] else m['receiver_id']
    previous_offer_idx = len(listing['offers'][target_user]) - 1
    offer_to_make_idx = previous_offer_idx + 1

    prices = get_quotes(listing, role=get_role(listing, current_user_id))
    if offer_to_make_idx > (len(prices) - 1):
        return {
            "instruction": f"Ignore message as we have run out of offers to make.",
            "agent_name": "Negotiator Agent",
            "listing_object": listing
        }

    price = prices[offer_to_make_idx]
    print("GOT REJECT MESSAGE", get_role(listing, current_user_id), prices)
    instruction = f"Make an offer at {price}. \n"
    average_market_price = market_prices[listing['material_code']] * listing['quantity']
    deviation_from_average_market_price = ((price - average_market_price) / average_market_price) * 100
    instruction += f"Deviation from average market price (%): {deviation_from_average_market_price}%"
    return {
        "instruction": instruction,
        "function": "make_an_offer",
        "agent_name": "Negotiator Agent",
        "args": {
            "listing_id": listing['listing_id'],
            "price": price,
        },
        "listing_object": listing
    }


def handle_accept(m, listing):
    if listing['listing_type'] == "demand":
        Orders.create(**{
            "listing_id": listing['listing_id'],
            "material_code": listing['material_code'],
            "quantity": listing['quantity'],
            "units": listing['quantity_unit'],
            "selling_price": m['payload']['price'],
            "delivery_date": listing['payload'].get('target_date', None),
            "accepted_date": datetime.datetime.fromisoformat(m['timestamp']).date(),
            "order_type": "supply",
            "status": OrderStatus.accepted.value,
            "run_id": m['run_id'],
        })

        return {
            "instruction": "Accept acknowledged... Will process further details soon.",
            "agent_name": "Order Management Agent",
            "listing_object": listing
        }
    else:
        requirement = Orders.select().where(
            (Orders.status == OrderStatus.procuring.value) &
            (Orders.material_code == listing['material_code'])
        ).order_by(Orders.accepted_date).get_or_none()
        if not requirement:
            return {
                "instruction": "Ignore message as no matching orders found for this.",
                "agent_name": "Order Management Agent",
                "listing_object": listing
            }
        # Requirement status will become ready once logistics delivers
        requirement.status = OrderStatus.waiting.value
        requirement.save()
        return {
            "instruction": "Tables have been updated... Will process further soon.",
            "agent_name": "Order Processor Agent",
            "listing_object": listing
        }
