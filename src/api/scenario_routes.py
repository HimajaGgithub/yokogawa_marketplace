from typing import Optional

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse

from src.entities.schema import ScenarioIdRequest
from src.services.scenario_service import get_scenario_types, get_scenario, run_scenario, \
    stream_messages, cleanup

scenario_router = APIRouter(prefix="/scenario", tags=["Scenario"])


@scenario_router.get("/types")
async def get_scenario_types_api():
    result = await get_scenario_types()
    return result


@scenario_router.get("")
async def get_scenario_api(scenario_id: str | None = None):
    result = await get_scenario(scenario_id)
    return result


@scenario_router.post("/run")
async def run_scenario_api(request: ScenarioIdRequest):
    result = await run_scenario(request)
    return result


@scenario_router.get("/live")
async def run_scenario_api(request: Request, run_id: str):
    return StreamingResponse(stream_messages(request, run_id), media_type="application/x-ndjson")

@scenario_router.get("/end")
async def cleanup_api(request: Request, run_id: str):
    result = await cleanup(request, run_id)
    return result

