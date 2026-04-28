import contextvars
import json
import os
from contextlib import contextmanager
from typing import Optional
from urllib.parse import urlparse
import requests

base_url = os.getenv('AGENT_BASE_URL')
password = os.getenv("PASSWORD", "password")

# Context variable for active session
current_session: contextvars.ContextVar[requests.Session] = contextvars.ContextVar("current_session")
run_id: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("run_id", default=None)


def _get_session():
    """Get the session from the current context or raise."""
    try:
        session = current_session.get()
        return session
    except LookupError:
        raise RuntimeError("No active user session. Use `with user(email): ...` or `run()`.")


def _user_login(_session, email_id):
    payload = {
        "email_id": email_id,
        "password": password
    }
    url = urlparse(os.getenv("AGENT_BASE_URL"))
    response = _session.post(base_url + "/users/login", json=payload, headers={
        "Origin": f"{url.scheme}://{url.netloc}"
    })
    # print("Login response status", response.status_code)
    if response.ok:
        jar = _session.cookies.get_dict()
        _session.headers.update({"X-CSRF-TOKEN": jar.get("csrf_access_token")})
        _session.headers.update({
            "Cookie": f"access_token_cookie={jar.get('access_token_cookie')}; "
                      f"csrf_access_token={jar.get('csrf_access_token')}"
        })
        _run_id = run_id.get()
        if _run_id:
            _session.headers.update({"x-run-id": _run_id})
        # print(json.dumps(response.json(), indent=4))
    else:
        print("Failed to login.")


def _logout():
    _session = _get_session()
    response = _session.post(base_url + "/users/logout")
    # _print_response("POST", "/users/logout", response)


def _print_response(method, endpoint, response):
    print(method.upper(), endpoint, ":")
    print(response.status_code, json.dumps(response.json(), indent=4))


@contextmanager
def login(email: str):
    """Login once, reuse session, logout on exit."""
    session = requests.Session()
    _user_login(session, email)
    print(f"\n--- Running as user: {email} ---")
    token = current_session.set(session)  # store in context
    try:
        yield
    finally:
        try:
            _logout()
        finally:
            current_session.reset(token)


def fetch(endpoint, payload=None, method="GET", print_response=True, get_response_code=False):
    """Make API calls using the current active session."""
    session = _get_session()
    additional_headers = {}
    if run_id.get():
        additional_headers = {"x-run-id": run_id.get()}
    url = base_url + endpoint
    if method.upper() == "POST":
        response = session.post(url, json=payload, headers=additional_headers)
    elif method.upper() == "PUT":
        response = session.put(url, json=payload, headers=additional_headers)
    else:
        response = session.get(url, headers=additional_headers)
    if print_response:
        _print_response(method, endpoint, response)
    if get_response_code:
        return response.status_code, response.json()
    return response.json()


def run(email: str, action_func, *args, **kwargs):
    with login(email):
        return action_func(*args, **kwargs)
