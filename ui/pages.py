import os
from datetime import date, datetime
from pathlib import Path
import numpy as np
import pandas as pd
import streamlit as st
from core import advice, agent, brief, db, disease, disease_kb, geo, health, ledger, planner, stages, viz
from core.crops import CROPS
from core.i18n import L, STATES
from ui import charts, theme
from ui.common import (IRRIGATION, SOIL_TYPES, STATUS, brief as render_brief, build_for, card, crop_name, esc, field_qty,
                       stage_card, tile, timeline)

ss = st.session_state
RANK = advice.RANK


def go(page, field_id=None):
    ss["nav"] = page
    if field_id:
        ss["field_id"] = field_id


def user_fields(user):
    return db.query("SELECT * FROM fields WHERE user_id=? ORDER BY id", (user["id"],))


def field_label(lang, f):
    return f"{f['name']} ({crop_name(lang, f['crop'])})"


def pick_field(user, lang, key="field_id"):
    fields = user_fields(user)
    if not fields:
        return None, fields
    ids = [f["id"] for f in fields]
    if ss.get(key) not in ids:
        ss[key] = ids[0]
    fid = st.selectbox(L(lang, "Field", "खेत"), ids, format_func=lambda i: field_label(lang, next(f for f in fields if f["id"] == i)), key=key)
    return next(f for f in fields if f["id"] == fid), fields


def empty_state(lang):
    st.markdown(theme.hero(L(lang, "Add your first field", "अपना पहला खेत जोड़ें"),
                           L(lang, "Tell us where it is, what you grow and when you sowed. Everything else is automatic.", "बताइए खेत कहां है, क्या उगा रहे हैं और कब बोया। बाकी सब अपने आप होगा।"), "clear", False, 0.3, "wheat"), unsafe_allow_html=True)
    st.button(L(lang, "Add a field", "खेत जोड़ें"), on_click=go, args=("fields",), type="primary")


def _today_cards(lang, d, info, f, irr, harv, cards):
    out = [stage_card(lang, info, f["crop"]), cards["weather"], cards["river"]]
    out.append({"level": irr["level"], "title": irr["title"], "headline": irr["headline"], "detail": irr["why"][1]} if irr else cards["water"])
    out.append(cards["spray"])
    out.append({"level": harv["level"], "title": harv["title"], "headline": harv["headline"], "detail": harv["why"][0]}
               if harv and harv["action"] == "plan" else cards["market"])
    return out


# ------------------------------------------------------------------ overview
def overview(user, lang):
    fields = user_fields(user)
    if not fields:
        return empty_state(lang)
    rows, alerts = [], []
    for f in fields[:6]:
        info = stages.stage_info(f["crop"], f["sowing_date"])
        d = build_for(f, light=True)
        cards = advice.build_cards(lang, d, f["crop"])
        irr = brief.irrigation_brief(lang, d, info)
        rows.append((f, info, d, cards, irr))
        for c in (cards["weather"], cards["river"]) + (({"level": irr["level"], "title": irr["title"], "headline": irr["headline"], "detail": ""},) if irr else ()):
            if c["level"] != "ok":
                alerts.append((f, c))
    f0, info0, d0 = rows[0][0], rows[0][1], rows[0][2]
    st.markdown(theme.hero(L(lang, f"Namaste, {user['name']}", f"नमस्ते, {user['name']}"),
                           L(lang, f"{len(fields)} field(s) watched live. {len(alerts)} item(s) need attention.", f"{len(fields)} खेत सीधे देखे जा रहे हैं। {len(alerts)} बातों पर ध्यान चाहिए।"),
                           theme.scene_kind(d0), theme.is_night(d0), info0["progress"], f0["crop"]), unsafe_allow_html=True)
    acres = sum(float(f["area_acre"] or 0) for f in fields)
    nxt = min((r[1]["days_to_maturity"] for r in rows if r[1]["phase"] != "overdue"), default=None)
    c = st.columns(4)
    c[0].markdown(tile(len(fields), L(lang, "Fields", "खेत")), unsafe_allow_html=True)
    c[1].markdown(tile(f"{acres:g}", L(lang, "Acres", "एकड़")), unsafe_allow_html=True)
    c[2].markdown(tile(len(alerts), L(lang, "Alerts", "चेतावनियां")), unsafe_allow_html=True)
    c[3].markdown(tile(nxt if nxt is not None else "-", L(lang, "Days to next harvest", "अगली कटाई में दिन")), unsafe_allow_html=True)
    st.markdown(theme.divider(), unsafe_allow_html=True)
    st.subheader(L(lang, "Needs attention", "ध्यान देने योग्य"))
    if not alerts:
        st.success(L(lang, "No alerts. Your fields look fine for the next few days.", "कोई चेतावनी नहीं। अगले कुछ दिन आपके खेत ठीक दिख रहे हैं।"))
    for f, c_ in sorted(alerts, key=lambda x: -RANK[x[1]["level"]]):
        st.markdown(f'<div class="card {c_["level"]}" style="min-height:0"><span class="label">{esc(f["name"])} / {esc(c_["title"])}</span>'
                    f'<div class="head">{esc(c_["headline"])}</div></div>', unsafe_allow_html=True)
    st.subheader(L(lang, "Your fields", "आपके खेत"))
    cols = st.columns(2)
    for i, (f, info, d, cards, irr) in enumerate(rows):
        with cols[i % 2]:
            nm = (info["stage"]["hi"] if lang == "hi" else info["stage"]["en"]) if info["stage"] else L(lang, "Not sown yet", "अभी बुवाई नहीं हुई")
            st.markdown(f'<div class="fieldcard"><div class="nm">{esc(f["name"])}</div><div class="note">{esc(crop_name(lang, f["crop"]))} / {f["area_acre"]:g} {esc(L(lang, "acre", "एकड़"))} / {esc(f["place"] or "")}</div>'
                        f'<div class="bar"><i style="width:{info["progress"]*100:.0f}%"></i></div>'
                        f'<div class="body"><b>{esc(nm)}</b>, {esc(L(lang, "harvest in about", "कटाई लगभग"))} {max(info["days_to_maturity"], 0)} {esc(L(lang, "days", "दिन में"))}</div></div>', unsafe_allow_html=True)
            st.button(L(lang, "Open dashboard", "डैशबोर्ड खोलें"), key=f"open{f['id']}", on_click=go, args=("field", f["id"]), use_container_width=True)


