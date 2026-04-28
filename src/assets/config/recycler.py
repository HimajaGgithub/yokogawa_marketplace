# Recycler 1 - Specializes in Lithium, Cobalt, Nickel extraction
description = """
# Recycler 1
Recycler 1 procures waste batteries from EV fleet and extracts Lithium, Cobalt, and Nickel.
Specializes in processing NMC and LCO battery waste for high-value materials.
"""

user_profile = {
    "biz_name": "GreenTech Recyclers",
    "email_id": "greentech@recycler.com",
    "password": "password",
    "location": "bengaluru",
    "biz_type": "recycler",
    "purchase_history": [],
    "preferences": {
        "Cobalt": {
            "purity": [60, 90]
        },
        "Lithium": {
            "purity": [60, 90]
        },
        "NMC": {
            "SoH": [60, 90]
        },
        "LFP": {
            "SoH": [60, 90]
        },
        "lfp_waste": {
            "SoH": [60, 90]
        },
        "nmc_waste": {
            "SoH": [60, 90]
        }
    },
    "role": "user",
    "mode": "dual",
    "daily_production": {
        "Lithium": [150, "tons"],
        "Cobalt": [120, "tons"],
        "Nickel": [100, "tons"],
        "Manganese": [100, "tons"],
    }
}

config = [
    {
        # todo: remove daily_production from config, as it is a public variable. config is only for private variables
        "key": "daily_production",
        "value": {
            "Lithium": [150, "tons"],
            "Cobalt": [120, "tons"],
            "Nickel": [100, "tons"],
            "Manganese": [100, "tons"],
        }
    },
    {
        "key": "materials_of_interest",
        "value": {
            "nmc_waste": {"SoH": [75, 90]},
            "lfp_waste": {"SoH": [75, 90]},
            "NMC": {"SoH": [75, 90]},
            "LFP": {"SoH": [75, 90]}
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
