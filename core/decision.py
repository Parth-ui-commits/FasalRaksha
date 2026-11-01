"""Explainable decision engine. No LLM in the loop: numbers come from live
probabilistic forecasts + transparent cost formulas, the LLM only explains them."""
import numpy as np
from .crops import CROPS, IMD_HEAVY_RAIN_MM


def prob(x):
    return round(float(x), 2)


def weather_risk(ens: dict, crop: str, horizon=5):
    c = CROPS[crop]
    rain = np.array(ens["rain_mm"])[:, :horizon]
    tmax = np.array(ens["tmax_c"])[:, :horizon]
    return {"members": ens["n_members"], "horizon_days": horizon,
            "p_heavy_rain": prob((rain.max(axis=1) >= IMD_HEAVY_RAIN_MM).mean()),
            "p_damaging_rain": prob((rain.max(axis=1) >= c["rain_sens_mm"]).mean()),
            "p_heat_stress": prob((tmax.max(axis=1) >= c["heat_tmax"]).mean()),
            "expected_rain_mm": round(float(rain.sum(axis=1).mean()), 1),
            "rain_p90_mm": round(float(np.percentile(rain.sum(axis=1), 90)), 1)}


def plan_harvest(ens: dict, crop: str, yield_qtl: float, price_rs_qtl: float, drainage: str = "moderate"):
    """Pick the harvest start day (0 = today) minimising expected loss.
    cost(d) = P(wet during drying) * wet_loss + d * standing_daily + P(storm before d) * storm_loss"""
    c = CROPS[crop]
    rain = np.array(ens["rain_mm"])
    D, days = c["dry_days"], rain.shape[1]
    horizon = min(7, days - D)
    wet_loss = c["wet_loss"] * (1.25 if drainage == "poor" else 1.0)
    value = yield_qtl * price_rs_qtl
    opts = []
    for d in range(max(horizon, 1)):
        p_wet = (rain[:, d:d + D].max(axis=1) >= c["rain_sens_mm"]).mean()
        p_storm = (rain[:, :d].max(axis=1) >= IMD_HEAVY_RAIN_MM).mean() if d else 0.0
        frac = p_wet * wet_loss + d * c["standing_daily"] + p_storm * c["storm_loss"]
        opts.append({"start_in_days": d, "date": ens["dates"][d], "p_rain_on_drying_days": prob(p_wet),
                     "p_storm_before_start": prob(p_storm), "expected_loss_pct": round(frac * 100, 1),
                     "expected_loss_rs": int(round(frac * value))})
    best = min(opts, key=lambda o: o["expected_loss_rs"])
    now = opts[0]
    return {"best": best, "harvest_today": now,
            "saving_vs_today_rs": now["expected_loss_rs"] - best["expected_loss_rs"],
            "crop_value_rs": int(value), "options": opts,
            "assumptions": {"dry_days": D, "rain_sens_mm": c["rain_sens_mm"], "wet_loss": wet_loss,
                            "standing_daily": c["standing_daily"], "storm_loss": c["storm_loss"],
                            "note": "crop loss parameters are agronomic assumptions, editable in core/crops.py"}}
