from .http import fetch_json

GEO = "https://geocoding-api.open-meteo.com/v1/search"


def geocode(name: str, state: str | None = None, count: int = 8):
    """Resolve a village/town/district name to coordinates (India-biased)."""
    res = fetch_json("open-meteo-geocoding", GEO, {"name": name, "count": count, "country_code": "IN"}, ttl=86400)
    if not res.ok:
        return res
    hits = res.data.get("results") or []
    if state:
        s = state.lower()
        f = [h for h in hits if s in (h.get("admin1") or "").lower()]
        hits = f or hits
    res.data = [{"name": h["name"], "state": h.get("admin1"), "district": h.get("admin2"),
                 "lat": h["latitude"], "lon": h["longitude"]} for h in hits]
    if not res.data:
        res.ok, res.error = False, f"no place found for '{name}'"
    return res
