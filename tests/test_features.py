"""Logic tests with synthetic arrays only. The app itself never uses sample data."""
import pathlib
import numpy as np
from core import spray, irrigation, advice, i18n, mandi, viz, decision


def hourly(rain_at=None, wind=8.0):
    times = [f"2026-11-02T{h:02d}:00" for h in range(24)] + [f"2026-11-03T{h:02d}:00" for h in range(24)]
    rain = [0.0] * 48
    for i in (rain_at or []):
        rain[i] = 2.0
    return {"time": times, "precipitation": rain, "precipitation_probability": [10] * 48,
            "wind_speed_10m": [wind] * 48, "temperature_2m": [25] * 48}


def test_spray_windows_found_and_blocked_by_rain():
    w = spray.spray_windows(hourly(), "2026-11-02T00:00")
    assert w and w[0]["start"].endswith("06:00")
    w2 = spray.spray_windows(hourly(rain_at=range(5, 22)), "2026-11-02T00:00")
    assert all(not ("2026-11-02T06" <= x["start"] <= "2026-11-02T18") for x in w2)


def test_spray_no_window_in_strong_wind():
    assert spray.spray_windows(hourly(wind=30.0), "2026-11-02T00:00") == []


def test_irrigation_gap():
    fc = {"et0_fao_evapotranspiration": [4.0] * 7}
    ens = {"rain_mm": np.zeros((10, 7)).tolist()}
    w = irrigation.water_balance(fc, ens, "wheat")
    assert w["need_mm"] == 23.0 and w["gap_mm"] == 23.0
    wet = {"rain_mm": np.full((10, 7), 10.0).tolist()}
    assert irrigation.water_balance(fc, wet, "wheat")["gap_mm"] == 0


def test_inr_indian_grouping():
    assert advice.inr(5760) == "₹5,760" and advice.inr(1234567) == "₹12,34,567"


def test_i18n_keys_match():
    assert set(i18n.T["en"]) == set(i18n.T["hi"])


def test_mandi_helpers():
    assert mandi.state_candidates("Uttarakhand")[0] == "Uttrakhand"
    assert mandi.parse_date("05/11/2026").month == 11 and mandi.parse_date("bad") is None


def test_no_em_dashes_in_source():
    root = pathlib.Path(__file__).resolve().parent.parent
    for f in list(root.glob("*.py")) + list((root / "core").glob("*.py")):
        txt = f.read_text(encoding="utf-8")
        assert "\u2014" not in txt and "\u2013" not in txt, f.name


def fake_dashboard():
    ens = {"dates": [f"2026-11-{d:02d}" for d in range(2, 12)], "n_members": 20,
           "rain_mm": np.tile([20, 20, 0, 0, 0, 0, 0, 0, 0, 0], (20, 1)).tolist(),
           "tmax_c": np.full((20, 10), 29.0).tolist()}
    return ens
