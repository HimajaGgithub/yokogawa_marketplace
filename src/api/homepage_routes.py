from fastapi import APIRouter

from src.services.homepage_service import view_user_stats, view_recent_activity

homepage_router = APIRouter(prefix="/home", tags=["Home"])


@homepage_router.get("/view-stats")
async def view_user_stats_api():
    response = await view_user_stats()
    return response


@homepage_router.get("/view-recent-activity")
async def view_recent_activity_api():
    response = await view_recent_activity()
    return response
