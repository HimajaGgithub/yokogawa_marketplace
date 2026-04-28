from fastapi import APIRouter, BackgroundTasks, Request

from src.entities.schema import ListingIdRequest
from src.services.logistics_service import deliver_listing

logistics_router = APIRouter(prefix="/logistics", tags=["Logistics"])


@logistics_router.post("/deliver")
async def deliver_listing_api(listing_id: ListingIdRequest, background_tasks: BackgroundTasks, request: Request):
    result = await deliver_listing(listing_id, background_tasks, request)
    return result
