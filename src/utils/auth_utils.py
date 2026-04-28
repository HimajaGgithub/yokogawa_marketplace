import datetime
import fnmatch
import os
import uuid
from datetime import timedelta
from hmac import compare_digest
from urllib.parse import urlparse

import jwt
from fastapi import HTTPException
from fastapi.security import HTTPBearer
from passlib.context import CryptContext
from starlette.datastructures import Headers, QueryParams

from src.entities.db_model import User, RevokedTokens
from src.properties.properties import protected_routes, exclude_routes, role_route_rules

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

if os.getenv("CORS_ALLOW_UI_URL"):
    DOMAIN = urlparse(os.getenv("CORS_ALLOW_UI_URL")).hostname
    print("USING DOMAIN", DOMAIN)
else:
    exit("DOMAIN not found in env.")

security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def is_protected(path: str) -> bool:
    if any(fnmatch.fnmatch(path, pattern) for pattern in protected_routes):
        if not any(fnmatch.fnmatch(path, pattern) for pattern in exclude_routes):
            return True
    return False


def is_authorized(role: str, path: str) -> bool:
    """Check if a user with a given role is authorized for a path."""
    rules = role_route_rules.get(role)
    if not rules:
        return False  # unknown role = no access

    if any(fnmatch.fnmatch(path, pattern) for pattern in rules["include"]):
        if not any(fnmatch.fnmatch(path, pattern) for pattern in rules["exclude"]):
            return True
    return False


def authenticate_request(cookies: dict, headers: Headers, query_params: QueryParams, path):
    """Authenticate using cookies + CSRF header. Works for HTTP and WebSockets."""
    token_str = cookies.get("access_token_cookie")
    if not token_str:
        raise HTTPException(status_code=401, detail="Access token cookie not found.")

    csrf_cookie = cookies.get("csrf_access_token", "")
    if not csrf_cookie:
        raise HTTPException(status_code=401, detail="CSRF token not found in cookies.")
    csrf = headers.get("X-CSRF-TOKEN") or query_params.get("csrf_token")
    if not csrf:
        raise HTTPException(status_code=401, detail="CSRF token found in neither header nor query params.")
    if not compare_digest(csrf_cookie, csrf):
        raise HTTPException(status_code=401, detail="CSRF Double Submit tokens do not match.")

    try:
        token = jwt.decode(token_str, SECRET_KEY, algorithms=[ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired.")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token.")

    if RevokedTokens.get_or_none(RevokedTokens.token == token_str):
        raise HTTPException(status_code=401, detail="Access token has been revoked.")

    if "sub" not in token:
        raise HTTPException(status_code=401, detail="Invalid jwt: sub missing.")
    if "role" not in token:
        raise HTTPException(status_code=401, detail="Invalid jwt: role missing.")

    if not is_authorized(token['role'], path):
        raise HTTPException(status_code=403, detail="Forbidden: Insufficient permissions.")

    user = User.get_or_none(User.user_id == token["sub"])
    if not user:
        raise HTTPException(
            status_code=401,
            detail=f"Invalid jwt: no user found with id {token['sub']}."
        )

    return user


def create_tokens(user: User):
    expire_time = datetime.datetime.now(datetime.UTC) + timedelta(days=30)
    csrf_token = str(uuid.uuid4())
    token_data = {"sub": str(user.user_id), "exp": expire_time, "csrf": csrf_token, "role": user.role}
    access_token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
    return access_token, csrf_token


def revoke_token(token):
    decoded = jwt.decode(token, SECRET_KEY, algorithms=ALGORITHM)
    exp = datetime.datetime.fromtimestamp(decoded['exp'])
    RevokedTokens.create(**{"token": token, "exp_timestamp": exp})


def set_cookies(request, response, access_token, csrf_token):
    host = request.headers.get("Origin")
    if host and ".com" in host:
        domain = urlparse(os.getenv("CORS_ALLOW_UI_URL")).hostname
    else:
        domain = urlparse(os.getenv("AGENT_BASE_URL")).hostname

    response.set_cookie(
        key="access_token_cookie", value=access_token, httponly=True,
        # Todo: secure must be set to True in production.
        secure=False,  # setting secure to False, allows the cookies to be available over http.
        samesite="lax",
        domain=domain
    )
    response.set_cookie(
        key="csrf_access_token", value=csrf_token, httponly=False,
        # Todo: secure must be set to True in production.
        secure=False,  # setting secure to False, allows the cookies to be available over http.
        # You can set it to true if using https.
        samesite="lax",
        domain=domain
    )
    return response


def unset_cookies(request, response):
    host = request.headers.get("Origin")
    if host and (".com" in host or "localhost" in host):
        domain = urlparse(os.getenv("CORS_ALLOW_UI_URL")).hostname
    else:
        domain = urlparse(os.getenv("AGENT_BASE_URL")).hostname
    response.set_cookie(key="access_token_cookie", value="", expires=0, httponly=True, secure=False, samesite="strict",
                        domain=domain)
    response.set_cookie(key="csrf_access_token", value="", expires=0, httponly=True, secure=False, samesite="strict",
                        domain=domain)
    return response


def extend_tokens(request, response):
    # Extend token life, so active tokens don't expire while being actively used.
    token = request.cookies.get("access_token_cookie", None)
    token = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    user = User.get_or_none(User.user_id == token["sub"])
    exp_timestamp = token['exp']
    now = datetime.datetime.now(datetime.UTC)
    target_timestamp = datetime.datetime.timestamp(now + timedelta(minutes=15))
    if target_timestamp > exp_timestamp:
        access_token, csrf_token = create_tokens(user)
        response = set_cookies(request, response, access_token, csrf_token)
    return response
