import datetime

from src.assets.agent_db import Calendar, Stock
from src.assets.api_utils import get_role
from src.entities.common_schema import MessageType
from src.properties.market_prices import market_prices
from src.utils.budget_calculations_utils import get_quotes, get_auction_bid


def check_interested(materials_of_interest, listing):
    if not listing['material_code'] in materials_of_interest:
        return False, "I don't have interest in this material."
    material_preferences = materials_of_interest[listing['material_code']]
    common_params = material_preferences.keys() & listing['payload'].keys()
    for param in common_params:
        preference = material_preferences[param]
        query_value = listing['payload'][param]

        if isinstance(preference, str) and preference == query_value:
            return True, "listing matches my criteria, so I can go ahead and procure this for later use."
        elif preference[0] <= query_value < preference[1]:
            return True, "listing matches my criteria, so I can go ahead and procure this for later use."
    return False, "I don't have permissions to procure this material."


def check_if_can_supply(listing, daily_production):
    surplus = (
        Stock.select()
        .where(
            (Stock.material_code == listing['material_code'])
            & (Stock.quantity >= listing['quantity'])
            & (Stock.material_type == "surplus")
            & (Stock.status == "available")
        )
        .get_or_none()
    )

    if surplus:
        print("FOUND matching surplus")

        difference = surplus.quantity - listing['quantity']
        surplus.quantity = listing['quantity']
        surplus.order_id = listing['listing_id']
        surplus.status = "reserved"
        surplus.save()

        # Save new entry for leftover stock
        if difference > 0:
            Stock.create(
                material_code=listing['material_code'],
                quantity=difference,
                units=listing['quantity_unit'],
                status="available",
                material_quality=surplus.material_quality,
                category=surplus.category,
                material_type="surplus",
            )
            return True, [
                f"Found {listing['quantity']} {listing['quantity_unit']} of {surplus.material_code} in inventory."
            ]

    target_date = datetime.datetime.fromisoformat(listing['payload']['target_date'])
    days_left = (target_date - datetime.datetime.now()).days
    busy_days = Calendar.select().where(
        (Calendar.date >= datetime.datetime.now(datetime.UTC)) &
        (Calendar.date <= listing['payload']['target_date']) &
        (Calendar.status == "occupied")
    ).count()

    work_days = days_left - busy_days
    print("WORK DAYS", work_days, "Busy days", busy_days)

    analysis = [
        f"* Delivery deadline: {target_date.date()} ({days_left} days from now)",
        f"  - Available workdays: {work_days} out of {days_left} total days",
        f"  - Busy days (occupied): {busy_days}",
        f"  - Total capacity: {daily_production[listing['material_code']][0] * work_days} units",
        f"  - Can produce the material in time if I procure all raw materials within reasonable deadlines.",
    ]
    if work_days > 0:
        if daily_production[listing['material_code']][0] * work_days >= listing['quantity']:
            return True, analysis
        else:
            return False, "We cannot participate in this listing as we don't have enough daily production for delivering on time.",
    else:
        return False, "Don't participate in this listing all machines are occupied."


