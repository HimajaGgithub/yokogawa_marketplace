from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Request, BackgroundTasks

from src.services.messages_service import get_all_notifications, mark_is_read, send_notification

message_router = APIRouter(prefix="/notifications", tags=["Notifications"])


@message_router.get("/")
async def get_all_notifications_api(
        newest_first: bool = True,
        read: Literal["all", "read", "unread"] = "all",
        page_number: int = 0,
        page_size: int = 10
):
    result = await get_all_notifications(newest_first, read, page_number, page_size)
    return result


@message_router.put("/read/{message_id}")
async def mark_is_read_api(message_id: str):
    result = await mark_is_read(message_id)
    return result

@message_router.post("")
async def send_notification_api(request: Request, background_tasks: BackgroundTasks):
    result = await send_notification(request, background_tasks)
    return result