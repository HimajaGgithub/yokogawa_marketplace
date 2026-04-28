import datetime
import importlib
from enum import Enum
from pathlib import Path

from peewee import (
    Model, CharField, DateTimeField, SQL, PrimaryKeyField, DatabaseProxy, FloatField, IntegerField
)
from playhouse.pool import PooledSqliteDatabase
from playhouse.sqlite_ext import JSONField


def check_value_in_constraint(field_name, values):
    return SQL(f"CHECK ({field_name} IN ({
    ",".join('"' + x + '"' for x in values)
    }))")


agent_db_proxy = DatabaseProxy()


class AgentDbModel(Model):
    class Meta:
        database = agent_db_proxy


class Config(AgentDbModel):
    key = CharField()
    value = JSONField()


class DecisionLogs(AgentDbModel):
    message_id = PrimaryKeyField()
    action = CharField()
    rationale = CharField()
    chain_of_thought = CharField()
    agent_name = CharField()
    tag = CharField()
    created_at = DateTimeField(default=lambda: datetime.datetime.now(datetime.UTC))


class Stock(AgentDbModel):
    created_at = DateTimeField(default=lambda: datetime.datetime.now(datetime.UTC))
    material_code = CharField()
    quantity = FloatField()
    units = CharField()
    # If status is available, and material_type is surplus,
    # then I can supply this material for anyone who asks.
    # Is status is reserved, then I have a particular order for this stock, so it is not
    # available for everyone.
    status = CharField(
        constraints=[
            check_value_in_constraint(
                "status",
                ["available", "reserved", "consumed", "expired"]
            )
        ]
    )

    # todo: reserve for a listing_id instead of reserve for an order id
    order_id = CharField(null=True)
    material_quality = CharField(null=True)
    category = CharField(null=True)

    run_id = CharField(null=True)
    # Material type will be raw-material, if I have to procure it

    # after processing, you will get finished-product for that order, and
    # you will get other entries which are surplus

    # surplus (available --> reserved)  (once there is an order which requires this)

    # Material type is finished-product if I'm supplying it
    # Material type is surplus if this material has been produced along with some other
    # order. Suppose, you have to produce Cobalt, and you are processing NMC battery.
    # Along with Cobalt, Nickel and Manganese produced will be surplus.
    # Surplus materials can be considered for satisfying other orders.

    material_type = CharField(
        constraints=[
            check_value_in_constraint(
                "material_type",
                ["raw-material", "finished-product", "surplus"]
            )
        ]
    )


# accepted -> processing -> ready -> delivered
# accepted -> procuring ----(once all waiting has become ready) ---> processing  ----> ready ----> delivered
#          | -> procuring dependency 1 ----(once accepted) ----> waiting --> ready
#          | -> procuring dependency 2 ----(once accepted) ----> waiting --> ready

class OrderStatus(str, Enum):
    accepted = 'accepted'
    procuring = 'procuring'
    waiting = 'waiting'
    processing = 'processing'
    ready = 'ready'
    delivered = 'delivered'
    expired = "expired"


class OrderType(str, Enum):
    procurement = "procurement"  # orders that I'm procuring for myself
    supply = 'supply'  # orders that I'm supplying for


_order_status = [x for x in OrderStatus]
_order_type = [x for x in OrderType]


class Calendar(AgentDbModel):
    listing_id = CharField(null=True)
    date = DateTimeField(default=lambda: datetime.datetime.now(datetime.UTC))
    status = CharField(default="occupied")
    run_id = CharField(null=True)


class Orders(AgentDbModel):
    order_id = PrimaryKeyField()
    listing_id = CharField(null=True)
    material_code = CharField()
    quantity = FloatField()
    selling_price = FloatField(null=True)
    parent_order_id = IntegerField(null=True)

    delivery_date = DateTimeField(null=True)
    accepted_date = DateTimeField(null=True)
    run_id = CharField()
    # budget = FloatField(null=True)  # target-price / procurement-budget
    # cost_price = FloatField(null=True)
    order_type = CharField(
        constraints=[
            check_value_in_constraint(
                "order_type",
                _order_type
            )
        ]
    )
    units = CharField()
    status = CharField(
        constraints=[
            check_value_in_constraint(
                "status",
                _order_status
            )
        ]
    )


tables = [Orders, Stock, Config, Calendar, DecisionLogs]


def init_db(db_path: Path):
    """Initialize the DB connection for a given path"""
    db = PooledSqliteDatabase(
        db_path,
        max_connections=8,  # adjust based on load
        stale_timeout=300,  # recycle idle connections after 5 minutes
        pragmas={
            "journal_mode": "wal",  # write-ahead log for concurrency
            "cache_size": -1024 * 64,  # 64MB page cache
            "foreign_keys": 1,
            "ignore_check_constraints": 0,
            "synchronous": 0,  # faster writes
        },
    )
    agent_db_proxy.initialize(db)
    db.connect()
    db.create_tables(tables)
    return db


TABLE_MAP = {
    "Orders": Orders,
    "Stock": Stock,
    "Config": Config,
    "Calendar": Calendar,
}

if __name__ == "__main__":
    db_dir = Path(".")

    for x in db_dir.iterdir():
        x.unlink()

    # create configs
    for p in Path("./src/assets/config").iterdir():
        if p.stem.endswith("template") or p.stem.startswith("__"):
            continue
        db_path = db_dir / f"{p.stem}.db"
        db = init_db(db_path)
        config_module_path = f"src.assets.config.{p.stem}"
        try:
            config_module = importlib.import_module(config_module_path)
            print(config_module.description)
            for entry in config_module.config:
                Config.create(**entry)
        except ModuleNotFoundError as e:
            print(e)
            print("Couldn't find config module", config_module_path)
