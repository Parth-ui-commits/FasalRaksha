"""Checks the agent loop wiring with a stand-in LLM (test only; the app always uses a real model)."""
import json
from types import SimpleNamespace as NS
from core import agent


def _msg(content=None, calls=None):
    return NS(content=content, tool_calls=calls)


def test_tool_then_answer(monkeypatch):
    call = NS(id="c1", function=NS(name="geocode_place", arguments=json.dumps({"name": "X"})))
    seq = iter([_msg(calls=[call]), _msg(content="Place found at 25.6")])
    monkeypatch.setattr(agent, "_call_llm", lambda msgs, system=None: next(seq))
    monkeypatch.setattr(agent, "run_tool", lambda n, a: {"data": [{"lat": 25.6}]})
    ans, ev, hist = agent.chat([], "hi", "some profile")
    assert "25.6" in ans and ev[0]["tool"] == "geocode_place"
    assert any(m["role"] == "tool" for m in hist)


def test_llm_failure_is_graceful(monkeypatch):
    def boom(msgs, system=None):
        raise RuntimeError("rate limit")
    monkeypatch.setattr(agent, "_call_llm", boom)
    ans, ev, hist = agent.chat([], "hi")
    assert ans == "LLM_ERROR" and ev[-1]["tool"] == "llm_error"
