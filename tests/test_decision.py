"""Unit tests use synthetic arrays ONLY to verify the maths; the app itself never uses mock data."""
import numpy as np
from core import decision, agent


def ens(rain):
    rain = np.array(rain, dtype=float)
    return {"dates": [f"2026-11-0{i+1}" for i in range(rain.shape[1])], "rain_mm": rain.tolist(),
            "tmax_c": np.full(rain.shape, 30.0).tolist(), "n_members": rain.shape[0]}


def test_waits_out_rain():
    # every member rains 20mm on days 0-1, dry afterwards -> should not start today
    r = [[20, 20, 0, 0, 0, 0, 0, 0, 0, 0]] * 10
    p = decision.plan_harvest(ens(r), "wheat", 40, 2400)
    assert p["best"]["start_in_days"] >= 2
    assert p["saving_vs_today_rs"] > 0


def test_harvest_now_if_storm_coming():
    # dry now, heavy storm in every member on day 3 -> harvest today
    r = [[0, 0, 0, 80, 0, 0, 0, 0, 0, 0]] * 10
    p = decision.plan_harvest(ens(r), "wheat", 40, 2400)
    assert p["best"]["start_in_days"] == 0


def test_grounding_check():
    ev = [{"x": 2400, "p": 0.6}]
    assert agent.ungrounded("Price 2400, 60 percent chance", ev) == []
    assert agent.ungrounded("Price 3100", ev) == ["3100"]
