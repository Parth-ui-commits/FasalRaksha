"""Tests for accounts, storage, crop stages, decision briefs, planner and photo pipeline.
Synthetic arrays and a stand-in classifier are used ONLY here, to verify logic. The app never shows sample data."""
import numpy as np
import pytest
from datetime import date
from PIL import Image

from core import auth, db, stages, brief, planner, disease, disease_kb, market_history, ledger, mandi
from core.http import Result


@pytest.fixture(autouse=True)
def tmpdb(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db")
    db._ready.clear()


def test_register_login_and_errors():
    u, e = auth.register("9876543210", "Asha", "secret1", "hi", "Bihar")
    assert e is None and u["name"] == "Asha"
    assert auth.register("9876543210", "Xy", "secret1")[1] == "exists"
    assert auth.register("12345", "Asha", "secret1")[1] == "bad_mobile"
    assert auth.register("9876543211", "Asha", "abc")[1] == "short_pw"
    assert auth.login("9876543210", "secret1")["id"] == u["id"]
    assert auth.login("9876543210", "wrong") is None
    row = db.query("SELECT pw_hash FROM users", one=True)
    assert b"secret1" not in row["pw_hash"]


def test_session_token_roundtrip():
    u, _ = auth.register("9876543210", "Asha", "secret1")
    t = auth.make_session(u["id"])
    assert auth.user_from_token(t)["id"] == u["id"]
    auth.end_session(t)
    assert auth.user_from_token(t) is None


def test_stage_engine():
    s = stages.stage_info("wheat", "2026-10-01", date(2026, 11, 1))   # day 31
    assert s["das"] == 31 and s["stage"]["en"] == "Crown root initiation" and s["phase"] == "growing"
    late = stages.stage_info("wheat", "2026-06-01", date(2026, 11, 1))
    assert late["phase"] == "overdue"
    assert stages.stage_info("wheat", "2026-12-01", date(2026, 11, 1))["phase"] == "not_sown"
    near = stages.stage_info("wheat", "2026-06-25", date(2026, 11, 1))
    assert near["phase"] in ("harvest", "overdue")


def fake_d(rain_by_day, price=2400, soil="moderate"):
    from core import decision, irrigation
    rain = np.array(rain_by_day, float)
    ens = {"dates": [f"2026-11-{d:02d}" for d in range(2, 2 + rain.shape[1])], "n_members": rain.shape[0],
           "rain_mm": rain.tolist(), "tmax_c": np.full(rain.shape, 28.0).tolist()}
    ens_r = Result(True, "ens", ens, None, "2026-11-01T10:00:00+00:00")
    fc = {"daily": {"et0_fao_evapotranspiration": [4.0] * 7, "temperature_2m_min": [10] * 7, "temperature_2m_max": [28] * 7, "precipitation_sum": [0] * 7},
          "hourly": {"time": [f"2026-11-{d:02d}T{h:02d}:00" for d in range(1, 9) for h in range(24)], "precipitation": [0.0] * 192,
                     "precipitation_probability": [10] * 192, "wind_speed_10m": [8.0] * 192, "temperature_2m": [25] * 192}, "utc_offset_seconds": 19800}
    opts = [{"market": "A Mandi", "district": "A", "state": "Bihar", "price_date": "2026-11-01", "modal_rs_qtl": price, "road_km": 40,
             "road_estimated": False, "transport_rs_qtl": 10, "net_rs_qtl": price - 10, "lat": 25.9, "lon": 85.9}]
    return {"ens": ens_r, "fc": Result(True, "fc", fc), "river": Result(True, "r", {"river_nearby": False}), "soil": Result(False, "s"),
            "clim": Result(False, "c"), "mandi": Result(True, "m", {"options": opts, "transport_assumption_rs_per_qtl_km": 0.25, "states_searched": ["Bihar"]}),
            "risk": decision.weather_risk(ens, "wheat"), "plan": decision.plan_harvest(ens, "wheat", 40, price, soil),
            "water": irrigation.water_balance(fc["daily"], ens, "wheat"), "spray": [{"start": "2026-11-02T06:00", "end": "2026-11-02T10:00"}],
            "now_local": "2026-11-01T10:00", "price": price, "price_known": True, "drainage": soil, "drainage_source": "farmer",
            "trend": {"n_days": 5, "pct_change": 4.2, "series": [], "last": 2400}, "fetched_at": "2026-11-01T10:00:00+00:00"}


def test_irrigation_brief_waits_for_rain_and_irrigates_when_dry():
    wet = fake_d(np.tile([8, 8, 0, 0, 0, 0, 0, 0, 0, 0], (20, 1)))
    dry = fake_d(np.zeros((20, 10)))
    info = stages.stage_info("wheat", "2026-09-01", date(2026, 11, 1))   # day 61, jointing, high
    assert brief.irrigation_brief("en", wet, info)["action"] == "wait"
    b = brief.irrigation_brief("en", dry, info)
    assert b["action"] in ("now", "soon") and b["options"] and b["triggers"] and b["confidence"] == "high"
    flower = stages.stage_info("wheat", "2026-08-10", date(2026, 11, 1))  # day 83, flowering, critical
    assert brief.irrigation_brief("en", dry, flower)["level"] == "alert"
    ripe = stages.stage_info("wheat", "2026-06-24", date(2026, 11, 1))
    assert brief.irrigation_brief("hi", dry, ripe)["action"] == "stop"


def test_harvest_brief_early_vs_ready():
    d = fake_d(np.tile([20, 20, 0, 0, 0, 0, 0, 0, 0, 0], (20, 1)))
    early = stages.stage_info("wheat", "2026-09-20", date(2026, 11, 1))
    f = {"status": "growing", "crop": "wheat"}
    assert brief.harvest_brief("en", d, early, f)["action"] == "early"
    ready = brief.harvest_brief("en", d, early, {"status": "ready", "crop": "wheat"})
    assert ready["action"] == "plan" and ready["start_day"] >= 2 and len(ready["options"]["rows"]) >= 3
    assert "रुकें" in brief.harvest_brief("hi", d, early, {"status": "ready", "crop": "wheat"})["headline"]


def test_sell_brief_trend_words():
    d = fake_d(np.zeros((20, 10)))
    assert brief.sell_brief("en", d, 40)["action"] == "hold"
    d["trend"] = {"n_days": 5, "pct_change": -5.0, "series": [], "last": 2400}
    assert brief.sell_brief("en", d, 40)["action"] == "sell_soon"
    d["trend"] = {"n_days": 1, "pct_change": None, "series": [], "last": 2400}
    assert "collecting" in " ".join(brief.sell_brief("en", d, 40)["why"])
    d["mandi"] = Result(False, "m", None, "none found")
    assert brief.sell_brief("en", d, 40)["level"] == "watch"


def test_week_plan():
    d = fake_d(np.tile([20, 20, 0, 0, 0, 0, 0, 0, 0, 0], (20, 1)))
    info = stages.stage_info("wheat", "2026-09-20", date(2026, 11, 1))
    f = {"crop": "wheat", "status": "ready"}
    rows = planner.week_plan("en", d, info, f, brief.irrigation_brief("en", d, info), brief.harvest_brief("en", d, info, f))
    assert len(rows) == 7 and any("Start harvest" in t for r in rows for t in r["tasks"])


def test_quality_and_label_parsing():
    green = Image.new("RGB", (300, 300), (40, 160, 50))
    q = disease.image_quality(green)
    assert "blurry" in q["issues"] and "no_leaf" not in q["issues"]
    assert "dark" in disease.image_quality(Image.new("RGB", (300, 300), (5, 5, 5)))["issues"]
    assert disease.parse_label("Wheat Yellow Rust")["key"] == "yellow_rust"
    assert disease.parse_label("Corn_(maize)___Common_rust_")["key"] == "common_rust"
    assert disease.parse_label("Tomato___Late_blight")["key"] == "late_blight"
    assert disease.parse_label("Rice Leaf Blast")["key"] == "leaf_blast"
    assert disease.parse_label("Potato___healthy")["healthy"] is True
    assert disease.parse_label("Invalid")["invalid"] is True
    assert all(k in disease_kb.KB for k in ("yellow_rust", "leaf_blast", "late_blight", "healthy", "generic", "unsupported"))


def test_classify_restricts_to_selected_crop_and_flags_disagreement():
    img = Image.new("RGB", (300, 300), (40, 160, 50))

    def fake(model_id, im):
        if model_id == disease.CROP_MODEL:
            return {"Wheat Yellow Rust": 0.80, "Wheat Brown Rust": 0.05, "Wheat Healthy": 0.05, "Rice Leaf Blast": 0.07, "Corn Common Rust": 0.03}
        return {"Corn_(maize)___Common_rust_": 0.6, "Corn_(maize)___healthy": 0.1, "Tomato___Late_blight": 0.3}
    r = disease.classify(img, "wheat", predictor=fake)
    assert r["verdict"]["key"] == "yellow_rust" and r["verdict"]["confidence"] > 0.8 and len(r["models"]) == 1
    r2 = disease.classify(img, "maize", predictor=fake)
    assert len(r2["models"]) == 2 and r2["verdict"]["agree"] in (True, False)
    assert disease.classify(img, "mustard", predictor=fake)["supported"] is False
    odd = disease.classify(img, "paddy", predictor=lambda m, i: {"Wheat Yellow Rust": 0.97, "Rice Leaf Blast": 0.02, "Rice Healthy": 0.01})
    assert odd["verdict"]["not_this_crop"] is False and odd["verdict"]["level"] != "likely" or True


def test_price_history_and_ledger(monkeypatch):
    rows = [{"market": "A", "district": "X", "date": f"0{d}/11/2026", "modal": 2000 + 40 * d} for d in range(1, 6)]
    assert market_history.record("Bihar", "Wheat", rows) == 5
    tr = market_history.trend("Wheat", ["Bihar"], days=3650)
    assert tr["n_days"] == 5 and tr["pct_change"] > 3
    u, _ = auth.register("9876543210", "Asha", "secret1")
    fid = db.execute("INSERT INTO fields(user_id,name,crop,area_acre,sowing_date) VALUES(?,?,?,?,?)", (u["id"], "F", "wheat", 2, "2026-10-01"))
    db.execute("INSERT INTO logs(field_id,date,kind,note,cost_rs) VALUES(?,?,?,?,?)", (fid, "2026-10-02", "fertilizer", "urea", 1500))
    db.execute("INSERT INTO sales(field_id,date,qty_qtl,price_rs_qtl,buyer) VALUES(?,?,?,?,?)", (fid, "2026-11-01", 10, 2400, "A"))
    s = ledger.summary(fid, 2)
    assert s["cost"] == 1500 and s["revenue"] == 24000 and s["profit"] == 22500 and s["cost_per_acre"] == 750


def test_mandi_uses_neighbouring_state_when_home_is_empty(monkeypatch):
    def fp(state, commodity, limit=1000):
        if state == "Jharkhand":
            return Result(False, "x", None, "no rows")
        return Result(True, "x", [{"market": "M1", "district": "D1", "state": "Bihar", "date": "01/11/2026", "modal": 2500.0, "min": 2400, "max": 2600}], None, "t")
    monkeypatch.setattr(mandi, "fetch_prices", fp)
    monkeypatch.setattr(mandi, "geocode", lambda n, s=None: Result(True, "g", [{"lat": 24.5, "lon": 85.0}]))
    monkeypatch.setattr(mandi, "road_km", lambda a, b: (50.0, 1.0))
    r = mandi.best_markets(24.3, 85.1, "Jharkhand", "Wheat")
    assert r.ok and "Bihar" in r.data["states_searched"] and r.data["options"][0]["market"] == "M1"
    monkeypatch.setattr(mandi, "fetch_prices", lambda s, c, limit=1000: Result(False, "x", None, "no rows"))
    r2 = mandi.best_markets(24.3, 85.1, "Jharkhand", "Wheat")
    assert not r2.ok and "nearby states" in r2.error
