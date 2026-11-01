"""Turns numbers into plain-language advice in English or Hindi. Deterministic, so it works even if the LLM is down."""
from datetime import datetime
from urllib.parse import quote
from .crops import CROPS, FROST_TMIN_C
from .i18n import t, CROP_NAMES

RANK = {"ok": 0, "watch": 1, "alert": 2}


def inr(n):
    n = int(round(n))
    s = str(abs(n))
    if len(s) > 3:
        head, tail, parts = s[:-3], s[-3:], []
        while len(head) > 2:
            parts.insert(0, head[-2:]); head = head[:-2]
        if head:
            parts.insert(0, head)
        s = ",".join(parts + [tail])
    return ("-" if n < 0 else "") + "₹" + s


def pct(p):
    return f"{round(p * 100)}%"


def fdate(s):
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M"):
        try:
            return datetime.strptime(s, fmt).strftime("%d %b")
        except ValueError:
            pass
    return s


def _card(level, title, headline, detail):
    return {"level": level, "title": title, "headline": headline, "detail": detail}


def _na(lang, title):
    return _card("watch", title, t(lang, "unavailable_head"), t(lang, "unavailable"))


def harvest(lang, d, crop):
    title = t(lang, "card_harvest")
    plan = d["plan"]
    if not plan:
        return _na(lang, title)
    best, now, known = plan["best"], plan["harvest_today"], d["price_known"]
    show = (lambda o: inr(o["expected_loss_rs"])) if known else (lambda o: f'{o["expected_loss_pct"]}%')
    level = "alert" if now["p_rain_on_drying_days"] >= 0.5 else "watch" if now["p_rain_on_drying_days"] >= 0.2 else "ok"
    if best["start_in_days"] == 0:
        head = t(lang, "adv_harvest_now")
        det = t(lang, "adv_harvest_detail_now", n=plan["assumptions"]["dry_days"], today=show(now))
    else:
        head = t(lang, "adv_harvest_wait", d=best["start_in_days"], date=fdate(best["date"]))
        save = inr(plan["saving_vs_today_rs"]) if known else f'{round(now["expected_loss_pct"] - best["expected_loss_pct"], 1)}%'
        det = t(lang, "adv_harvest_detail_wait", p=pct(now["p_rain_on_drying_days"]), today=show(now),
                date=fdate(best["date"]), best=show(best), save=save)
    if not known:
        det += " " + t(lang, "adv_harvest_pct_note")
    return _card(level, title, head, det)


def weather_card(lang, d, crop):
    title, r = t(lang, "card_weather"), d["risk"]
    if not r:
        return _na(lang, title)
    c = CROPS[crop]
    level = ("alert" if r["p_heavy_rain"] >= 0.3 or r["p_heat_stress"] >= 0.5
             else "watch" if r["p_damaging_rain"] >= 0.4 or r["p_heat_stress"] >= 0.2 else "ok")
    det = t(lang, "adv_weather_detail", mm=c["rain_sens_mm"], pd=pct(r["p_damaging_rain"]), ph=pct(r["p_heavy_rain"]),
            t=c["heat_tmax"], crop=CROP_NAMES[crop][lang], pt=pct(r["p_heat_stress"]), er=r["expected_rain_mm"])
    fc = d["fc"]
    if fc.ok:
        tmin = min(x for x in fc.data["daily"]["temperature_2m_min"][:5] if x is not None)
        if tmin <= FROST_TMIN_C:
            det += " " + t(lang, "adv_cold", tmin=round(tmin, 1))
            level = max(level, "watch", key=RANK.get)
    return _card(level, title, t(lang, "adv_weather_" + level), det)


def river_card(lang, d, crop):
    title, res = t(lang, "card_river"), d["river"]
    if not res.ok:
        return _na(lang, title)
    r = res.data
    if not r.get("river_nearby"):
        return _card("ok", title, t(lang, "adv_river_none"), t(lang, "adv_river_none_detail"))
    lvl = r["level"]
    level = {"normal": "ok", "watch": "watch", "high": "alert", "severe": "alert"}[lvl]
    return _card(level, title, t(lang, "adv_river_" + lvl), t(lang, "adv_river_detail", r=r["ratio_vs_past_p90"]))


def water_card(lang, d, crop):
    title, w = t(lang, "card_water"), d["water"]
    if not w:
        return _na(lang, title)
    level = "ok" if w["gap_mm"] <= 5 else "watch" if w["gap_mm"] <= 25 else "alert"
    return _card(level, title, t(lang, "adv_water_" + level),
                 t(lang, "adv_water_detail", need=w["need_mm"], rain=w["useful_rain_mm"],
                   gap=w["gap_mm"], gap_dry=w["gap_dry_mm"]))


def fwin(lang, w):
    return t(lang, "win_fmt", date=fdate(w["start"]), a=w["start"][11:16], b=w["end"][11:16])


def spray_card(lang, d, crop):
    title, wins = t(lang, "card_spray"), d["spray"]
    if wins is None:
        return _na(lang, title)
    if not wins:
        return _card("watch", title, t(lang, "adv_spray_no"), t(lang, "adv_spray_no_detail"))
    return _card("ok", title, t(lang, "adv_spray_yes", list="; ".join(fwin(lang, w) for w in wins)),
                 t(lang, "adv_spray_detail"))


def market_card(lang, d, crop):
    title, m = t(lang, "card_market"), d["mandi"]
    if not m.ok:
        return _card("watch", title, t(lang, "adv_market_none"), t(lang, "adv_market_none_detail"))
    o = m.data["options"][0]
    return _card("ok", title,
                 t(lang, "adv_market_head", market=o["market"], district=o["district"], net=inr(o["net_rs_qtl"])),
                 t(lang, "adv_market_detail", modal=inr(o["modal_rs_qtl"]), tr=inr(o["transport_rs_qtl"]),
                   km=o["road_km"], date=fdate(o["price_date"])))


def build_cards(lang, d, crop):
    return {"harvest": harvest(lang, d, crop), "weather": weather_card(lang, d, crop),
            "river": river_card(lang, d, crop), "water": water_card(lang, d, crop),
            "spray": spray_card(lang, d, crop), "market": market_card(lang, d, crop)}


def priority(cards):
    return max(cards.values(), key=lambda c: RANK[c["level"]])


def share_text(lang, place, crop, cards):
    lines = [f"FasalRaksha | {place} | {CROP_NAMES[crop][lang]}"]
    for k in ("harvest", "weather", "river", "water", "spray", "market"):
        c = cards[k]
        lines.append(f'{c["title"]}: {c["headline"]}')
    return "\n".join(lines)


def whatsapp_url(text):
    return "https://wa.me/?text=" + quote(text)
