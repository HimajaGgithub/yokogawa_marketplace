from src.tests.config import recycler

from src.utils.fetch_utils import login, fetch

def set_mode(mode):
    data = {
        "mode": mode
    }
    fetch("/users/mode", data, "POST")

if __name__ == "__main__":
    with login(recycler):
        set_mode("dual")
