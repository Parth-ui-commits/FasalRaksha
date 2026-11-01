import altair as alt
import pandas as pd
import streamlit as st
from core.i18n import L

GREEN, GOLD, RED, BLUE = "#2F6B3F", "#C98A1B", "#B42318", "#3B6EA8"


def show(chart, h=260):
    st.altair_chart(chart.properties(width="container", height=h))


def rain_band(lang, df):
    base = alt.Chart(df).encode(x=alt.X("day:O", sort=None, title=None, axis=alt.Axis(labelAngle=0)))
    band = base.mark_area(opacity=0.22, color=GREEN).encode(y=alt.Y("rain_p10:Q", title=L(lang, "Rain (mm)", "बारिश (मिमी)")), y2="rain_p90:Q")
    line = base.mark_line(color=GREEN, point=True).encode(y="rain_mean:Q")
    show(band + line)


def damaging_prob(lang, df):
    bars = alt.Chart(df).mark_bar(color=GOLD).encode(x=alt.X("day:O", sort=None, title=None, axis=alt.Axis(labelAngle=0)),
                                                    y=alt.Y("p_damaging:Q", title=None, scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%")))
    show(bars)


def temp_line(lang, df):
    ln = alt.Chart(df).mark_line(color=RED, point=True).encode(x=alt.X("day:O", sort=None, title=None, axis=alt.Axis(labelAngle=0)),
                                                              y=alt.Y("tmax_mean:Q", title=L(lang, "Highest temperature (C)", "सबसे ज़्यादा तापमान (डिग्री)"), scale=alt.Scale(zero=False)))
    show(ln, 200)


def water_bars(lang, et):
    et = et.melt("day", var_name="kind", value_name="mm")
    et["kind"] = et["kind"].map({"et0": L(lang, "Crop water loss (ET0)", "पानी की खपत (ET0)"), "rain": L(lang, "Rain", "बारिश")})
    ch = alt.Chart(et).mark_bar().encode(x=alt.X("day:O", sort=None, title=None, axis=alt.Axis(labelAngle=0)), y=alt.Y("mm:Q", title="mm"), xOffset="kind:N",
                                         color=alt.Color("kind:N", scale=alt.Scale(range=[GOLD, GREEN]), legend=alt.Legend(title=None)))
    show(ch, 240)


def wind_rain(lang, hr):
    wind = alt.Chart(hr).mark_line(color=GREEN).encode(x=alt.X("time:T", title=None), y=alt.Y("wind:Q", title=L(lang, "Wind (km/h)", "हवा (किमी/घंटा)")))
    limit = alt.Chart(pd.DataFrame({"y": [15]})).mark_rule(color=RED, strokeDash=[4, 4]).encode(y="y:Q")
    rain = alt.Chart(hr).mark_bar(color=BLUE, opacity=0.7).encode(x="time:T", y=alt.Y("rain:Q", title=L(lang, "Rain (mm)", "बारिश (मिमी)")))
    show(alt.layer(wind + limit, rain).resolve_scale(y="independent"), 240)


def net_price(lang, opts):
    bars = alt.Chart(opts).mark_bar(color=GREEN).encode(y=alt.Y("market:N", sort="-x", title=None),
                                                       x=alt.X("net_rs_qtl:Q", title=L(lang, "Net price per quintal", "शुद्ध भाव प्रति क्विंटल")))
    show(bars, 38 * len(opts) + 40)


def price_trend(lang, series):
    df = pd.DataFrame(series)
    ln = alt.Chart(df).mark_line(color=GOLD, point=True).encode(x=alt.X("date:T", title=None), y=alt.Y("price:Q", title=L(lang, "Average price per quintal", "औसत भाव प्रति क्विंटल"), scale=alt.Scale(zero=False)))
    show(ln, 200)


def scan_bars(lang, top):
    df = pd.DataFrame([{"name": r["name"], "score": r["score"]} for r in top])
    ch = alt.Chart(df).mark_bar(color=GREEN).encode(y=alt.Y("name:N", sort="-x", title=None),
                                                   x=alt.X("score:Q", title=L(lang, "Confidence", "भरोसा"), scale=alt.Scale(domain=[0, 1]), axis=alt.Axis(format="%")))
    show(ch, 30 * len(df) + 50)


def cost_bars(lang, by_kind, labels):
    df = pd.DataFrame([{"kind": labels.get(k, k), "rs": v} for k, v in by_kind.items() if v > 0])
    if df.empty:
        return
    ch = alt.Chart(df).mark_bar(color=GOLD).encode(y=alt.Y("kind:N", sort="-x", title=None), x=alt.X("rs:Q", title="Rs"))
    show(ch, 30 * len(df) + 50)
