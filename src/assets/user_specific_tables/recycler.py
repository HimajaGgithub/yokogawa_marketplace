#recycler_with_yield.py
import importlib
from pathlib import Path
from peewee import (
    Model, AutoField, CharField, IntegerField, FloatField, DatabaseProxy, SqliteDatabase
)
from src.properties.market_prices import market_prices, unit_quantity
# -----------------------------
# DB proxy base
# -----------------------------
db_proxy = DatabaseProxy()


class DBBaseModel(Model):
    class Meta:
        database = db_proxy


# -----------------------------
# SoHRecoveryProfile model
# -----------------------------
class SoHRecoveryProfile(DBBaseModel):
    id = AutoField()
    recycler_name = CharField(max_length=100)
    battery_type = CharField(max_length=50)
    SoH = IntegerField()  # 50 → 100
    material = CharField(max_length=50)
    purity = FloatField()  # %
    quantity = FloatField()  # tons recovered per ton waste


# -----------------------------
# New calculation-based tables
# -----------------------------
class ThermalProfile(DBBaseModel):
    id = AutoField()
    recycler_name = CharField()
    battery_type = CharField()
    material = CharField()
    SoH = IntegerField()
    estimated_heat_kwh = FloatField()
    energy_consumption_kwh_per_ton = FloatField()
    optimal_temp_c = FloatField()


class YieldLoss(DBBaseModel):
    id = AutoField()
    recycler_name = CharField()
    battery_type = CharField()
    material = CharField()
    SoH = IntegerField()
    expected_quantity = FloatField()
    recovered_quantity = FloatField()
    loss_quantity = FloatField()


class MaterialCostEstimate(DBBaseModel):
    id = AutoField()
    recycler_name = CharField()
    material = CharField()
    unit_cost_usd = FloatField()
    energy_cost_usd = FloatField()
    processing_cost_usd = FloatField()
    total_cost_usd = FloatField()


class RecyclerEfficiency(DBBaseModel):
    id = AutoField()
    recycler_name = CharField()
    battery_type = CharField()
    total_input = FloatField()
    total_recovered = FloatField()
    efficiency_percent = FloatField()


class EnvironmentalImpact(DBBaseModel):
    id = AutoField()
    recycler_name = CharField()
    material = CharField()
    quantity = FloatField()
    co2_kg = FloatField()
    energy_kwh = FloatField()


class ProcessingTimeEstimate(DBBaseModel):
    id = AutoField()
    recycler_name = CharField()
    battery_type = CharField()
    material = CharField()
    SoH = IntegerField()
    estimated_hours = FloatField()


# -----------------------------
# Configuration extraction utilities
# -----------------------------
# def extract_materials_from_config(config_data):
#     """Extract materials and their associated battery types from config"""
#     materials_info = {}
    
#     for config_item in config_data:
#         if config_item.get("key") == "unit_quantity":
#             unit_quantity = config_item.get("value", {})
#             for material, battery_configs in unit_quantity.items():
#                 materials_info[material] = {}
#                 for battery_type, config_details in battery_configs.items():
#                     materials_info[material][battery_type] = {
#                         "waste_battery_type": config_details[0],
#                         "quantity_needed": config_details[1],
#                         "units": config_details[2],
#                         "quality": config_details[3],
#                         "category": config_details[4]
#                     }
    
#     return materials_info


# def extract_cost_info_from_config(config_data):
#     """Extract cost information from config"""
#     cost_info = {}
    
#     for config_item in config_data:
#         if config_item.get("key") == "selling_prices":
#             selling_prices = config_item.get("value", {})
#             for material, price_range in selling_prices.items():
#                 cost_info[material] = {
#                     "min_price": price_range[0],
#                     "max_price": price_range[1],
#                     "avg_price": (price_range[0] + price_range[1]) / 2
#                 }
#         elif config_item.get("key") == "processing_cost_percentage":
#             processing_cost_pct = config_item.get("value", 60)
#             cost_info["processing_cost_percentage"] = processing_cost_pct
    
#     return cost_info


