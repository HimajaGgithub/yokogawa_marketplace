import os

from dotenv import load_dotenv

load_dotenv()

base_url = os.environ.get("AGENT_BASE_URL")
if not base_url:
    base_url = "http://localhost:8000"

print("Using base url", base_url)

password = "password"
refurb = "refurbisher@refurbisher.com"
recycler = "greentech@recycler.com"
logistics = "logistics@logistics.com"
oem = "mercedes@oem.com"
fleet = "aether@fleet.com"
ess = "ess@ess.com"
manufacturer = "exide@manufacturer.com"
admin = "admin@yokogawa.com"

ess_1 = "ess_1@ess.com"
ess_2 = "ess_2@ess.com"
refurb_1 = "refurbisher_1@refurbisher.com"
refurb_2 = "refurbisher_2@refurbisher.com"
refurb_3 = "refurbisher_3@refurbisher.com"
fleet_1 = "fleet_1@fleet.com"
fleet_2 = "fleet_2@fleet.com"
manu_1 = "manu_1@manufacturer.com"
recycler_2 = "eco@recycler.com"
oem_1 = "oem_1@oem.com"
oem_2 = "oem_2@oem.com"
