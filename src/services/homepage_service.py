import datetime

from playhouse.shortcuts import model_to_dict

from src.entities.context import current_user
from src.entities.db_model import Listing, Messages, User
from src.entities.common_schema import MessageType


async def view_user_stats():
    user = current_user.get()
    my_listings = list(Listing.select().where(Listing.user_id == user.user_id))
    my_auctions = [x for x in my_listings if x.payload.get("transaction_type") == "auction"]
    count = 0
    now = datetime.datetime.now(datetime.UTC)
    for x in my_auctions:
        end_date = x.payload.get("end_date")
        end_date = datetime.datetime.fromisoformat(end_date).astimezone(datetime.UTC)
        if (end_date - now) < datetime.timedelta(hours=1):
            count += 1
    return {
        "total_listings": len(my_listings),
        "total_bids_received": sum(len(x.offers) for x in my_auctions),
        "ending_soon_count": count,
    }


async def view_recent_activity():
    user = current_user.get()

    notifications = list(
        Messages.select().where(
            (Messages.receiver_id == user.user_id) &
            (Messages.message_type.in_(
                [MessageType.negotiation_offer.value, MessageType.auction_new_highest_bid.value]))
        ).order_by(Messages.timestamp.desc()).limit(10)
    )

    if not notifications:
        return []

    result = []
    receiver_name = user.biz_name

    for message in notifications:
        message_dict = model_to_dict(message)
        sender = User.get(User.user_id == message.sender_id)
        sender_name = sender.biz_name

        listing = Listing.get(Listing.listing_id == message.listing_id)
        listing_quantity = listing.quantity
        listing_quantity_unit = listing.quantity_unit
        listing_material_code = listing.material_code
        listing_status = listing.status

        message_dict['sender_name'] = sender_name
        message_dict['receiver_name'] = receiver_name
        message_dict['listing_quantity'] = listing_quantity
        message_dict['listing_quantity_unit'] = listing_quantity_unit
        message_dict['listing_material_code'] = listing_material_code
        message_dict['listing_status'] = listing_status

        result.append(message_dict)

    return result
