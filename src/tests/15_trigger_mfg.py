import datetime
import uuid
from datetime import timedelta

import requests

data = {
    "run_id": str(uuid.uuid4()),
    "db_entries": [
        {
            "table": "Orders",
            "entries": [
                {
                    "listing_id": None,
                    "material_code": "NMC",
                    "quantity": 100,
                    "units": "MWh",
                    "selling_price": 30_00_000,
                    "delivery_date": (datetime.datetime.now(datetime.UTC).date() + timedelta(days=30)).isoformat(),
                    "accepted_date": datetime.datetime.now(datetime.UTC).date().isoformat(),
                    "order_type": "supply",
                    "status": "accepted",
                }
            ]
        }
    ]
}

requests.post("http://localhost:8001", json=data)
