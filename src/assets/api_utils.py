import json
import os
from json import JSONDecodeError
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

from src.assets.agent_db import DecisionLogs, agent_db_proxy, Config
from src.entities.common_schema import permission_map
from src.utils.fetch_utils import fetch
from src.utils.llm_utils import client, model

load_dotenv()

mode_switch = os.getenv("llm", default="on")


def get_role(listing, current_user_id) -> Literal['buyer', 'seller']:
    is_owner = listing['user_id'] == current_user_id
    if listing['listing_type'] == "demand":
        return "buyer" if is_owner else "seller"
    if listing['listing_type'] == "supply":
        return "seller" if is_owner else "buyer"


def make_counter_offer(listing_id, price, other_user, **kwargs):
    payload = {
        "listing_id": listing_id,
        "replying_to_user": other_user,
        "negotiation_type": "counter_offer",
        "price": price,
        "message": "No, your quote is way too low, I need more.", **kwargs
    }
    return fetch("/listing/negotiate", payload, "post", get_response_code=True)


def fetch_user_details():
    return fetch("/users/profile")


def send_pending_signal(listing_id, description, other_user, price, **kwargs):
    return fetch("/auction/pending-approval", {
        "listing_id": listing_id,
        "description": description,
        "winning_user": other_user,
        "price": price,
        **kwargs
    }, "post", get_response_code=True)


def close_auction(listing_id, **kwargs):
    return fetch(f"/auction/close-auction", {
        "listing_id": listing_id, **kwargs
    }, method="post", get_response_code=True)


def place_bid(listing_id, price, message="This is my bid.", **kwargs):
    payload = {
        "listing_id": listing_id,
        "price": price,
        "message": message, **kwargs
    }
    return fetch("/auction/place-bid", payload, "post", get_response_code=True)


def logistics_deliver(listing_id, message="Your order is ready!", **kwargs):
    payload = {
        "listing_id": listing_id,
        "message": message, **kwargs
    }
    return fetch("/logistics/deliver", payload, "post", get_response_code=True)


def accept_offer(listing_id, other_user, price, message="Ok! Sold!", **kwargs):
    payload = {
        "listing_id": listing_id,
        "replying_to_user": other_user,
        "negotiation_type": "accept",
        "price": price,
        "message": message, **kwargs
    }
    return fetch("/listing/negotiate", payload, "post", get_response_code=True)


def reject_offer(listing_id, other_user, price, message="Nope!", **kwargs):
    payload = {
        "listing_id": listing_id,
        "replying_to_user": other_user,
        "negotiation_type": "reject",
        "price": price,
        "message": message, **kwargs
    }
    return fetch("/listing/negotiate", payload, "post", get_response_code=True)


def reject_invite(listing_id, **kwargs):
    payload = {
        "listing_id": listing_id,
        **kwargs
    }
    return fetch("/listing/rsvp-reject", payload, "post", get_response_code=True)


def inform_pending_approval(listing_id, other_user, description="Offer is pending approval.", **kwargs):
    if "message" in kwargs:
        del kwargs['message']
    payload = {
        "listing_id": listing_id,
        "replying_to_user": other_user,
        "negotiation_type": "approval_pending",
        "message": description, **kwargs
    }
    return fetch("/listing/negotiate", payload, "post", get_response_code=True)


def get_listing_details(listing_id):
    return fetch(f"/listing/view-listing/{listing_id}", method="get")


def generate_listing_preview(message):
    payload = {"message": message}
    return fetch("/listing/generate-preview", payload, "POST")


def create_listing(x):
    return fetch("/listing/create-listing", x, "POST")


def get_all_users():
    return fetch("/users", method="GET")


def make_an_offer(listing_id, price, message="Willing to go lower.", **kwargs):
    payload = {
        "listing_id": listing_id,
        "negotiation_type": "offer",
        "price": price,
        "message": message, **kwargs
    }
    return fetch("/listing/negotiate", payload, "post", get_response_code=True)


def send_notification(payload, message_type, **kwargs):
    payload.update(kwargs)
    data = {
        "payload": payload,
        "message_type": message_type
    }
    print("Sending notification with data", data)
    return fetch("/notifications", data, "post", get_response_code=True)


function_map = {
    "reject_invite": reject_invite,
    "reject_offer": reject_offer,
    "make_an_offer": make_an_offer,
    "accept_offer": accept_offer,
    "make_counter_offer": make_counter_offer,
    "place_bid": place_bid,
    "close_auction": close_auction,
    # "send_notification": send_notification,
    "send_pending_signal": send_pending_signal,
    "inform_pending_approval": inform_pending_approval,
}


def get_llm_response(original_message, inference_result):
    if mode_switch == "off":
        return {"message": "",
                "action": "",
                "rationale": "",
                "chain_of_thought": "",
                "analysis": ""}
    context = {
        "incoming_message": original_message,
        "inference_engine_response": inference_result
    }

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": Path("./src/prompts/generate_rationale.jinja").read_text(encoding="utf-8")},
            {"role": "user", "content": json.dumps(context, indent=4)}
        ]
    )
    try:
        result_content = response.choices[0].message.content
        print(result_content)
        result = json.loads(result_content)
        return result
    except JSONDecodeError:
        return {}


def log(entry):
    agent_name = entry['agent_name']
    if "chain_of_thought" not in entry:
        result = get_llm_response({}, entry)
        if not isinstance(result, dict) and "action" not in result:
            print("WARNING: action not found in entry. Could not log to DecisionLogs.")
            print("Entry:", entry)
            print("Result", result)
            return ()
        entry.update(result)

    with agent_db_proxy.connection_context():
        DecisionLogs.create(
            action=entry.get('action', ""),
            rationale=entry.get('rationale', ""),
            chain_of_thought=entry.get('chain_of_thought', ""),
            agent_name=agent_name,
            tag=entry.get('tag', 'marketplace')
        )


def check_permissions(m):
    permissions = Config.get(Config.key == "permissions").value
    print("Config permissions", permissions)
    for permission, message_types in permission_map.items():
        if m['message_type'] in message_types and permission.value in permissions:
            return True
    return False
