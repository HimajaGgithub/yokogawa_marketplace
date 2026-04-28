import random
from peewee import (
    Model, AutoField, CharField, FloatField, IntegerField,
    DatabaseProxy, SqliteDatabase
)
from playhouse.sqlite_ext import JSONField
from pathlib import Path
import numpy as np
from src.properties.market_prices import unit_quantity, battery_types
# -----------------------------
# DB proxy base
# -----------------------------
db_proxy = DatabaseProxy()


class DBBaseModel(Model):
    class Meta:
        database = db_proxy


# -----------------------------
# TABLE DEFINITIONS (UPDATED)
# -----------------------------

# 1. Material Usage (no batch_id, no quantity, dynamic quality)
class MaterialUsage(DBBaseModel):
    id = AutoField()
    material_name = CharField()
    unit = CharField()
    category = CharField()
    quality = IntegerField()  # range 60–90


class Yield(DBBaseModel):
    battery_type= CharField()
    SoH = FloatField()
    per_material_usable_tons = JSONField()
    total_usable_tons = FloatField()


# 2. Equipment Maintenance (removed technician & battery_type, updated types)
class EquipmentMaintenance(DBBaseModel):
    id = AutoField()
    equipment_type = CharField()  # e.g. mixer, furnace, conveyor, dryer
    maintenance_type = CharField()  # e.g. preventive, corrective
    status = CharField()  # completed, pending, delay, waiting


# 3. Thermal Analysis (removed battery_type, added operational & categorical data)
class ThermalAnalysis(DBBaseModel):
    id = AutoField()
    temperature_c = FloatField()
    pressure_pa = FloatField()
    operational_condition = CharField()  # e.g. normal, overload, idle
    mode = CharField()  # categorical, e.g. test, production, standby


# 4. Environmental Impact (removed battery_type)
class EnvironmentalImpact(DBBaseModel):
    id = AutoField()
    emission_type = CharField()  # CO2, NOx, SOx
    emission_value = FloatField()
    unit = CharField()


# 5. Accessory Inventory (removed component_type, battery_type, supplier; quality A–D)
class AccessoryInventory(DBBaseModel):
    id = AutoField()
    accessory_name = CharField()
    stock_level = IntegerField()
    quality_grade = CharField()  # A, B, C, D




def generate_usable_materials_table_copy(config):
    """
    For the battery_type found in config (first key in unit_quantity),
    generate a table of usable raw-materials contained in 1 unit of battery
    across SoH from 100.0 down to 60.0 (step 0.5).

    Returns:
        - rows: list of dicts, one per SoH, with per-material usable tons and total usable tons
        - df (optional): pandas DataFrame (if pandas available), flattened with columns:
            ['battery_type','SoH','Cobalt','Lithium','Manganese','Nickel','total_usable_tons']
    """

    # db.create_tables([Yield], safe=True)

    # locate unit_quantity section

    # Choose battery_type robustly: first key in unit_quantity


    # Build SoH array 100.0 -> 60.0 step 0.5
    SoHs = np.arange(100.0, 59.9, -0.5)  # 100.0, 99.5, ..., 60.0
    specific_battery_type = list(set(battery_types) & set(config.user_profile["preferences"].keys()))[0]
    rows = []
    for SoH in SoHs:
        SoH_rounded = round(float(SoH), 1)
        per_material = {}
        total_usable = 0.0
        for material, quantity, unit, quality, category in unit_quantity[specific_battery_type].values():
            usable = quantity * (SoH_rounded / 100.0)   # Q_base * (SoH/100)
            usable_rounded = round(usable, 6)
            per_material[material] = usable_rounded
            total_usable += usable
        total_usable = round(total_usable, 6)

        row = {
            "battery_type": specific_battery_type,
            "SoH": SoH_rounded,
            "per_material_usable_tons": per_material,
            "total_usable_tons": total_usable
        }
        rows.append(row)
    #print(rows)
    # Insert all rows into the database at once
    # with db.atomic():
    #     Yield.insert_many(rows).execute()

    # # Close the database connection
    # db.close()

    return rows
# -----------------------------
# SIMULATION FUNCTION
# -----------------------------
def simulate_battery_production(config):
    
    specific_battery_type = list(set(battery_types) & set(config.user_profile["preferences"].keys()))[0]


    days = 60
    for day in range(1, days + 1):

        for material_name, (m_name, qty, unit, quality, category) in unit_quantity[specific_battery_type].items():
            # Insert into MaterialUsage
            MaterialUsage.create(
                material_name=m_name,
                unit=unit,
                category=category,
                quality=random.randint(60, 90)  # dynamic range
            )

        # Add random Equipment Maintenance logs
        EquipmentMaintenance.create(
            equipment_type=random.choice(["mixer", "furnace", "conveyor", "dryer"]),
            maintenance_type=random.choice(["preventive", "corrective"]),
            status=random.choice(["completed", "pending", "delay", "waiting"])
        )

        # Add random Thermal Analysis logs
        ThermalAnalysis.create(
            temperature_c=round(random.uniform(20, 80), 2),
            pressure_pa=round(random.uniform(100_000, 200_000), 2),
            operational_condition=random.choice(["normal", "overload", "idle"]),
            mode=random.choice(["test", "production", "standby"])
        )

        # Add random Environmental Impact logs
        EnvironmentalImpact.create(
            emission_type=random.choice(["CO2", "NOx", "SOx"]),
            emission_value=round(random.uniform(50, 200), 2),
            unit="kg"
        )

        # Add random Accessory Inventory logs
        AccessoryInventory.create(
            accessory_name=random.choice(["bolt", "nut", "wire", "connector"]),
            stock_level=random.randint(10, 500),
            quality_grade=random.choice(["A", "B", "C", "D"])
        )


def load(db, config):
    """Initialize the DB connection for a given path"""
    rows = generate_usable_materials_table_copy(config=config)
    db_proxy.initialize(db)
    tables = [Yield,MaterialUsage,
        EquipmentMaintenance,
        ThermalAnalysis,
        EnvironmentalImpact,
        AccessoryInventory]
    db.drop_tables(tables)
    db.create_tables(tables,safe=True)
    simulate_battery_production(config)
    #thermal_records = generate_thermal_data(config)
    with db.atomic():
        Yield.insert_many(rows).execute()


