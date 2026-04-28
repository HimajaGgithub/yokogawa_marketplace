from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Request

from src.entities.schema import (
    UserMessageInput,
    FinalListingCreation, NegotiateMessage, ListingIdRequest
)
from src.services.llm_listing_service import (
    generate_listing_preview,
    create_listing,
    negotiate,
    get_threads,
    rsvp_reject
)
from src.services.marketplace_service import view_listing

listing_router = APIRouter(prefix="/listing", tags=['Listing'])


@listing_router.post("/negotiate")
async def negotiate_api(negotiateMessage: NegotiateMessage, background_tasks: BackgroundTasks, request:Request):
    """
    If you are making an offer, your payload must look like this.
    payload = {
        "listing_id": listing_id,
        "action": "offer",
        "price": price,
        "message": "This is my offer."
    }

    If you are making a counter-offer, your payload must look like this.
    payload = {
        "listing_id": listing_id,
        "replying_to_user": other_user_id,
        "action": "counter_offer",
        "price": price,
        "message": "No, your quote is way too low, I need more."
    }

    If you are accepting an offer, your payload must look like this:
    payload = {
        "listing_id": listing_id,
        "replying_to_user": other_user_id,
        "action": "accept",
        "message": "I accept your offer! Sold!"
    }

    If you are rejecting an offer, your payload must look like this:
    payload = {
        "listing_id": listing_id,
        "replying_to_user": other_user_id,
        "action": "reject",
        "message": "Nope."
    }
    """
    response = await negotiate(negotiateMessage,background_tasks, request)
    return response


@listing_router.post("/generate-preview")
async def generate_listing_preview_api(user_input: UserMessageInput):
    """
    Use this api to create a new listing first by having a message in
    natural language describing what type of listing it is. You will have to
    mention all the required details based on the type, if it is a supply listing
    and the decided transaction type is auction, then start date, end date and reserve
    price must be mentioned. If the transaction type is negotiation then mention
    the listing price and the target price.
    If the listing type is demand you are free to have any specifications that are needed.
    But title, description of the item, location and quantity of the item are to be filled
    irrespective of the listing type.
    """
    result = await generate_listing_preview(user_input)
    return result


@listing_router.post("/create-listing")
async def create_listing_api(
        listing_data: FinalListingCreation,
        background_tasks: BackgroundTasks,
        request: Request
):
    """
    The payload for this api comes from the generate preview if anything is missing then
    fill it up here but the payload must have the following structure.
    {
    title: str,
    description: str,
    listing_type: str,
    category: Enum (waste battery or refurbished battery or raw material),
    material_code: Enum - One of ("Lithium", "Cobalt", "Iron", "Phosphate", "Graphite", "Manganese",
        "Nickel", "Titanium", "LFP", "NMC", "LTO", "LCO"
        )
    quantity: int,
    quantity_unit: str,
    status: str,
    location: str,
    payload: {}
    }
    """
    result = await create_listing(request, listing_data, background_tasks)
    return result

@listing_router.post("/rsvp-reject")
async def rsvp_reject_api(
        listing_id_request: ListingIdRequest,
        background_tasks: BackgroundTasks,
        request: Request
):
    result = await rsvp_reject(listing_id_request.listing_id, background_tasks, request)
    return result


@listing_router.get("/view-listing/{listing_id}")
async def view_listing_details_api(listing_id: str):
    result = await view_listing(listing_id)
    return result

@listing_router.get("/threads")
async def get_scenario_threads_api(listing_id: Optional[str]=None, run_id: Optional[str] = None, scenario_id: Optional[str] = None,
                                   page_number: int = 0, page_size: int = 10
                                   ):
    result = await get_threads(listing_id, run_id, scenario_id, page_number, page_size)
    return result
