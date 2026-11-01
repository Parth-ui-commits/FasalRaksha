"""Decision briefs: not just yes or no. Each brief gives a recommendation, the evidence behind it,
the alternatives compared, how confident the forecast is, and what would change the advice."""
import numpy as np
from .advice import inr, pct, fdate
from .i18n import L

WATER_WORD = {"critical": ("very high (critical stage)", "बहुत ज़्यादा (नाज़ुक अवस्था)"), "high": ("high", "ज़्यादा"),
              "medium": ("medium", "मध्यम"), "low": ("low", "कम")}
DRAIN_WORD = {"fast": ("drains quickly, so it dries out sooner", "पानी जल्दी निकलता है, इसलिए जल्दी सूखती है"),
              "moderate": ("drains at a moderate rate", "पानी मध्यम गति से निकलता है"),
              "poor": ("drains slowly, so avoid over-irrigating", "पानी धीरे निकलता है, इसलिए ज़्यादा सिंचाई से बचें")}
CONF_WORD = {"high": ("High", "उच्च"), "medium": ("Medium", "मध्यम"), "low": ("Low", "कम")}


def _conf(p):
    return "high" if (p <= 0.2 or p >= 0.8) else "low" if 0.35 <= p <= 0.65 else "medium"


def _brief(**kw):
    base = {"options": None, "confidence": None, "conf_note": "", "triggers": [], "next_check": "", "action": None, "start_day": None}
    base.update(kw)
    return base


def irrigation_brief(lang, d, info):
    w, ens_res = d["water"], d["ens"]
    if not w or not ens_res.ok or info.get("stage") is None:
        return None
    rain = np.array(ens_res.data["rain_mm"], float)
    n = ens_res.data["n_members"]
    p48 = float((rain[:, :2].sum(axis=1) >= 10).mean())
    st = info["stage"]
    water, gap = st["water"], w["gap_mm"]
    name = st["hi"] if lang == "hi" else st["en"]
    if water == "low":
        act = "stop"
    elif gap <= 5:
        act = "none"
    elif p48 >= 0.6 and not (water == "critical" and gap > 25):
        act = "wait"
    elif gap > 25 or water == "critical":
        act = "now"
    else:
        act = "soon"
    head = {"stop": L(lang, "Stop irrigation, the crop is ripening", "सिंचाई बंद करें, फसल पक रही है"),
            "none": L(lang, "No irrigation needed for the next 5 days", "अगले 5 दिन सिंचाई की ज़रूरत नहीं"),
            "wait": L(lang, "Hold irrigation, rain is likely within 2 days", "सिंचाई रोकें, 2 दिन में बारिश की संभावना है"),
            "now": L(lang, "Irrigate within 24 hours", "24 घंटे के भीतर सिंचाई करें"),
            "soon": L(lang, "Plan irrigation in the next 2 to 3 days", "अगले 2 से 3 दिन में सिंचाई की योजना बनाएं")}[act]
    level = "alert" if (act == "now" and water == "critical") else "watch" if act in ("now", "soon") else "ok"
    ww, dw = WATER_WORD[water], DRAIN_WORD[d["drainage"]]
    why = [L(lang, f"Crop stage: {name}, day {info['das']}. Water sensitivity: {ww[0]}.", f"फसल की अवस्था: {name}, दिन {info['das']}। पानी की संवेदनशीलता: {ww[1]}।"),
           L(lang, f"The crop needs about {w['need_mm']} mm over 5 days. Useful rain expected: {w['useful_rain_mm']} mm. Shortfall: {w['gap_mm']} mm.",
             f"फसल को 5 दिन में लगभग {w['need_mm']} मिमी पानी चाहिए। उपयोगी बारिश: {w['useful_rain_mm']} मिमी। कमी: {w['gap_mm']} मिमी।"),
           L(lang, f"Chance of 10 mm or more rain in the next 2 days: {pct(p48)}.", f"अगले 2 दिन में 10 मिमी या अधिक बारिश की संभावना: {pct(p48)}।")]
    if d["drainage_source"] != "assumed":
        why.append(L(lang, f"Your soil {dw[0]}.", f"आपकी मिट्टी में {dw[1]}।"))
    options, best = None, None
    if act not in ("stop", "none"):
        best = {"now": 0, "soon": 1, "wait": 2}[act]
        options = {"cols": [L(lang, "Option", "विकल्प"), L(lang, "What to expect", "क्या होगा")], "best": best, "rows": [
            [L(lang, "Irrigate today", "आज सिंचाई करें"),
             L(lang, f"Covers the {w['gap_mm']} mm shortfall. {pct(p48)} chance that rain arrives anyway, so some water may be wasted.",
               f"{w['gap_mm']} मिमी की कमी पूरी होगी। {pct(p48)} संभावना है कि बारिश आ जाए, तब कुछ पानी बेकार जाएगा।")],
            [L(lang, "Irrigate in 2 to 3 days", "2 से 3 दिन में सिंचाई करें"),
             L(lang, f"Saves water if rain comes. Stress risk at the {name} stage if no useful rain ({pct(1 - p48)} chance).",
               f"बारिश आई तो पानी बचेगा। बारिश न आई ({pct(1 - p48)} संभावना) तो {name} अवस्था में पानी की कमी का जोखिम।")],
            [L(lang, "Wait for rain", "बारिश का इंतज़ार करें"),
             L(lang, f"Needs at least 10 mm in 2 days: {pct(p48)} chance. Re-check after 2 days.",
               f"2 दिन में कम से कम 10 मिमी चाहिए: {pct(p48)} संभावना। 2 दिन बाद फिर देखें।")]]}
    return _brief(kind="irrigation", level=level, title=L(lang, "Irrigation decision", "सिंचाई का फ़ैसला"), headline=head, why=why,
                  options=options, confidence=_conf(p48),
                  conf_note=L(lang, f"Based on {n} forecast runs.", f"{n} पूर्वानुमान रन पर आधारित।"),
                  triggers=[L(lang, "If the rain chance for the next 2 days goes above 60 percent, hold irrigation.", "अगले 2 दिन में बारिश की संभावना 60 प्रतिशत से ऊपर जाए तो सिंचाई रोकें।"),
                            L(lang, "If leaves roll or the soil cracks, irrigate even if rain is forecast.", "पत्तियां मुड़ें या मिट्टी में दरार पड़ें तो बारिश के पूर्वानुमान के बावजूद सिंचाई करें।")],
                  next_check=L(lang, "Check again tomorrow morning.", "कल सुबह फिर देखें।"), action=act)


