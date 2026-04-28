import datetime
import json
import os
from contextlib import asynccontextmanager
from datetime import timedelta
from typing import Literal, Union, Optional
from uuid import UUID

from azure.servicebus import ServiceBusMessage
from azure.servicebus.aio import ServiceBusClient
from azure.servicebus.management import ServiceBusAdministrationClient
from fastapi import FastAPI, Request

from src.entities.common_schema import MessageType
from src.entities.context import current_user, run_id, agent_name
from src.entities.db_model import User, Messages

conn = os.getenv('NAMESPACE_CONNECTION_STR')

admin = ServiceBusAdministrationClient.from_connection_string(conn)


async def init_service_bus_client(app: FastAPI):
    app.state.servicebus_client = ServiceBusClient.from_connection_string(conn)


async def close_servicebus_client(app: FastAPI):
    """Gracefully close the ServiceBusClient on shutdown."""
    client: ServiceBusClient | None = getattr(app.state, "servicebus_client", None)
    if client:
        await client.close()
        app.state.servicebus_client = None


def get_servicebus_client(app: FastAPI) -> ServiceBusClient:
    """Fetch the ServiceBusClient from app.state."""
    client: ServiceBusClient | None = getattr(app.state, "servicebus_client", None)
    if not client:
        raise RuntimeError("ServiceBusClient has not been initialized")
    return client


async def get_sb_client_from_request(request: Request):
    return get_servicebus_client(request.app)


def get_entities(user: Union[User, str, UUID]):
    if isinstance(user, UUID):
        user = str(user)
    if isinstance(user, str):
        return f"topic_{user}", f"human_{user}", f"agent_{user}"
    return f"topic_{user.user_id}", f"human_{user.user_id}", f"agent_{user.user_id}"


async def create_entities_for_user(user: User):
    topic, human_sub, agent_sub = get_entities(user)
    admin.create_topic(topic)
    admin.create_subscription(topic, human_sub, lock_duration=timedelta(seconds=300))
    admin.create_subscription(topic, agent_sub, lock_duration=timedelta(seconds=300))


def convert_id_to_str(x):
    if isinstance(x, UUID):
        return str(x)
    elif isinstance(x, User):
        return str(x.user_id)
    else:
        return str(UUID(x))


async def send(request: Request | FastAPI, receivers, message_type: MessageType, payload, sender: Optional[User]= None):
    # Normalize receivers into a list of string IDs
    if not isinstance(receivers, list):
        receivers = [receivers]

    receivers = [convert_id_to_str(r) for r in receivers]

    if sender:
        sender_user = sender
    else:
        sender_user = current_user.get()

    _run_id = run_id.get()
    _agent = agent_name.get()
    payload['agent_name'] = _agent
    listing_id = payload.get("listing_id")
    parent_listing_id = payload.get('variables', {}).get("parent_listing_id", None)
    timestamp = datetime.datetime.now(datetime.UTC).isoformat()

    # Prepare all message rows for DB
    message_json_list = [
        {
            "run_id": _run_id,
            "sender_id": str(sender_user.user_id),
            "receiver_id": rid,
            "timestamp": timestamp,  # same timestamp for all
            "message_type": message_type.value,
            "listing_id": listing_id,
            "parent_listing_id": parent_listing_id,
            "payload": payload,
            "is_read": False
        }
        for rid in receivers
    ]

    # Insert into DB
    Messages.insert_many(message_json_list).execute()

    # Send to each receiver’s topic
    if isinstance(request, Request):
        servicebus_client = await get_sb_client_from_request(request)
    else:
        servicebus_client = get_servicebus_client(request)

    for rid, msg in zip(receivers, message_json_list):
        topic = get_entities(rid)[0]
        sb_sender = servicebus_client.get_topic_sender(topic)
        async with sb_sender:
            await sb_sender.send_messages(ServiceBusMessage(json.dumps(msg)))


@asynccontextmanager
async def receiver_context(request, user: Union[User, str, UUID], subscriber: Literal['human', 'agent']):
    topic, human_sub, agent_sub = get_entities(user)
    sub = human_sub if subscriber == "human" else agent_sub
    if isinstance(request, Request):
        servicebus_client = await get_sb_client_from_request(request)
    else:  
        servicebus_client =  request
    async with servicebus_client.get_subscription_receiver(
            topic_name=topic,
            subscription_name=sub,
            max_wait_time=5
    ) as receiver:
        received_messages = await receiver.receive_messages(max_message_count=10)
        try:
            yield received_messages
        finally:
            for m in received_messages:
                await receiver.complete_message(m)


async def print_topics_all():
    topics = admin.list_topics()
    for topic in topics:
        print(f"## Topic Name: {topic.name}")
        for sub in admin.list_subscriptions(topic_name=topic.name):
            print("- Subscription", sub.name)
        print()
