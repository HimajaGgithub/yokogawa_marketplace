import asyncio
import datetime
import importlib
import os
from pathlib import Path

import dotenv
from azure.core.exceptions import ResourceNotFoundError
from azure.servicebus.management import ServiceBusAdministrationClient

dotenv.load_dotenv()

import src.assets.agent_db as agent_db_module
import src.entities.db_model as market_db_module
from src.entities.common_schema import modes
from src.utils.auth_utils import pwd_context
from src.utils.service_bus_utils import get_entities, create_entities_for_user

conn = os.getenv('NAMESPACE_CONNECTION_STR')

dry_run = False


async def delete_service_bus_entities(market_db_path):
    try:
        servicebus_admin_client = ServiceBusAdministrationClient.from_connection_string(conn)
        market_db_module.init_db(market_db_path)
        users = market_db_module.User.select()
        for user in users:
            topic, human_sub, agent_sub = get_entities(user)

            # Delete human subscription if it exists
            try:
                servicebus_admin_client.get_subscription(topic, human_sub)
                if not dry_run:
                    servicebus_admin_client.delete_subscription(topic, human_sub)
                print("Deleted human subscription for user", user.user_id)
            except ResourceNotFoundError:
                print("Human subscription not found for user", user.user_id)

            # Delete agent subscription if it exists
            try:
                servicebus_admin_client.get_subscription(topic, agent_sub)
                if not dry_run:
                    servicebus_admin_client.delete_subscription(topic, agent_sub)
                servicebus_admin_client.delete_subscription(topic, agent_sub)
                print("Deleted agent subscription for user", user.user_id)
            except ResourceNotFoundError:
                print("Agent subscription not found for user", user.user_id)

            # Delete topic if it exists
            try:
                servicebus_admin_client.get_topic(topic)
                if not dry_run:
                    servicebus_admin_client.delete_topic(topic)
                print("Deleted topic for user", user.user_id)
            except ResourceNotFoundError:
                print("Topic not found for user", user.user_id)
    except Exception as e:
        print(f"Error deleting topic: {e}")


def get_config_modules(config_dir):
    for p in config_dir.iterdir():
        if p.stem.endswith("template") or p.stem.startswith("__"):
            continue
        config_module_path = f"src.assets.config.{p.stem}"
        config_module = importlib.import_module(config_module_path)
        yield config_module, config_module_path


async def create_users(config_dir):
    for config_module, config_module_path in get_config_modules(config_dir):
        user_profile = config_module.user_profile
        for material in user_profile['preferences']:
            for parameter, preferences in user_profile['preferences'][material].items():
                if isinstance(preferences, list):
                    assert all(isinstance(x, (float, int)) for x in preferences), "List preference must be a tuple"
                    assert len(preferences) == 2, "List Preference must be list of len==2, containing min, max values."
                else:
                    assert isinstance(preferences, str), "Preference must be list or string."
        user_profile['password'] = pwd_context.hash(user_profile['password'])
        user = market_db_module.User.create(**user_profile)
        print("User", user.biz_name, "created.")
        await create_entities_for_user(user)
        print("Created service-bus entities for user.")


async def create_admin():
    admin, created = market_db_module.User.get_or_create(biz_name="admin", defaults={
        "biz_name": "admin",
        "email_id": "admin@yokogawa.com",
        "biz_type": "admin",
        "location": "bengaluru",
        "password": pwd_context.hash("password"),
        "role": "admin",
    })
    await create_entities_for_user(admin)
    market_db_module.db_proxy.commit()
    print("Created admin user with id:", admin.user_id)


async def create_agents():
    market = market_db_module.User.create(**{
        "biz_name": "Marketplace Agent",
        "email_id": "market@yokogawa.com",
        "password": pwd_context.hash("password"),
        "location": "bengaluru",
        "biz_type": "",
        "purchase_history": [],
        "preferences": {},
        "role": "agent"
    })
    await create_entities_for_user(market)
    market_db_module.db_proxy.commit()
    print("Created market user with id:", market.user_id)