def harvest_brief(lang, d, info, field):
    plan = d["plan"]
    if not plan or info.get("stage") is None and info["phase"] != "not_sown":
        return None
    title = L(lang, "Harvest decision", "कटाई का फ़ैसला")
    ready = field.get("status") == "ready"
    if info["phase"] in ("growing", "not_sown") and info["days_to_maturity"] > 10 and not ready:
        n, dt = info["days_to_maturity"], info["maturity_date"].strftime("%d %b")
        why = [L(lang, f"The crop is expected to mature around {dt}.", f"फसल लगभग {dt} तक पकने की उम्मीद है।"),
               L(lang, "We compare harvest days when about 10 days remain. If your crop is ready earlier, mark the field as ready to harvest.",
                 "लगभग 10 दिन बचने पर हम कटाई के दिनों की तुलना करते हैं। फसल पहले तैयार हो तो खेत को 'कटाई के लिए तैयार' चिह्नित करें।")]
        return _brief(kind="harvest", level="ok", title=title, action="early",
                      headline=L(lang, f"Not harvest time yet. Expected around {dt}, about {n} days from now.", f"अभी कटाई का समय नहीं। लगभग {dt} को, यानी करीब {n} दिन बाद।"),
                      why=why, next_check=L(lang, "Check again in a week.", "एक हफ्ते बाद फिर देखें।"))
    best, now, known = plan["best"], plan["harvest_today"], d["price_known"]
    show = (lambda o: inr(o["expected_loss_rs"])) if known else (lambda o: f"{o['expected_loss_pct']}%")
    level = "alert" if now["p_rain_on_drying_days"] >= 0.5 else "watch" if now["p_rain_on_drying_days"] >= 0.2 else "ok"
    b = best["start_in_days"]
    head = (L(lang, "Start harvest today", "आज ही कटाई शुरू करें") if b == 0 else
            L(lang, f"Wait {b} day(s), start on {fdate(best['date'])}", f"{b} दिन रुकें, {fdate(best['date'])} से कटाई शुरू करें"))
    why = [L(lang, f"If you start today, {pct(now['p_rain_on_drying_days'])} of forecasts bring damaging rain while the crop dries. Expected loss {show(now)}.",
             f"आज शुरू करने पर फसल सूखने के दौरान {pct(now['p_rain_on_drying_days'])} पूर्वानुमानों में नुकसानदेह बारिश है। अनुमानित नुकसान {show(now)}।")]
    if b > 0:
        why.append(L(lang, f"Starting on {fdate(best['date'])} lowers the expected loss to {show(best)}.", f"{fdate(best['date'])} से शुरू करने पर अनुमानित नुकसान घटकर {show(best)} रह जाता है।"))
        why.append(L(lang, f"Chance of a heavy storm before that day: {pct(best['p_storm_before_start'])}.", f"उस दिन से पहले भारी तूफ़ान की संभावना: {pct(best['p_storm_before_start'])}।"))
    if d["drainage"] == "poor":
        why.append(L(lang, "Your soil drains slowly, so wet harvest conditions hurt more.", "आपकी मिट्टी में पानी धीरे निकलता है, इसलिए गीली कटाई ज़्यादा नुकसान करती है।"))
    if not known:
        why.append(L(lang, "Enter your price or wait for mandi data to see the value in rupees.", "रुपये में असर देखने के लिए अपनी कीमत भरें या मंडी का डेटा आने दें।"))
    opts = plan["options"][:5]
    rows = []
    for o in opts:
        when = L(lang, "Today", "आज") if o["start_in_days"] == 0 else L(lang, f"In {o['start_in_days']} days", f"{o['start_in_days']} दिन बाद") + f" ({fdate(o['date'])})"
        rows.append([when, pct(o["p_rain_on_drying_days"]), show(o)])
    best_i = next(i for i, o in enumerate(opts) if o["start_in_days"] == b)
    second = sorted(opts, key=lambda o: o["expected_loss_rs"])[1] if len(opts) > 1 else None
    close = second is not None and plan["crop_value_rs"] > 1 and (second["expected_loss_rs"] - best["expected_loss_rs"]) < 0.01 * plan["crop_value_rs"]
    note = L(lang, f"Based on {d['ens'].data['n_members']} forecast runs.", f"{d['ens'].data['n_members']} पूर्वानुमान रन पर आधारित।")
    if close:
        note += " " + L(lang, "Two days are almost equal, so choose the one that suits your labour and machine.", "दो दिन लगभग बराबर हैं, इसलिए जो आपके मज़दूर और मशीन के लिए सुविधाजनक हो वह चुनें।")
    return _brief(kind="harvest", level=level, title=title, headline=head, why=why, action="plan", start_day=b,
                  options={"cols": [L(lang, "Start", "शुरुआत"), L(lang, "Rain chance on drying days", "सुखाने के दिनों में बारिश की संभावना"), L(lang, "Expected loss", "अनुमानित नुकसान")],
                           "rows": rows, "best": best_i},
                  confidence=_conf(best["p_rain_on_drying_days"]), conf_note=note,
                  triggers=[L(lang, "If the rain chance on your drying days rises above 30 percent, harvest earlier or arrange covering and drying space.", "सुखाने के दिनों में बारिश की संभावना 30 प्रतिशत से ऊपर जाए तो कटाई जल्दी करें या ढकने और सुखाने की जगह तैयार रखें।"),
                            L(lang, "If the grain is still soft or green, do not harvest only because of the forecast. Check ripeness first.", "दाना अब भी नरम या हरा हो तो केवल पूर्वानुमान के कारण कटाई न करें। पहले पकना जांचें।")],
                  next_check=L(lang, "Check again tomorrow morning and just before cutting.", "कल सुबह और कटाई से ठीक पहले फिर देखें।"))


