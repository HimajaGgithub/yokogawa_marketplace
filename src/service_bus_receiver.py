import asyncio
import datetime
import json
from uuid import UUID

from dotenv import load_dotenv
load_dotenv()
import os

from src.utils.service_bus_utils import admin
from src.utils.service_bus_utils import receiver_context, get_entities
from azure.servicebus.aio import ServiceBusClient


async def run():
    user_id = str(UUID("f2519d2d2be14f9e8a8110f8f0257b5d"))
    topic, user_sub, agent_sub = get_entities(user_id)

    conn = os.getenv('NAMESPACE_CONNECTION_STR')
    client = ServiceBusClient.from_connection_string(conn)

    while True:
        async with receiver_context(client, user_id, "agent") as messages:
            if not messages:
                props = admin.get_subscription_runtime_properties(topic, agent_sub)
                print("Active:", props.active_message_count, "Dead-letter:", props.dead_letter_message_count)
                await asyncio.sleep(0.5)
                continue
            for m in messages:
                body = json.loads(b"".join(m.body).decode("utf-8"))
                print("Message sent at", body["timestamp"],
                      "Message enqueued at", m.enqueued_time_utc,
                      "received at", datetime.datetime.now(datetime.UTC))
                print(json.dumps(body, indent=4))


asyncio.run(run())