def extract_production_info_from_config(config_data):
    """Extract daily production information from config"""
    production_info = {}
    
    for config_item in config_data:
        if config_item.get("key") == "daily_production":
            daily_production = config_item.get("value", {})
            for material, production_data in daily_production.items():
                production_info[material] = {
                    "quantity": production_data[0],
                    "units": production_data[1]
                }
    
    return production_info


def parse_SoH_from_quality(quality_str):
    """Extract SoH value from quality string like 'SoH 60'"""
    if isinstance(quality_str, str) and quality_str.startswith("SoH "):
        try:
            return int(quality_str.split(" ")[1])
        except (IndexError, ValueError):
            pass
    return None


# -----------------------------
# Dynamic calculation functions
# -----------------------------
def calc_purity_from_config(material, SoH, base_purity_map=None):
    """Calculate purity based on material and SoH, with optional base purity override"""
    if base_purity_map is None:
        base_purity_map = {
            "Lithium": 80, "Nickel": 75, "Manganese": 74, "Cobalt": 78,
            "Graphite": 70, "Iron": 77, "Titanium": 76, "Phosphate": 72
        }
    
    factor_map = {
        "Lithium": 0.20, "Nickel": 0.15, "Manganese": 0.17, "Cobalt": 0.18,
        "Graphite": 0.25, "Iron": 0.15, "Titanium": 0.16, "Phosphate": 0.18
    }
    
    bp = base_purity_map.get(material.lower(), 70)
    f = factor_map.get(material.lower(), 0.15)
    return round(bp - (100 - SoH) * f, 2)


def calc_quantity_from_config(material, SoH, production_info):
    """Calculate quantity based on material, SoH, and production info from config"""
    if material in production_info:
        daily_qty = production_info[material]["quantity"]
        # Scale based on SoH - higher SoH means better recovery
        scaled_qty = daily_qty * (SoH / 100.0) * 0.1  # Convert daily to per-ton waste
        return round(scaled_qty, 3)
    
    # Fallback to default calculation
    base_qty_map = {
        "Lithium": 0.25, "Nickel": 0.20, "Manganese": 0.15,
        "Cobalt": 0.18, "Graphite": 0.30, "Iron": 0.22, 
        "Titanium": 0.12, "Phosphate": 0.16
    }
    bq = base_qty_map.get(material.lower(), 0.1)
    return round(bq * (SoH / 100.0), 3)


def calc_thermal_profile_from_config(material, SoH, cost_info=None):
    """Calculate thermal profile with optional cost info consideration"""
    base_heat = SoH * 0.5
    
    # Adjust based on material properties
    material_heat_factor = {
        "Lithium": 1.2, "Cobalt": 1.5, "Nickel": 1.3, "Manganese": 1.0,
        "Iron": 0.8, "Phosphate": 0.9, "Graphite": 0.7
    }
    
    heat_factor = material_heat_factor.get(material.lower(), 1.0)
    heat = round(base_heat * heat_factor, 2)
    energy = round(heat * 0.2, 2)
    temp = 300 + (SoH / 2) + (heat_factor * 10)
    
    return heat, energy, temp


def calc_material_cost_from_config(material, cost_info):
    """Calculate material cost based on config information"""
    if material in cost_info:
        avg_selling_price = cost_info[material]["avg_price"]
        processing_cost_pct = cost_info.get("processing_cost_percentage", 60) / 100
        
        # Estimate costs as percentage of selling price
        unit_cost = avg_selling_price * 0.4  # 40% of selling price
        processing_cost = avg_selling_price * processing_cost_pct
        energy_cost = avg_selling_price * 0.05  # 5% of selling price
        total_cost = unit_cost + processing_cost + energy_cost
        
        return unit_cost, energy_cost, processing_cost, total_cost
    
    # Fallback values
    return 1000, 50, 200, 1250


def calc_processing_time_from_config(material, SoH, materials_info):
    """Calculate processing time based on material complexity and SoH"""
    base_time_map = {
        "Lithium": 5, "Nickel": 4, "Manganese": 3.5, "Cobalt": 4.5,
        "Graphite": 2.5, "Iron": 3, "Titanium": 4, "Phosphate": 3.2
    }
    
    # Check if material has complex processing requirements
    complexity_factor = 1.0
    if material in materials_info:
        battery_types = list(materials_info[material].keys())
        if len(battery_types) > 1:  # Multiple battery types = more complex
            complexity_factor = 1.2
    
    base_time = base_time_map.get(material.lower(), 3)
    processing_time = base_time * complexity_factor * (100 / SoH)
    return round(processing_time, 2)


