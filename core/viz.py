"""Turns raw results into small tables for charts. Pure functions, easy to test."""
from datetime import datetime
import numpy as np
import pandas as pd


def _label(d):
    try:
        return datetime.strptime(d, "%Y-%m-%d").strftime("%d %b")
    except ValueError:
        return d


def daily_table(ens, sens_mm):
    rain = np.array(ens["rain_mm"], dtype=float)
    tmax = np.array(ens["tmax_c"], dtype=float)
    p10, p90 = np.percentile(rain, [10, 90], axis=0)
    return pd.DataFrame({
        "day": [_label(d) for d in ens["dates"]],
        "rain_mean": rain.mean(axis=0).round(1), "rain_p10": p10.round(1), "rain_p90": p90.round(1),
        "p_damaging": (rain >= sens_mm).mean(axis=0).round(2),
        "tmax_mean": tmax.mean(axis=0).round(1), "tmax_p90": np.percentile(tmax, 90, axis=0).round(1)})


def harvest_table(plan, known):
    rows = []
    for o in plan["options"]:
        rows.append({"start_in_days": o["start_in_days"], "date": _label(o["date"]),
                     "p_rain": o["p_rain_on_drying_days"],
                     "loss_rs": o["expected_loss_rs"] if known else None,
                     "loss_pct": o["expected_loss_pct"], "best": o["start_in_days"] == plan["best"]["start_in_days"]})
    return pd.DataFrame(rows)


def hourly_table(fc, now_iso, hours=48):
    h = fc["hourly"]
    i0 = next((i for i, x in enumerate(h["time"]) if x >= now_iso), 0)
    sl = slice(i0, i0 + hours)
    return pd.DataFrame({"time": pd.to_datetime(h["time"][sl]),
                         "wind": [float(x or 0) for x in h["wind_speed_10m"][sl]],
                         "rain": [float(x or 0) for x in h["precipitation"][sl]]})


def et0_table(fc, days=7):
    d = fc["daily"]
    return pd.DataFrame({"day": [_label(x) for x in d["time"][:days]],
                         "et0": [float(x or 0) for x in d["et0_fao_evapotranspiration"][:days]],
                         "rain": [float(x or 0) for x in d["precipitation_sum"][:days]]})
