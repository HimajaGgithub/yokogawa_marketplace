from fastapi import APIRouter, BackgroundTasks, Request

from src.entities.schema import Bid, ListingIdRequest, PendingApproval
from src.services.auction_service import place_bid, close_auction, pending_approval

auction_router = APIRouter(prefix="/auction", tags=["Auction"])

@auction_router.post("/pending-approval")
async def pending_approval_api(pending_approval_obj: PendingApproval, request: Request, background_tasks: BackgroundTasks):
    response = await pending_approval(pending_approval_obj, request, background_tasks)
    return response


@auction_router.post("/place-bid")
async def place_bid_api(bid: Bid, request: Request, background_tasks: BackgroundTasks):
    """
    This api must be used to place a bid for a particular item in the marketplace
    using the listing id.
    The payload for this api is:
    {
        listing_id: str,
        bidder_name: str,
        time: datetime,
        price: float,
        message: str
    }
    """
    response = await place_bid(bid, background_tasks, request)
    return response


@auction_router.post("/close-auction")
async def close_auction_api(listing_id_request: ListingIdRequest, request: Request, background_tasks: BackgroundTasks):
    """
    This api must be hit when the end date is crossed using the listing id.
    payload for this api is:
    {
        listing_id: str
    }
    """
    response = await close_auction(listing_id_request, request, background_tasks)
    return response
