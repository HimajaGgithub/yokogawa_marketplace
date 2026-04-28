description = """
# oem 2
Volvo supplies ev fleet trucks and cars and procure new batteries.
"""

user_profile = {
    "biz_name": "Volvo",
    "email_id": "volvo@oem.com",
    "password": "password",
    "location": "bengaluru",
    "biz_type": "oem",
    "purchase_history": [],
    "preferences": {
        "NMC": {
            "SoH": [90, 101]
        },
        "LFP": {
            "SoH": [90, 101]
        }
    },
    "role": "user",
    "mode": "auto"
}

config = [
    {
        "key": "daily_production",
        "value": {
            "truck": [100, "units"],
        }
    },
    {
        "key": "materials_of_interest",
        "value": {
            "NMC": {"SoH": [95, 101]},
            "LFP": {"SoH": [95, 101]}
        }
    },
    {
        "key": "negotiation_model",
        "value": {
            "buyer_distribution": [
                0,
                10,
                20,
                40,
                80,
                100
            ],
            "buyer_margin_max": 100,
            "buyer_margin_min": 90,
            "buyer_scheme": "distribution",
            "seller_distribution": [
                0,
                10,
                20,
                40,
                80,
                100
            ],
            "seller_margin_max": 110,
            "seller_margin_min": 100,
            "seller_scheme": "distribution"
        }
    },
]
