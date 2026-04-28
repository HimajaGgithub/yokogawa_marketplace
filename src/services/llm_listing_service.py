import datetime
import json
import traceback
from collections import defaultdict
from pathlib import Path
from typing import Optional
from uuid import UUID

from fastapi import BackgroundTasks, Request
from playhouse.shortcuts import model_to_dict
from starlette.responses import JSONResponse

from src.entities.common_schema import MessageType, RSVPStatus
from src.entities.context import current_user
from src.entities.db_model import Listing, Messages, Runs, User
from src.entities.schema import (
    UserMessageInput, ListingType, MaterialCode, FinalListingCreation,
    NegotiateMessage, TransactionType, StatusType, NegotiationType
)
from src.services.marketplace_service import get_dict
from src.services.match_listings_service import find_matches
from src.services.scenario_service import _enrich_message, combine
from src.utils.agents_utils import generate_mp_rationale, generate_transaction_summary
from src.utils.llm_utils import client, model
from src.utils.service_bus_utils import send


async def generate_listing_preview(request: UserMessageInput):
    try:
        user = current_user.get()
    except LookupError:
        user = None
    system_prompt = Path("src/prompts/generate_listing_preview.jinja").read_text()
    material_types = f"""
    The material type must be one of: {[x for x in MaterialCode]}
    """
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt + material_types},
            {"role": "user", "content": request.message}
        ]
    )
    preview = json.loads(response.choices[0].message.content)
    print("preview", preview)

    if isinstance(preview["quantity"], str):
        preview['quantity'] = eval(preview['quantity'])
        if not isinstance(preview['quantity'], float):
            return JSONResponse(status_code=400, content="Could not parse quantity as a float.")

    action = "Buy" if preview['listing_type'] == "demand" else "Sell"
    target_date = preview.get("payload", {}).get("target_date", "")
    if not target_date:
        target_date = preview.get("payload", {}).get("end_date", "")

    transaction_type = preview.get("payload", {}).get("transaction_type")

    mapping = {
        "NMC": "NMC batteries",
        "LFP": "LFP batteries",
        "LCO": "LCO batteries",
        "LTO": "LTO batteries",
        "lfp_waste": "LFP waste batteries",
        "nmc_waste": "NMC waste batteries",
        "lto_waste": "LTO waste batteries",
        "lco_waste": "LCO waste batteries",
    }
    code = preview['material_code']
    name = mapping[code] if code in mapping else code

    preview[
        'title'] = f"{action} {round(preview['quantity'])} {preview['quantity_unit']} of {name} around {preview['location']} by {target_date}"
    if transaction_type:
        preview['title'] += f" via {transaction_type}"

    return {
        "response": preview,
        "user_id": str(user.user_id) if user else ""
    }


virtual_takeover = {
    "Cobalt": 500
}


