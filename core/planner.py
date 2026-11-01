"""7-day work plan: weather, irrigation, harvest, spray windows and alerts, day by day."""
from datetime import datetime
import numpy as np
from . import spray
from .crops import CROPS, IMD_HEAVY_RAIN_MM, FROST_TMIN_C
from .i18n import L

DAY_HI = ["सोम", "मंगल", "बुध", "गुरु", "शुक्र", "शनि", "रवि"]


def _day(lang, s):
    d = datetime.strptime(s, "%Y-%m-%d")
    return (DAY_HI[d.weekday()] if lang == "hi" else d.strftime("%a")) + d.strftime(" %d %b")


def week_plan(lang, d, info, field, irr, harv, days=7):
    if not d["ens"].ok:
        return []
    ens = d["ens"].data
    c = CROPS[field["crop"]]
    rain, tmax = np.array(ens["rain_mm"], float), np.array(ens["tmax_c"], float)
    n = min(days, rain.shape[1])
    wins = {}
    if d["fc"].ok and d["now_local"]:
        for w in spray.spray_windows(d["fc"].data["hourly"], d["now_local"], hours_ahead=168, min_len=3, top=100):
            day = w["start"][:10]
            length = int(w["end"][11:13]) - int(w["start"][11:13])
            if day not in wins or length > wins[day][2]:
                wins[day] = (w["start"][11:16], w["end"][11:16], length)
    tmin = d["fc"].data["daily"]["temperature_2m_min"] if d["fc"].ok else []
    rows = []
    for i in range(n):
        date_s = ens["dates"][i]
        tasks, alerts = [], []
        if irr:
            if irr["action"] == "now" and i == 0:
                tasks.append(L(lang, "Irrigate", "सिंचाई करें"))
            elif irr["action"] == "soon" and i == 2:
                tasks.append(L(lang, "Irrigate if no rain came", "बारिश न आई हो तो सिंचाई करें"))
            elif irr["action"] == "wait" and i == 2:
                tasks.append(L(lang, "Re-check soil moisture", "मिट्टी की नमी फिर जांचें"))
        if harv and harv.get("action") == "plan" and harv["start_day"] == i:
            tasks.append(L(lang, "Start harvest", "कटाई शुरू करें"))
        if info.get("next") and info.get("days_to_next") == i + 0 and info["days_to_next"] <= n:
            nm = info["next"][2] if lang == "hi" else info["next"][1]
            tasks.append(L(lang, f"New stage: {nm}", f"नई अवस्था: {nm}"))
        if date_s in wins:
            a, b, _ = wins[date_s]
            tasks.append(L(lang, f"Good spray hours {a} to {b}", f"छिड़काव के अच्छे घंटे {a} से {b}"))
        if (rain[:, i] >= IMD_HEAVY_RAIN_MM).mean() >= 0.3:
            alerts.append(L(lang, "Heavy rain likely", "भारी बारिश की संभावना"))
        if (tmax[:, i] >= c["heat_tmax"]).mean() >= 0.5:
            alerts.append(L(lang, "Heat stress risk", "गर्मी का जोखिम"))
        if i < len(tmin) and tmin[i] is not None and tmin[i] <= FROST_TMIN_C:
            alerts.append(L(lang, "Frost risk", "पाले का जोखिम"))
        rows.append({"day": _day(lang, date_s), "rain_mm": round(float(np.median(rain[:, i])), 1),
                     "p_rain": round(float((rain[:, i] >= c["rain_sens_mm"]).mean()), 2),
                     "tmax": round(float(tmax[:, i].mean()), 1), "tasks": tasks, "alerts": alerts})
    return rows