# ------------------------------------------------------------------ field dashboard
def week_table(lang, rows):
    head = "".join(f"<th>{esc(h)}</th>" for h in (L(lang, "Day", "दिन"), L(lang, "Weather", "मौसम"), L(lang, "Tasks", "काम"), L(lang, "Alerts", "चेतावनी")))
    body = ""
    for r in rows:
        tasks = "".join(f'<span class="pill task">{esc(t_)}</span>' for t_ in r["tasks"]) or "-"
        al = "".join(f'<span class="pill alert">{esc(a)}</span>' for a in r["alerts"]) or "-"
        wx = f'{r["rain_mm"]} mm, {round(r["p_rain"]*100)}% {esc(L(lang, "chance of damaging rain", "नुकसानदेह बारिश की संभावना"))}, {r["tmax"]} C'
        body += f"<tr><td><b>{esc(r['day'])}</b></td><td>{wx}</td><td>{tasks}</td><td>{al}</td></tr>"
    st.markdown(f'<table class="week"><tr>{head}</tr>{body}</table>', unsafe_allow_html=True)


def field_page(user, lang):
    f, fields = pick_field(user, lang)
    if not f:
        return empty_state(lang)
    info = stages.stage_info(f["crop"], f["sowing_date"])
    with st.spinner(L(lang, "Loading live data...", "सीधा डेटा लाया जा रहा है...")):
        d = build_for(f)
    qty = field_qty(f)
    cards = advice.build_cards(lang, d, f["crop"])
    irr = brief.irrigation_brief(lang, d, info)
    harv = brief.harvest_brief(lang, d, info, f)
    sell = brief.sell_brief(lang, d, qty)
    sname = (info["stage"]["hi"] if lang == "hi" else info["stage"]["en"]) if info["stage"] else L(lang, "Not sown yet", "बुवाई बाकी")
    st.markdown(theme.hero(f["name"], f'{crop_name(lang, f["crop"])} / {sname} / {f["place"] or ""}', theme.scene_kind(d), theme.is_night(d), info["progress"], f["crop"]), unsafe_allow_html=True)
    if info["phase"] != "not_sown":
        timeline(lang, f["crop"], info)
    t_today, t_dec, t_week, t_wx, t_water, t_mkt = st.tabs([L(lang, k[0], k[1]) for k in (
        ("Today", "आज"), ("Decisions", "फ़ैसले"), ("Week plan", "हफ्ते की योजना"), ("Weather", "मौसम"), ("Water and spray", "पानी और छिड़काव"), ("Market", "मंडी"))])

    with t_today:
        today = _today_cards(lang, d, info, f, irr, harv, cards)
        top = max(today, key=lambda c: RANK[c["level"]])
        st.markdown(f'<div class="priority {top["level"]}"><span class="label">{esc(L(lang, "Most important today", "आज की सबसे ज़रूरी बात"))}</span><div class="head">{esc(top["headline"])}</div></div>', unsafe_allow_html=True)
        for a, b in ((0, 1), (2, 3), (4, 5)):
            c1, c2 = st.columns(2)
            with c1:
                card(lang, today[a])
            with c2:
                card(lang, today[b])
        text = advice.share_text(lang, f["name"], f["crop"], dict(zip(("harvest", "weather", "river", "water", "spray", "market"), [today[i] for i in (0, 1, 2, 3, 4, 5)])))
        b1, b2 = st.columns(2)
        b1.link_button(L(lang, "Share on WhatsApp", "व्हाट्सऐप पर भेजें"), advice.whatsapp_url(text), use_container_width=True)
        b2.download_button(L(lang, "Download advisory", "सलाह डाउनलोड करें"), text, file_name="fasalraksha_advisory.txt", use_container_width=True)
        st.markdown(f'<div class="note">{esc(L(lang, "Data fetched", "डेटा लिया गया"))}: {(d["fetched_at"] or "")[:16].replace("T", " ")} UTC. '
                    f'{esc(L(lang, "Estimates use forecasts and crop parameters that are assumptions. Confirm with your local KVK before major decisions.", "ये अनुमान पूर्वानुमान और फसल के मानकों पर आधारित हैं, जो मान्यताएं हैं। बड़े फ़ैसले से पहले अपने KVK से पुष्टि करें।"))}</div>', unsafe_allow_html=True)

    with t_dec:
        for b in (irr, harv, sell):
            render_brief(lang, b)
        if not (irr or harv):
            st.warning(L(lang, "Weather data is not available right now. Press Refresh in a minute.", "मौसम का डेटा अभी उपलब्ध नहीं। एक मिनट बाद फिर कोशिश करें।"))

    with t_week:
        rows = planner.week_plan(lang, d, info, f, irr, harv)
        if rows:
            week_table(lang, rows)
        else:
            st.warning(L(lang, "Forecast not available right now.", "पूर्वानुमान अभी उपलब्ध नहीं।"))

    with t_wx:
        if d["ens"].ok:
            df = viz.daily_table(d["ens"].data, CROPS[f["crop"]]["rain_sens_mm"])
            n = d["ens"].data["n_members"]
            l, r = st.columns(2)
            with l:
                st.markdown(f"**{L(lang, 'Rain (mm)', 'बारिश (मिमी)')}**")
                charts.rain_band(lang, df)
            with r:
                st.markdown(f"**{L(lang, 'Chance of damaging rain', 'नुकसानदेह बारिश की संभावना')}**")
                charts.damaging_prob(lang, df)
            st.caption(L(lang, f"Based on {n} forecast runs. The shaded band covers the middle 80 percent of runs.", f"{n} पूर्वानुमान रन पर आधारित। छायांकित पट्टी बीच के 80 प्रतिशत रन दिखाती है।"))
            charts.temp_line(lang, df)
            if d["clim"].ok:
                fc10 = round(float(np.median(np.array(d["ens"].data["rain_mm"]).sum(axis=1))), 1)
                st.caption(L(lang, f"Forecast rain for 10 days: {fc10} mm (average for this time of year: {d['clim'].data['mean_mm']} mm).",
                             f"अगले 10 दिन की अनुमानित बारिश: {fc10} मिमी (इस समय का औसत: {d['clim'].data['mean_mm']} मिमी)।"))
            card(lang, cards["weather"])
            card(lang, cards["river"])
        else:
            st.warning(L(lang, "This data source is not responding right now.", "यह डेटा स्रोत अभी जवाब नहीं दे रहा।"))

    with t_water:
        w = d["water"]
        if w:
            m = st.columns(3)
            m[0].metric(L(lang, "Crop water need (5 days)", "फसल की पानी की ज़रूरत (5 दिन)"), f'{w["need_mm"]} mm')
            m[1].metric(L(lang, "Useful rain expected", "उपयोगी बारिश"), f'{w["useful_rain_mm"]} mm')
            m[2].metric(L(lang, "Shortfall", "कमी"), f'{w["gap_mm"]} mm')
            charts.water_bars(lang, viz.et0_table(d["fc"].data))
        if irr:
            render_brief(lang, irr)
        if d["fc"].ok:
            st.markdown(f"**{L(lang, 'Wind and rain, next 48 hours', 'अगले 48 घंटों की हवा और बारिश')}**")
            charts.wind_rain(lang, viz.hourly_table(d["fc"].data, d["now_local"]))
        card(lang, cards["spray"])
        src = {"farmer": L(lang, "from your soil type", "आपकी बताई मिट्टी से"), "satellite": L(lang, "from satellite soil data", "उपग्रह मिट्टी डेटा से"), "assumed": L(lang, "assumed because soil data is unavailable", "मान लिया गया क्योंकि मिट्टी का डेटा उपलब्ध नहीं")}[d["drainage_source"]]
        st.caption(L(lang, f"Soil drainage: {d['drainage']} ({src}).", f"मिट्टी की जल निकासी: {d['drainage']} ({src})।"))

    with t_mkt:
        render_brief(lang, sell)
        mk = d["mandi"]
        if mk.ok:
            opts = pd.DataFrame(mk.data["options"])
            charts.net_price(lang, opts)
            st.map(pd.concat([pd.DataFrame({"lat": [f["lat"]], "lon": [f["lon"]]}), opts[["lat", "lon"]]]))
            st.caption(L(lang, f"Net price = market price minus transport at Rs {mk.data['transport_assumption_rs_per_qtl_km']} per quintal per km. States searched: {', '.join(mk.data['states_searched'])}.",
                         f"शुद्ध भाव = मंडी भाव घटाकर परिवहन (₹{mk.data['transport_assumption_rs_per_qtl_km']} प्रति क्विंटल प्रति किमी)। खोजे गए राज्य: {', '.join(mk.data['states_searched'])}।"))
        tr = d.get("trend")
        if tr and tr["n_days"] >= 2:
            st.markdown(f"**{L(lang, 'Price history collected by this app', 'इस ऐप द्वारा जमा किया गया भाव इतिहास')}**")
            charts.price_trend(lang, tr["series"])


