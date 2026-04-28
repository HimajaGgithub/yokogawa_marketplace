from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=".env.marketplace")
from src.tests.config import admin
from src.utils.fetch_utils import login, fetch


def close_scenario(run_id):
    return fetch(f"/scenario/end?run_id={run_id}")


if __name__ == "__main__":
    last_run_id_file = Path("last_run_id.txt")
    if last_run_id_file.exists():
        run_id_str = last_run_id_file.read_text()
        with login(admin):
            if run_id_str:
                close_scenario(run_id_str)
