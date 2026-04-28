import os
from urllib.parse import urlparse

protected_routes = [
    "/users*",
    "/listing/*",
    "/marketplace/*",
    "/home/*",
    "/auction/*",
    "/notifications*",
    "/scenario/*",
    "/logistics/*",
    "/agent/*",
]

exclude_routes = [
    "/users/login",
    "/users/logout",
    "/users/register",
    "/home/public/*",
]

role_route_rules = {
    "admin": {
        "include": ["*"],
        "exclude": []
    },
    "user": {
        "include": ["*"],
        "exclude": ["/scenario/*"]
    },
}

# TODO: switch this based on the env['DOMAIN']

if os.getenv("env", "local") == "local":
    user_email_url_map = {
        "exide@manufacturer.com": f"http://localhost:8001",
        "greentech@recycler.com": f"http://localhost:8002",
        "eco@recycler.com": f"http://localhost:8003",
        "aether@fleet.com": f"http://localhost:8004",
        "sun@manufacturer.com": f"http://localhost:8005",
        "mercedes@oem.com": f"http://localhost:8006",
        "ola@fleet.com": f"http://localhost:8007",
        "volvo@oem.com": f"http://localhost:8008",
        "recycler@yokogawa.com": f"http://localhost:8009",
    }
else:
    user_email_url_map = {
        "exide@manufacturer.com": os.getenv("pod_path_manufacturer"),
        "greentech@recycler.com": os.getenv("pod_path_recycler"),
        "eco@recycler.com": os.getenv("pod_path_recycler_2"),
        "aether@fleet.com": os.getenv("pod_path_fleet"),
        "sun@manufacturer.com": os.getenv("pod_path_manufacturer_2"),
        "mercedes@oem.com": os.getenv("pod_path_oem"),
        "ola@fleet.com": os.getenv("pod_path_fleet_2"),
        "volvo@oem.com": os.getenv("pod_path_oem_2"),
        "recycler@yokogawa.com": os.getenv("pod_path_market")
    }