async def create_listing(request, listing_data: FinalListingCreation, background_tasks: BackgroundTasks):
    user = current_user.get()
    listing_dict = listing_data.model_dump()
    listing_dict['user_id'] = str(user.user_id)
    listing_dict['item_name'] = f"[{user.biz_name}]: " + listing_data.title
    current_date = datetime.datetime.now(datetime.UTC).strftime("%Y-%m-%dT%H:%M")

    if listing_dict['listing_type'] == ListingType.SUPPLY.value and listing_dict['payload'][
        'transaction_type'] == "auction":
        listing_dict['offers'] = []
        listing_dict['payload']['start_date'] = current_date
    else:
        listing_dict['offers'] = {}

    new_listing: Listing = Listing.create(**listing_dict)

    # Matching algo
    # todo: generate some chain-of-thought for why the platform has matched.
    # generate one message for new listing found... initiating search
    # another message for matches found, sending invitations.
    print(model_to_dict(new_listing))
    print(new_listing, isinstance(new_listing, Listing))
    marketplace_agent: User = User.get(User.email_id == "market@yokogawa.com")
    recycler_agent: User = User.get(User.email_id == "recycler@yokogawa.com")

    background_tasks.add_task(
        send, request, list({str(marketplace_agent.user_id), str(user.user_id)}),
        MessageType.new_listing, {
            "listing_id": str(new_listing.listing_id),
            "listing_name": new_listing.item_name,
            "variables": new_listing.payload,
            "message": listing_data.message,
            "action": listing_data.action,
            "rationale": listing_data.rationale,
            "analysis": listing_data.analysis
        }
    )

    if user.user_id == recycler_agent.user_id and listing_data.target_user:
        target = User.get_or_none(User.user_id == listing_data.target_user)
        if target:
            _users = [target]
        else:
            _users = []
    else:
        _users = find_matches(new_listing)

    print("New listing matched with _users", _users)
    user_data = [model_to_dict(user) for user in _users]
    listing_item = model_to_dict(new_listing)
    mp_agent_response = generate_mp_rationale(matched_users=user_data, listing_item=listing_item)

    print(mp_agent_response)
    new_listing.matches = {
        str(x.user_id): RSVPStatus.invited.value for x in _users
    }
    new_listing.save()

    background_tasks.add_task(
        send, request, _users, MessageType.market_listing_announcement, {
            "listing_id": str(new_listing.listing_id),
            "listing_name": new_listing.item_name,
            "variables": new_listing.payload,
            "message": mp_agent_response["message"],
            "action": mp_agent_response["action"],
            "rationale": mp_agent_response["rationale"],
        })
    return {
        "message": "Listing created successfully",
        "listing_id": str(new_listing.listing_id),
    }


async def rsvp_reject(listing_id, background_tasks: BackgroundTasks, request: Request):
    user = current_user.get()

    listing: Optional[Listing] = Listing.get_or_none(Listing.listing_id == listing_id)
    if not listing:
        return JSONResponse(
            status_code=400,
            content=f"Listing not found with id: {listing_id}"
        )
    if str(user.user_id) not in listing.matches:
        return JSONResponse(
            status_code=400,
            content=f"You can't reject an invite which you haven't gotten."
        )
    listing.matches[str(user.user_id)] = RSVPStatus.rejected.value
    listing.save()

    listing_owner = User.get(User.user_id == listing.user_id)
    background_tasks.add_task(
        send, request, listing_owner, MessageType.rsvp_reject, {
            "listing_id": str(listing.listing_id)
        })

    recycler_agent: User = User.get(User.email_id == "recycler@yokogawa.com")
    invite_status = [v for k, v in listing.matches.items() if k != str(recycler_agent.user_id)]
    if all(status == RSVPStatus.rejected.value for status in invite_status):
        if (listing.material_code in virtual_takeover and
                (listing.quantity > virtual_takeover[listing.material_code])):
            print("Virtual recycler invited.")
            listing.matches[str(recycler_agent)] = RSVPStatus.invited.value
            listing.save()

            background_tasks.add_task(
                send, request, recycler_agent, MessageType.takeover, {
                    "listing_id": str(listing.listing_id)
                }, listing_owner
            )
    return JSONResponse(content="Invite status updated successfully.", status_code=200)


