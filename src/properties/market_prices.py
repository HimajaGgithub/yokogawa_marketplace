from types import MappingProxyType

import numpy as np


def deep_freeze(obj):
    if isinstance(obj, dict):
        return MappingProxyType({k: deep_freeze(v) for k, v in obj.items()})
    elif isinstance(obj, list):
        return tuple(deep_freeze(v) for v in obj)
    else:
        return obj


market_prices = {
    "NMC": 115_000,
    "LCO": 400_000,
    "LTO": 600_000,
    "LFP": 360_000,
    "Cobalt": 25_000,
    "Lithium": 9000,
    "Iron": 1_400,
    "Graphite": 1_500,
    "Manganese": 800,
    "Nickel": 3_000,
    "Titanium": 14_000,
    "nmc_waste": 500,
    "lco_waste": 4000,
    "lto_waste": 6000,
    "lfp_waste": 3600,
    "truck": 4_00_000,
    "car": 8_00_000,
}

unit_quantity = {
    "NMC": {
        "Cobalt": ["Cobalt", 0.022, "tons", "purity 80", "raw material"],
        # "Lithium": ["Lithium", 0.020, "tons", "purity 80", "raw material"],
        # "Manganese": ["Manganese", 0.18, "tons", "purity 80", "raw material"],
        # "Nickel": ["Nickel", 0.060, "tons", "purity 80", "raw material"],
        # "Graphite": ["Graphite", 0.11, "tons", "purity 80", "raw material"]
    },
    "LFP": {
        "Lithium": ["Lithium", 0.038, "tons", "purity 80", "raw material"],
        # "Iron": ["Iron", 0.18, "tons", "purity 80", "raw material"],
        # "Graphite": ["Graphite", 0.11, "tons", "purity 80", "raw material"],
    },
    "LCO": {
        # "Lithium": ["Lithium", 0.071, "tons", "purity 80", "raw material"],
        "Cobalt": ["Cobalt", 0.6, "tons", "purity 80", "raw material"],
        # "Graphite": ["Graphite", 0.11, "tons", "purity 80", "raw material"],
    },
    "LTO": {
        # "Lithium": ["Lithium", 0.041, "tons", "purity 80", "raw material"],
        "Titanium": ["Titanium", 0.47, "tons", "purity 80", "raw material"],
        # "Graphite": ["Graphite", 0.08, "tons", "purity 80", "raw material"],
    },
    "Cobalt": {
        "nmc_waste": ["nmc_waste", 1.06, "MWh", "SoH 70", "waste battery"],
    },
    "Lithium": {
        "lfp_waste": ["lfp_waste", 1.06, "MWh", "SoH 70", "waste battery"],
    },
    "nmc_waste": {
        "nmc_waste": ["nmc_waste", 1, "MWh", "SoH 70", "waste battery"],
    },
    "lfp_waste": {
        "lfp_waste": ["lfp_waste", 1, "MWh", "SoH 70", "waste battery"],
    },
    "truck": {
        "NMC": ["NMC", 1.25, "MWh", "SoH 94", "new battery"],
    },
    "car": {
        "LFP": ["LFP", 1.25, "MWh", "SoH 94", "new battery"],
    }
}

unit_quantity = deep_freeze(unit_quantity)

battery_types = ["NMC", "LFP", "LCO", "LTO"]


material_yield = {
    "Cobalt": 0.94,
    "Lithium": 0.94,
}

stock_buffer = {
    "Cobalt": 1.25,
    "Lithium": 1.25,
    "nmc_waste": 1.25
}
