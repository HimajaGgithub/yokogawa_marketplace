import operator
from functools import reduce

from playhouse.shortcuts import model_to_dict
from starlette.responses import JSONResponse

from src.entities.context import current_user
from src.entities.db_model import Listing, User
from src.entities.schema import BizType, StatusType, ListingType

preferences = {
    BizType.Manufacturer: [
        (BizType.OEM, ListingType.DEMAND),
        (BizType.Recycler, ListingType.SUPPLY),
        (BizType.EV_Fleet, ListingType.SUPPLY)
    ],
    BizType.EV_Fleet: [
        (BizType.Recycler, ListingType.DEMAND),
    ],
    BizType.Recycler: [
        (BizType.EV_Fleet, ListingType.SUPPLY),
        (BizType.Manufacturer, ListingType.DEMAND),
    ],
    BizType.OEM: [
        (BizType.Manufacturer, ListingType.SUPPLY),
    ],
}


def _add_user_info(listing, user_mapping):
    if listing['user_id'] in user_mapping:
        lister = user_mapping[listing['user_id']]
    else:
        lister = User.get(User.user_id == listing['user_id'])
    listing['lister_info'] = {
        'biz_name': lister.biz_name,
        'biz_type': lister.biz_type,
        'location': lister.location,
        'email_id': lister.email_id
    }
    return listing


def get_dict(listing: Listing, user_mapping):
    user = current_user.get()
    model = model_to_dict(listing, exclude=[Listing.matches])

    if not isinstance(listing.created_at, str):
        model['created_at'] = listing.created_at.isoformat()
    if not isinstance(listing.last_modified_at, str):
        model['last_modified_at'] = listing.last_modified_at.isoformat()

    if listing.user_id != user.user_id and user.role != "admin":
        if "target_price" in model['payload']:
            del model['payload']['target_price']
        if "budget" in model['payload']:
            del model['payload']['budget']
        if "negotiation_model" in model['payload']:
            del model['payload']['negotiation_model']
        if isinstance(model['offers'], dict):
            model['offers'] = {k: v for k, v in model['offers'].items() if k == str(user.user_id)}

    _add_user_info(model, user_mapping)
    return model


async def view_listing(listing_id: str):
    listing: Listing = Listing.get_or_none(Listing.listing_id == listing_id)
    if not listing:
        return JSONResponse(status_code=400, content=f"Could not find listing with listing id: {listing_id}")
    return get_dict(listing, {})


async def show_general_items(listing_type=None, page_number=0, page_size=10):
    user = current_user.get()
    filters = (
            (Listing.user_id != user.user_id) &
            (Listing.status != StatusType.COMPLETED.value)
    )
    if listing_type:
        filters &= (Listing.listing_type == listing_type.value)
    listings_from_other_users = (
        Listing
        .select()
        .where(
            filters
        ).order_by(Listing.created_at.desc())
        .offset(page_number * page_size)
        .limit(page_size)
    )
    print(listings_from_other_users)
    items = list(listings_from_other_users)

    users_list = list(set([x.user_id for x in items]))
    users = User.select().where(User.user_id.in_(users_list))
    users_map = {x.user_id: x for x in users}

    result = [get_dict(x, users_map) for x in items]
    return result


async def get_my_purchase_history(page_number, page_size):
    user = current_user.get()
    items = list(
        Listing
        .select()
        .where(Listing.listing_id.in_(user.purchase_history))
        .order_by(
            Listing.last_modified_at.desc()
        ).offset(page_number * page_size)
        .limit(page_size)
    )
    users_list = list(set([x.user_id for x in items]))
    users = User.select().where(User.user_id.in_(users_list))
    users_map = {x.user_id: x for x in users}

    result = [get_dict(x, users_map) for x in items]
    return result


async def get_my_listings(page_number, page_size):
    user = current_user.get()
    items = list(
        Listing
        .select()
        .where(
            (Listing.user_id == user.user_id) &
            (Listing.status.not_in([StatusType.COMPLETED.value, StatusType.DELIVERED.value]))
        ).order_by(
            Listing.created_at.desc()
        ).offset(page_number * page_size)
        .limit(page_size)
    )
    users_list = list(set([x.user_id for x in items]))
    users = User.select().where(User.user_id.in_(users_list))
    users_map = {x.user_id: x for x in users}

    result = [get_dict(x, users_map) for x in items]
    return result


async def show_items_for_me(page_number, page_size):
    user = current_user.get()
    if BizType(user.biz_type) not in preferences:
        return await show_general_items(page_number=page_number, page_size=page_size)
    prefs = preferences[BizType(user.biz_type)]
    conditions = [
        ((User.biz_type == x[0]) & (Listing.listing_type == x[1])) for x in prefs
    ]
    or_condition = reduce(operator.or_, conditions)
    items = list(
        Listing.select(Listing, User)
        .join(User, on=(Listing.user_id == User.user_id))
        .where(
            (Listing.status.in_([StatusType.ACTIVE.value, StatusType.PENDING.value])) &
            (Listing.user_id != user.user_id) &
            (Listing.material_code.in_([x for x in user.preferences.keys()])) &
            or_condition
        ).order_by(
            Listing.last_modified_at.desc()
        ).offset(page_number * page_size)
        .limit(page_size)
    )

    users_list = list(set([x.user_id for x in items]))
    users = User.select().where(User.user_id.in_(users_list))
    users_map = {x.user_id: x for x in users}

    output = [get_dict(x, users_map) for x in items]
    result = []
    for x in output:
        material_preferences = user.preferences.get(x['material_code'], {})
        common_params = material_preferences.keys() & x['payload'].keys()
        for param in common_params:
            preference = material_preferences[param]
            query_value = x['payload'][param]

            if isinstance(preference, str) and preference == query_value:
                result.append(x)
                break
            elif preference[0] <= query_value < preference[1]:
                result.append(x)
                break

    return result
