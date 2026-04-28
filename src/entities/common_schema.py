import json
from enum import Enum


class MessageType(str, Enum):
    # participate | conclude
    auction_new_highest_bid = "auction_new_highest_bid"
    negotiation_offer = "negotiation_offer"
    negotiation_counter_offer = "negotiation_counter_offer"
    negotiation_reject = "negotiation_reject"
    # this is user-level only
    market_listing_announcement = "market_listing_announcement"
    # winners - agent would make new listings and call delivery if this permission is given.
    negotiation_accept = "negotiation_accept"
    auction_winner = "auction_winner"
    auction_closed = "auction_closed"
    listing_delivery = "listing_delivery"
    # new_listing has to handled by agent
    new_listing = "new_listing"
    # approval_pending is only for human / ui
    approval_pending = "approval pending"
    notification = "notification"
    # takeover is for virtual recycler
    takeover = "takeover"
    rsvp_reject = "rsvp_reject"


class Permission(str, Enum):
    new_listing = "new_listing"
    enter = "enter"
    participate = "participate"
    conclude = "conclude"
    acknowledge = "acknowledge"

permission_map = {
    Permission.new_listing: [MessageType.new_listing.value],
    Permission.enter: [MessageType.market_listing_announcement.value],
    Permission.participate: [
        MessageType.auction_new_highest_bid.value,
        MessageType.negotiation_offer.value,
        MessageType.negotiation_counter_offer.value,
        MessageType.negotiation_reject.value,
        MessageType.takeover.value
    ],
    Permission.acknowledge:[
        MessageType.negotiation_accept,
        MessageType.auction_closed,
        MessageType.auction_winner,
        MessageType.listing_delivery
    ]
}

modes = {
    "manual": [
    ],
    "auto": [
        Permission.new_listing, # new_listing created by self
        Permission.enter,  # market_listing_announcement
        Permission.participate,  # auction_new_highest_bid, negotiation_offer, negotiation_counter_offer, negotiation_reject
        Permission.conclude,  # auction_new_highest_bid, negotiation_offer, negotiation_counter_offer, negotiation_reject
        Permission.acknowledge  # negotiation_accept, auction_winner, auction_closed, listing_delivery
    ],
    "dual": [
        Permission.new_listing,
        Permission.acknowledge,
        # you can disable enter and participate permission in the user settings
        # then, later you can give "participate" permission at a listing level.
        Permission.enter,  # market_listing_announcement
        Permission.participate,
    ],
}


class RSVPStatus(Enum):
    invited = "invited"
    interested = "interested"
    rejected = "rejected"

if __name__ == "__main__":
    print(json.dumps(modes, indent=4))
