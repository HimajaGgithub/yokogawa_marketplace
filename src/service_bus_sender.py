import asyncio
import datetime
import json
from uuid import UUID

from azure.servicebus import ServiceBusMessage, ServiceBusClient
from dotenv import load_dotenv
load_dotenv()

from src.utils.service_bus_utils import get_entities

import os


message = json.loads(
    f"""
{{
    "run_id": "fd4d70cc-9a01-4685-a48f-fb626bca2f78",
    "sender_id": "fd27c464-da6c-4a17-b865-1f0b20c28aeb",
    "receiver_id": "f2519d2d2be14f9e8a8110f8f0257b5d",
    "timestamp": "{datetime.datetime.now(datetime.UTC).isoformat()}",
    "message_type": "negotiation_offer",
    "listing_id": "e16d8b2a-d126-4a80-a1ce-0416dd32d9ec",
    "parent_listing_id": null,
    "payload": {{
        "listing_id": "e16d8b2a-d126-4a80-a1ce-0416dd32d9ec",
        "price": 50186.1359102085,
        "listing_name": "Demand for Cobalt",
        "user_name": "recycler",
        "description": "Offer received for your listing.",
        "variables": {{
            "transaction_type": null,
            "listing_price": null,
            "target_price": null,
            "target_date": "2025-09-23T00:00:00"
        }},
        "agent_name": "recycler-user-agent"
    }},
    "is_read": false
}}
""" 
)

print(message)

conn = os.getenv('NAMESPACE_CONNECTION_STR')

async def run():
    print(conn)
    client = ServiceBusClient.from_connection_string(conn)
    topic = get_entities(str(UUID(message['receiver_id'])))[0]
    sb_sender = client.get_topic_sender(topic)
    print(topic, sb_sender)
    with sb_sender:
        sb_sender.send_messages(ServiceBusMessage(json.dumps(message)))


asyncio.run(run())
