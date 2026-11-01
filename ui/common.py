"""Shared building blocks for every page."""
import html
import streamlit as st
from core import advice, dashboard, stages
from core.advice import pct
from core.crops import CROPS
from core.i18n import L, CROP_NAMES, STATES

esc = html.escape
SOIL_TYPES = {"": ("I do not know", "पता नहीं"), "sandy": ("Sandy (water drains fast)", "रेतीली (पानी जल्दी निकलता है)"),
              "loamy": ("Loamy (balanced)", "दोमट (संतुलित)"), "clay_loam": ("Clay loam", "चिकनी दोमट"),
              "clayey": ("Clayey (holds water, drains slowly)", "चिकनी (पानी रुकता है)")}
IRRIGATION = {"canal": ("Canal", "नहर"), "tubewell": ("Tubewell or borewell", "ट्यूबवेल या बोरवेल"), "pond": ("Pond or river", "तालाब या नदी"),
              "rainfed": ("Rain only", "केवल बारिश"), "drip": ("Drip or sprinkler", "ड्रिप या स्प्रिंकलर")}
STATUS = {"growing": ("Growing", "बढ़ रही है"), "ready": ("Ready to harvest", "कटाई के लिए तैयार"), "harvested": ("Harvested", "कट चुकी")}


def crop_name(lang, c):
    return CROP_NAMES[c][lang] if c in CROP_NAMES else c


def field_qty(f):
    return float(f["area_acre"] or 1) * float(f["exp_yield_qtl_acre"] or stages.DEFAULT_YIELD_QTL_ACRE.get(f["crop"], 10))


@st.cache_data(ttl=900, show_spinner=False)
def cached_build(lat, lon, state, crop, qty, soil_type, light):
    return dashboard.build(lat, lon, state, crop, qty, 0.0, soil_type, light)


def build_for(f, light=False):
    return cached_build(f["lat"], f["lon"], f["state"] or "Bihar", f["crop"], field_qty(f), f["soil_type"] or "", light)


def card(lang, c):
    st.markdown(
        f'<div class="card {c["level"]}"><span class="label">{esc(c["title"])}</span>'
        f'<span class="chip {c["level"]}">{esc(_status(lang, c["level"]))}</span>'
        f'<div class="head">{esc(c["headline"])}</div><div class="body">{esc(c["detail"])}</div></div>', unsafe_allow_html=True)


def _status(lang, level):
    return {"ok": L(lang, "Safe", "ठीक"), "watch": L(lang, "Watch", "सावधान"), "alert": L(lang, "Act now", "तुरंत ध्यान दें")}[level]


def stage_card(lang, info, crop):
    if info["phase"] == "not_sown":
        return {"level": "ok", "title": L(lang, "Crop stage", "फसल की अवस्था"),
                "headline": L(lang, f"Sowing date is {info['days_to_next']} day(s) away", f"बुवाई की तारीख {info['days_to_next']} दिन दूर है"),
                "detail": L(lang, "Update the sowing date in My fields if it has changed.", "तारीख बदली हो तो 'मेरे खेत' में सही करें।")}
    st_ = info["stage"]
    name, tip = (st_["hi"], st_["tip_hi"]) if lang == "hi" else (st_["en"], st_["tip_en"])
    nxt = ""
    if info["next"] and info["days_to_next"] is not None:
        nn = info["next"][2] if lang == "hi" else info["next"][1]
        nxt = L(lang, f" Next stage: {nn} in {info['days_to_next']} day(s).", f" अगली अवस्था: {nn}, {info['days_to_next']} दिन में।")
    level = "watch" if st_["water"] == "critical" else "ok"
    return {"level": level, "title": L(lang, "Crop stage", "फसल की अवस्था"),
            "headline": L(lang, f"{name}, day {info['das']} of about {info['maturity_days']}", f"{name}, लगभग {info['maturity_days']} में से दिन {info['das']}"),
            "detail": tip + nxt}


def timeline(lang, crop, info):
    cyc = stages.CYCLE[crop]
    M = cyc["maturity"]
    segs = ""
    for i, s in enumerate(cyc["stages"]):
        end = cyc["stages"][i + 1][0] if i + 1 < len(cyc["stages"]) else M
        w = (end - s[0]) / M * 100
        cls = "done" if info["das"] >= end else "now" if s[0] <= info["das"] < end else "todo"
        name = s[2] if lang == "hi" else s[1]
        segs += f'<div class="seg {cls}" style="width:{w:.1f}%" title="{esc(name)}">{esc(name) if w > 13 else ""}</div>'
    pos = min(100, max(0, info["das"] / M * 100))
    st.markdown(f'<div class="tl">{segs}<div class="marker" style="left:{pos:.1f}%"></div></div>'
                f'<div class="note">{esc(L(lang, "Day", "दिन"))} {max(info["das"], 0)} / {M}. '
                f'{esc(L(lang, "Expected maturity", "पकने की संभावित तारीख"))}: {info["maturity_date"].strftime("%d %b %Y")}</div>', unsafe_allow_html=True)


def brief(lang, b):
    if not b:
        return
    conf = ""
    if b["confidence"]:
        n = {"low": 1, "medium": 2, "high": 3}[b["confidence"]]
        word = {"high": L(lang, "High", "उच्च"), "medium": L(lang, "Medium", "मध्यम"), "low": L(lang, "Low", "कम")}[b["confidence"]]
        pips = "".join(f'<i class="{"on" if k < n else ""}"></i>' for k in range(3))
        conf = (f'<h5>{esc(L(lang, "Confidence", "भरोसा"))}</h5><div>{esc(word)}<span class="pips">{pips}</span> '
                f'<span class="note">{esc(b["conf_note"])}</span></div>')
    why = "".join(f"<li>{esc(w)}</li>" for w in b["why"])
    opts = ""
    if b["options"]:
        o = b["options"]
        head = "".join(f"<th>{esc(c)}</th>" for c in o["cols"])
        rows = "".join(f'<tr class="{"best" if i == o["best"] else ""}">' + "".join(f"<td>{esc(str(c))}</td>" for c in r) + "</tr>" for i, r in enumerate(o["rows"]))
        opts = f'<h5>{esc(L(lang, "Options compared", "विकल्पों की तुलना"))}</h5><table><tr>{head}</tr>{rows}</table>'
    trig = "".join(f"<li>{esc(t_)}</li>" for t_ in b["triggers"])
    trig = f'<h5>{esc(L(lang, "What would change this advice", "किस बात से यह सलाह बदलेगी"))}</h5><ul>{trig}</ul>' if trig else ""
    nxt = f'<h5>{esc(L(lang, "Next check", "अगली जांच"))}</h5><div>{esc(b["next_check"])}</div>' if b["next_check"] else ""
    st.markdown(f'<div class="brief {b["level"]}"><span class="label">{esc(b["title"])}</span>'
                f'<span class="chip {b["level"]}">{esc(_status(lang, b["level"]))}</span>'
                f'<div class="head">{esc(b["headline"])}</div><h5>{esc(L(lang, "Why", "क्यों"))}</h5><ul>{why}</ul>{opts}{conf}{trig}{nxt}</div>',
                unsafe_allow_html=True)


def tile(n, t_):
    return f'<div class="tile"><div class="n">{esc(str(n))}</div><div class="t">{esc(t_)}</div></div>'
