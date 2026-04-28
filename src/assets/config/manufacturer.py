description = """
# Manufacturer
Manufacturer supplies NMC batteries, and procures raw materials.
"""

user_profile = {
    "biz_name": "Exide",
    "email_id": "exide@manufacturer.com",
    "password": "password",
    "location": "bengaluru",
    "biz_type": "manufacturer",
    "purchase_history": [],
    "preferences": {
        "Cobalt": {
            "purity": [60, 90],
        },
        "Lithium": {
            "purity": [60, 90],
        },
        "NMC": {
            "SoH": [90, 101]
        },
        "LFP": {
            "SoH": [90, 101]
        },
        "nmc_waste": {
            "SoH": [90, 101]
        },
        "lfp_waste": {
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
            "NMC": [100, "MWh"],
            "LFP": [100, "MWh"],
        }
    },
    {
        "key": "materials_of_interest",
        "value": {
            "NMC": {"SoH": [95, 101]},
            "LFP": {"SoH": [95, 101]},
            "nmc_waste": {"SoH": [95, 101]},
            "lfp_waste": {"SoH": [95, 101]},
            "Cobalt": {"purity": [75, 90]},
            "Lithium": {"purity": [75, 90]},
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
    }
]
