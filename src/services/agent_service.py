import requests
from starlette.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from src.entities.context import current_user
from src.properties.properties import user_email_url_map


async def decision_logs(agent_name, page_number, page_size):
    user = current_user.get()
    if user.email_id not in user_email_url_map:
        return JSONResponse(content="Could not find user in map. Please contact the devs.", status_code=400)
    url = user_email_url_map[user.email_id]
    params = {
        "page_number": page_number,
        "page_size": page_size
    }
    if agent_name:
        params['agent_name'] = agent_name
    res = await run_in_threadpool(requests.get, url + "/decision_logs", params=params)
    return res.json()
