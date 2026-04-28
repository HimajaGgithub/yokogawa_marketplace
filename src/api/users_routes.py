from fastapi import APIRouter, Request

from src.entities.schema import UserCreate, UserLogin, ModeRequest
from src.services.user_service import register, login, get_profile, logout, get_listing_prompts, set_mode, get_users

ACCESS_TOKEN_EXPIRE_MINUTES = 30

user_router = APIRouter(prefix="/users", tags=['Users'])


@user_router.post("/register", response_model=dict)
async def register_api(user_data: UserCreate):
    result = await register(user_data)
    return result


@user_router.post("/login", response_model=dict)
async def login_api(user_data: UserLogin, request: Request):
    result = await login(user_data, request)
    return result


@user_router.get("/profile", response_model=dict)
async def get_profile_api():
    result = await get_profile()
    return result

@user_router.get("", response_model=list)
async def get_users_api():
    result = await get_users()
    return result


@user_router.get("/listing-prompts")
async def get_listing_prompts_api():
    result = await get_listing_prompts()
    return result


@user_router.post("/logout", response_model=dict)
async def logout_api(request: Request):
    result = await logout(request)
    return result

@user_router.post("/mode", response_model=dict)
async def set_mode_api(mode: ModeRequest):
    result = await set_mode(mode)
    return result

# TODO: delete account, change password api