async def negotiate(negotiate_message: NegotiateMessage, background_tasks: BackgroundTasks, request: Request):
    user = current_user.get()

    listing: Optional[Listing] = Listing.get_or_none(Listing.listing_id == negotiate_message.listing_id)
    if not listing:
        return JSONResponse(
            status_code=400,
            content=f"Listing not found with id: {negotiate_message.listing_id}"
        )
    if listing.status == StatusType.COMPLETED.value:
        return JSONResponse(
            status_code=400,
            content=f"Listing status is completed... Cannot accept new negotiations on this listing."
        )
    if listing.payload.get("transaction_type",
                           "") != TransactionType.NEGOTIATION.value and listing.listing_type != ListingType.DEMAND.value:
        return JSONResponse(
            status_code=400,
            content=f"Listing not up for negotiation."
        )
    if listing.user_id == user.user_id:
        # you are the owner
        if not negotiate_message.replying_to_user:
            return JSONResponse(
                status_code=400,
                content=f"Request must specify who you are replying to. Request is missing replying_to_user field."
            )
        options = ["accept", "reject", "counter_offer", "approval_pending"]
        target_user_id = str(UUID(negotiate_message.replying_to_user))
        if negotiate_message.negotiation_type == NegotiationType.APPROVAL_PENDING:
            notify = str(listing.user_id)  # notify self
        else:
            notify = str(UUID(negotiate_message.replying_to_user))
    else:
        options = ['offer']
        target_user_id = str(user.user_id)
        notify = str(listing.user_id)

    if negotiate_message.negotiation_type.value not in options:
        return JSONResponse(
            status_code=400,
            content=f"Not permitted to make {negotiate_message.negotiation_type.value} on this listing."
        )

    if not listing.offers:
        listing.offers = {}
    existing_chat = listing.offers.get(target_user_id, [])

    negotiate_message.user_name = user.biz_name
    if negotiate_message.negotiation_type == NegotiationType.OFFER:
        entry = negotiate_message.model_dump(exclude={'listing_id', 'replying_to_user'})
        entry['action_type'] = negotiate_message.negotiation_type.value
        existing_chat.append(entry)
        existing_chat = sorted(existing_chat, key=lambda x: x['timestamp'], reverse=True)
        listing.offers[target_user_id] = existing_chat
    else:
        latest_offer = existing_chat[0]
        if negotiate_message.negotiation_type == NegotiationType.COUNTER_OFFER:
            latest_offer['counter_offer'] = negotiate_message.price
        elif negotiate_message.negotiation_type == NegotiationType.APPROVAL_PENDING:
            latest_offer['suggested_price'] = negotiate_message.price
        else:
            latest_offer['action_type'] = negotiate_message.negotiation_type.value

        if negotiate_message.rationale and negotiate_message.negotiation_type == NegotiationType.APPROVAL_PENDING:
            latest_offer['owners_reply'] = negotiate_message.rationale
        else:
            latest_offer['owners_reply'] = negotiate_message.message
        latest_offer['owner_replied_at'] = datetime.datetime.now(datetime.UTC).isoformat()
        existing_chat[0] = latest_offer

    if negotiate_message.negotiation_type.value in ['accept']:
        listing.status = StatusType.COMPLETED.value
        winner_user_model: User = User.get(User.user_id == negotiate_message.replying_to_user)

        # Save buyer_id, so we can use this buyer_id when delivering logistics.
        # If listing_type is demand, then the listing_owner itself will be the buyer.
        if listing.listing_type == ListingType.SUPPLY.value:
            listing.payload['buyer_id'] = str(winner_user_model.user_id)
            listing.payload['buyer_name'] = winner_user_model.biz_name
            listing.payload['price'] = negotiate_message.price
        else:
            listing.payload['seller_id'] = str(winner_user_model.user_id)
            listing.payload['seller_name'] = winner_user_model.biz_name
            listing.payload['price'] = negotiate_message.price

        if winner_user_model.purchase_history:
            winner_user_model.purchase_history.append(str(listing.listing_id))
        else:
            winner_user_model.purchase_history = [str(listing.listing_id)]
        winner_user_model.save()

        # add it for seller also
        if user.purchase_history:
            user.purchase_history.append(str(listing.listing_id))
        else:
            user.purchase_history = [str(listing.listing_id)]
        user.save()

        try:
            summary = generate_transaction_summary(listing)
            listing.transaction_summary = summary
        except Exception:
            traceback.print_exc()
            listing.transaction_summary = {}


    elif negotiate_message.negotiation_type in [NegotiationType.OFFER, NegotiationType.COUNTER_OFFER,
                                                NegotiationType.REJECT]:
        # the following if is for that case where listing is pending approval, and the bot
        # rejects offers from another user
        if listing.status != StatusType.APPROVAL_PENDING.value:
            # If you reject, the supply is still open for others to negotiate.
            listing.status = StatusType.PENDING.value
    elif negotiate_message.negotiation_type == NegotiationType.APPROVAL_PENDING:
        listing.status = StatusType.APPROVAL_PENDING.value

    listing.save()

    mapping = {
        NegotiationType.OFFER: MessageType.negotiation_offer,
        NegotiationType.COUNTER_OFFER: MessageType.negotiation_counter_offer,
        NegotiationType.ACCEPT: MessageType.negotiation_accept,
        NegotiationType.REJECT: MessageType.negotiation_reject,
        NegotiationType.APPROVAL_PENDING: MessageType.approval_pending,
    }

    _type = mapping[negotiate_message.negotiation_type]
    background_tasks.add_task(
        send, request, notify, _type, {
            "listing_id": str(listing.listing_id),
            "price": negotiate_message.price,
            "listing_name": listing.item_name,
            "user_name": user.biz_name,
            "message": negotiate_message.message,
            "action": negotiate_message.action,
            "rationale": negotiate_message.rationale,
            "analysis": negotiate_message.analysis,
            "variables": listing.payload
        }
    )
    return {
        "message": f"{negotiate_message.negotiation_type.value} action performed successfully."
    }