def sell_brief(lang, d, qty):
    title = L(lang, "Selling decision", "बिक्री का फ़ैसला")
    m = d["mandi"]
    if not m.ok:
        return _brief(kind="sell", level="watch", title=title, action="none",
                      headline=L(lang, "No mandi price found near you right now", "अभी आपके पास मंडी भाव नहीं मिला"),
                      why=[(m.error or "")[:220]],
                      triggers=[L(lang, "Call your local mandi or trader to get today's price.", "आज का भाव जानने के लिए अपनी स्थानीय मंडी या व्यापारी से फ़ोन पर पूछें।")],
                      next_check=L(lang, "Check again tomorrow.", "कल फिर देखें।"))
    opts = m.data["options"]
    top = opts[0]
    tr = d.get("trend") or {"n_days": 0, "pct_change": None}
    rain_risk = (d["risk"] or {}).get("p_damaging_rain", 0)
    rev = inr(top["net_rs_qtl"] * qty)
    why = [L(lang, f"{top['market']} gives {inr(top['net_rs_qtl'])} per quintal after transport ({inr(top['modal_rs_qtl'])} market price, {top['road_km']} km).",
             f"{top['market']} में परिवहन के बाद {inr(top['net_rs_qtl'])} प्रति क्विंटल मिलेगा ({inr(top['modal_rs_qtl'])} मंडी भाव, {top['road_km']} किमी)।"),
           L(lang, f"For {qty:g} quintal this is about {rev}.", f"{qty:g} क्विंटल के लिए यह लगभग {rev} होता है।")]
    act, level = "sell", "ok"
    if tr["pct_change"] is None:
        why.append(L(lang, f"Price trend: collecting data ({tr['n_days']} day(s) so far). It becomes useful after about 3 days of use.", f"भाव का रुझान: डेटा जमा हो रहा है (अब तक {tr['n_days']} दिन)। करीब 3 दिन के उपयोग के बाद यह काम का होगा।"))
        head = L(lang, f"Sell at {top['market']} for the best net price", f"सबसे अच्छे शुद्ध भाव के लिए {top['market']} में बेचें")
    elif tr["pct_change"] >= 3 and rain_risk < 0.4:
        act = "hold"
        why.append(L(lang, f"Prices rose about {tr['pct_change']}% over the last {tr['n_days']} days.", f"पिछले {tr['n_days']} दिनों में भाव लगभग {tr['pct_change']}% बढ़े हैं।"))
        head = L(lang, f"You may hold a few days if storage is dry and safe, then sell at {top['market']}", f"भंडारण सूखा और सुरक्षित हो तो कुछ दिन रोक सकते हैं, फिर {top['market']} में बेचें")
    elif tr["pct_change"] <= -3:
        act, level = "sell_soon", "watch"
        why.append(L(lang, f"Prices fell about {abs(tr['pct_change'])}% over the last {tr['n_days']} days.", f"पिछले {tr['n_days']} दिनों में भाव लगभग {abs(tr['pct_change'])}% गिरे हैं।"))
        head = L(lang, f"Sell soon at {top['market']}, prices are falling", f"जल्दी {top['market']} में बेचें, भाव गिर रहे हैं")
    else:
        why.append(L(lang, f"Prices were steady over the last {tr['n_days']} days.", f"पिछले {tr['n_days']} दिनों में भाव स्थिर रहे।"))
        head = L(lang, f"Sell at {top['market']} for the best net price", f"सबसे अच्छे शुद्ध भाव के लिए {top['market']} में बेचें")
    if rain_risk >= 0.4:
        level = "watch"
        why.append(L(lang, f"Rain is likely ({pct(rain_risk)} chance of damaging rain), so do not leave produce uncovered.", f"बारिश की संभावना है (नुकसानदेह बारिश {pct(rain_risk)}), इसलिए उपज खुली न छोड़ें।"))
    rows = [[o["market"], inr(o["net_rs_qtl"]), f"{o['road_km']}", fdate(o["price_date"])] for o in opts[:3]]
    stale = any(o["road_estimated"] for o in opts[:1])
    return _brief(kind="sell", level=level, title=title, headline=head, why=why, action=act,
                  options={"cols": [L(lang, "Market", "मंडी"), L(lang, "Net price per quintal", "शुद्ध भाव प्रति क्विंटल"), L(lang, "Road km", "सड़क किमी"), L(lang, "Price date", "भाव की तारीख")], "rows": rows, "best": 0},
                  confidence="medium" if stale else "high",
                  conf_note=L(lang, "Reported market prices can differ from what a trader offers you.", "रिपोर्ट किया गया मंडी भाव और व्यापारी का दिया भाव अलग हो सकता है।"),
                  triggers=[L(lang, "Call the mandi or trader to confirm the price before loading the truck.", "ट्रक लादने से पहले मंडी या व्यापारी से फ़ोन पर भाव पक्का करें।"),
                            L(lang, "If transport cost is higher than assumed, the nearer mandi may win.", "परिवहन खर्च अनुमान से ज़्यादा हो तो नज़दीकी मंडी बेहतर हो सकती है।")],
                  next_check=L(lang, "Check prices again tomorrow.", "कल भाव फिर देखें।"))
