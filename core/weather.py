import numpy as np
from datetime import date, timedelta
from .http import fetch_json

ENS = "https://ensemble-api.open-meteo.com/v1/ensemble"
ARCHIVE = "https://archive-api.open-meteo.com/v1/archive"
FORECAST = "https://api.open-meteo.com/v1/forecast"


def ensemble_daily(lat, lon, days=10, model="ecmwf_ifs025"):
    """Per-member daily rain (mm) and Tmax (C). Members = probabilistic forecast."""
    res = fetch_json("open-meteo-ensemble", ENS, {
        "latitude": lat, "longitude": lon, "hourly": "precipitation,temperature_2m",
        "models": model, "forecast_days": days, "timezone": "auto"}, ttl=1800)
    if not res.ok:
        return res
    h = res.data["hourly"]
    dates = [t[:10] for t in h["time"]]
    udates = list(dict.fromkeys(dates))
    idx = {d: [i for i, x in enumerate(dates) if x == d] for d in udates}
    pk = [k for k in h if k.startswith("precipitation")]
    tk = [k for k in h if k.startswith("temperature_2m")]
    if not pk or not tk:
        res.ok, res.error = False, "ensemble response missing members"
        return res
    rain = np.array([[np.nansum(np.array(h[k], dtype=float)[idx[d]]) for d in udates] for k in pk])
    tmax = np.array([[np.nanmax(np.array(h[k], dtype=float)[idx[d]]) for d in udates] for k in tk])
    res.data = {"dates": udates, "rain_mm": rain.round(1).tolist(), "tmax_c": tmax.round(1).tolist(),
                "n_members": len(pk), "model": model}
    return res


def rain_climatology(lat, lon, window_days=10, years=10):
    """Mean rainfall for the same calendar window over past years (ERA5 via Open-Meteo)."""
    end = date.today() - timedelta(days=5)
    start = date(end.year - years, 1, 1)
    res = fetch_json("open-meteo-archive", ARCHIVE, {
        "latitude": lat, "longitude": lon, "start_date": start.isoformat(), "end_date": end.isoformat(),
        "daily": "precipitation_sum", "timezone": "auto"}, ttl=86400)
    if not res.ok:
        return res
    d = res.data["daily"]
    today = date.today()
    totals = []
    for y in range(start.year, end.year):
        a = date(y, today.month, min(today.day, 28))
        s = sum((p or 0) for t, p in zip(d["time"], d["precipitation_sum"])
                if a <= date.fromisoformat(t) < a + timedelta(days=window_days))
        totals.append(s)
    res.data = {"window_days": window_days, "mean_mm": round(float(np.mean(totals)), 1),
                "p90_mm": round(float(np.percentile(totals, 90)), 1), "years": len(totals)}
    return res


def forecast_basic(lat, lon, days=7):
    """Deterministic daily + hourly forecast: ET0, min/max temperature, wind, rain probability."""
    return fetch_json("open-meteo-forecast", FORECAST, {
        "latitude": lat, "longitude": lon, "forecast_days": days, "timezone": "auto",
        "daily": "et0_fao_evapotranspiration,temperature_2m_max,temperature_2m_min,precipitation_sum",
        "hourly": "precipitation,precipitation_probability,wind_speed_10m,temperature_2m"}, ttl=1800)
