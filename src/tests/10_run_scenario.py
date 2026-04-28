import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=".env.marketplace")
from src.entities.db_model import Scenario, init_db
from src.tests.config import admin
from src.utils.fetch_utils import login, run_id, fetch

init_db(Path(os.environ.get('DB_PATH')))


def get_run(scenario_id):
    payload = {"scenario_id": str(scenario_id)}
    return fetch("/scenario/run", payload, "POST")


scenario = [
    "Negotiation Scenario",  # 1
    "Auction Scenario",  # 2
    "End-to-End Scenario",  # 3
    "Smart Routing Scenario"  # 4
]

idx = 0
if sys.argv[1]:
    try:
        idx = int(sys.argv[1])
        idx -= 1
        assert len(scenario) > idx
    except ValueError:
        exit("Scenario must be a valid idx.")
else:
    exit("Please specify which scenario to run (1, 2, 3 and so on).")

scenario = Scenario.get(Scenario.scenario_name == scenario[idx])

with login(admin):
    run_obj = get_run(scenario.scenario_id)
run_id.set(run_obj['run_id'])
print("Running scenario, with run_id", run_id.get())

Path("last_run_id.txt").write_text(json.dumps({"run_id": run_id.get()}), encoding="utf-8")