def calc_environmental_impact_from_config(material, quantity, production_info=None):
    """Calculate environmental impact with production scale consideration"""
    co2_factor_map = {
        "Lithium": 15, "Nickel": 20, "Manganese": 18, "Cobalt": 22,
        "Graphite": 12, "Iron": 10, "Titanium": 14, "Phosphate": 13
    }
    energy_factor_map = {
        "Lithium": 5, "Nickel": 6, "Manganese": 5.5, "Cobalt": 7,
        "Graphite": 4, "Iron": 3, "Titanium": 4.5, "Phosphate": 4.2
    }
    
    # Scale factors based on production efficiency
    scale_factor = 1.0
    if production_info and material in production_info:
        daily_qty = production_info[material]["quantity"]
        if daily_qty > 2.0:  # Higher production = better efficiency
            scale_factor = 0.9
    
    co2 = co2_factor_map.get(material.lower(), 10) * quantity * scale_factor
    energy = energy_factor_map.get(material.lower(), 5) * quantity * scale_factor
    return co2, energy


# -----------------------------
# Main seeding function
# -----------------------------
def seed_recycler_db(db_file: Path, module_name):
    """Seed a recycler DB with SoHRecoveryProfile + extended calculation tables"""
    print(f"\nExtending {db_file.name}...")
    
    
    # Extract configuration data
    config_data = getattr(module_name, "config", [])
    user_profile = getattr(module_name, "user_profile", {})
    
    if not config_data:
        print(f"⚠️ No config data found for {module_name}, skipping")
        return
    
    # Extract information from config
    materials_info = extract_materials_from_config(config_data)
    cost_info = extract_cost_info_from_config(config_data)
    production_info = extract_production_info_from_config(config_data)
    
    if not materials_info:
        print(f"⚠️ No materials found in config for {module_name}, skipping")
        return
    
    recycler_name = user_profile.get("biz_name", module_name)
    
    # Initialize database
    db = SqliteDatabase(db_file)
    db_proxy.initialize(db)
    
    with db:
        # Create all tables
        db.create_tables([
            SoHRecoveryProfile,
            ThermalProfile,
            YieldLoss,
            MaterialCostEstimate,
            RecyclerEfficiency,
            EnvironmentalImpact,
            ProcessingTimeEstimate
        ], safe=True)
        
        # Generate SoH values and collect data
        SoH_values = range(50, 101, 5)
        SoH_rows = []
        thermal_rows = []
        yield_rows = []
        processing_time_rows = []
        
        total_input_per_material = {}
        total_recovered_per_material = {}
        
        # Process each material and battery type combination
        for material, battery_configs in materials_info.items():
            total_input_per_material[material] = 0
            total_recovered_per_material[material] = 0
            
            for battery_type, config_details in battery_configs.items():
                # Determine SoH range from quality field
                quality = config_details.get("quality", "")
                base_SoH = parse_SoH_from_quality(quality)
                
                if base_SoH:
                    # Use SoH from config as base, generate range around it
                    SoH_range = range(max(50, base_SoH - 10), min(101, base_SoH + 15), 5)
                else:
                    SoH_range = SoH_values
                
                for SoH in SoH_range:
                    qty = calc_quantity_from_config(material, SoH, production_info)
                    pur = calc_purity_from_config(material, SoH)
                    
                    SoH_rows.append({
                        "recycler_name": recycler_name,
                        "battery_type": battery_type.upper(),
                        "SoH": SoH,
                        "material": material,
                        "purity": pur,
                        "quantity": qty
                    })
                    
                    total_input_per_material[material] += 1  # Simulate 1 ton input
                    total_recovered_per_material[material] += qty
                    
                    # Thermal profile
                    heat, energy, temp = calc_thermal_profile_from_config(material, SoH, cost_info)
                    thermal_rows.append({
                        "recycler_name": recycler_name,
                        "battery_type": battery_type.upper(),
                        "material": material,
                        "SoH": SoH,
                        "estimated_heat_kwh": heat,
                        "energy_consumption_kwh_per_ton": energy,
                        "optimal_temp_c": temp
                    })
                    
                    # Yield loss
                    expected_qty = qty * 1.05  # Assume 5% expected higher
                    yield_rows.append({
                        "recycler_name": recycler_name,
                        "battery_type": battery_type.upper(),
                        "material": material,
                        "SoH": SoH,
                        "expected_quantity": expected_qty,
                        "recovered_quantity": qty,
                        "loss_quantity": round(expected_qty - qty, 3)
                    })
                    
                    # Processing time
                    proc_time = calc_processing_time_from_config(material, SoH, materials_info)
                    processing_time_rows.append({
                        "recycler_name": recycler_name,
                        "battery_type": battery_type.upper(),
                        "material": material,
                        "SoH": SoH,
                        "estimated_hours": proc_time
                    })
        
        # Insert data
        if SoH_rows:
            SoHRecoveryProfile.insert_many(SoH_rows).execute()
            print(f"Inserted SoHRecoveryProfile rows: {len(SoH_rows)}")
        
        if thermal_rows:
            ThermalProfile.insert_many(thermal_rows).execute()
            print(f"Inserted ThermalProfile rows: {len(thermal_rows)}")
        
        if yield_rows:
            YieldLoss.insert_many(yield_rows).execute()
            print(f"Inserted YieldLoss rows: {len(yield_rows)}")
        
        if processing_time_rows:
            ProcessingTimeEstimate.insert_many(processing_time_rows).execute()
            print(f"Inserted ProcessingTimeEstimate rows: {len(processing_time_rows)}")
        
        # Material cost estimates
        cost_rows = []
        for material in materials_info.keys():
            unit_cost, energy_cost, processing_cost, total_cost = calc_material_cost_from_config(material, cost_info)
            cost_rows.append({
                "recycler_name": recycler_name,
                "material": material,
                "unit_cost_usd": unit_cost,
                "energy_cost_usd": energy_cost,
                "processing_cost_usd": processing_cost,
                "total_cost_usd": total_cost
            })
        
        if cost_rows:
            MaterialCostEstimate.insert_many(cost_rows).execute()
            print(f"Inserted MaterialCostEstimate rows: {len(cost_rows)}")
        
        # Recycler efficiency
        efficiency_rows = []
        battery_types_processed = set()
        for material, battery_configs in materials_info.items():
            for battery_type in battery_configs.keys():
                battery_types_processed.add(battery_type.upper())
        
        for battery_type in battery_types_processed:
            total_input = sum(total_input_per_material.values())
            total_recovered = sum(total_recovered_per_material.values())
            efficiency = round(total_recovered / total_input * 100, 2) if total_input else 0
            
            efficiency_rows.append({
                "recycler_name": recycler_name,
                "battery_type": battery_type,
                "total_input": total_input,
                "total_recovered": total_recovered,
                "efficiency_percent": efficiency
            })
        
        if efficiency_rows:
            RecyclerEfficiency.insert_many(efficiency_rows).execute()
            print(f"Inserted RecyclerEfficiency rows: {len(efficiency_rows)}")
        
        # Environmental impact
        env_rows = []
        for material in materials_info.keys():
            qty = total_recovered_per_material[material]
            co2, energy = calc_environmental_impact_from_config(material, qty, production_info)
            env_rows.append({
                "recycler_name": recycler_name,
                "material": material,
                "quantity": qty,
                "co2_kg": co2,
                "energy_kwh": energy
            })
        
        if env_rows:
            EnvironmentalImpact.insert_many(env_rows).execute()
            print(f"Inserted EnvironmentalImpact rows: {len(env_rows)}")
    


def load(db,config):

    db_proxy.initialize(db)
    with db:
        # Create all tables
        tables = [
            SoHRecoveryProfile,
            ThermalProfile,
            YieldLoss,
            MaterialCostEstimate,
            RecyclerEfficiency,
            EnvironmentalImpact,
            ProcessingTimeEstimate
        ]
        db.drop_tables(tables)
        db.create_tables(tables, safe=True)