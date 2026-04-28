import datetime
import uuid
from enum import Enum
from pathlib import Path

from peewee import (
    Model, CharField, FloatField, DatabaseProxy,
    DateTimeField, BooleanField,
    UUIDField, SqliteDatabase, PrimaryKeyField, SQL
)
from playhouse.sqlite_ext import JSONField

from src.entities.common_schema import MessageType
from src.entities.schema import UserType


def check_value_in_constraint(field_name, values):
    return SQL(f"CHECK ({field_name} IN ({
    ",".join('"' + x + '"' for x in values)
    }))")


db_proxy = DatabaseProxy()


class DBBaseModel(Model):
    class Meta:
        database = db_proxy


_user_roles = [x for x in UserType]


class User(DBBaseModel):
    user_id = UUIDField(primary_key=True, default=uuid.uuid4)
    biz_name = CharField()
    email_id = CharField(unique=True)
    password = CharField()
    location = CharField()
    biz_type = CharField()
    mode = CharField(default="auto")
    purchase_history = JSONField(default=list, null=True)
    daily_production = JSONField(default=dict, null=True)
    preferences = JSONField(default=dict, null=True)
    role = CharField(
        constraints=[check_value_in_constraint("role", _user_roles)]
    )


class Listing(DBBaseModel):
    listing_id = UUIDField(primary_key=True, default=uuid.uuid4)
    user_id = UUIDField()
    item_name = CharField()
    category = CharField()
    material_code = CharField()
    listing_type = CharField()
    quantity = FloatField()
    quantity_unit = CharField()
    matches = JSONField(default=dict, null=True)
    status = CharField()
    description = CharField(null=True)
    location = CharField(null=True)
    payload = JSONField(default=dict)
    offers = JSONField()
    transaction_summary = JSONField(default=dict, null=True)
    created_at = DateTimeField(default=lambda: datetime.datetime.now(datetime.UTC))
    last_modified_at = DateTimeField(default=lambda: datetime.datetime.now(datetime.UTC))

    def save(self, *args, **kwargs):
        self.last_modified_at = datetime.datetime.now(datetime.UTC)
        return super(Listing, self).save(*args, **kwargs)

_message_types = [x for x in MessageType]


class Scenario(DBBaseModel):
    scenario_id = UUIDField(primary_key=True, default=uuid.uuid4)
    scenario_name = CharField(unique=True)
    description = CharField()
    tag = CharField()
    expected_outcome = CharField()
    participants = JSONField(default=list)
    module = CharField()


class Runs(DBBaseModel):
    run_id = UUIDField(primary_key=True, default=uuid.uuid4)
    user_id = CharField()
    scenario_id = CharField()
    created_at = DateTimeField(default=lambda: datetime.datetime.now(datetime.UTC))


class Messages(DBBaseModel):
    message_id = PrimaryKeyField()
    run_id = CharField(null=True)
    listing_id = CharField()
    parent_listing_id = CharField(null=True)
    sender_id = CharField()
    receiver_id = CharField()
    timestamp = DateTimeField()
    message_type = CharField(
        constraints=[check_value_in_constraint("message_type", _message_types)]
    )
    payload = JSONField(default=dict)
    is_read = BooleanField(default=False)


class RevokedTokens(DBBaseModel):
    token = CharField(unique=True)
    exp_timestamp = DateTimeField()

    class Meta:
        indexes = (
            # This creates a non-unique index on the 'exp_timestamp' column.
            (('exp_timestamp',), False),
        )


tables = [User, Listing, RevokedTokens, Messages, Scenario, Runs]


def init_db(db_path: Path):
    """Initialize the DB connection for a given path"""
    db = SqliteDatabase(db_path)
    db_proxy.initialize(db)
    db.connect()
    db.create_tables(tables)
    return db