# ------------------------------------------------------------------ crop doctor
ISSUE = {"small": ("The photo is very small. Move closer.", "फोटो बहुत छोटी है। पास से लें।"),
         "blurry": ("The photo looks blurry. Hold steady and tap to focus.", "फोटो धुंधली लग रही है। हाथ स्थिर रखें और फोकस करें।"),
         "dark": ("Too dark. Take the photo in daylight.", "बहुत अंधेरा है। दिन की रोशनी में फोटो लें।"),
         "bright": ("Too bright or washed out. Avoid harsh direct sun on the leaf.", "बहुत तेज़ रोशनी है। पत्ती पर सीधी तेज़ धूप से बचें।"),
         "no_leaf": ("This may not show a green leaf up close. Fill the frame with one leaf.", "इसमें हरी पत्ती पास से नहीं दिख रही। फ्रेम में एक पत्ती भरकर रखें।")}
SCAN_CROPS = ["wheat", "paddy", "maize", "potato", "tomato", "mustard"]
EXTRA_NAMES = {"potato": {"en": "Potato", "hi": "आलू"}, "tomato": {"en": "Tomato", "hi": "टमाटर"}}


def doctor(user, lang):
    st.subheader(L(lang, "Crop Doctor", "फसल डॉक्टर"))
    st.caption(L(lang, "Photograph one leaf up close in daylight. Neural networks screen for common diseases. This is a first check, not a diagnosis.",
                 "दिन की रोशनी में एक पत्ती की पास से फोटो लें। न्यूरल नेटवर्क आम रोगों की शुरुआती जांच करते हैं। यह निदान नहीं, पहली जांच है।"))
    f, fields = pick_field(user, lang, "doc_field")
    default = SCAN_CROPS.index(f["crop"]) if f and f["crop"] in SCAN_CROPS else 0
    nm = lambda c: (EXTRA_NAMES.get(c) or {"en": crop_name("en", c), "hi": crop_name("hi", c)})[lang]  # noqa: E731
    crop = st.selectbox(L(lang, "Crop in the photo", "फोटो में फसल"), SCAN_CROPS, index=default, format_func=nm)
    tab_up, tab_cam = st.tabs([L(lang, "Upload a photo", "फोटो अपलोड करें"), L(lang, "Use camera", "कैमरा चलाएं")])
    with tab_up:
        up = st.file_uploader(L(lang, "Leaf photo", "पत्ती की फोटो"), type=["jpg", "jpeg", "png", "webp"])
    with tab_cam:
        cam = st.camera_input(L(lang, "Take a photo", "फोटो लें"))
    src = up or cam
    if src and st.button(L(lang, "Check this leaf", "इस पत्ती की जांच करें"), type="primary"):
        from PIL import Image
        img = Image.open(src)
        with st.spinner(L(lang, "Analysing the photo...", "फोटो की जांच हो रही है...")):
            try:
                res = disease.classify(img, crop)
                err = None
            except disease.Unavailable as e:
                res, err = None, str(e)
            except Exception as e:  # noqa: BLE001
                res, err = None, f"{type(e).__name__}: {e}"
        ss["scan"] = {"res": res, "err": err, "crop": crop, "img": img, "field": f["id"] if f else None}
    sc = ss.get("scan")
    if not sc:
        return history(user, lang, f)
    st.image(sc["img"], width=260)
    if sc["err"]:
        st.error(L(lang, "The photo models could not run. ", "फोटो मॉडल नहीं चल सके। ") + sc["err"])
        st.code(".\\install_cnn.ps1", language="powershell")
        return
    res = sc["res"]
    for code in res["quality"]["issues"]:
        st.warning(L(lang, *ISSUE[code]))
    if not res["supported"]:
        kb = disease_kb.KB["unsupported"]
        _scan_card(lang, kb, "watch", kb["name"], None)
        return
    v = res["verdict"]
    if not v:
        st.warning(L(lang, "The models did not recognise this crop in the photo. Try a closer photo of one leaf.", "मॉडल को फोटो में यह फसल नहीं पहचान आई। एक पत्ती की पास से फोटो लें।"))
        return
    kb = disease_kb.KB.get(v["key"], disease_kb.KB["generic"])
    name = kb["name"][1] if lang == "hi" else kb["name"][0]
    if v["key"] == "generic":
        name = f'{name}: {v["name"]}'
    lvl = {"likely": L(lang, "Likely", "संभावित"), "possible": L(lang, "Possible, please confirm", "संभव, कृपया पुष्टि करें"), "unsure": L(lang, "Not sure", "पक्का नहीं")}[v["level"]]
    level = "ok" if kb["urgency"] == "ok" else "alert" if (kb["urgency"] == "act" and v["level"] != "unsure") else "watch"
    if v["level"] == "unsure":
        name = L(lang, "The result is not clear. Retake the photo.", "नतीजा साफ नहीं है। फोटो दोबारा लें।")
    extra = f"{lvl}, {round(v['confidence']*100)}%"
    if v["agree"] is True:
        extra += L(lang, ". Both models agree.", "। दोनों मॉडल एकमत हैं।")
    elif v["agree"] is False:
        extra += L(lang, ". The two models disagree, so please confirm with an expert.", "। दोनों मॉडल अलग राय देते हैं, इसलिए विशेषज्ञ से पुष्टि करें।")
    if v["not_this_crop"]:
        st.warning(L(lang, "The model thinks this may not be a leaf of the crop you selected.", "मॉडल को लगता है यह चुनी हुई फसल की पत्ती नहीं है।"))
    _scan_card(lang, kb, level, name, extra)
    d = None
    if sc["field"]:
        fld = next((x for x in fields if x["id"] == sc["field"]), None)
        d = build_for(fld, light=True) if fld else None
    if kb["urgency"] in ("act", "watch") and d and d["spray"]:
        st.info(L(lang, "Next good spray time if your KVK advises spraying: ", "KVK छिड़काव की सलाह दे तो अगला अच्छा समय: ") + advice.fwin(lang, d["spray"][0]))
    for r in res["models"]:
        st.markdown(f"**{r['kind']}**")
        charts.scan_bars(lang, r["top"])
    if sc["field"] and not ss.get("saved_scan") == id(sc):
        p = Path(db.DB_PATH).parent / "uploads" / str(user["id"])
        p.mkdir(parents=True, exist_ok=True)
        path = p / f"{datetime.utcnow():%Y%m%d%H%M%S}.jpg"
        im = sc["img"].convert("RGB"); im.thumbnail((800, 800)); im.save(path, quality=85)
        db.execute("INSERT INTO scans(field_id,created_at,image_path,crop,label,confidence,model,payload) VALUES(?,?,?,?,?,?,?,?)",
                   (sc["field"], datetime.utcnow().isoformat(timespec="seconds"), str(path), sc["crop"], v["key"], v["confidence"],
                    ",".join(r["model"] for r in res["models"]), ""))
        ss["saved_scan"] = id(sc)
    st.caption(L(lang, "Models were trained mostly on clear single-leaf photos. Field photos can be less accurate. Mustard is not covered yet.", "मॉडल ज़्यादातर साफ, एक पत्ती वाली फोटो पर सीखे हैं। खेत की फोटो में सटीकता कम हो सकती है। सरसों अभी शामिल नहीं है।"))
    history(user, lang, f)


