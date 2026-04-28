from fastapi import Request, BackgroundTasks
from fastapi.responses import JSONResponse

from src.entities.common_schema import MessageType
from src.entities.context import current_user
from src.entities.db_model import Listing
from src.entities.schema import StatusType, ListingIdRequest
from src.utils.service_bus_utils import send


async def deliver_listing(delivery_message: ListingIdRequest, background_tasks: BackgroundTasks, request: Request):
    user = current_user.get()
    listing: Listing = Listing.get_or_none(Listing.listing_id == delivery_message.listing_id)
    if not listing:
        return JSONResponse(content=f"Listing not found with id:{delivery_message.listing_id}", status_code=400)
    if not listing.status == StatusType.COMPLETED.value:
        return JSONResponse(
            content=f"Listing not completed yet. Negotiation / Auction has to end before delivery.",
            status_code=400
        )

    if listing.listing_type == "demand":
        buyer_id = listing.user_id
        seller_id = user.user_id
    else:  # listing type is "supply"
        seller_id = listing.user_id
        if "buyer_id" not in listing.payload:
            return JSONResponse(
                content="Key 'buyer_id' not found in listing payload.", status_code=400
            )
        buyer_id = listing.payload['buyer_id']

    listing.status = StatusType.DELIVERED.value
    listing.save()

    background_tasks.add_task(
        send, request, buyer_id, MessageType.listing_delivery, {
            "listing_id": str(listing.listing_id),
            "listing_name": listing.item_name,
            "material_code": listing.material_code,
            "quantity": listing.quantity,
            "quantity_unit": listing.quantity_unit,
            "location": listing.location,
            "sender_name": user.biz_name,
            "message": delivery_message.message,
            "action": delivery_message.action,
            "rationale": delivery_message.rationale,
            "variables": listing.payload
        }
    )
    return {"message": "Buyer will be notified of the delivery."}
