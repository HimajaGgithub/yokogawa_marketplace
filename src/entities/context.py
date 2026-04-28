from contextvars import ContextVar
import uuid
from typing import Optional

from src.entities.db_model import User

current_user: ContextVar[User] = ContextVar("current_user")
run_id: ContextVar[str] = ContextVar("run_id", default=str(uuid.uuid4()))
agent_name: ContextVar[Optional[str]] = ContextVar("agent_name", default=None)