def _scan_card(lang, kb, level, name, extra):
    acts = "".join(f"<li>{esc(a[1] if lang == 'hi' else a[0])}</li>" for a in kb["actions"])
    look = kb["look"][1] if lang == "hi" else kb["look"][0]
    st.markdown(f'<div class="brief {level}"><span class="label">{esc(L(lang, "Result", "नतीजा"))}</span><div class="head">{esc(name)}</div>'
                + (f'<div class="note">{esc(extra)}</div>' if extra else "")
                + f'<h5>{esc(L(lang, "What it looks like", "यह कैसा दिखता है"))}</h5><div>{esc(look)}</div>'
                f'<h5>{esc(L(lang, "What to do now", "अभी क्या करें"))}</h5><ul>{acts}</ul></div>', unsafe_allow_html=True)


def history(user, lang, f):
    if not f:
        return
    rows = db.query("SELECT * FROM scans WHERE field_id=? ORDER BY id DESC LIMIT 6", (f["id"],))
    if not rows:
        return
    st.markdown(theme.divider(), unsafe_allow_html=True)
    st.subheader(L(lang, "Earlier scans of this field", "इस खेत की पिछली जांचें"))
    cols = st.columns(3)
    for i, r in enumerate(rows):
        with cols[i % 3]:
            if os.path.exists(r["image_path"]):
                st.image(r["image_path"], width=180)
            kb = disease_kb.KB.get(r["label"], disease_kb.KB["generic"])
            st.caption(f'{r["created_at"][:10]} / {kb["name"][1] if lang == "hi" else kb["name"][0]} / {round((r["confidence"] or 0)*100)}%')


