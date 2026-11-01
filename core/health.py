"""Live upstream health, shown in the UI so judges can see real APIs responding."""
import os, time, requests

CHECKS = {
    "Open-Meteo ensemble": "https://ensemble-api.open-meteo.com/v1/ensemble?latitude=28.6&longitude=77.2&hourly=precipitation&models=ecmwf_ifs025&forecast_days=1",
    "Open-Meteo flood (GloFAS)": "https://flood-api.open-meteo.com/v1/flood?latitude=28.6&longitude=77.2&daily=river_discharge&forecast_days=1",
    "ISRIC SoilGrids": "https://rest.isric.org/soilgrids/v2.0/properties/query?lat=28.6&lon=77.2&property=clay&depth=0-5cm&value=mean",
    "OSRM routing": "https://router.project-osrm.org/route/v1/driving/77.2,28.6;77.3,28.7?overview=false",
}


def check_all():
    out = {}
    for name, url in CHECKS.items():
        t = time.time()
        try:
            ok = requests.get(url, timeout=15).status_code == 200
        except Exception:  # noqa: BLE001
            ok = False
        out[name] = {"ok": ok, "ms": int((time.time() - t) * 1000)}
    out["data.gov.in key"] = {"ok": bool(os.getenv("DATA_GOV_IN_API_KEY")), "ms": 0}
    return out
