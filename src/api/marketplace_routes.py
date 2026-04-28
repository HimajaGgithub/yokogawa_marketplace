from typing import Optional

from fastapi import APIRouter

from src.entities.schema import ListingType
from src.services.marketplace_service import show_items_for_me, show_general_items, get_my_listings, get_my_purchase_history

marketplace_router = APIRouter(prefix="/marketplace", tags=["Marketplace"])


@marketplace_router.get("/latest-items-for-me")
async def show_items_for_me_api(page_number: int = 0, page_size: int = 10):
    response = await show_items_for_me(page_number, page_size)
    return response


@marketplace_router.get("/supply-demand-items")
async def show_general_items_api(listing_type: Optional[ListingType] = None,
                                 page_number: int = 0, page_size: int = 10):
    response = await show_general_items(listing_type, page_number, page_size)
    return response


@marketplace_router.get("/view-my-listings")
async def get_my_listings_api(page_number: int = 0, page_size: int = 10):
    response = await get_my_listings(page_number, page_size)
    return response

@marketplace_router.get("/purchase-history")
async def get_my_purchase_history_api(page_number: int = 0, page_size: int = 10):
    response = await get_my_purchase_history(page_number, page_size)
    return response
