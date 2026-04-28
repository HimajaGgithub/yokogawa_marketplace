import asyncio
import contextvars
import datetime
import json
import os
import time
import traceback
from collections import defaultdict
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

import requests
from azure.servicebus.aio import ServiceBusReceiver, ServiceBusClient
from azure.servicebus.exceptions import ServiceBusError, ServiceBusAuthenticationError
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from peewee import fn, DatabaseProxy
from playhouse.shortcuts import model_to_dict
from starlette.responses import JSONResponse

load_dotenv()

from src.entities.common_schema import modes
from src.assets.agent_db import Stock, Orders, DecisionLogs, init_db, TABLE_MAP, Calendar, Config
from src.assets.agent_functions import (check_for_ready_orders, check_for_accepted_orders,
                                        check_for_processing_orders, check_for_large_orders,
                                        inference_engine, check_for_supply_in_stock)
from src.assets.api_utils import fetch_user_details, get_llm_response, function_map, log, check_permissions
from src.utils.fetch_utils import _user_login, current_session

conn = os.getenv('NAMESPACE_CONNECTION_STR')
base_url = os.getenv('AGENT_BASE_URL')
email_id = os.getenv("EMAIL_ID")
db_path = os.getenv("DB_PATH")

db: Optional[DatabaseProxy] = None

current_user_id: contextvars.ContextVar[str] = contextvars.ContextVar("current_user_id")
current_user_profile: contextvars.ContextVar[dict] = contextvars.ContextVar("current_user_profile")
user_location: contextvars.ContextVar[str] = contextvars.ContextVar("user_location")


async def init_service_bus_client(app: FastAPI):
    app.state.servicebus_client = ServiceBusClient.from_connection_string(conn)


async def close_servicebus_client(app: FastAPI):
    """Gracefully close the ServiceBusClient on shutdown."""
    client: ServiceBusClient | None = getattr(app.state, "servicebus_client", None)
    if client:
        await client.close()
        app.state.servicebus_client = None


def get_servicebus_client(app: FastAPI) -> ServiceBusClient:
    """Fetch the ServiceBusClient from app.state."""
    client: ServiceBusClient | None = getattr(app.state, "servicebus_client", None)
    if not client:
        raise RuntimeError("ServiceBusClient has not been initialized")
    return client


def get_entities(user):
    return f"topic_{user}", f"human_{user}", f"agent_{user}"


async def internal_loop():
    while True:
        try:
            with db.connection_context():
                current_user = current_user_profile.get()
                if current_user['email_id'] == "recycler@yokogawa.com":
                    check_for_large_orders(user_location.get())
                else:
                    check_for_accepted_orders(user_location.get())
                check_for_supply_in_stock(user_location.get())
                check_for_processing_orders()
                check_for_ready_orders()
        except KeyboardInterrupt:
            print("Received keyboard interrupt.")
            traceback.print_exc()
            break
        except Exception as e:
            print(f"[internal_loop] Error: {e}")
            traceback.print_exc()
        await asyncio.sleep(5)


async def main_loop(app):
    topic, _, agent_sub = get_entities(current_user_id.get())
    sb_client = get_servicebus_client(app)

    reconnect_delay = 5
    while True:
        try:
            async with sb_client.get_subscription_receiver(
                    topic_name=topic,
                    subscription_name=agent_sub,
                    max_wait_time=3
            ) as receiver:
                receiver: ServiceBusReceiver
                while True:
                    received_messages = await receiver.receive_messages(max_message_count=10)
                    if not received_messages:
                        continue

                    for m in received_messages:
                        with db.connection_context():
                            start = time.perf_counter()
                            try:
                                body = json.loads(b"".join(m.body).decode("utf-8"))
                                print("Message sent at", body["timestamp"],
                                      "Message enqueued at", m.enqueued_time_utc,
                                      "received at", datetime.datetime.now(datetime.UTC))
                                print(json.dumps(body, indent=4))

                                if not check_permissions(body):
                                    print("No permissions to process this message.")
                                    await receiver.complete_message(m)
                                    continue

                                result = await inference_engine(body, current_user_id.get(), current_user_profile.get())
                                if result['instruction'] == "no permissions":
                                    # Please don't remove this check
                                    # as we are checking for "conclude" permissions inside the inference_engine
                                    print("No permissions to handle this message.")
                                    await receiver.complete_message(m)
                                    continue

                                llm_response = get_llm_response(body, result)
                                if llm_response:
                                    if 'args' in result:
                                        for k, v in llm_response.items():
                                            result['args'][k] = v

                                if "function" in result and result['function'] in function_map:
                                    response_status, response_json = function_map[result['function']](**result['args'])
                                    if response_status != 200:
                                        raise ValueError(
                                            f"API call failed with status {response_status}, response {response_json}")
                                llm_response["agent_name"] = result["agent_name"]
                                log(llm_response)
                                print("Result", json.dumps(result, indent=4))
                                await receiver.complete_message(m)
                            except Exception as process_error:
                                await receiver.abandon_message(m)
                                print(f"Error: {process_error}")
                                traceback.print_exc()
                            end = time.perf_counter()
                            print("Took", int(round((end - start) * 1e6)), "µs to process the service bus message.")
                            # Successful loop → reset backoff
                            reconnect_delay = 5
        except KeyboardInterrupt:
            print("Received keyboard interrupt.")
            traceback.print_exc()
            break
        except asyncio.CancelledError:
            print("Cancelling main loop.")
            break
        except (ServiceBusError, ServiceBusAuthenticationError) as sb_error:
            print(f"[ServiceBusError] {sb_error}.")
            traceback.print_exc()
            print(f"Retrying in {reconnect_delay} seconds...")
            await asyncio.sleep(reconnect_delay)
            try:
                old_client = getattr(app.state, "servicebus_client", None)
                if old_client:
                    await old_client.close()
            except Exception:
                pass

            await init_service_bus_client(app)
            sb_client = get_servicebus_client(app)
            reconnect_delay = min(reconnect_delay * 2, 300)  # exponential back-off
            continue
        except Exception as loop_error:
            print(f"Error in main loop: {loop_error}")
            traceback.print_exc()
            exit(1)


