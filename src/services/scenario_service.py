import asyncio
import importlib
import json
import time
from typing import Optional, List

import requests
from fastapi import Request
from playhouse.shortcuts import model_to_dict
from starlette.responses import JSONResponse

from src.entities.context import current_user
from src.entities.db_model import Messages, User, Scenario, Runs
from src.entities.schema import ScenarioIdRequest
from src.properties.properties import user_email_url_map


async def get_scenario(scenario_id: Optional[str]):
    if not scenario_id:
        scenarios = Scenario.select()
        return [model_to_dict(x) for x in scenarios]
    scenario = Scenario.get_or_none(Scenario.scenario_id == scenario_id)
    return model_to_dict(scenario)


async def get_scenario_types():
    types = Scenario.select(Scenario.tag).distinct()
    return [x.tag for x in types]


def _enrich_message(m, users_map):
    sender = users_map.get(str(m["sender_id"]))
    receiver = users_map.get(str(m["receiver_id"]))
    m["sender"] = sender.biz_name if sender else None
    m["receiver"] = receiver.biz_name if receiver else None
    m['sender_location'] = sender.location if sender else None
    m['receiver_location'] = receiver.location if receiver else None
    m['sender_biz_type'] = sender.biz_type if sender else None
    m['receiver_biz_type'] = receiver.biz_type if receiver else None
    return m


def combine(dicts: List[dict]):
    if len(dicts) == 1:
        return dicts[0]

    result = dicts[0]
    for obj in dicts[1:]:
        for k, v in obj.items():
            if k in result and isinstance(v, str) and result[k] != v:
                result[k] += ", " + v
    return result


async def run_scenario(request: ScenarioIdRequest):
    user = current_user.get()
    scenario = Scenario.get_or_none(Scenario.scenario_id == request.scenario_id)
    if not scenario:
        return JSONResponse(content=f"No scenario found with id: {request.scenario_id}", status_code=400)

    run: Runs = Runs.create(**{
        "scenario_id": request.scenario_id,
        "user_id": str(user.user_id),
    })

    # create users (if not existing)
    # deploy pods (if not existing)
    # clear db for each user
    # insert new assets.db and configs for each user
    # send run_id to azure, azure will set it in the env vars, and restart the pods
    # agents will look into their asset.db on start.

    scenario_module = importlib.import_module(scenario.module)
    print("HELLO WORLD")
    for user, db_entries in scenario_module.table_entries.items():
        assert user in user_email_url_map, (f"Please update the src.properties.properties file "
                                            f"to include {user}. The user's email must be specified "
                                            f"in the scenario module.")
        url = user_email_url_map[user]
        post_start = time.perf_counter()
        requests.post(
            url=url,
            json={
                "db_entries": db_entries,
                "run_id": str(run.run_id)
            }
        )
        post_end = time.perf_counter()
        print("User", user, "db_entries", db_entries, int(round((post_end - post_start) * 1e6)))
    return {"run_id": str(run.run_id)}


async def cleanup(request: Request, run_id: str):
    run = Runs.get_or_none(Runs.run_id == run_id)
    if not run:
        return JSONResponse(content=f"No run found with id: {run_id}", status_code=400)

    scenario = Scenario.get_or_none(Scenario.scenario_id == run.scenario_id)
    if not scenario:
        return JSONResponse(content=f"No scenario found with id: {run.scenario_id}", status_code=400)

    scenario_module = importlib.import_module(scenario.module)
    for user, db_entries in scenario_module.table_entries.items():
        assert user in user_email_url_map, (f"Please update the src.properties.properties file "
                                            f"to include {user}. The user's email must be specified "
                                            f"in the scenario module.")
        url = user_email_url_map[user]
        res = requests.post(
            url=url,
            json={
                "cleanup": True,
                "run_id": str(run.run_id)
            }
        )
        if not res.ok:
            return JSONResponse(content=f"Failed to reach {user} user's agent.", status_code=400)
    return JSONResponse(content="Attempted cleanup. Please wait a moment before cleanup finishes.")


async def stream_messages(request: Request, run_id: str):
    last_message_id = None
    users_map = {}

    # helper to resolve user info

    while True:
        if await request.is_disconnected():
            break

        # fetch messages newer than last seen
        query = (
            Messages.select()
            .where(
                (Messages.run_id == run_id)
                & (Messages.message_id > last_message_id) if last_message_id else (Messages.run_id == run_id)
            )
            .order_by(Messages.timestamp)
        )

        new_messages = list(query)

        if new_messages:
            last_message_id = new_messages[-1].message_id

            # fetch any missing users
            user_ids = {m.sender_id for m in new_messages} | {m.receiver_id for m in new_messages}
            missing_users = user_ids - set(users_map.keys())
            if missing_users:
                for u in User.select().where(User.user_id.in_(missing_users)):
                    users_map[str(u.user_id)] = u

            # yield enriched messages
            for m in new_messages:
                data = _enrich_message(model_to_dict(m), users_map)
                yield json.dumps(data, default=str) + "\n"

        await asyncio.sleep(4)
