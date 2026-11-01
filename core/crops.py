"""Crop parameters. ASSUMPTIONS: these are agronomic heuristics, NOT live data.
Replace with values from ICAR or your state agricultural university and cite them in the deck.
Everything else in the system is driven by live APIs."""

IMD_HEAVY_RAIN_MM = 64.5   # IMD 'heavy rain' lower bound (mm per 24 h)
FROST_TMIN_C = 4           # air temperature at or below which ground frost becomes possible

CROPS = {
    "wheat":   {"agmarknet": "Wheat", "dry_days": 2, "rain_sens_mm": 5, "wet_loss": 0.10,
                "standing_daily": 0.005, "storm_loss": 0.15, "heat_tmax": 35, "kc": 1.15},
    "paddy":   {"agmarknet": "Paddy(Dhan)(Common)", "dry_days": 2, "rain_sens_mm": 10, "wet_loss": 0.08,
                "standing_daily": 0.004, "storm_loss": 0.20, "heat_tmax": 35, "kc": 1.20},
    "maize":   {"agmarknet": "Maize", "dry_days": 3, "rain_sens_mm": 10, "wet_loss": 0.12,
                "standing_daily": 0.003, "storm_loss": 0.10, "heat_tmax": 38, "kc": 1.20},
    "mustard": {"agmarknet": "Mustard", "dry_days": 2, "rain_sens_mm": 5, "wet_loss": 0.10,
                "standing_daily": 0.008, "storm_loss": 0.15, "heat_tmax": 32, "kc": 1.10},
}
