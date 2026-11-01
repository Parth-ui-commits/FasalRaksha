"""Tool-calling assistant on any OpenAI-compatible endpoint (default: Groq free tier).
Auto-selects an available model, returns structured tool errors, bounded self-correction, numeric grounding check."""
import json, os, re
from openai import OpenAI, NotFoundError
from . import geo, weather, flood, soil, mandi, decision
from .crops import CROPS

BASE_URL = os.getenv("LLM_BASE_URL", "https://api.groq.com/openai/v1")
PREFERRED = ["llama-3.3-70b-versatile", "openai/gpt-oss-120b", "openai/gpt-oss-20b",
             "qwen/qwen3-32b", "llama-3.1-8b-instant"]
MAX_STEPS = 8
_resolved = None

SYSTEM = """You are FasalRaksha, an agronomy and market advisor for Indian farmers.
Rules:
- Reply in the language the farmer wrote in (Hindi or English), in short plain sentences. Lead with ONE clear action.
- Plain text only. No emojis, no markdown headings, no dashes used as punctuation.
- Use tools for every number (weather, flood, soil, prices). Never invent or recall figures.
- If the farmer profile below gives a location, crop and quantity, use them. Do not ask for them again.
- If a tool fails or data is missing, say so plainly, use what you have, and try one fallback before giving up.
- Give probabilities as chances (for example '6 in 10 forecasts show rain'), name the data source and its date, and give the rupee impact when available.
- You do not replace an extension officer. For pesticide or medical-grade advice, tell the farmer to contact their KVK."""

TOOLS = [
    {"name": "geocode_place", "description": "Find lat/lon for a village, town or district in India.",
     "input_schema": {"type": "object", "properties": {"name": {"type": "string"}, "state": {"type": "string"}}, "required": ["name"]}},
    {"name": "farm_risk", "description": "Live 5-day probabilistic weather risk, river-flood risk, soil drainage and 10-year rainfall context for a location and crop.",
     "input_schema": {"type": "object", "properties": {"lat": {"type": "number"}, "lon": {"type": "number"},
                                                       "crop": {"type": "string", "enum": list(CROPS)}}, "required": ["lat", "lon", "crop"]}},
    {"name": "harvest_plan", "description": "Best harvest start day minimising expected loss in rupees, using the live ensemble forecast.",
     "input_schema": {"type": "object", "properties": {"lat": {"type": "number"}, "lon": {"type": "number"},
                                                       "crop": {"type": "string", "enum": list(CROPS)},
                                                       "yield_qtl": {"type": "number"}, "price_rs_qtl": {"type": "number"}},
                      "required": ["lat", "lon", "crop", "yield_qtl", "price_rs_qtl"]}},
    {"name": "best_mandi", "description": "Top mandis by NET price after transport, from today's Agmarknet data.",
     "input_schema": {"type": "object", "properties": {"lat": {"type": "number"}, "lon": {"type": "number"},
                                                       "state": {"type": "string"}, "crop": {"type": "string", "enum": list(CROPS)}},
                      "required": ["lat", "lon", "state", "crop"]}},
]


def _openai_tools():
    return [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                                              "parameters": t["input_schema"]}} for t in TOOLS]


def _client():
    return OpenAI(base_url=BASE_URL, api_key=os.getenv("LLM_API_KEY", ""), timeout=60)


def _available():
    return [m.id for m in _client().models.list().data]


def resolve_model(force=False):
    """Use LLM_MODEL if the provider has it, otherwise the first preferred model that exists."""
    global _resolved
    if _resolved and not force:
        return _resolved
    want = os.getenv("LLM_MODEL", "").strip()
    try:
        avail = _available()
    except Exception:  # noqa: BLE001 - provider without a models list endpoint
        if want:
            _resolved = want
            return want
        raise
    if want in avail:
        _resolved = want
    else:
        _resolved = next((p for p in PREFERRED if p in avail), None)
        if not _resolved:
            raise RuntimeError(f"No usable model found. Provider offers: {avail[:15]}")
    return _resolved


def diagnose():
    info = {"base_url": BASE_URL, "requested_model": os.getenv("LLM_MODEL"), "key_set": bool(os.getenv("LLM_API_KEY"))}
    try:
        info["available"] = _available()[:25]
        info["model"] = resolve_model(force=True)
        r = _client().chat.completions.create(model=info["model"], max_tokens=5,
                                              messages=[{"role": "user", "content": "Reply with the single word OK"}])
        info["ok"], info["reply"] = True, (r.choices[0].message.content or "")[:20]
    except Exception as e:  # noqa: BLE001
        info["ok"], info["error"] = False, f"{type(e).__name__}: {str(e)[:300]}"
    return info


def _compact(name, out):
    """Keep what we send to the model small (free tiers limit tokens per minute)."""
    if name == "harvest_plan" and isinstance(out, dict) and "options" in out:
        slim = {k: v for k, v in out.items() if k != "options"}
        slim["options_summary"] = [(o["start_in_days"], o["expected_loss_rs"]) for o in out["options"]]
        return slim
    return out