# ------------------------------------------------------------------ diary and profit
KIND = {"sowing": ("Sowing", "बुवाई"), "irrigation": ("Irrigation", "सिंचाई"), "fertilizer": ("Fertilizer", "खाद"), "spray": ("Spray", "छिड़काव"),
        "weeding": ("Weeding", "निराई"), "labour": ("Labour", "मज़दूरी"), "harvest": ("Harvest", "कटाई"), "other": ("Other", "अन्य")}


def diary(user, lang):
    st.subheader(L(lang, "Diary and profit", "डायरी और मुनाफ़ा"))
    f, _ = pick_field(user, lang, "diary_field")
    if not f:
        return empty_state(lang)
    s = ledger.summary(f["id"], f["area_acre"] or 1)
    c = st.columns(4)
    c[0].markdown(tile(advice.inr(s["cost"]), L(lang, "Total cost", "कुल खर्च")), unsafe_allow_html=True)
    c[1].markdown(tile(advice.inr(s["revenue"]), L(lang, "Sales so far", "अब तक बिक्री")), unsafe_allow_html=True)
    c[2].markdown(tile(advice.inr(s["profit"]), L(lang, "Profit so far", "अब तक मुनाफ़ा")), unsafe_allow_html=True)
    c[3].markdown(tile(advice.inr(s["cost_per_acre"]), L(lang, "Cost per acre", "खर्च प्रति एकड़")), unsafe_allow_html=True)
    l, r = st.columns(2)
    with l:
        st.markdown(f"**{L(lang, 'Add work or expense', 'काम या खर्च जोड़ें')}**")
        with st.form("logform", clear_on_submit=True):
            dt = st.date_input(L(lang, "Date", "तारीख"), value=date.today(), key="ld")
            kind = st.selectbox(L(lang, "Type", "प्रकार"), list(KIND), format_func=lambda k: KIND[k][1 if lang == "hi" else 0])
            note = st.text_input(L(lang, "Note", "टिप्पणी"))
            cost = st.number_input(L(lang, "Cost in rupees", "खर्च (₹)"), min_value=0.0, step=100.0)
            if st.form_submit_button(L(lang, "Save", "सेव करें"), use_container_width=True):
                db.execute("INSERT INTO logs(field_id,date,kind,note,cost_rs) VALUES(?,?,?,?,?)", (f["id"], dt.isoformat(), kind, note, cost))
                st.rerun()
    with r:
        st.markdown(f"**{L(lang, 'Record a sale', 'बिक्री दर्ज करें')}**")
        with st.form("saleform", clear_on_submit=True):
            dt2 = st.date_input(L(lang, "Date", "तारीख"), value=date.today(), key="sd")
            q = st.number_input(L(lang, "Quantity (quintal)", "मात्रा (क्विंटल)"), min_value=0.0, step=1.0)
            p = st.number_input(L(lang, "Price per quintal (₹)", "भाव प्रति क्विंटल (₹)"), min_value=0.0, step=50.0)
            buyer = st.text_input(L(lang, "Buyer or mandi", "खरीदार या मंडी"))
            if st.form_submit_button(L(lang, "Save sale", "बिक्री सेव करें"), use_container_width=True):
                db.execute("INSERT INTO sales(field_id,date,qty_qtl,price_rs_qtl,buyer) VALUES(?,?,?,?,?)", (f["id"], dt2.isoformat(), q, p, buyer))
                st.rerun()
    if s["by_kind"]:
        st.markdown(f"**{L(lang, 'Where the money went', 'पैसा कहां गया')}**")
        charts.cost_bars(lang, s["by_kind"], {k: KIND[k][1 if lang == "hi" else 0] for k in KIND})
    if s["logs"]:
        st.dataframe(pd.DataFrame([{L(lang, "Date", "तारीख"): x["date"], L(lang, "Type", "प्रकार"): KIND.get(x["kind"], ("", ""))[1 if lang == "hi" else 0], L(lang, "Note", "टिप्पणी"): x["note"], "Rs": x["cost_rs"]} for x in s["logs"]]), hide_index=True)


