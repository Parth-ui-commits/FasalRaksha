"""Builds everything a field dashboard needs in one parallel pass. No Streamlit here, so it can be tested."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from . import weather, flood, soil, mandi, decision, irrigation, spray, market_history
from .crops import CROPS
from .http import Result

SOIL_DRAINAGE = {"sandy": "fast", "loamy": "moderate", "clay_loam": "moderate", "clayey": "poor"}
SKIPPED = lambda src: Result(False, src, None, "skipped (overview mode)")  # noqa: E731


def build(lat, lon, state, crop, qty, price_override=0.0, soil_type="", light=False):
    with ThreadPoolExecutor(6) as ex:
        f_ens = ex.submit(weather.ensemble_daily, lat, lon)
        f_fc = ex.submit(weather.forecast_basic, lat, lon)
        f_fl = ex.submit(flood.river_risk, lat, lon)
        f_so = None if (light or soil_type in SOIL_DRAINAGE) else ex.submit(soil.soil_profile, lat, lon)
        f_cl = None if light else ex.submit(weather.rain_climatology, lat, lon)
        f_md = None if light else ex.submit(mandi.best_markets, lat, lon, state, CROPS[crop]["agmarknet"])
        ens, fc, river = f_ens.result(), f_fc.result(), f_fl.result()
        sol = f_so.result() if f_so else Result(False, "isric-soilgrids", None, "not needed" if soil_type in SOIL_DRAINAGE else "skipped (overview mode)")
        clim = f_cl.result() if f_cl else SKIPPED("open-meteo-archive")
        md = f_md.result() if f_md else SKIPPED("data.gov.in(Agmarknet)")

    price = float(price_override or 0)
    if not price and md.ok and md.data["options"]:
        price = float(md.data["options"][0]["modal_rs_qtl"])
    if soil_type in SOIL_DRAINAGE:
        drainage, drainage_source = SOIL_DRAINAGE[soil_type], "farmer"
    elif sol.ok:
        drainage, drainage_source = sol.data["drainage"], "satellite"
    else:
        drainage, drainage_source = "moderate", "assumed"

    risk = decision.weather_risk(ens.data, crop) if ens.ok else None
    plan = decision.plan_harvest(ens.data, crop, qty, price or 1.0, drainage) if ens.ok else None
    water = irrigation.water_balance(fc.data["daily"], ens.data, crop) if (ens.ok and fc.ok) else None

    now_local, windows = None, None
    if fc.ok:
        off = fc.data.get("utc_offset_seconds", 0)
        now_local = (datetime.now(timezone.utc) + timedelta(seconds=off)).strftime("%Y-%m-%dT%H:00")
        windows = spray.spray_windows(fc.data["hourly"], now_local)
    trend = None
    if not light:
        try:
            names = mandi.state_candidates(state)
            trend = market_history.trend(CROPS[crop]["agmarknet"], names)
        except Exception:  # noqa: BLE001
            trend = None
    return {"ens": ens, "fc": fc, "river": river, "soil": sol, "clim": clim, "mandi": md,
            "risk": risk, "plan": plan, "water": water, "spray": windows, "now_local": now_local,
            "price": price or None, "price_known": bool(price), "drainage": drainage,
            "drainage_source": drainage_source, "trend": trend,
            "fetched_at": ens.fetched_at or fc.fetched_at}
