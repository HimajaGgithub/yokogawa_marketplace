from src.tests.config import refurb, fleet
from src.utils.fetch_utils import fetch, login


def get_recommendations_for_me():
    fetch(f"/marketplace/latest-items-for-me", method="get")


def get_supply_demand_items():
    fetch(f"/marketplace/supply-demand-items", method="get")
    fetch(f"/marketplace/supply-demand-items?listing_type=supply", method="get")
    fetch(f"/marketplace/supply-demand-items?listing_type=demand", method="get")


def get_my_listings():
    fetch("/marketplace/view-my-listings", method="get")


def view_listing(listing_id):
    fetch(f"/listing/view-listing/{listing_id}", method="get")

def view_stats():
    fetch("/home/view-stats", method="get")


def view_recent_activity():
    fetch("/home/view-recent-activity", method="get")


if __name__ == "__main__":
    listing_id = "5480a186-dc46-4f8d-a0c0-fd1b08e92b61"
    with login(fleet):
        get_supply_demand_items()
        get_recommendations_for_me()
        get_my_listings()
        view_recent_activity()
        view_stats()
        view_listing(listing_id)

    with login(refurb):
        get_supply_demand_items()
        get_recommendations_for_me()
        get_my_listings()
        view_recent_activity()
        view_stats()
        view_listing(listing_id)