# ------------------------------------------------------------------ assistant
def assistant(user, lang):
    st.subheader(L(lang, "Ask the assistant", "सहायक से पूछें"))
    f, _ = pick_field(user, lang, "ask_field")
    if not f:
        return empty_state(lang)
    info = stages.stage_info(f["crop"], f["sowing_date"])
    sname = info["stage"]["en"] if info["stage"] else "not sown"
    ctx = (f'Field "{f["name"]}" near {f["place"]}, state {f["state"]}, lat {f["lat"]:.3f}, lon {f["lon"]:.3f}. Crop {f["crop"]}, stage {sname}, day {info["das"]}, '
           f'harvest expected {info["maturity_date"]:%d %b}. Area {f["area_acre"]:g} acre, expected harvest {field_qty(f):g} quintal.')
    st.caption(L(lang, "Your field details are already shared with the assistant.", "आपके खेत की जानकारी सहायक के पास पहले से है।"))
    key = f"log{f['id']}"
    ss.setdefault(key, [])
    ss.setdefault("hist" + key, [])
    for m in ss[key]:
        with st.chat_message(m["role"]):
            st.write(m["text"])
    spoken = None
    try:
        from streamlit_mic_recorder import speech_to_text
        spoken = speech_to_text(language="hi-IN" if lang == "hi" else "en-IN", start_prompt=L(lang, "Speak", "बोलिए"), stop_prompt=L(lang, "Stop", "रुकिए"), just_once=True, key="stt")
    except Exception:  # noqa: BLE001
        pass
    if spoken and spoken == ss.get("last_spoken"):
        spoken = None
    q = st.chat_input(L(lang, "Ask about your crop, weather, prices or what to do next", "अपनी फसल, मौसम, भाव या आगे क्या करें, पूछें")) or spoken
    if q:
        if spoken:
            ss["last_spoken"] = spoken
        ss[key].append({"role": "user", "text": q})
        with st.spinner(L(lang, "Checking live forecasts, river levels, soil and prices...", "सीधे पूर्वानुमान, नदी, मिट्टी और भाव जांचे जा रहे हैं...")):
            ans, ev, ss["hist" + key] = agent.chat(ss["hist" + key], q, ctx)
        if ans == "LLM_ERROR":
            ans = L(lang, "The assistant could not answer. Technical detail: ", "सहायक जवाब नहीं दे सका। तकनीकी जानकारी: ") + next((e["output"]["error"] for e in ev if e["tool"] == "llm_error"), "")
        ss[key].append({"role": "assistant", "text": ans})
        st.rerun()


