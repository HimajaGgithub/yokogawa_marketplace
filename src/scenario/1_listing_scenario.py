import datetime
from datetime import timedelta

from src.assets.agent_db import OrderStatus
from src.properties.market_prices import unit_quantity

scenario_name = "Negotiation Scenario"
description = """
This demonstrates a negotiation flow between a manufacturer and recycler.
* The manufacturer has an order for which they have to procure some raw materials.
* Manufacturer checks their internal assets db, and posts a demand for the required materials
* The market-place notifies multiple recyclers based on their preferences for material type and purity.
* Interested recyclers will make quotes for the manufacturer.
* Manufacturer negotiates and both parties come to an agreement.
"""
tag = "Negotiation"
expected_outcome = "Listing is created based on the agents internal assets db."
participants = [
    "GreenTech Recycler Agent",
    "Eco Recycler Agent",
    "Exide Agent",
    "Marketplace Agent",
]
quantity = 150
table_entries = {
    "exide@manufacturer.com": [
        {
            "table": "Orders",
            "entries": [
                {
                    "listing_id": None,
                    "material_code": "NMC",
                    "quantity": quantity,
                    "units": "MWh",
                    "selling_price": 30_00_000,
                    "delivery_date": (datetime.datetime.now(datetime.UTC).date() + timedelta(days=30)).isoformat(),
                    "accepted_date": datetime.datetime.now(datetime.UTC).date().isoformat(),
                    "order_type": "supply",
                    "status": OrderStatus.accepted.value,
                }
            ]
        },
    ],
    "greentech@recycler.com": [
        {
            "table": "Stock",
            "entries": [
                {
                    "created_at": (datetime.datetime.now(datetime.UTC).date() - datetime.timedelta(days=5)).isoformat(),
                    "material_code": "nmc_waste",
                    "category": "waste battery",
                    "quantity": unit_quantity['NMC']['Cobalt'][1] * quantity,
                    "units": "MWh",
                    "material_quality": "SoH 80",
                    "status": "available",
                    "material_type": "surplus",
                }
            ]
        }
    ],
    "eco@recycler.com": [
        {
            "table": "Stock",
            "entries": [
                {
                    "created_at": (datetime.datetime.now(datetime.UTC).date() - datetime.timedelta(days=5)).isoformat(),
                    "material_code": "nmc_waste",
                    "category": "waste battery",
                    "quantity": unit_quantity['NMC']['Cobalt'][1] * quantity,
                    "units": "MWh",
                    "material_quality": "SoH 80",
                    "status": "available",
                    "material_type": "surplus",
                }
            ]
        }
    ]
}
