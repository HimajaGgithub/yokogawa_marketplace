import json
import os
from json import JSONDecodeError
from pathlib import Path

from dotenv import load_dotenv
from playhouse.shortcuts import model_to_dict

from src.entities.common_schema import MessageType
from src.entities.db_model import Listing, Messages, init_db
from src.utils.llm_utils import client, model

mode_switch = os.getenv("llm", default="on")


def generate_mp_rationale(matched_users, listing_item):
    if mode_switch == "off":
        return {"message": "",
                "action": "",
                "rationale": ""}
    context = {
        "matched_users": matched_users,
        "listing_object": listing_item
    }

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": Path("./src/prompts/marketplace_rationale.jinja").read_text()},
            {"role": "user", "content": json.dumps(context, indent=4, default=str)}
        ]
    )
    try:
        result_content = response.choices[0].message.content
        print(result_content)
        result = json.loads(result_content)
        return result
    except JSONDecodeError:
        return {}


def _extract_responder_engagement(messages, listing_owner_id):
    responder_messages = []
    first_analysis = ""
    first_analysis_captured = False

    for msg in messages:
        msg_type = msg.get('message_type', '')
        sender_id = msg.get('sender_id', '')

        if sender_id == listing_owner_id:
            continue

        if msg_type in ['auction_new_highest_bid', 'negotiation_offer']:
            responder_messages.append(msg)

            if not first_analysis_captured:
                payload = msg.get('payload', {})
                first_analysis = payload.get('analysis', '')
                first_analysis_captured = True

    return {
        'first_analysis': first_analysis,
        'responder_messages': responder_messages
    }


def _get_winner_info(listing):
    buyer_id = listing.payload.get('buyer_id')
    buyer_name = listing.payload.get('buyer_name')
    final_price = listing.payload.get('price')

    return {
        'buyer_id': buyer_id,
        'buyer_name': buyer_name,
        'final_price': final_price
    }


def _generate_summary(analysis, messages, prompt_file, listing_item):
    system_prompt = Path(f"./src/prompts/{prompt_file}.jinja").read_text()
    context = {
        "analysis": analysis,
        "responder_messages": [
            {
                'timestamp': msg.get('timestamp'),
                'type': msg.get('message_type'),
                'price': msg.get('payload', {}).get('price'),
                'message': msg.get('payload', {}).get('message', ''),
                'rationale': msg.get('payload', {}).get('rationale', '')
            }
            for msg in messages
        ],
        "listing_item": listing_item
    }

    print("CONTEXT for", prompt_file, json.dumps(context, indent=4, default=str))

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(context, indent=4, default=str)}
        ]
    )

    content = response.choices[0].message.content
    summary = json.loads(content)
    print("RESPONSE", json.dumps(summary, indent=4))
    return summary


def generate_transaction_summary(listing: Listing):
    if mode_switch == "off":
        return {
            "owner_summary": {},
            "other_summary": {}
        }

    # owner query
    owner_id = str(listing.user_id)

    other_id = listing.payload.get('buyer_id')
    if other_id is None or other_id == owner_id:
        other_id = listing.payload.get('seller_id')

    query = (
            (Messages.listing_id == str(listing.listing_id)) &
            (Messages.sender_id == owner_id)
    )

    owner_messages = [model_to_dict(x) for x in Messages.select().where(query).order_by(Messages.timestamp)]
    analysis = [
        m['payload'].get('analysis', None) for m in owner_messages if m['payload'].get("analysis", None)
    ]

    listing_item = model_to_dict(listing, exclude=[Listing.transaction_summary])

    if isinstance(listing_item['offers'], dict):
        listing_item['offers'] = {k: v for k, v in listing_item['offers'].items() if k == str(other_id)}

    owner_summary = _generate_summary(
        analysis,
        owner_messages,
        "transaction_summary_owner",
        listing_item
    )

    # other query

    query = (
            (Messages.listing_id == str(listing.listing_id)) &
            (Messages.sender_id == other_id) &
            (Messages.message_type.in_(
                [MessageType.auction_new_highest_bid.value, MessageType.negotiation_offer.value]))
    )

    other_messages = [model_to_dict(x) for x in Messages.select().where(query).order_by(Messages.timestamp)]
    analysis = [
        m['payload'].get('analysis', None) for m in other_messages if m['payload'].get("analysis", None)
    ]
    other_summary = _generate_summary(
        analysis,
        other_messages,
        "transaction_summary_other",
        listing_item
    )

    return {
        "owner_summary": owner_summary,
        "other_summary": other_summary
    }


if __name__ == "__main__":
    load_dotenv(".env.marketplace")
    init_db(Path(os.getenv("DB_PATH")))
    print(
        json.dumps(
            generate_transaction_summary(
                Listing.get(Listing.listing_id == "59323fb3-b4d3-4783-976f-88f9a43cc1d8")),
            indent=4
        )
    )
