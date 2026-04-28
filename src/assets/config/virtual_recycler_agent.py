description = """
# Yokogawa recycler agent
Yokogawa recycler agent buys from other recyclers and sells it to manufacturers.
"""

user_profile = {
    "biz_name": "Virtual Recycler Agent",
    "email_id": "recycler@yokogawa.com",
    "password": "password",
    "location": "bengaluru",
    "biz_type": "virtual_recycler",
    "purchase_history": [],
    "preferences": {},
    "role": "user",
    "mode": "auto"
}

config = [
    {
        "key": "daily_production",
        "value": {}
    },
    {
        "key": "materials_of_interest",
        "value": {
            "Cobalt": {"purity": [60, 101]},
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
            "seller_margin_max": 130,
            "seller_margin_min": 110,
            "seller_scheme": "distribution"
        }
    },
]
