import json

from peewee import fn
from playhouse.shortcuts import model_to_dict

from src.entities.context import current_user
from src.entities.db_model import Listing, User
from src.entities.schema import BizType, ListingType, MaterialCode

# Maps preferences[current-listing-type][current-user-type] -> [target-user-types]
preferences = {
    ListingType.SUPPLY: {
        BizType.Manufacturer: [BizType.EV_Fleet, BizType.OEM],
        BizType.Recycler: [BizType.Manufacturer],
        BizType.EV_Fleet: [BizType.Recycler, BizType.Refurbisher, BizType.Manufacturer],
        BizType.OEM: [BizType.EV_Fleet],
        BizType.Refurbisher: [BizType.ESS_Operator],
        BizType.ESS_Operator: [BizType.Recycler]
    },
    ListingType.DEMAND: {
        BizType.Manufacturer: [BizType.Recycler],
        BizType.Recycler: [BizType.ESS_Operator, BizType.EV_Fleet],
        BizType.EV_Fleet: [BizType.Manufacturer, BizType.OEM],
        BizType.OEM: [BizType.Manufacturer],
        BizType.Refurbisher: [BizType.EV_Fleet],
        BizType.ESS_Operator: [BizType.Refurbisher]
    }
}

def find_matches(listing: Listing):
    """
    Returns a list of users whose preferences matches the listing.
    Does not consider the users production capacity and listing target date.
    """
    _current_user = current_user.get()
    material_code = listing.material_code
    if isinstance(material_code, MaterialCode):
        material_code = material_code.value
    print("material_code", material_code, isinstance(material_code, str))
    query_payload = listing.payload

    target_biz_types = preferences[listing.listing_type][BizType(_current_user.biz_type)]
    print("In find matches", material_code, query_payload, target_biz_types)

    # Fetch user if the user is in target biz_types, and user preferences has the listings material
    candidates = User.select().where(
        (User.biz_type.in_(target_biz_types) &  # Use .value here
        fn.json_extract(User.preferences, f"$.{material_code}").is_null(False))
    )

    result = []
    for user in candidates:
        material_preferences = user.preferences.get(material_code, {})
        common_params = material_preferences.keys() & query_payload.keys()
        for param in common_params:
            preference = material_preferences[param]
            query_value = query_payload[param]

            if isinstance(preference, str) and preference == query_value:
                result.append(user)
                break
            elif preference[0] <= query_value < preference[1]:
                result.append(user)
                break
    return result


if __name__ == "__main__":
    current_user.set(User.get_or_none(User.user_id == "dc094ba003864ea6a3683dee7072b30a"))
    query_listing = Listing.get_or_none(Listing.listing_id == "c6130fe2-0f93-4bca-8746-6e93e9e80125")
    print(query_listing, isinstance(query_listing, Listing))
    res = find_matches(query_listing)
    print("Looking for", json.dumps(model_to_dict(query_listing), indent=4, default=str))
    print("Matches", len(res))
    for l in res:
        print(json.dumps(model_to_dict(l), indent=4, default=str))
        print("---- ---- ----")
