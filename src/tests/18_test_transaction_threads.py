import json

from src.tests.config import recycler, oem, manufacturer, fleet

from src.utils.fetch_utils import login, fetch

def get_threads(params):
    url = f"/listing/threads?"
    for k, v in params.items():
        url += k + "=" + v
    return fetch(url, print_response=False, get_response_code=True)


if __name__ == "__main__":
    with login(oem):
        # mercedes
        oem_response, oem_threads = get_threads({"listing_id": "4864128e-c05b-4b13-bdc7-18f62718538c"})
    with login(manufacturer):
        # exide
        manu_response, manufacturer_threads = get_threads({"listing_id": "f435f2e0-e36b-4ac9-afe9-ce17d2cbbb1f"})
    with login(recycler):
        # greentech
        recycler_response, recycler_threads = get_threads({"listing_id": "b4ab67e5-09ec-4549-aab6-f0907e4e1dad"})
    with login(fleet):
        # aether
        fleet_response, fleet_threads = get_threads({"listing_id": "b4ab67e5-09ec-4549-aab6-f0907e4e1dad"})

    assert oem_threads['events'] == manufacturer_threads['events']
    assert recycler_threads['events'] == fleet_threads['events']
    assert manufacturer_threads['events'] == recycler_threads['events']
