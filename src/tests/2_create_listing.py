from src.tests.config import refurb, fleet, manu_1, recycler, recycler_2, oem_1, oem_2, oem, manufacturer
from src.utils.fetch_utils import fetch, login

base_url = "http://localhost:8000"

def generate_listing_preview(message):
    payload = {"message": message}
    return fetch("/listing/generate-preview", payload, "POST")

def ensure_required_fields(x):
    # Fix missing category
    if x['response'].get('category') is None:
        x['response']['category'] = "waste battery"  # or decide based on logic

    # Fix missing target price when negotiation
    payload = x['response'].get("payload", {})
    if payload.get("transaction_type") == "negotiation" and not payload.get("target_price"):
        listing_price = payload.get("listing_price")
        if listing_price:
            # Assume target price = 90% of listing price if not explicitly provided
            payload["target_price"] = round(listing_price * 0.9, 2)

    return x

def create_listing(x):
    x = ensure_required_fields(x)
    fetch("/listing/create-listing", x['response'], "POST")

if __name__ == "__main__":
    with login(manufacturer):
        demand_message = """
        I have a demand for 600 tons of Cobalt, around bengaluru, with 85% purity . 
        I need it by 2nd November 2025. I'm up for negotiations.
        """
        x = generate_listing_preview(demand_message)
        create_listing(x)
    exit()

    with login(oem):
        messages = [
        """
        I have a demand for 500 class 8 trailer truck EV NMC batteries (SoH 100), around Bengaluru. 
        The average battery capacity is 600 kWh per battery. The category is new batteries. 
        I need it by 30th November 2025. The recycled content is set at 20%.
        """,
        """
        I have a demand for 500 class 8 trailer truck EV NMC batteries (SoH 100), around Bengaluru. 
        The average battery capacity is 0.6 MWh per battery. The category is new batteries. 
        I need it by 30th November 2025. The recycled content is set at 20%.
        """,
        """
        I have a demand for 300 MWh of  NMC batteries (SoH 100), around Bengaluru. 
        The category is new batteries. I need it by 30th November 2025. 
        The recycled content is set at 20%.
        """,
        ]
        for m in messages:
            print("Input:", m)
            x = generate_listing_preview(m)

    exit()

    with login(refurb):
        demand_message = """
        I have a demand for 30 kgs of Lithium waste batteries, around bengaluru, 
        in a really good working condition with 80% state of health. I'm up for negotiations.
        """
        x = generate_listing_preview(demand_message)
        create_listing(x)

        demand_message = """
        I have a demand for 300 units of refurbished batteries, around bengaluru, 
        in a really good working condition with 75% state of health. I'm up for negotiations.
        """
        x = generate_listing_preview(demand_message)
        create_listing(x)

        supply_message = """
        I have a supply for 500 units of refurbished batteries, in chennai.
        The state of health is 75%, and the output rate is 12 watt-hours.
        I'm up for negotiations. My listing price must be 3000, and target price is 2700.
        """
        x = generate_listing_preview(supply_message)
        create_listing(x)

        supply_message = """
        I have a supply for 500 Cobalt batteries, in chennai.
        The state of health is 82%, and the output rate is 24 watt-hours.
        I'm up for negotiations. My listing price must be 6000, and target price is 5400.
        """
        x = generate_listing_preview(supply_message)
        create_listing(x)

    with login(fleet):
        supply_message = """
        I have a supply for 30 kgs of Lithium batteries which are waste batteries.
        I want them in good working condition, the brand is everyday and the 
        state of health is 80%, the voltage is 5V. My location is bangalore. 
        I am opening this for auction with start date is 15th August and end date as 
        20th August 2025, and the reserve price as 300 INR.
        """
        x = generate_listing_preview(supply_message)
        create_listing(x)

    with login(manu_1):
        supply_message = """
        We have a supply of 500 newly manufactured LTO heavy-duty battery systems, 
        each with a capacity of 50 kWh and an efficiency rating of 92%, 
        available from our Pune plant. 
        Listing price must be €15,000 per unit, target price €14,000.
        """
        x = generate_listing_preview(supply_message)
        create_listing(x)

        demand_message = """
        We require 1 ton of Cobalt oxide to meet next quarter's production target 
        of 1000 NMC battery modules at our Hyderabad facility. 
        Purity should be at least 98%, and delivery is required within 4 weeks.
        """
        x = generate_listing_preview(demand_message)
        create_listing(x)

        demand_message = """
        Looking for 500 kg of Nickel material compatible with NMC cells, 
        to be supplied to our Delhi plant. 
        Supplier must ensure consistent quality and provide batch test certificates.
        """
        x = generate_listing_preview(demand_message)
        create_listing(x)

    with login(recycler):
        supply_message = """
        We have 100 kg Lithium at the price of €30, per kg.
        We can deliver it within 200 km radius of Kolkata within 12 hours.
        """
        x = generate_listing_preview(supply_message)
        create_listing(x)

        demand_message = """
        We need LFP battery for recycling purpose and the quantity required is 153 battery packs,
        for the cost of €7650, per pack. The delivery should be done within 4 days to our facility in Hyderabad.
        """
        x = generate_listing_preview(demand_message)
        create_listing(x)

    with login(recycler_2):
        supply_message = """
        We have 100 kg Lithium available for sale at €6.50 per kg.
        Additionally, we can supply 800 kg Iron and 400 kg Phosphorus.
        Delivery is possible within 150 km radius of Odisha within 24 hours.
        """
        x = generate_listing_preview(supply_message)
        create_listing(x)

        demand_message = """
        We need LCO battery packs for recycling purpose and the quantity required is 151 units,
        for the cost of €7550 in total (≈€50.00 per pack).
        The delivery should be done within 2 days to our facility in Hyderabad.
        """
        x = generate_listing_preview(demand_message)
        create_listing(x)

    with login(oem_1):
        supply_message = """
        We have 85 NMC battery packs available at the price of €4,200 per pack.
        Additionally, we can supply separated raw materials: 600 kg Nickel, 320 kg Manganese, and 250 kg Cobalt.
        We can deliver it within a 250 km radius of Bangalore within 36 hours.
        """
        x = generate_listing_preview(supply_message)
        create_listing(x)   

        demand_message = """
        We need NMC battery packs for recycling purpose and the quantity required is 140 units,
        for the cost of €588,000 in total (≈€4,200 per pack).
        The delivery should be done within 5 days to our facility in Pune.
        """
        x = generate_listing_preview(demand_message)
        create_listing(x)

    with login(oem_2):
        supply_message = """
        We have 50 LTO battery packs available for sale at €3,000 per pack.
        We can also supply 200 kg Lithium and 150 kg Titanium oxide.
        Delivery can be arranged within 150 km radius of Chennai within 24 hours.
        """
        x = generate_listing_preview(supply_message)
        create_listing(x)   

        demand_message = """
        We need LTO battery packs for second-life energy storage projects,
        with the quantity required being 75 units at a total cost of €225,000 (≈€3,000 per pack).
        The delivery should be completed within 4 days to our facility in Delhi.
        """
        x = generate_listing_preview(demand_message)
        create_listing(x)
