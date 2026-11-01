"""Live mandi prices (Agmarknet via data.gov.in) and net-realisation ranking.
Net price = modal price minus transport cost, so the best mandi is the one that leaves the most money
with the farmer, not the one with the highest sticker price."""
import math, os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from .http import fetch_json, Result
from .geo import geocode

OGD = "https://api.data.gov.in/resource/9ef84268d588465aa308a864a43d0070"  # verify in your data.gov.in account
OSRM = "https://router.project-osrm.org/route/v1/driving/{a};{b}"
STATE_ALIASES = {"Uttarakhand": ["Uttrakhand", "Uttarakhand"], "Delhi": ["NCT of Delhi", "Delhi"]}
REVERSE = {"Uttrakhand": "Uttarakhand", "NCT of Delhi": "Delhi"}
# Geographic fact (not data): neighbouring states, used when the home state has few priced markets.
NEIGHBORS = {
    "Andhra Pradesh": ["Telangana", "Karnataka", "Tamil Nadu", "Odisha", "Chhattisgarh"], "Assam": ["West Bengal"],
    "Bihar": ["Uttar Pradesh", "Jharkhand", "West Bengal"], "Chhattisgarh": ["Madhya Pradesh", "Maharashtra", "Telangana", "Odisha", "Jharkhand", "Uttar Pradesh"],
    "Delhi": ["Haryana", "Uttar Pradesh"], "Gujarat": ["Rajasthan", "Madhya Pradesh", "Maharashtra"],
    "Haryana": ["Punjab", "Rajasthan", "Uttar Pradesh", "Delhi", "Himachal Pradesh", "Uttarakhand"],
    "Himachal Pradesh": ["Punjab", "Haryana", "Uttarakhand"], "Jharkhand": ["Bihar", "West Bengal", "Odisha", "Chhattisgarh", "Uttar Pradesh"],
    "Karnataka": ["Maharashtra", "Telangana", "Andhra Pradesh", "Tamil Nadu", "Kerala"], "Kerala": ["Karnataka", "Tamil Nadu"],
    "Madhya Pradesh": ["Uttar Pradesh", "Rajasthan", "Gujarat", "Maharashtra", "Chhattisgarh"],
    "Maharashtra": ["Gujarat", "Madhya Pradesh", "Chhattisgarh", "Telangana", "Karnataka"], "Odisha": ["Jharkhand", "West Bengal", "Chhattisgarh", "Andhra Pradesh"],
    "Punjab": ["Haryana", "Rajasthan", "Himachal Pradesh"], "Rajasthan": ["Punjab", "Haryana", "Uttar Pradesh", "Madhya Pradesh", "Gujarat"],
    "Tamil Nadu": ["Kerala", "Karnataka", "Andhra Pradesh"], "Telangana": ["Maharashtra", "Karnataka", "Andhra Pradesh", "Chhattisgarh"],
    "Uttar Pradesh": ["Uttarakhand", "Himachal Pradesh", "Haryana", "Delhi", "Rajasthan", "Madhya Pradesh", "Chhattisgarh", "Jharkhand", "Bihar"],
    "Uttarakhand": ["Himachal Pradesh", "Uttar Pradesh"], "West Bengal": ["Odisha", "Jharkhand", "Bihar", "Assam"],
}


def state_candidates(state):
    return STATE_ALIASES.get(state, [state])


def parse_date(s):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except (TypeError, ValueError):
            pass
    return None


