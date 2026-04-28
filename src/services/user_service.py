from textwrap import dedent
from uuid import UUID

import requests
from fastapi import Request
from fastapi.responses import JSONResponse
from playhouse.shortcuts import model_to_dict
from starlette.concurrency import run_in_threadpool

from src.entities.context import current_user
from src.entities.db_model import User
from src.entities.schema import UserCreate, UserLogin, ModeRequest
from src.prompts.listing_prompts import get_sample_prompts
from src.properties.properties import user_email_url_map
from src.utils.auth_utils import pwd_context, create_tokens, set_cookies, unset_cookies, revoke_token
from src.utils.service_bus_utils import create_entities_for_user

ACCESS_TOKEN_EXPIRE_MINUTES = 30


async def register(user_data: UserCreate):
    user_data.password = pwd_context.hash(user_data.password)
    user = User.create(**user_data.model_dump())
    await create_entities_for_user(user)
    return {
        "message": "User created successfully",
        "user_id": user.user_id,
        "email_id": user.email_id
    }


async def login(user_data: UserLogin, request: Request):
    user = User.get_or_none(User.email_id == user_data.email_id)
    if not user:
        return JSONResponse(status_code=401, content={"error": "Invalid user name."})

    if not pwd_context.verify(user_data.password, user.password):
        return JSONResponse(status_code=401, content={"error": "Invalid password."})

    content = {
        "message": "Login successful",
        "user": {
            **{
                k: str(v) if isinstance(v, UUID) else v
                for k, v in model_to_dict(user, exclude=[User.password]).items()
            }
        }
    }

    access_token, csrf_token = create_tokens(user)
    response_headers = {
        "X-CSRF-TOKEN": csrf_token
    }
    response = JSONResponse(content=content, headers=response_headers)
    response = set_cookies(request, response, access_token, csrf_token)
    return response


async def get_profile():
    user = current_user.get()
    response = model_to_dict(user, exclude=[User.password])
    return response

async def get_users():
    users = User.select().where(User.role.not_in(['admin', 'agent','virtual']))
    response = [model_to_dict(u, exclude=[User.password]) for u in users]
    return response

async def logout(request: Request):
    response = JSONResponse(content={"message": "Logout successful."})
    token = request.cookies.get("access_token_cookie", None)
    if token:
        revoke_token(token)
    response = unset_cookies(request, response)
    return response


async def get_listing_prompts():
    user = current_user.get()
    listing_prompts = get_sample_prompts()
    return [" ".join(dedent(x).split('\n')).strip() for x in listing_prompts[user.biz_type]]


async def set_mode(mode: ModeRequest):
    user = current_user.get()
    if user.email_id not in user_email_url_map:
        return JSONResponse(content="Could not find user in map. Please contact the devs.", status_code=400)
    url = user_email_url_map[user.email_id]
    res = await run_in_threadpool(requests.post, **{"url": url + "/mode", "json": mode.model_dump()})
    if res.ok:
        user.mode = mode.mode.value
        user.save()
    return res.json()
