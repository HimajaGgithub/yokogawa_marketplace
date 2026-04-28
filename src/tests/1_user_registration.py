import json

import requests

from src.tests.config import password, fleet, ess, refurb, logistics, oem, fleet_1, fleet_2, refurb_1, \
    refurb_2, refurb_3, manufacturer, ess_1, manu_1, recycler, recycler_2, oem_1, oem_2
from src.utils.fetch_utils import fetch, run

base_url = "http://localhost:8000"

session = requests.Session()


def user_register(email):
    # Mapping prefixes to valid biz_type values
    prefix_map = {
        "fleet": "ev_fleet",
        "refurbisher": "refurbisher",
        "recycler": "recycler",
        "ess": "ess",
        "oem": "oem",
        "logistics": "logistics",
        "manufacturer": "manufacturer",
        "manu": "manufacturer"
    }

    prefix = email.split("@")[0].split("_")[0]
    biz_type = prefix_map.get(prefix)

    if not biz_type:
        print(f"Could not determine biz_type for {email}")
        return

    payload = {
        "biz_name": email.split("@")[0],
        "email_id": email,
        "password": password,
        "location": "chennai",
        "biz_type": biz_type,
        "role": "user"
    }

    response = session.post(base_url + "/users/register", json=payload)
    print(response.status_code, json.dumps(response.json(), indent=4))


def user_profile():
    fetch("/users/profile", None, "get")


if __name__ == '__main__':
    user_register(manufacturer)
    user_register(manu_1)
    user_register(oem)
    user_register(ess)
    user_register(logistics)
    user_register(recycler)
    user_register(recycler_2)
    user_register(oem_1)
    user_register(oem_2)
    user_register(ess_1)
    user_register(refurb)
    user_register(refurb_1)
    user_register(refurb_2)
    user_register(refurb_3)
    user_register(fleet)
    user_register(fleet_1)
    user_register(fleet_2)

    run(fleet, user_profile)