def _f(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def fetch_prices(state: str, commodity: str, limit=1000):
    key = os.getenv("DATA_GOV_IN_API_KEY", "").strip()
    if not key or key.lower() == "none":
        return Result(False, "data.gov.in(Agmarknet)", error="DATA_GOV_IN_API_KEY not set")
    res = None
    for cand in state_candidates(state):
        res = fetch_json("data.gov.in(Agmarknet)", OGD, {
            "api-key": key, "format": "json", "limit": limit,
            "filters[state.keyword]": cand, "filters[commodity]": commodity}, ttl=3600)
        if res.ok and res.data.get("records"):
            break
    if not res.ok:
        return res
    rows = []
    for r in res.data.get("records", []):
        p = _f(r.get("modal_price"))
        if p:
            rows.append({"market": r.get("market"), "district": r.get("district"), "state": REVERSE.get(r.get("state"), r.get("state")),
                         "date": r.get("arrival_date"), "modal": p, "min": _f(r.get("min_price")), "max": _f(r.get("max_price"))})
    if not rows:
        return Result(False, res.source, None, f"no live price rows for {commodity} in {state}", res.fetched_at)
    try:
        from . import market_history
        market_history.record(state, commodity, rows)
    except Exception:  # noqa: BLE001 - history is a bonus, never block prices
        pass
    return Result(True, res.source, rows, res.error, res.fetched_at, res.from_cache)


def haversine(a, b):
    r = 6371
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dphi, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def road_km(a, b):
    res = fetch_json("osrm", OSRM.format(a=f"{a[1]},{a[0]}", b=f"{b[1]},{b[0]}"),
                     {"overview": "false"}, ttl=7 * 86400)
    if res.ok and res.data.get("routes"):
        r = res.data["routes"][0]
        return r["distance"] / 1000, r["duration"] / 3600
    return None, None


def best_markets(farm_lat, farm_lon, state, commodity, top=5, radius_km=250):
    rate = float(os.getenv("TRANSPORT_RS_PER_QTL_KM", "0.25"))  # assumption, editable
    home = fetch_prices(state, commodity)
    rows = list(home.data) if home.ok else []
    searched = [state]
    if len({(r["market"], r["district"]) for r in rows}) < 3:   # thin home market: also look across the border
        nb = NEIGHBORS.get(state, [])
        with ThreadPoolExecutor(6) as ex:
            for s, r in zip(nb, ex.map(lambda x: fetch_prices(x, commodity), nb)):
                if r.ok:
                    rows += r.data
                    searched.append(s)
    if not rows:
        return Result(False, "data.gov.in(Agmarknet)", None,
                      f"No {commodity} prices reported today in {state} or nearby states. "
                      "Many crops are traded only in season, so try again later or check another crop.",
                      home.fetched_at)
    latest = {}
    for r in rows:   # newest row per market (dates parsed properly, not as text)
        k = (r["market"], r["district"], r["state"])
        d = parse_date(r["date"]) or datetime.min
        if k not in latest or d > latest[k][0]:
            latest[k] = (d, r)
    districts = sorted({(k[1], k[2]) for k in latest if k[1]})

    def geo_one(item):
        name, st = item
        g = geocode(name, st)
        return item, ((g.data[0]["lat"], g.data[0]["lon"]) if g.ok else None)

    with ThreadPoolExecutor(8) as ex:
        pts = dict(ex.map(geo_one, districts))
    cands = []
    for (mk, dist, st), (d, r) in latest.items():
        pt = pts.get((dist, st))
        if pt:
            km = haversine((farm_lat, farm_lon), pt)
            if km <= radius_km:
                cands.append((km, r, pt, d))
    cands.sort(key=lambda x: x[0])
    out = []
    for straight, r, pt, d in cands[:8]:   # road distance only for the nearest few (be kind to OSRM)
        km, hrs = road_km((farm_lat, farm_lon), pt)
        est = km is None
        km = straight * 1.3 if est else km
        net = r["modal"] - rate * km
        out.append({"market": r["market"], "district": r["district"], "state": r["state"],
                    "price_date": d.strftime("%Y-%m-%d") if d != datetime.min else r["date"],
                    "modal_rs_qtl": r["modal"], "road_km": round(km), "road_estimated": est,
                    "transport_rs_qtl": round(rate * km), "net_rs_qtl": round(net), "lat": pt[0], "lon": pt[1]})
    out.sort(key=lambda x: -x["net_rs_qtl"])
    if not out:
        return Result(False, home.source, None, f"Prices exist in {', '.join(searched)}, but no priced mandi within {radius_km} km.", home.fetched_at)
    return Result(True, home.source, {"options": out[:top], "markets_with_live_prices": len(latest),
                                      "states_searched": searched, "transport_assumption_rs_per_qtl_km": rate},
                  None, home.fetched_at)
