import asyncio
import datetime
import os
import time
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, Request, Response, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from starlette.responses import JSONResponse

load_dotenv()

import src.utils.service_bus_utils as service_bus_utils
from src.entities.db_model import init_db
from src.api.agent_routes import agent_router
from src.api.auction_routes import auction_router
from src.api.homepage_routes import homepage_router
from src.api.list_item_routes import listing_router
from src.api.logistics_routes import logistics_router
from src.api.marketplace_routes import marketplace_router
from src.api.message_routes import message_router
from src.api.scenario_routes import scenario_router
from src.api.users_routes import user_router
from src.entities.context import current_user, run_id, agent_name
from src.entities.db_model import (
    User, Listing, RevokedTokens
)
from src.entities.schema import ListingType, TransactionType, StatusType, ListingIdRequest
from src.services.auction_service import close_auction
from src.utils.budget_calculations_utils import generate_html
from src.utils.auth_utils import authenticate_request, is_protected, extend_tokens


async def auction_close_task(app):
    while True:
        now = datetime.datetime.now(datetime.UTC).isoformat()
        auctions_to_expire = Listing.select().where(
            (Listing.listing_type == ListingType.SUPPLY.value) &
            (Listing.status.in_([StatusType.ACTIVE.value, StatusType.PENDING.value])) &
            (Listing.payload["transaction_type"] == TransactionType.AUCTION.value) &
            (Listing.payload["end_date"] < now)
        )

        for x in auctions_to_expire:
            x: Listing
            user = User.get_or_none(User.user_id == x.user_id)
            if not user: continue
            current_user.set(user)
            await close_auction(ListingIdRequest(listing_id=str(x.listing_id)), app)
            print(f"Closing auction {x.listing_id} as it is expired.")

        await asyncio.sleep(300)


async def token_cleanup_task():
    while True:
        now = datetime.datetime.now(datetime.UTC)
        RevokedTokens.delete().where(RevokedTokens.exp_timestamp < now).execute()
        # Run cleanup every hour
        await asyncio.sleep(3600)


@asynccontextmanager
async def lifespan(app: FastAPI):
    db_path = Path(os.getenv("DB_PATH"))
    init_db(db_path)

    await service_bus_utils.init_service_bus_client(app)
    tasks = [
        asyncio.create_task(token_cleanup_task()),
        asyncio.create_task(auction_close_task(app))
    ]
    yield
    # Cancel background tasks before closing ServiceBus client
    for t in tasks:
        t.cancel()
        try:
            await t
        except asyncio.CancelledError:
            pass
    await service_bus_utils.close_servicebus_client(app)


app = FastAPI(lifespan=lifespan)


@app.middleware("http")
async def check_logged_in(request: Request, call_next):
    pre_start = time.perf_counter()
    if request.method == "OPTIONS":
        return Response(status_code=200)

    if is_protected(request.url.path):
        try:
            auth_start = time.perf_counter()
            user: User = authenticate_request(request.cookies, request.headers, request.query_params, request.url.path)
            auth_end = time.perf_counter()
            print("Auth took", int(round((auth_end - auth_start) * 1e6)), "µs.")
            _run_id = request.headers.get("x-run-id", default=str(uuid.uuid4()))
            run_id.set(_run_id)
            print("RUN id is set to", run_id.get())
            _agent = request.headers.get("x-agent-name", default=f"{user.biz_name} Agent")
            agent_name.set(_agent)
            current_user.set(user)
        except HTTPException as e:
            return JSONResponse(status_code=e.status_code, content={"error": e.detail})

    pre_end = time.perf_counter()
    response = await call_next(request)
    post_start = time.perf_counter()
    if is_protected(request.url.path):
        extend_tokens(request, response)
    post_end = time.perf_counter()
    print(
        "Middleware Pre",
        int(round((pre_end - pre_start) * 1e6)),
        "µs. Post",
        int(round((post_end - post_start) * 1e6)),
        "µs."
    )
    return response


ORIGIN = os.getenv("CORS_ALLOW_UI_URL")

# The order of middleware matters.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[ORIGIN],
    allow_credentials=True,
    # When allow credentials=True, you can't use a wildcard '*'
    # So, you have to write it all out.
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-CSRF-TOKEN"],
    expose_headers=['X-CSRF-TOKEN']
)

app.include_router(user_router)
app.include_router(listing_router)
app.include_router(logistics_router)
app.include_router(auction_router)
app.include_router(agent_router)
app.include_router(marketplace_router)
app.include_router(homepage_router)
app.include_router(message_router)
app.include_router(scenario_router)

templates = Jinja2Templates(directory="./src/templates")


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse(
        name="index.html",
        context={
            "budget_calculations":"", # generate_html(),
            "request": request
        })


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        print("Removing connection", websocket in self.active_connections)
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@app.websocket("/messages")
async def websocket_endpoint(websocket: WebSocket):
    try:
        user = authenticate_request(websocket.cookies, websocket.headers, websocket.query_params, websocket.url.path)
    except HTTPException as e:
        await websocket.close(code=1008, reason=e.detail)
        return
    await manager.connect(websocket)
    topic, human_sub, _ = service_bus_utils.get_entities(user)

    sb_client = service_bus_utils.get_servicebus_client(websocket.app)
    async with sb_client.get_subscription_receiver(
            topic_name=topic,
            subscription_name=human_sub,
            max_wait_time=3
    ) as receiver:
        try:
            while True:
                # Run websocket.receive() and receiver.receive_messages() in parallel
                servicebus_task = asyncio.create_task(
                    receiver.receive_messages(max_message_count=10)
                )
                websocket_task = asyncio.create_task(websocket.receive())

                done, pending = await asyncio.wait(
                    [servicebus_task, websocket_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )

                if websocket_task in done:
                    message = await websocket_task
                    if message["type"] == "websocket.disconnect":
                        raise WebSocketDisconnect()
                    else:
                        print(f"Client {user.user_id} sent message: {message}")

                if servicebus_task in done:
                    messages = await servicebus_task
                    for m in messages:
                        body = b"".join(m.body).decode("utf-8")
                        await websocket.send_text(body)
                        await receiver.complete_message(m)

                # Cancel whichever didn’t finish
                for task in pending:
                    task.cancel()
                    try:
                        await task
                    except asyncio.CancelledError:
                        pass

        except WebSocketDisconnect:
            print(f"Client {user.user_id} disconnected")
            manager.disconnect(websocket)
