"""Run this FIRST: python check_data.py
Prints OK/FAIL for every live data source so you know what works before starting the app."""
from dotenv import load_dotenv
load_dotenv()
from core import geo, weather, flood, soil, mandi


def show(name, res, extra=""):
    status = "OK  " if res.ok else "FAIL"
    print(f"[{status}] {name:<14} {extra if res.ok else res.error}")


g = geo.geocode("Samastipur", "Bihar")
show("Geocoding", g, f"{g.data[0]['name']} -> {g.data[0]['lat']:.2f}, {g.data[0]['lon']:.2f}" if g.ok else "")
if not g.ok:
    raise SystemExit("Geocoding failed, check your internet connection and try again.")
lat, lon = g.data[0]["lat"], g.data[0]["lon"]

e = weather.ensemble_daily(lat, lon)
show("Ensemble", e, f"{e.data['n_members']} members, {len(e.data['dates'])} days" if e.ok else "")

f = flood.river_risk(lat, lon)
show("Flood/GloFAS", f, str(f.data) if f.ok else "")

s = soil.soil_profile(lat, lon)
show("SoilGrids", s, str(s.data) if s.ok else "")

c = weather.rain_climatology(lat, lon)
show("Climatology", c, str(c.data) if c.ok else "")

m = mandi.fetch_prices("Bihar", "Wheat")
show("Mandi prices", m, f"{len(m.data)} rows, e.g. {m.data[0]}" if m.ok else "")

print("\nIf any line says FAIL, copy that line and ask for help. Everything OK? Run: streamlit run app.py")
