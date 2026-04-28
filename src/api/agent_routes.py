from typing import Optional

from fastapi import APIRouter

from src.services.agent_service import decision_logs

agent_router = APIRouter(prefix="/agent", tags=["Agent"])


@agent_router.get("/decision_logs")
async def decision_logs_api(agent_name: Optional[str] = None, page_number: int = 0, page_size: int = 10):
    result = await decision_logs(agent_name, page_number, page_size)
    return result