@asynccontextmanager
async def lifespan(app: FastAPI):
    global db
    await init_service_bus_client(app)
    db = init_db(Path(db_path))

    session = requests.Session()
    _user_login(session, email_id)
    current_session.set(session)
    profile = fetch_user_details()
    print("GOT user profile", json.dumps(profile))
    current_user_id.set(profile['user_id'])
    user_location.set(profile['location'])
    current_user_profile.set(profile)
    app.state.profile = profile

    tasks = [
        asyncio.create_task(main_loop(app)),
        asyncio.create_task(internal_loop()),
    ]

    yield
    # Cancel background tasks before closing ServiceBus client
    for t in tasks:
        t.cancel()
        try:
            await t
        except asyncio.CancelledError:
            pass
    await close_servicebus_client(app)


def run(self):
    session = current_session.get()
    _response = session.request(
        method="POST",
        url=base_url + "/run",
        json={"user_message": self.user_message}
    )

    _res = _response.text
    if _response.ok:
        _res = _response.json()
    return json.dumps(_res)


app = FastAPI(lifespan=lifespan)

app.mount("/static", StaticFiles(directory=Path("./src/assets/static")), name="static")

templates = Jinja2Templates(directory="./src/templates")


@app.get("/")
async def home(request: Request):
    current_user_name = os.getenv("EMAIL_ID")
    if current_user_name:
        current_user_name = current_user_name.split("@")[0]
    return templates.TemplateResponse(
        name="agent.html",
        context={
            "user_name": current_user_name,
            "preferences": request.app.state.profile.get("preferences"),
            "request": request
        }
    )


@app.post("/")
async def incoming_signal(request: Request):
    body = await request.json()
    if "cleanup" in body:
        stocks = Stock.select().where(Stock.run_id == body['run_id'])
        stock_count = 0
        for stock in stocks:
            stock.status = "expired"
            stock.save()
            stock_count += 1

        order_count = 0
        orders = Orders.select().where(Orders.run_id == body['run_id'])
        for order in orders:
            order.status = "expired"
            order.save()
            order_count += 1

        calendar_count = 0
        entries = Calendar.select().where(Calendar.run_id == body['run_id'])
        for entry in entries:
            entry.status = "expired"
            entry.save()
            calendar_count += 1
        return JSONResponse(content="Cleanup attempted.")

    for t in body['db_entries']:
        table_name = t['table']
        entries = t['entries']
        # TABLE_MAP[table_name]._meta.database = db
        for entry in entries:
            x = TABLE_MAP[table_name].create(run_id=str(body['run_id']), **entry)
            print(table_name, entry, x)


@app.post("/mode")
async def mode_api(request: Request):
    body = await request.json()
    if not body['listing_id']:
        permissions: Config = Config.get(Config.key == "permissions")
        if not body['mode'] in modes:
            return JSONResponse(content="Invalid mode.", status_code=400)
        permissions.value = [x.value for x in modes[body['mode']]]
        permissions.save()
    return JSONResponse(content={"message": "Mode successfully updated."}, status_code=200)


@app.post("/negotiation")
async def negotiation_model_api(request: Request):
    body = await request.json()
    negotiation_model: Config = Config.get_or_none(Config.key == "negotiation_model")
    if negotiation_model:
        negotiation_model.value = body
        negotiation_model.save()
    else:
        Config.create(**{"key": "negotiation_model", "value": body})
    return JSONResponse(content={"message": "Negotiation model successfully updated."}, status_code=200)


@app.get("/decision_logs")
async def decision_logs_api(agent_name: Optional[str] = None, page_number: int = 0, page_size: int = 10):
    if not agent_name:
        subquery = (
            DecisionLogs
            .select(DecisionLogs.agent_name)
            .distinct()
            .order_by(DecisionLogs.agent_name)
            .offset(page_number * page_size)
            .limit(page_size)
        )
        query = (
            DecisionLogs
            .select(
                DecisionLogs.agent_name,
                fn.MIN(DecisionLogs.created_at).alias("viewing_logs_from"),
                fn.MAX(DecisionLogs.created_at).alias("viewing_logs_to"),
                DecisionLogs.tag,
                fn.COUNT(DecisionLogs.message_id).alias("decisions_taken"),
            )
            .where(DecisionLogs.agent_name.in_(subquery))
            .group_by(DecisionLogs.agent_name, DecisionLogs.tag)
            .order_by(DecisionLogs.agent_name)
        )
        result = defaultdict(lambda: {"tags": []})
        for row in query:
            agent_data = result[row.agent_name]
            agent_data["agent_name"] = row.agent_name
            agent_data["tags"].append({
                "tag": row.tag,
                "decisions_taken": row.decisions_taken,
                "from": row.viewing_logs_from,
                "to": row.viewing_logs_to
            })
        return list(result.values())

    query = (
        DecisionLogs.select()
        .where(DecisionLogs.agent_name == agent_name)
        .order_by(DecisionLogs.created_at.desc())
        .offset(page_number * page_size)
        .limit(page_size)
    )
    result = [model_to_dict(x) for x in query]
    return result