def handle_market_listing_announcement(m, listing, current_user_id, daily_production,
                                       materials_of_interest, current_user_profile):
    average_market_price = market_prices[listing['material_code']] * listing['quantity']

    if current_user_profile['email_id'] == "recycler@yokogawa.com":
        if listing['listing_type'] == "demand" and m['message_type'] == MessageType.takeover.value:
            price = get_quotes(listing, role=get_role(listing, current_user_id))[0]
            analysis_steps = [
                f"  - Average market price: ${average_market_price:,}"
                f"  - Offered price: ${price:,}"
            ]
            return {
                "instruction": "Start negotiations as the others have dropped out.",
                "function": "make_an_offer",
                "agent_name": "Negotiator Agent",
                "args": {
                    "listing_id": listing['listing_id'],
                    "price": price
                },
                "listing_object": listing,
                "analysis": "\n".join(analysis_steps)
            }
        return {
            "instruction": "No action needed at this moment.",
            "agent_name": "Stock Manager Agent",
            "listing_object": listing
        }

    if listing['listing_type'] == "demand":
        if listing['material_code'] not in daily_production:
            return {
                "instruction": "Ignore listing announcement as we don't "
                               "produce the required material for this listing.",
                "agent_name": "Stock Manager Agent",
                "listing_object": listing
            }
        # check calendar
        can_supply, analysis = check_if_can_supply(listing, daily_production)
        if can_supply:
            # make an offer
            print("MAKING OFFER", get_role(listing, current_user_id))
            prices = get_quotes(listing, role=get_role(listing, current_user_id))
            price = prices[0]

            deviation_from_average_market_price = ((price - average_market_price) / average_market_price) * 100

            analysis_steps = [
                f"* Evaluating demand listing for {listing['quantity']} {listing['quantity_unit']} of {listing['material_code']}",
                f"  - Daily production rate: {daily_production[listing['material_code']][0]} {daily_production[listing['material_code']][1]}/day",
            ]
            analysis_steps += analysis
            analysis_steps += [
                f"  - Required quantity: {listing['quantity']} units",
                f"  - Generated {len(prices)} price quotes for budget analysis",
                f"  - Budget range: ${min(prices):,} - ${max(prices):,}",
                f"  - Average market price: ${average_market_price:,}"
                f"  - Deviation from market price: {deviation_from_average_market_price} %"
            ]

            instruction = f"""
Make supply offer for {listing['material_code']}.
{listing['quantity']} {listing['quantity_unit']}. Offer price: ${price:,}.
            """
            return {
                "instruction": instruction,
                "function": "make_an_offer",
                "agent_name": "Negotiator Agent",
                "args": {
                    "listing_id": listing['listing_id'],
                    "price": price
                },
                "listing_object": listing,
                "analysis": "\n".join(analysis_steps)
            }
        else:
            return {
                "instruction": analysis,
                "agent_name": "Production Capacity Estimator Agent",
                "listing_object": listing,
                "function": "reject_invite",
                "args": {
                    "listing_id": listing['listing_id'],
                }
            }
    else:
        interested, reason = check_interested(materials_of_interest, listing)
        if not interested:
            return {
                "instruction": "Ignore listing announcement because " + reason,
                "agent_name": "Stock Manager Agent",
                "listing_object": listing,
                "function": "reject_invite",
                "args": {
                    "listing_id": listing['listing_id'],
                }
            }

        if listing['payload']['transaction_type'] == "auction":
            # todo: add quality key to listing.payload all over the place
            reserve_price = listing['payload']['reserve_price']

            print("base price for auction", reserve_price)
            n = len(listing['offers']) + 1 if len(listing['offers']) else 0

            price = get_auction_bid(listing, n=n)[0]

            deviation_from_average_market_price = ((price - average_market_price) / average_market_price) * 100

            analysis_steps = [
                f"  - Auction opportunity for {listing['quantity']} {listing['quantity_unit']} of {listing['material_code']}",
                f"  - Reserve price: ${reserve_price:,}",
                f"  - Average market price: ${average_market_price:,}"
            ]

            return {
                "instruction": f"Enter auction for {listing['material_code']} - {listing['quantity']} {listing['quantity_unit']}. "
                               f"Reserve price: ${reserve_price:,}. My bid: ${price:,} "
                               f"strategic variation: ${price - reserve_price}). "
                               f"Deviation from average market price (%): {deviation_from_average_market_price}",
                "function": "place_bid",
                "agent_name": "Bidder Agent",
                "args": {
                    "listing_id": listing['listing_id'],
                    "price": price,
                },
                "listing_object": listing,
                "analysis": "\n".join(analysis_steps)
            }

        else:
            # make an offer for the supply listing, as we have a requirement
            print("ENTERING NEGOTIATION", get_role(listing, current_user_id))
            prices = get_quotes(listing, role=get_role(listing, current_user_id))
            price = prices[0]

            deviation_from_average_market_price = ((price - average_market_price) / average_market_price) * 100

            analysis_steps = [
                f"  - Negotiation opportunity for {listing['quantity']} {listing['quantity_unit']} of {listing['material_code']}",
            ]
            if listing['payload'].get("SoH"):
                soh = listing['payload'].get("SoH")
                analysis_steps.append(
                    f"  - SOH requirement: {soh}%"
                )
                quality_requirements = f"{soh}% SOH"
            else:
                purity = listing['payload'].get('purity')
                analysis_steps.append(
                    f"  - Purity requirement: {purity}%",
                )
                quality_requirements = f"{purity}% purity"

            analysis_steps += [
                f"  - Generated {len(prices)} price quotes for strategy development",
                f"  - Budget allocation: ${min(prices):,} - ${max(prices):,}",
                f"  - Average market price: ${average_market_price:,}"
            ]

            return {
                "instruction": f"Enter negotiation for {listing['material_code']} - {listing['quantity']} {listing['quantity_unit']}. "
                               f"Initial offer: ${price:,}"
                               f"Budget allocation: ${min(prices):,} - ${max(prices):,} "
                               f"(headroom: ${max(prices) - price:,}). "
                               f"Deviation from average market price (%): {deviation_from_average_market_price}"
                               f"Quality requirements: {quality_requirements}",
                "function": "make_an_offer",
                "agent_name": "Negotiator Agent",
                "args": {
                    "listing_id": listing['listing_id'],
                    "price": price,
                },
                "listing_object": listing,
                "analysis": "\n".join(analysis_steps)
            }