# ------------------------------------------------------------------ fields
def fields_page(user, lang):
    st.subheader(L(lang, "My fields", "मेरे खेत"))
    fields = user_fields(user)
    with st.expander(L(lang, "Add a new field", "नया खेत जोड़ें"), expanded=not fields):
        c1, c2 = st.columns([2, 1])
        place = c1.text_input(L(lang, "Village or town", "गांव या कस्बा"), key="np")
        hint = c2.selectbox(L(lang, "State (helps find the place)", "राज्य (जगह खोजने में मदद)"), [""] + STATES, format_func=lambda s: s or L(lang, "Any", "कोई भी"), key="nh")
        if st.button(L(lang, "Find location", "जगह खोजें")):
            r = geo.geocode(place, hint or None) if place.strip() else None
            ss["fm"] = r.data if (r and r.ok) else []
            if not ss["fm"]:
                st.warning(L(lang, "No place found. Try another spelling.", "कोई जगह नहीं मिली। दूसरी वर्तनी आज़माएं।"))
        m = ss.get("fm") or []
        loc = None
        if m:
            i = st.selectbox(L(lang, "Select the correct place", "सही जगह चुनें"), range(len(m)), format_func=lambda i: ", ".join(x for x in (m[i]["name"], m[i].get("district"), m[i].get("state")) if x))
            loc = m[i]
        crop = st.selectbox(L(lang, "Crop", "फसल"), list(CROPS), format_func=lambda c: crop_name(lang, c), key="nc")
        with st.form("addfield", clear_on_submit=False):
            name = st.text_input(L(lang, "Field name", "खेत का नाम"), value=L(lang, "North field", "उत्तर वाला खेत"))
            area = st.number_input(L(lang, "Area (acre)", "क्षेत्रफल (एकड़)"), min_value=0.1, value=2.0, step=0.5)
            sow = st.date_input(L(lang, "Sowing date (transplanting date for paddy)", "बुवाई की तारीख (धान में रोपाई की तारीख)"), value=date.today())
            soil = st.selectbox(L(lang, "Soil type", "मिट्टी का प्रकार"), list(SOIL_TYPES), format_func=lambda k: SOIL_TYPES[k][1 if lang == "hi" else 0])
            irr = st.selectbox(L(lang, "Water source", "पानी का स्रोत"), list(IRRIGATION), format_func=lambda k: IRRIGATION[k][1 if lang == "hi" else 0])
            yld = st.number_input(L(lang, "Expected yield (quintal per acre), edit to your own", "अपेक्षित उपज (क्विंटल प्रति एकड़), अपने हिसाब से बदलें"), min_value=1.0, value=float(stages.DEFAULT_YIELD_QTL_ACRE[crop]), step=1.0, key=f"y_{crop}")
            if st.form_submit_button(L(lang, "Save field", "खेत सेव करें"), use_container_width=True):
                if not loc:
                    st.error(L(lang, "Find and select the location first.", "पहले जगह खोजकर चुनें।"))
                else:
                    fid = db.execute("INSERT INTO fields(user_id,name,place,state,district,lat,lon,crop,area_acre,sowing_date,soil_type,irrigation,exp_yield_qtl_acre,status,created_at) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                                     (user["id"], name, loc["name"], loc.get("state"), loc.get("district"), loc["lat"], loc["lon"], crop, area, sow.isoformat(), soil, irr, yld, "growing", datetime.utcnow().isoformat(timespec="seconds")))
                    ss["field_id"] = fid
                    st.success(L(lang, "Field saved.", "खेत सेव हो गया।"))
                    st.rerun()
    for f in fields:
        info = stages.stage_info(f["crop"], f["sowing_date"])
        with st.expander(f'{f["name"]}  /  {crop_name(lang, f["crop"])}  /  {f["place"]}'):
            st.write(L(lang, f"Sown on {f['sowing_date']}, day {max(info['das'], 0)}. Area {f['area_acre']:g} acre. Expected harvest {field_qty(f):g} quintal.",
                       f"बुवाई {f['sowing_date']} को, दिन {max(info['das'], 0)}। क्षेत्रफल {f['area_acre']:g} एकड़। अपेक्षित उपज {field_qty(f):g} क्विंटल।"))
            keys = list(STATUS)
            stt = st.selectbox(L(lang, "Status", "स्थिति"), keys, index=keys.index(f["status"] or "growing"), format_func=lambda k: STATUS[k][1 if lang == "hi" else 0], key=f"st{f['id']}")
            c1, c2 = st.columns(2)
            if c1.button(L(lang, "Update status", "स्थिति बदलें"), key=f"us{f['id']}"):
                db.execute("UPDATE fields SET status=? WHERE id=?", (stt, f["id"])); st.rerun()
            if c2.checkbox(L(lang, "Delete this field and its records", "यह खेत और इसका रिकॉर्ड हटाएं"), key=f"dc{f['id']}") and c2.button(L(lang, "Delete now", "अभी हटाएं"), key=f"dd{f['id']}"):
                for t_ in ("logs", "sales", "scans"):
                    db.execute(f"DELETE FROM {t_} WHERE field_id=?", (f["id"],))
                db.execute("DELETE FROM fields WHERE id=?", (f["id"],)); st.rerun()


# ------------------------------------------------------------------ help and sources
def help_page(user, lang):
    st.subheader(L(lang, "Help and government schemes", "मदद और सरकारी योजनाएं"))
    items = [("Kisan Call Centre", "किसान कॉल सेंटर", "Free advice from agriculture experts. Call 1800-180-1551.", "कृषि विशेषज्ञों से मुफ़्त सलाह। 1800-180-1551 पर कॉल करें।"),
             ("Krishi Vigyan Kendra (KVK)", "कृषि विज्ञान केंद्र (KVK)", "Your district KVK gives local advice on seeds, diseases and sprays. Visit kvk.icar.gov.in to find yours.", "आपके ज़िले का KVK बीज, रोग और छिड़काव पर स्थानीय सलाह देता है। अपना KVK खोजने के लिए kvk.icar.gov.in देखें।"),
             ("PM-KISAN", "पीएम-किसान", "Income support for eligible farmer families. pmkisan.gov.in", "पात्र किसान परिवारों के लिए आय सहायता। pmkisan.gov.in"),
             ("PM Fasal Bima Yojana", "प्रधानमंत्री फसल बीमा योजना", "Crop insurance against weather and other losses. Check the last date to enrol each season. pmfby.gov.in", "मौसम और अन्य नुकसान के विरुद्ध फसल बीमा। हर मौसम में पंजीकरण की अंतिम तारीख देखें। pmfby.gov.in"),
             ("Soil Health Card", "मृदा स्वास्थ्य कार्ड", "A soil test tells you what nutrients your field needs. soilhealth.dac.gov.in", "मिट्टी की जांच बताती है कि खेत को कौन से पोषक तत्व चाहिए। soilhealth.dac.gov.in"),
             ("e-NAM", "ई-नाम", "National online market for selling produce. enam.gov.in", "उपज बेचने का राष्ट्रीय ऑनलाइन बाज़ार। enam.gov.in")]
    for a in items:
        st.markdown(f'<div class="feature"><b>{esc(L(lang, a[0], a[1]))}</b><div>{esc(L(lang, a[2], a[3]))}</div></div>', unsafe_allow_html=True)
    st.caption(L(lang, "Details and websites can change. Please verify on the official site before applying.", "विवरण और वेबसाइट बदल सकती हैं। आवेदन से पहले आधिकारिक साइट पर जांच लें।"))


def sources(user, lang):
    import importlib.util
    st.subheader(L(lang, "Live data sources", "सीधे डेटा स्रोत"))
    f, _ = pick_field(user, lang, "src_field")
    if f:
        d = build_for(f)
        rows = []
        for k in ("ens", "fc", "river", "soil", "clim", "mandi"):
            r = d[k]
            status = L(lang, "Not responding", "जवाब नहीं दे रहा") if not r.ok else L(lang, "Using saved copy", "सेव की गई कॉपी") if (r.error or "").startswith("stale") else L(lang, "Working", "चल रहा है")
            rows.append({L(lang, "Source", "स्रोत"): r.source, L(lang, "Status", "स्थिति"): status, L(lang, "Note", "टिप्पणी"): (r.error or "")[:140]})
        st.dataframe(pd.DataFrame(rows), hide_index=True)
    c1, c2 = st.columns(2)
    if c1.button(L(lang, "Check source health", "स्रोतों की जांच करें")):
        for name, v in health.check_all().items():
            st.write(("OK" if v["ok"] else "FAIL"), "|", name, f'{v["ms"]} ms' if v["ms"] else "")
    if c2.button(L(lang, "Test language model", "भाषा मॉडल जांचें")):
        info = agent.diagnose()
        st.success(L(lang, f"Language model works: {info['model']}", f"भाषा मॉडल चल रहा है: {info['model']}")) if info["ok"] else (st.error(info["error"]), st.json(info))
    cnn = importlib.util.find_spec("torch") is not None and importlib.util.find_spec("transformers") is not None
    st.write(L(lang, "Crop Doctor photo models: ", "फसल डॉक्टर फोटो मॉडल: ") + (L(lang, "installed", "इंस्टॉल हैं") if cnn else L(lang, "not installed (run install_cnn.ps1)", "इंस्टॉल नहीं (install_cnn.ps1 चलाएं)")))
    st.write(L(lang, "Price history rows stored: ", "सेव किए गए भाव के रिकॉर्ड: ") + str(db.query("SELECT COUNT(*) n FROM prices", one=True)["n"]))
    st.caption(L(lang, "Weather and flood data: Open-Meteo.com (CC BY 4.0). Soil data: ISRIC SoilGrids. Mandi prices: Agmarknet via data.gov.in. Road distances: OSRM with OpenStreetMap data. Photo models: MobileNetV2 and ViT-tiny from Hugging Face.",
                 "मौसम और बाढ़ का डेटा: Open-Meteo.com (CC BY 4.0)। मिट्टी का डेटा: ISRIC SoilGrids। मंडी भाव: data.gov.in के ज़रिये Agmarknet। सड़क की दूरी: OSRM, OpenStreetMap डेटा के साथ। फोटो मॉडल: Hugging Face से MobileNetV2 और ViT-tiny।"))
