import json
import os
import sys
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=".env.marketplace")
from src.entities.db_model import Scenario, init_db
from src.tests.config import admin
from src.utils.fetch_utils import login, fetch

init_db(Path(os.environ.get('DB_PATH')))


def get_run(scenario_id):
    payload = {"scenario_id": str(scenario_id)}
    return fetch("/scenario/run", payload, "POST")


def get_scenario_types():
    return fetch("/scenario/types")


def get_one_scenario(scenario_id):
    return fetch(f"/scenario?scenario_id={scenario_id}")


def get_threads(params):
    url = f"/listing/threads?"
    for k, v in params.items():
        url += k + "=" + v
    return fetch(url, print_response=False)
    # return fetch(f"/scenario/threads?scenario_id={_scenario_id}")


def get_all_scenarios():
    return fetch(f"/scenario")


def fmt_time(ts):
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return dt.strftime("%H:%M:%S")


def listing_name(details, lid):
    info = details.get(lid, {})
    name = info.get("item_name", "Unknown")
    return f"{name} ({lid[:8]}...)"


def ancestors(details, lid):
    """Return list of ancestor IDs from root → this listing."""
    chain = []
    while lid:
        chain.append(lid)
        lid = details.get(lid, {}).get("payload", {}).get("parent_listing_id")
    return list(reversed(chain))


def print_ascii_tree(data):
    events = data.get("events", [])
    details = data.get("listing_details", {})

    last_lid = None  # track which listing we’re currently printing under

    for ev in events:
        lid = ev["listing_id"]
        chain = ancestors(details, lid)  # root → lid
        indent = "    " * len(chain)
        ts = fmt_time(ev["timestamp"])

        # If listing changes, print its header again
        if lid != last_lid:
            for depth, ancestor in enumerate(chain):
                indent_hdr = "    " * depth
                print(f"{indent_hdr}└── [Listing {listing_name(details, ancestor)}]")
            last_lid = lid

        # Print event under the current listing
        print(f"{indent}• {ev['message_type']} [{ts}] {ev['sender']} → {ev['receiver']}")


if __name__ == "__main__":
    scenario = Scenario.get(Scenario.scenario_name == "Negotiation Scenario")

    threads_params = {}
    if len(sys.argv) == 2 and sys.argv[1]:
        threads_params = json.loads(sys.argv[1])
    else:
        last_run_id_file = Path("last_run_id.txt")
        if last_run_id_file.exists():
            threads_params = json.load(last_run_id_file.open())
    print(threads_params)

    with login(admin):
        if threads_params:
            print("Trying to get threads for", threads_params)
            response = get_threads(threads_params)
            print_ascii_tree(response)
        else:
            get_scenario_types()
            get_one_scenario(scenario.scenario_id)
            result = get_all_scenarios()
            responses = []
            for x in result:
                response = get_threads({"scenario_id":x['scenario_id']})
                responses.append(response)
            for x in responses:
                print_ascii_tree(x)
                print("\n---- ---- ----\n\n")