async def get_threads(listing_id, run_id, scenario_id, page_number, page_size):
    user = current_user.get()
    if run_id:
        run_id = str(UUID(run_id))
        messages_query = Messages.select().where(Messages.run_id == run_id).order_by(Messages.timestamp)
        total_records = messages_query.count()

    elif scenario_id:
        latest_run = Runs.select().where(
            (Runs.user_id == str(user.user_id)) &
            (Runs.scenario_id == scenario_id)
        ).order_by(
            Runs.created_at.desc()
        ).get_or_none()
        if not latest_run:
            return {}
        listings = Messages.select(Messages.listing_id).distinct().where(Messages.run_id == latest_run.run_id)
        messages_query = Messages.select().where(Messages.listing_id.in_(listings)).order_by(Messages.timestamp)
        total_records = messages_query.count()
    elif listing_id:
        run_ids = Messages.select(Messages.run_id).where(Messages.listing_id == listing_id).distinct()
        listing_ids = Messages.select(Messages.listing_id).where(Messages.run_id.in_(run_ids)).distinct()
        messages_query = Messages.select().where(
            (Messages.listing_id.in_(listing_ids))
        ).order_by(Messages.timestamp)
        total_records = messages_query.count()
    else:
        base_query = (
            Listing.select(Listing.listing_id)
            .order_by(Listing.last_modified_at)
        )
        total_records = base_query.count()
        sub_query = base_query.offset(page_number * page_size).limit(page_size)
        listing_ids = [str(x) for x in sub_query]
        messages_query = Messages.select().where(Messages.listing_id.in_(listing_ids)).order_by(Messages.timestamp)

    messages = [model_to_dict(x) for x in messages_query]

    users_list = list(set([x['sender_id'] for x in messages] + [x['receiver_id'] for x in messages]))
    users = User.select().where(User.user_id.in_(users_list))
    users_map = {str(x.user_id): x for x in users}

    messages = [_enrich_message(m, users_map) for m in messages]

    listing_ids = list(set([x['listing_id'] for x in messages]))
    listings = Listing.select().where(Listing.listing_id.in_(listing_ids))
    listing_objects = [get_dict(x, users_map) for x in listings]
    listing_details = {str(x['listing_id']): x for x in listing_objects}
    # print("listing details", json.dumps(listing_details, indent=4, default=str))

    for m in messages:
        listing_owner = str(listing_details[m['listing_id']]['user_id'])
        m['is_receiver_listing_owner'] = m['receiver_id'] == listing_owner
        m['is_sender_listing_owner'] = m['sender_id'] == listing_owner

    timestamp_groups = defaultdict(list)
    for m in messages:
        timestamp_groups[m['timestamp']].append(m)

    events = [combine(group) for group in timestamp_groups.values()]
    result = {
        "events": sorted(events, key=lambda x: datetime.datetime.fromisoformat(x['timestamp'].replace(" ", 'T'))),
        "listing_details": listing_details,
        "users": [model_to_dict(u, only=[User.user_id, User.biz_name, User.biz_type]) for u in users]
    }

    # total_pages = (total_records + page_size - 1) // page_size
    # print("Total records, total pages", total_records, total_pages)
    # result['total_pages'] = total_pages
    # result['total_records'] = total_records
    # result['current_page'] = page_number
    return result
