import datetime
from datetime import timedelta

from src.assets.agent_db import Orders, OrderStatus, Config
from src.assets.agents.sales import check_interested
from src.properties.market_prices import market_prices
from src.utils.budget_calculations_utils import get_auction_bid


def handle_winner(m, listing):
    requirement = Orders.select().where(
        (Orders.listing_id == listing['listing_id'])
    ).get_or_none()
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
        "agent_name": "Order Management Agent",
        "listing_object": listing
    }


def handle_new_highest_bid(m, listing, current_user_id, materials_of_interest):
    if current_user_id == listing['user_id']:
        # I'm owner
        if listing['status'] in ["accepted", "completed"]:
            return {
                "instruction": "The auction has closed, this bid was probably outbid at the last moment.",
                "agent_name": "Sales Agent",
                "listing_object": listing
            }

        n = len(listing['offers'])
        _, auction_acceptance_factor, _ = get_auction_bid(listing, n=n)
        print("Auction", listing['payload']['reserve_price'], auction_acceptance_factor, m['payload']['price'])
        if m['payload']['price'] > (listing['payload']['reserve_price'] * auction_acceptance_factor):
            permissions = Config.get(Config.key == "permissions").value
            if not "conclude" in permissions:
                # todo: you have to mark the order as ready, once the human closes the auction.
                # since the order
                return {
                    "instruction": f"After evaluating the bid of {m['payload']['price']}"
                                   f"the agent has decided this price is acceptable and wants to send it for human approval."
                                   f"Generate a message explaining why this price is deemed good for the auction.",
                    "agent_name": "Bidder Agent",
                    "function": "send_pending_signal",
                    "args": {
                        "listing_id": listing['listing_id'],
                        "description": f"We have an auction that can be completed. Please check {listing['item_name']}.",
                        "other_user": m['sender_id'],
                        "price": m['payload']['price'],
                    }
                }
            order = Orders.get_or_none(Orders.listing_id == listing['listing_id'])
            order.selling_price = listing['offers'][0]['price']
            order.delivery_date = datetime.datetime.now(datetime.UTC) + timedelta(days=2)
            order.accepted_date = datetime.datetime.now(datetime.UTC)
            order.status = OrderStatus.ready.value
            order.save()

            return {
                "instruction": f"Close auction for {listing['material_code']} - {listing['quantity']} {listing['quantity_unit']}. "
                               f"Winning bid: ${m['payload']['price']:,}. Reserve price: ${listing['payload']['reserve_price']:,}. "
                               f"Achievement: {(m['payload']['price'] / listing['payload']['reserve_price']):,.2f}x reserve (target: {auction_acceptance_factor}x). "
                               f"The profit margin attained by closing this auction is {(m['payload']['price'] / listing['payload']['reserve_price']) * 100}%."
                               f"Gross profit: ${m['payload']['price'] - listing['payload']['reserve_price']:,.2f}. Delivery scheduled within 2 days.",
                "function": "close_auction",
                "agent_name": "Sales Agent",
                "args": {
                    "listing_id": listing['listing_id'],
                    "price": listing['offers'][0]['price'],
                },
                "listing_object": listing
            }
        else:
            return {
                "instruction": "Let the auction run, no action needed.",
                "agent_name": "Sales Agent",
                "listing_object": listing
            }
    else:
        if listing['status'] in ["completed", "accepted"]:
            return {
                "instruction": "The auction has closed, won't bid anymore on this.",
                "agent_name": "Bidder agent",
                "listing_object": listing
            }

        interested, reason = check_interested(materials_of_interest, listing)
        if not interested:
            return {
                "instruction": "Ignore listing announcement because " + reason,
                "agent_name": "Stock Manager Agent",
                "listing_object": listing
            }

        if len(listing['offers']) + 1 >= 10:
            return {
                "instruction": f"Ignore message as we have run out of budget.",
                "agent_name": "Bidder Agent",
                "listing_object": listing
            }

        price = get_auction_bid(listing, n=len(listing['offers']) + 1)[0]
        bids_made = len([x for x in listing['offers'] if x['bidder_id'] == current_user_id])
        percentage_change_in_bid = ((price - m['payload']['price']) / m['payload']['price']) * 100

        average_market_price = market_prices[listing['material_code']] * listing['quantity']
        deviation_from_average_market_price = ((price - average_market_price) / average_market_price) * 100

        instruction = f"""
Place bid #{bids_made + 1} for {listing['material_code']} at a value of ${price:,}.
Previous highest bid: ${m['payload']['price']:,},
Percentage increase from the previous bid {percentage_change_in_bid}.
Deviation from average market price: {round(deviation_from_average_market_price, 3)}%
        """.strip()

        return {
            "instruction": instruction,
            "function": "place_bid",
            "agent_name": "Bidder Agent",
            "args": {
                "listing_id": listing['listing_id'],
                "price": price,
            },
            "listing_object": listing
        }


def handle_closed(m, listing):
    return {
        "instruction": "Accept that the auction has closed, and that we won't be relying on this listing for procuring the required materials.",
        "agent_name": "Bidder Agent",
        "listing_object": listing
    }
