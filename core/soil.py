from .http import fetch_json

SOIL = "https://rest.isric.org/soilgrids/v2.0/properties/query"
DEPTHS = ["0-5cm", "5-15cm", "15-30cm"]


def soil_profile(lat, lon):
    """ISRIC SoilGrids 250 m topsoil (0-30 cm, depth-weighted)."""
    res = fetch_json("isric-soilgrids", SOIL, {
        "lat": lat, "lon": lon, "property": ["clay", "sand", "soc", "phh2o"],
        "depth": DEPTHS, "value": "mean"}, ttl=7 * 86400, timeout=40)
    if not res.ok:
        return res
    w = {"0-5cm": 5, "5-15cm": 10, "15-30cm": 15}
    out = {}
    for layer in res.data["properties"]["layers"]:
        df = layer["unit_measure"].get("d_factor", 1) or 1
        num = den = 0.0
        for dep in layer["depths"]:
            v = dep["values"].get("mean")
            if v is not None and dep["label"] in w:
                num += (v / df) * w[dep["label"]]; den += w[dep["label"]]
        if den:
            out[layer["name"]] = round(num / den, 1)
    if "clay" not in out or "sand" not in out:
        res.ok, res.error = False, "soil layers unavailable at this point"
        return res
    clay, sand = out["clay"], out["sand"]  # % (g/100g)
    drainage = "poor" if clay >= 40 else "fast" if sand >= 60 else "moderate"
    res.data = {"clay_pct": clay, "sand_pct": sand, "organic_carbon_g_kg": out.get("soc"),
                "ph": out.get("phh2o"), "drainage": drainage}
    return res
