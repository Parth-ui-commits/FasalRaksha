import numpy as np
from .http import fetch_json

FLOOD = "https://flood-api.open-meteo.com/v1/flood"
PAST, FUT = 30, 7


def river_risk(lat, lon):
    """GloFAS river discharge. The grid is ~5 km, so a farm may not sit on a river cell:
    query a 3x3 neighbourhood and use the cell with the largest mean flow (the river)."""
    offs = [(dy * 0.05, dx * 0.05) for dy in (-1, 0, 1) for dx in (-1, 0, 1)]
    res = fetch_json("open-meteo-flood(GloFAS)", FLOOD, {
        "latitude": ",".join(f"{lat+a:.4f}" for a, _ in offs),
        "longitude": ",".join(f"{lon+b:.4f}" for _, b in offs),
        "daily": "river_discharge", "past_days": PAST, "forecast_days": FUT}, ttl=3600)
    if not res.ok:
        return res
    cells = res.data if isinstance(res.data, list) else [res.data]
    best = None
    for c in cells:
        q = np.array([x if x is not None else np.nan for x in c["daily"]["river_discharge"]], dtype=float)
        if np.isnan(q).all():
            continue
        m = np.nanmean(q[:PAST])
        if best is None or m > best[0]:
            best = (m, q, c)
    if best is None or best[0] < 1.0:
        res.data = {"river_nearby": False, "level": "none",
                    "note": "no significant river cell within ~5 km"}
        return res
    m, q, c = best
    past, fut = q[:PAST], q[PAST:]
    p90 = float(np.nanpercentile(past, 90))
    ratio = float(np.nanmax(fut) / max(p90, 1e-6))
    level = "severe" if ratio >= 2.0 else "high" if ratio >= 1.5 else "watch" if ratio >= 1.2 else "normal"
    res.data = {"river_nearby": True, "cell_lat": c["latitude"], "cell_lon": c["longitude"],
                "mean_past_m3s": round(float(m), 1), "peak_forecast_m3s": round(float(np.nanmax(fut)), 1),
                "ratio_vs_past_p90": round(ratio, 2), "level": level}
    return res
