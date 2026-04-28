from typing import Optional

from fastapi import BackgroundTasks, Request, FastAPI
from starlette.responses import JSONResponse

from src.entities.context import current_user
from src.entities.db_model import Listing, User
from src.entities.schema import Bid, ListingIdRequest, StatusType, PendingApproval
from src.entities.common_schema import MessageType
from src.utils.agents_utils import generate_transaction_summary
from src.utils.service_bus_utils import send


async def place_bid(bid: Bid, background_tasks: BackgroundTasks, request: Request):
    user = current_user.get()
    listing: Optional[Listing] = Listing.get_or_none(Listing.listing_id == bid.listing_id)
    if not listing:
        return JSONResponse(status_code=400, content=f"Could not find listing with listing id: {bid.listing_id}")

    if user.user_id == listing.user_id:
        return JSONResponse(status_code=400, content=f"You can't bid on your own supply.")
    if not listing.payload.get("transaction_type") == "auction":
        return JSONResponse(status_code=400, content=f"Bidding not supported for this listing.")
    if listing.status == StatusType.COMPLETED.value:
        return JSONResponse(status_code=400, content=f"Bidding is closed for this auction.")

    if bid.price < listing.payload.get("reserve_price"):
        return JSONResponse(status_code=400, content=f"Bid must be equal or greater than the reserve price.")

    bid.bidder_name = user.biz_name
    bid_json = bid.model_dump(exclude={"listing_id"})
    bid_json['bidder_id'] = str(user.user_id)
    if listing.offers:
        if bid.price <= listing.offers[0]['price']:
            return JSONResponse(
                status_code=400,
                content=f"Could not place bid. Bid is lesser than the current highest bid."
            )
    listing.offers.append(bid_json)
    listing.offers = sorted(listing.offers, key=lambda x: x['time'], reverse=True)
    listing.save()

    bidders = list(set([x["bidder_id"] for x in listing.offers]))
    notify = [x for x in bidders if x != str(user.user_id)] + [str(listing.user_id)]

    background_tasks.add_task(
        send, request, notify, MessageType.auction_new_highest_bid, {
            "listing_id": str(listing.listing_id),
            "price": bid.price,
            "listing_name": listing.item_name,
            "user_name": user.biz_name,
            "variables": listing.payload,
            "message": bid.message,
            "action": bid.action,
            "rationale": bid.rationale,
            "analysis": bid.analysis
        })
    return {
        "message": "Bid placed successfully",
    }


async def close_auction(listing_id_request: ListingIdRequest, request: Request | FastAPI,
                        background_tasks: BackgroundTasks = None, ):
    user = current_user.get()
    listing: Optional[Listing] = Listing.get_or_none(Listing.listing_id == listing_id_request.listing_id)
    if not listing:
        return JSONResponse(status_code=400,
                            content=f"Could not find listing with listing id: {listing_id_request.listing_id}")
    if user.user_id != listing.user_id:
        return JSONResponse(status_code=400, content=f"You don't have permissions to close the auction.")
    if not listing.payload.get("transaction_type") == "auction":
        return JSONResponse(status_code=400, content=f"Close auction not applicable.")

    winner = None
    if listing.offers:
        winner = listing.offers[0]
    others = None
    if listing.offers:
        others = listing.offers[1:]
    if winner:
        winner_user_model: User = User.get(User.user_id == winner['bidder_id'])
        if winner_user_model.purchase_history:
            winner_user_model.purchase_history.append(str(listing.listing_id))
        else:
            winner_user_model.purchase_history = [str(listing.listing_id)]
        winner_user_model.save()

        # add it for seller also
        if user.purchase_history:
            user.purchase_history.append(str(listing.listing_id))
        else:
            user.purchase_history = [str(listing.listing_id)]
        user.save()

        receiver = winner['bidder_id']
        listing.payload['buyer_id'] = str(receiver)
        listing.payload['price'] = winner['price']
        listing.payload['buyer_name'] = winner_user_model.biz_name
        message_type = MessageType.auction_winner
        payload = {
            "listing_id": str(listing.listing_id),
            "listing_name": listing.item_name,
            "price": winner['price'],
            "user_name": user.biz_name,
            "variables": listing.payload,
            "message": listing_id_request.message,
            "action": listing_id_request.action,
            "rationale": listing_id_request.rationale,
        }
        if background_tasks:
            background_tasks.add_task(send, request, receiver, message_type, payload)
        else:
            await send(request, receiver, message_type, payload)
    if others:
        other_bidders = list(set([x['bidder_id'] for x in others if x['bidder_id'] != winner['bidder_id']]))
        message_type = MessageType.auction_closed
        payload = {
            "listing_id": str(listing.listing_id),
            "price": winner['price'],
            "listing_name": listing.item_name,
            "user_name": user.biz_name,
            "message": f"Auction has closed.",
            "variables": listing.payload,
        }
        if background_tasks:
            background_tasks.add_task(send, request, other_bidders, message_type, payload)
        else:
            await send(request, other_bidders, message_type, payload)

    listing.status = StatusType.COMPLETED.value
    summary = generate_transaction_summary(listing)
    listing.transaction_summary = summary
    listing.save()
    return {"message": "Auction closed successfully."}


async def pending_approval(pending_approval_obj: PendingApproval, request, background_tasks):
    user = current_user.get()
    listing: Optional[Listing] = Listing.get_or_none(Listing.listing_id == pending_approval_obj.listing_id)

    if not listing:
        return JSONResponse(status_code=400,
                            content=f"Could not find listing with listing id: {pending_approval_obj.listing_id}")
    if user.user_id != listing.user_id:
        return JSONResponse(status_code=400, content=f"You don't have permissions to close the auction.")
    if not listing.payload.get("transaction_type") == "auction":
        return JSONResponse(status_code=400, content=f"Pending approval operation not applicable.")

    listing.status = StatusType.APPROVAL_PENDING.value
    for offer in listing.offers:
        if offer['price'] == pending_approval_obj.price and offer['bidder_id'] == pending_approval_obj.winning_user:
            offer['suggested_price'] = pending_approval_obj.price
            offer['rationale'] = pending_approval_obj.rationale
            break
    listing.save()

    message_type = MessageType.approval_pending
    payload = {
        "listing_id": str(listing.listing_id),
        "listing_name": listing.item_name,
        "price":pending_approval_obj.price,
        "variables": listing.payload,
        "message": pending_approval_obj.message,
        "action": pending_approval_obj.action,
        "rationale": pending_approval_obj.rationale,
    }
    background_tasks.add_task(send, request, str(user.user_id) , message_type, payload)
    return  JSONResponse(status_code=200, content=f"Status updated successfully.")