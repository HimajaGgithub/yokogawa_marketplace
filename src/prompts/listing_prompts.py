import asyncio
import datetime
import json

from dotenv import load_dotenv

load_dotenv()

from src.entities.schema import BizType
from src.entities.schema import UserMessageInput
from src.services.llm_listing_service import generate_listing_preview

def get_sample_prompts():
    listing_prompts = {
        BizType.Manufacturer: [
            f"""
            I have a demand for 660 tons of Cobalt raw material, around Bengaluru, with 80% purity.
            I need it by {(datetime.datetime.today()+datetime.timedelta(days=6)).date().isoformat()}. 
            My negotiation margins must be 102, 104, 105, 106, 108, 110.
            """,
            """
            I have a demand for 50 tons of Cobalt raw material, around Bengaluru, with 80% purity.
            I need it by 25th November, 2025. 
            """,
            f"""
            I have a supply for 80 MWh of new NMC batteries, in Bengaluru. The state of health is 
            95%, I'm up for negotiations. My listing price must be ${80 * 115_000 * 1.1}, and target price is $ {80 * 115_000}.
            """,
        ],

        BizType.Recycler: [
            """
            I have a demand for 30 MWh of LFP waste batteries, around Bengaluru.
            The batteries have a state of health (SoH) 80%. I need it by 25th November, 2025.
            """,
            f"""
            I have a supply for 60 tons of Lithium, in Bengaluru. The purity is 80%.
            I'm up for negotiations. The listing price is $ {60 * 9000 * 1.1}. Target price is ${60 * 9000}.
            """,
        ],
        BizType.EV_Fleet: [
            f"""
            I have a supply for 300 MWh of NMC waste batteries, in Bengaluru.The state of health is 
            80%. The listing is up for auction. My reserve price must be $ {300 * 500 * 0.85}. Auction end date is 24 November 2025.
            """,
            f"""
            I have a supply for 240 MWh of NMC batteries, in Bengaluru.The state of health is 
            98%. The auction's reserve price must be $ {240 * 115_000 * 0.85}. Auction end date is 18th November 2025.
            """,
            f"""
            I have a supply for 300 MWh of LFP waste batteries, in Bengaluru.The state of health is 
            80%. The listing must go for auction, end date is 20th November 2025. The reserve price is {300 * 3600 * 0.85}.
            """,
        ],
        BizType.OEM: [
            """
            I have a demand for 500 MWh NMC batteries (SoH 100), around Bengaluru. The category is new 
            batteries. I need it by 30th November 2025. The recycled content is set at 20%.
            """,
            """
            I have a demand for 20 MWh LFP fresh batteries around Bengaluru, with 100% state of health (SoH).
            I need it by 25th November, 2025. The recycled content must be 30%.
            """,
        ],
    }
    return listing_prompts


async def main():
    for k, v in get_sample_prompts().items():
        print("#", k)
        for prompt in v:
            print("Prompt:")
            print(prompt)
            res = await generate_listing_preview(UserMessageInput(message=prompt))
            print(json.dumps(res, indent=4))
            print("____ ____ ____")


if __name__ == "__main__":
    asyncio.run(main())
