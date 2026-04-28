description = """
# EV-fleet
Sells waste NMC and LCO batteries.
"""

user_profile = {
    "biz_name": "Ather",
    "email_id": "aether@fleet.com",
    "password": "password",
    "location": "bengaluru",
    "biz_type": "ev_fleet",
    "purchase_history": [],
    "preferences": {
        "nmc_waste": {
            "SoH": [60, 101]
        },
        "lfp_waste": {
            "SoH": [60, 101]
        },
    },
    "role": "user",
    "mode": "auto"
}

config = [
    {
        "key": "daily_production",
        "value": {
            "nmc_waste": [100, "Mwh"],
            "lfp_waste": [100, "Mwh"],
        }
    },
    {
        "key": "materials_of_interest",
        "value": {}
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
