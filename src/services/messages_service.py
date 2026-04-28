from fastapi import BackgroundTasks, Request
from playhouse.shortcuts import model_to_dict
from starlette.responses import JSONResponse

from src.entities.common_schema import MessageType
from src.entities.context import current_user
from src.entities.db_model import Messages
from src.utils.service_bus_utils import send


async def send_notification(request: Request, background_tasks: BackgroundTasks):
    user = current_user.get()
    body = await request.json()
    background_tasks.add_task(
        send, request, [user.user_id], MessageType(body['message_type']), body['payload']
    )
    return {"message": "Notification sent successfully."}


async def get_all_notifications(newest_first: bool, read: str, page_number: int = 0, page_size: int = 10):
    user = current_user.get()

    skip = page_number * page_size

    query = (
        Messages.select().where(Messages.receiver_id == user.user_id)
    )

    if read == "read":
        query = query.where(Messages.is_read == True)
    elif read == "unread":
        query = query.where(Messages.is_read == False)
    total_records = query.count()

    notifications = (
        Messages
        .select()
        .where(Messages.receiver_id == user.user_id)
        .order_by(
            Messages.timestamp.desc() if newest_first else Messages.timestamp
        )
        .offset(skip)
        .limit(page_size)
    )
    if read == "read":
        notifications = notifications.where(Messages.is_read == True)
    elif read == "unread":
        notifications = notifications.where(Messages.is_read == False)

    return {
        "total_records": total_records,
        "page_number": page_number,
        "page_size": page_size,
        "messages": [model_to_dict(x) for x in notifications]
    }


async def mark_is_read(message_id: str):
    user = current_user.get()

    if message_id == "all":
        query = Messages.update({Messages.is_read: True}).where(
            (Messages.is_read == False) &
            (Messages.receiver_id == str(user.user_id))
        )
        rows = query.execute()
        return JSONResponse(status_code=200, content=f"Marked {rows} as read.")
    message: Messages = Messages.get_or_none(Messages.message_id == message_id)
    if not message:
        return JSONResponse(status_code=400, content=f"Message not found with id {message_id}.")
    if message.receiver_id != str(user.user_id):
        return JSONResponse(status_code=401, content=f"You are not the recipient of this message.")
    message.is_read = True
    message.save()
    return {"message": "Message marked as read successfully."}
