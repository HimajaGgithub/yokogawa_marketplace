from src.tests.config import recycler, admin

from src.utils.fetch_utils import login, fetch

def get_all_users():
    fetch("/users", method="GET")

if __name__ == "__main__":
    with login(recycler):
        get_all_users()

    with login(admin):
        get_all_users() 