async def create_asset_dbs(asset_db_dir, config):
    config_module_path = f"src.assets.config.{config}"
    config_module = importlib.import_module(config_module_path)
    print(config_module.description)

    asset_db_path = asset_db_dir / f"{config_module_path.split('.')[-1]}.db"
    db = agent_db_module.init_db(asset_db_path)

    if config in ["fleet", "fleet_2"]:
        agent_db_module.Stock.create(**{
            "created_at": (datetime.datetime.now(datetime.UTC).date() - datetime.timedelta(days=5)).isoformat(),
            "material_code": "nmc_waste",
            "category": "waste battery",
            "quantity": 50_000_000,
            "units": "MWh",
            "material_quality": "SoH 70",
            "status": "available",
            "material_type": "surplus",
        })

        agent_db_module.Stock.create(**{
            "created_at": (datetime.datetime.now(datetime.UTC).date() - datetime.timedelta(days=5)).isoformat(),
            "material_code": "lfp_waste",
            "category": "waste battery",
            "quantity": 50_000_000,
            "units": "MWh",
            "material_quality": "SoH 70",
            "status": "available",
            "material_type": "surplus",
        })

    for entry in config_module.config:
        agent_db_module.Config.create(**entry)

    if "mode" in config_module.user_profile:
        agent_db_module.Config.create(**{
            "key": "permissions",
            "value": [x.value for x in modes[config_module.user_profile['mode']]]
        })

    specific_module_path = f"src.assets.user_specific_tables.{config.split('_')[0]}"
    try:
        specific_module = importlib.import_module(specific_module_path)
        specific_module.load(db, config_module)
    except ModuleNotFoundError:
        print("Warn: Could not find specific module:", specific_module_path)
        return

    db.close()


async def create_marketplace_db(marketplace_db_path, config_dir):
    market_db_module.init_db(marketplace_db_path)

    print("Tables created.")
    print("Creating admin user.")
    await create_admin()
    await create_agents()
    await create_users(config_dir)

    for p in Path("./src/scenario").iterdir():
        if p.stem.startswith("__"):
            continue
        scenario_module_path = f"src.scenario.{p.stem}"
        print("Running", scenario_module_path)
        scenario_module = importlib.import_module(scenario_module_path)
        market_db_module.Scenario.create(**{
            "scenario_name": scenario_module.scenario_name,
            "description": scenario_module.description,
            "tag": scenario_module.tag,
            "expected_outcome": scenario_module.expected_outcome,
            "participants": scenario_module.participants,
            "module": scenario_module_path
        })

    print("Scenarios created.")


async def main():
    x = input("This will delete all existing dbs and entities. \nProceed? (yes or no, default yes)\n> ")
    if x == "no":
        exit()

    market_db_path = Path("marketplace.db")
    asset_db_dir = Path(".")
    if asset_db_dir.exists():
        for x in asset_db_dir.iterdir():
            print(f"User {x.stem} assets db deleted.")
            if not dry_run:
                x.unlink()

    await delete_service_bus_entities(market_db_path)

    print("Deleting db file.")
    if not dry_run:
        market_db_module.db_proxy.close()
        market_db_path.unlink()

    x = input("Create new dbs, users and assets? (yes or no, default yes)\n> ")
    if x == "no":
        exit()

    print("Creating new db file...")
    user_configs_dir = Path("./src/assets/config")
    await create_marketplace_db(market_db_path, user_configs_dir)

    asset_db_dir.mkdir(exist_ok=True)

    users = [x.stem for x in user_configs_dir.iterdir() if not "__" in x.stem and not "template" in x.stem]
    for config in users:
        await create_asset_dbs(asset_db_dir, config)


# async def test():
#     asset_db_dir = Path(".")
#     user_configs_dir = Path("./src/assets/config")
#     users = [x.stem for x in user_configs_dir.iterdir() if not "__" in x.stem and not "template" in x.stem]
#     for config in users:
#         await create_asset_dbs(asset_db_dir, config)

if __name__ == "__main__":
    asyncio.run(main())
