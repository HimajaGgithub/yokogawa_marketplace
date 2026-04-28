import datetime

scenario_name = "Auction Scenario"
description = """
This demonstrates a auction between recyclers, for a supply listing from ev-fleet.
* Ev-fleet posts a supply for waste-batteries, which are sitting idle for more than 30 days in their inventory.
* Marketplace agent notifies respective recyclers, whose preferences match with this listing.
* The interested recyclers will get into competitive bidding rounds.
* Ev-fleet will end the auction once its internal goals have reached.
"""

tag = "Auction"
expected_outcome = "Bidder with highest bid wins"

participants = [
    "Ather Agent",
    "GreenTech Recycler Agent",
    "Eco Recycler Agent",
    "Marketplace Agent",
]

quantity = 220
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
                    "quantity": quantity,
                    "units": "MWh",
                    "material_quality": "SoH 80",
                    "status": "available",
                    "material_type": "surplus",
                }
            ]
        }
    ],
}
