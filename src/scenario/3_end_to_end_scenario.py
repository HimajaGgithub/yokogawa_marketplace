import datetime
from datetime import timedelta

from src.assets.agent_db import OrderStatus

scenario_name = "End-to-End Scenario"
description = """
This demonstrates end-to-end flow between manufacturer, recycler and ev-fleet.
* The manufacturer has an order for which they have to procure some raw materials.
* Manufacturer checks their internal assets db, and posts a demand for the required materials
* The market-place notifies multiple recyclers based on their preferences for material type and purity.
* Interested recyclers will make quotes for the manufacturer.
* Manufacturer negotiates and both parties come to an agreement.
* Recycler accepts the order, and procures necessary waste batteries to satisfy the order.
* The ev-fleet checks for demands from recycler and supplies the required material with logistics.
"""
tag = "End-to-End"
expected_outcome = "Transactions happen between multiple user types end-to-end."
participants = [
    "Exide Agent",
    "GreenTech Recycler Agent",
    "Eco Recycler Agent",
    "Aether Agent",
    "Marketplace Agent",
    "Mercedes Agent"
]
quantity = 400
table_entries = {
    "mercedes@oem.com": [
        {
            "table": "Orders",
            "entries": [
                {
                    "listing_id": None,
                    "material_code": "truck",
                    "quantity": quantity,
                    "units": "MWh",
                    "selling_price": quantity * 25_00_000,
                    "delivery_date": (datetime.datetime.now(datetime.UTC).date() + timedelta(days=30)).isoformat(),
                    "accepted_date": datetime.datetime.now(datetime.UTC).date().isoformat(),
                    "order_type": "supply",
                    "status": OrderStatus.accepted.value,
                }
            ]
        },
    ],
}
