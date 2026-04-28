import datetime

scenario_name = "Smart Routing Scenario"
description = """
This demonstrates a auction between recyclers, for a supply listing from ev-fleet.
* Ev-fleet posts a supply for waste-batteries, which are sitting idle for more than 30 days in their inventory.
* Marketplace agent notifies respective recyclers, whose preferences match with this listing.
* The interested recyclers will get into competitive bidding rounds.
* Ev-fleet will end the auction once its internal goals have reached.
"""

tag = "smart_routing"
expected_outcome = "ev fleet creates listings to manufacturer and recycler"

participants = [
    "Ather Agent",
    "GreenTech Recycler Agent",
    "Marketplace Agent",
    "Exide Agent",
]

q1 = 340
q2 = 260

table_entries = {
    "aether@fleet.com": [
        {
            "table": "Stock",
            "entries": [
                {
                    "created_at": (
                            datetime.datetime.now(datetime.UTC).date() - datetime.timedelta(days=100)).isoformat(),
                    "material_code": "nmc_waste",
                    "category": "waste battery",
                    "quantity": q1,
                    "units": "MWh",
                    "material_quality": "SoH 80",
                    "status": "available",
                    "material_type": "surplus",
                },
                {
                    "created_at": (
                            datetime.datetime.now(datetime.UTC).date() - datetime.timedelta(days=100)).isoformat(),
                    "material_code": "nmc_waste",
                    "category": "waste battery",
                    "quantity": q2,
                    "units": "MWh",
                    "material_quality": "SoH 98",
                    "status": "available",
                    "material_type": "surplus",
                }
            ]
        }
    ],
}
