from src.tests.config import manufacturer
from src.utils.fetch_utils import login, fetch


def get_agent_cards():
    return fetch(f"/agent/decision_logs")


def get_agent_logs(agent_name):
    return fetch(f"/agent/decision_logs?agent_name={agent_name}")


if __name__ == "__main__":
    with login(manufacturer):
        get_agent_cards()
        get_agent_logs("Order Processor Agent")
        get_agent_logs("Negotiator Agent")
        get_agent_logs("Bidder Agent")
