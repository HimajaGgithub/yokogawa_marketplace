import importlib
from pathlib import Path
from peewee import (
    Model, AutoField, CharField, IntegerField, FloatField, DatabaseProxy, SqliteDatabase
)

# -----------------------------
# DB proxy base
# -----------------------------
db_proxy = DatabaseProxy()


class DBBaseModel(Model):
    class Meta:
        database = db_proxy


# -----------------------------
# Fleet Usage / Battery Models
# -----------------------------
class FleetBatteryDegradation(DBBaseModel):
    id = AutoField()
    fleet_name = CharField()
    battery_type = CharField()
    age_years = IntegerField()
    SoH = FloatField()  # Remaining State of Health (%)


class FleetEnergyUsage(DBBaseModel):
    id = AutoField()
    fleet_name = CharField()
    daily_distance_km = FloatField()
    energy_per_km_kwh = FloatField()
    total_daily_energy_kwh = FloatField()


class BatteryRetirement(DBBaseModel):
    id = AutoField()
    fleet_name = CharField()
    battery_type = CharField()
    SoH = FloatField()
    retired_units = IntegerField()  # No. of batteries retired at this SoH


class WasteBatterySupply(DBBaseModel):
    id = AutoField()
    fleet_name = CharField()
    battery_type = CharField()
    SoH = FloatField()
    available_tons = FloatField()


class FleetOperationalCost(DBBaseModel):
    id = AutoField()
    fleet_name = CharField()
    energy_cost_usd = FloatField()
    maintenance_cost_usd = FloatField()
    total_cost_usd = FloatField()


class FleetEfficiency(DBBaseModel):
    id = AutoField()
    fleet_name = CharField()
    battery_type = CharField()
    km_travelled = FloatField()
    energy_used_kwh = FloatField()
    efficiency_kwh_per_km = FloatField()


class FleetEnvironmentalImpact(DBBaseModel):
    id = AutoField()
    fleet_name = CharField()
    co2_saved_kg = FloatField()
    recycled_batteries_tons = FloatField()


# -----------------------------
# Calculation Utilities
# -----------------------------
def calc_degradation(age_years: int, base_SoH=100) -> float:
    return round(base_SoH - (age_years * 5), 2)  # assume 5% loss per year


def calc_daily_energy(distance_km: float, per_km_kwh: float):
    return round(distance_km * per_km_kwh, 2)


def calc_retirement(SoH: float, total_units: int):
    if SoH < 70:  # retirement threshold
        return int(total_units * 0.1)  # 10% retired
    return 0


def calc_operational_cost(energy_kwh: float, cost_per_kwh=0.1, maintenance=50):
    return round(energy_kwh * cost_per_kwh + maintenance, 2)


def calc_efficiency(km: float, energy: float):
    return round(energy / km, 3) if km else 0


def calc_env_impact(recycled_tons: float):
    co2_saved = recycled_tons * 200  # assume 200kg saved per ton recycled
    return co2_saved




def load(db,config):

    db_proxy.initialize(db)
    tables = [
            FleetBatteryDegradation,
            FleetEnergyUsage,
            BatteryRetirement,
            WasteBatterySupply,
            FleetOperationalCost,
            FleetEfficiency,
            FleetEnvironmentalImpact
        ]
    with db:
        db.drop_tables(tables)
        db.create_tables(tables)

        profile = getattr(config, "user_profile", None)
        if not profile:
            print(f"⚠️ Skipping {config}, no user_profile in {config}")
            return

        fleet_name = profile.get("biz_name", config)
        battery_types = profile.get("preferences", {}).keys()

        age_range = range(1, 11)  # simulate 10 years
        total_units = 1000

        # Degradation + Retirement + Waste Supply
        degradation_rows, retire_rows, waste_rows = [], [], []
        for age in age_range:
            for btype in battery_types:
                SoH = calc_degradation(age)
                degradation_rows.append({
                    "fleet_name": fleet_name,
                    "battery_type": btype,
                    "age_years": age,
                    "SoH": SoH
                })
                retired = calc_retirement(SoH, total_units)
                retire_rows.append({
                    "fleet_name": fleet_name,
                    "battery_type": btype,
                    "SoH": SoH,
                    "retired_units": retired
                })
                waste_rows.append({
                    "fleet_name": fleet_name,
                    "battery_type": btype,
                    "SoH": SoH,
                    "available_tons": retired * 0.5  # assume 0.5 ton per retired unit
                })

        FleetBatteryDegradation.insert_many(degradation_rows).execute()
        BatteryRetirement.insert_many(retire_rows).execute()
        WasteBatterySupply.insert_many(waste_rows).execute()

        # Energy Usage + Costs (simulate 20 days per battery type)
        energy_rows, cost_rows, eff_rows, env_rows = [], [], [], []
        days = 20  # number of days to simulate

        for btype in battery_types:
            for day in range(1, days + 1):
                daily_km = 150 + (day * 5)  # vary daily distance
                per_km_kwh = 0.15 + (day * 0.002)  # vary consumption slightly
                total_energy = calc_daily_energy(daily_km, per_km_kwh)

                # Energy usage
                energy_rows.append({
                    "fleet_name": fleet_name,
                    "daily_distance_km": daily_km,
                    "energy_per_km_kwh": per_km_kwh,
                    "total_daily_energy_kwh": total_energy
                })

                # Costs
                total_cost = calc_operational_cost(total_energy)
                cost_rows.append({
                    "fleet_name": fleet_name,
                    "energy_cost_usd": total_energy * 0.1,
                    "maintenance_cost_usd": 50 + (day % 5) * 10,  # vary maintenance
                    "total_cost_usd": total_cost
                })

                # Efficiency
                eff_rows.append({
                    "fleet_name": fleet_name,
                    "battery_type": btype,
                    "km_travelled": daily_km,
                    "energy_used_kwh": total_energy,
                    "efficiency_kwh_per_km": calc_efficiency(daily_km, total_energy)
                })

                # Environmental impact
                recycled_tons = 5 + (day % 3)  # vary between 5-7 tons
                env_rows.append({
                    "fleet_name": fleet_name,
                    "co2_saved_kg": calc_env_impact(recycled_tons),
                    "recycled_batteries_tons": recycled_tons
                })

        FleetEnergyUsage.insert_many(energy_rows).execute()
        FleetOperationalCost.insert_many(cost_rows).execute()
        FleetEfficiency.insert_many(eff_rows).execute()
        FleetEnvironmentalImpact.insert_many(env_rows).execute()