def run_tool(name, a):
    try:
        if name == "geocode_place":
            r = geo.geocode(a["name"], a.get("state"))
        elif name == "farm_risk":
            ens = weather.ensemble_daily(a["lat"], a["lon"])
            fl, so = flood.river_risk(a["lat"], a["lon"]), soil.soil_profile(a["lat"], a["lon"])
            cl = weather.rain_climatology(a["lat"], a["lon"])
            return {"weather": decision.weather_risk(ens.data, a["crop"]) if ens.ok else {"error": ens.error},
                    "river": fl.data if fl.ok else {"error": fl.error},
                    "soil": so.data if so.ok else {"error": so.error},
                    "climatology_10d_rain": cl.data if cl.ok else {"error": cl.error},
                    "sources": [x.source for x in (ens, fl, so, cl) if x.ok], "fetched_at": ens.fetched_at,
                    "degraded": [x.source for x in (ens, fl, so, cl) if not x.ok or x.error]}
        elif name == "harvest_plan":
            ens = weather.ensemble_daily(a["lat"], a["lon"])
            if not ens.ok:
                return {"error": ens.error}
            so = soil.soil_profile(a["lat"], a["lon"])
            drain = so.data["drainage"] if so.ok else "moderate"
            return {**decision.plan_harvest(ens.data, a["crop"], a["yield_qtl"], a["price_rs_qtl"], drain),
                    "source": ens.source, "fetched_at": ens.fetched_at, "soil_drainage_used": drain}
        elif name == "best_mandi":
            r = mandi.best_markets(a["lat"], a["lon"], a["state"], CROPS[a["crop"]]["agmarknet"])
        else:
            return {"error": f"unknown tool {name}"}
        return {"data": r.data, "source": r.source, "fetched_at": r.fetched_at} if r.ok else {"error": r.error, "source": r.source}
    except Exception as e:  # noqa: BLE001 - tool errors go back to the model, not the user
        return {"error": f"{type(e).__name__}: {e}"}


NUM = re.compile(r"\d+(?:[.,]\d+)?")


def _nums(obj, acc):
    if isinstance(obj, dict):
        [_nums(v, acc) for v in obj.values()]
    elif isinstance(obj, (list, tuple)):
        [_nums(v, acc) for v in obj]
    elif isinstance(obj, (int, float)):
        for r in (1, 2):
            acc.add(str(round(obj, r)).rstrip("0").rstrip("."))
        acc.update({str(int(round(obj))), str(round(obj * 100)), str(round(obj * 10))})
    elif isinstance(obj, str):
        acc.update(n.replace(",", ".") for n in NUM.findall(obj))


def ungrounded(answer: str, evidence: list) -> list:
    """Numbers in the answer that appear in NO tool output (simple hallucination guard)."""
    ok = set()
    _nums(evidence, ok)
    bad = []
    for n in NUM.findall(answer):
        n = n.replace(",", ".")
        if n not in ok and float(n) > 10:  # ignore small counts like '3 days'
            bad.append(n)
    return bad


def _assistant_dict(m):
    d = {"role": "assistant", "content": m.content or ""}
    if m.tool_calls:
        d["tool_calls"] = [{"id": c.id, "type": "function",
                            "function": {"name": c.function.name, "arguments": c.function.arguments}}
                           for c in m.tool_calls]
    return d


def _call_llm(msgs, system=SYSTEM):
    """Up to 3 tries. A 404 forces model re-detection. Small open models sometimes emit a malformed tool call."""
    global _resolved
    last = None
    for attempt in range(3):
        try:
            return _client().chat.completions.create(
                model=resolve_model(force=isinstance(last, NotFoundError)), max_tokens=1000, temperature=0.2,
                messages=[{"role": "system", "content": system}] + msgs,
                tools=_openai_tools(), tool_choice="auto").choices[0].message
        except NotFoundError as e:
            last, _resolved = e, None
        except Exception as e:  # noqa: BLE001
            last = e
    raise last


def chat(history: list, user_msg: str, profile_text: str = ""):
    """Returns (answer, evidence_log, updated_history). History holds plain dicts (no system message)."""
    system = SYSTEM + (f"\n\nFarmer profile: {profile_text}" if profile_text else "")
    msgs = history + [{"role": "user", "content": user_msg}]
    evidence = []
    try:
        for _ in range(MAX_STEPS):
            m = _call_llm(msgs, system)
            msgs.append(_assistant_dict(m))
            if not m.tool_calls:
                text = m.content or ""
                bad = ungrounded(text, [e["output"] for e in evidence])
                if bad and evidence:  # one self-correction pass
                    msgs.append({"role": "user", "content": f"These figures are not in any tool output: {bad}. "
                                 "Rewrite using only tool figures, or call a tool to verify."})
                    evidence.append({"tool": "grounding_check", "input": {}, "output": {"flagged": bad}})
                    continue
                return text, evidence, msgs
            for c in m.tool_calls:
                try:
                    args = json.loads(c.function.arguments or "{}")
                    out = run_tool(c.function.name, args)
                except json.JSONDecodeError:
                    args, out = {}, {"error": "tool arguments were not valid JSON; call again"}
                evidence.append({"tool": c.function.name, "input": args, "output": out})
                msgs.append({"role": "tool", "tool_call_id": c.id,
                             "content": json.dumps(_compact(c.function.name, out), default=str)})
    except Exception as e:  # noqa: BLE001 - rate limit, bad key, network
        evidence.append({"tool": "llm_error", "input": {}, "output": {"error": f"{type(e).__name__}: {str(e)[:300]}"}})
        return "LLM_ERROR", evidence, msgs
    return "I could not complete the analysis right now. Please try again.", evidence, msgs
