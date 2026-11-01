"""Look and feel: farm colours, a field landscape that changes with the real forecast, and small SVG ornaments."""
import html, random
from urllib.parse import quote

esc = html.escape

SKY = {"clear": ("#79B8E4", "#EAF4F8"), "cloudy": ("#8D9CAA", "#D8DEE3"), "rain": ("#667A8C", "#B1BCC6"),
       "storm": ("#46525F", "#8A95A0"), "hot": ("#F0A04B", "#FBE3B8"), "night": ("#14213D", "#2E4A76")}

_TILE = ("<svg xmlns='http://www.w3.org/2000/svg' width='140' height='140'><g fill='none' stroke='#8A6D2B' stroke-opacity='.085' "
         "stroke-width='1.5' stroke-linecap='round'><path d='M70 120V52'/><path d='M70 66q-12-4-14-16M70 66q12-4 14-16M70 82q-12-4-14-16"
         "M70 82q12-4 14-16M70 98q-12-4-14-16M70 98q12-4 14-16M70 50q0-12 0-20'/></g></svg>")

CSS = """
<style>
#MainMenu, footer {visibility: hidden;}
.stApp {background-color: #F6F0E0; background-image: url("data:image/svg+xml;utf8,__TILE__");}
.block-container {padding-top: 1.4rem; max-width: 1240px;}
h1, h2, h3 {font-family: Georgia, 'Noto Serif Devanagari', serif; color: #3B2A1A; letter-spacing: -0.01em;}
section[data-testid="stSidebar"] {background: #ECE2C8; border-right: 1px solid #D8CBA6;}
.brand {display: flex; align-items: center; gap: 10px; padding: 4px 0 14px 0; border-bottom: 2px dotted #C9B98E; margin-bottom: 12px;}
.brand b {font-family: Georgia, serif; font-size: 1.35rem; color: #2F6B3F;} .brand small {display: block; color: #6B5B3A; font-size: .72rem;}
.hero {position: relative; border-radius: 12px; overflow: hidden; height: 250px; margin-bottom: 18px; border: 1px solid #CDBF95; box-shadow: 0 8px 24px rgba(60,40,10,.14);}
.hero svg {width: 100%; height: 100%; display: block;}
.hero-text {position: absolute; left: 30px; top: 26px; color: #fff; text-shadow: 0 1px 8px rgba(0,0,0,.55); max-width: 62%;}
.hero-title {font-family: Georgia, 'Noto Serif Devanagari', serif; font-size: 2rem; font-weight: 700; line-height: 1.15;}
.hero-sub {font-size: 1rem; margin-top: 6px;}
@keyframes drift {0% {transform: translateX(-34px);} 100% {transform: translateX(34px);}}
@keyframes fall {0% {transform: translateY(-40px); opacity: 0;} 25% {opacity: .85;} 100% {transform: translateY(250px); opacity: 0;}}
@keyframes sway {0% {transform: rotate(-1.2deg);} 100% {transform: rotate(1.2deg);}}
.drift {animation: drift 18s ease-in-out infinite alternate;} .rain {stroke: #E3EEF6; stroke-width: 1.6; animation: fall 1.1s linear infinite;}
.card {background: #FFFBF2; border: 1px solid #DDD0A8; border-left: 6px solid #9aa79d; border-radius: 8px; padding: 16px 18px;
       min-height: 178px; margin-bottom: 14px; box-shadow: 0 6px 16px rgba(80,55,20,.07);}
.card.ok {border-left-color: #2F6B3F;} .card.watch {border-left-color: #C98A1B;} .card.alert {border-left-color: #B42318;}
.label {font-size: .72rem; text-transform: uppercase; letter-spacing: .08em; color: #6B5B3A; margin-right: 8px;}
.chip {display: inline-block; font-size: .72rem; font-weight: 700; padding: 2px 9px; border-radius: 10px;}
.chip.ok {background: #DDEEDD; color: #1F5130;} .chip.watch {background: #FBEBC8; color: #7A4B0A;} .chip.alert {background: #FBD9D4; color: #8A1C12;}
.head {font-size: 1.1rem; font-weight: 650; margin: .45rem 0 .4rem 0; line-height: 1.35; color: #2A2A22;}
.body {font-size: .93rem; color: #3A3A30; line-height: 1.55;}
.priority {border: 1px solid #DDD0A8; border-left: 7px solid #2F6B3F; background: #FFFBF2; padding: 14px 20px; border-radius: 8px; margin-bottom: 16px;}
.priority.watch {border-left-color: #C98A1B;} .priority.alert {border-left-color: #B42318;} .priority .head {font-size: 1.3rem; margin: .2rem 0 0 0;}
.note {color: #6B5B3A; font-size: .82rem;}
.tile {background: #FFFBF2; border: 1px solid #DDD0A8; border-radius: 8px; padding: 14px 16px; text-align: left; box-shadow: 0 4px 12px rgba(80,55,20,.06);}
.tile .n {font-family: Georgia, serif; font-size: 1.9rem; color: #2F6B3F; line-height: 1.1;} .tile .t {font-size: .78rem; color: #6B5B3A; text-transform: uppercase; letter-spacing: .06em;}
.fieldcard {background: #FFFBF2; border: 1px solid #DDD0A8; border-radius: 10px; padding: 16px 18px; margin-bottom: 14px; box-shadow: 0 6px 16px rgba(80,55,20,.07);}
.fieldcard .nm {font-family: Georgia, 'Noto Serif Devanagari', serif; font-size: 1.15rem; color: #3B2A1A; font-weight: 700;}
.bar {height: 9px; border-radius: 6px; background: #E8DDBB; overflow: hidden; margin: 8px 0;} .bar i {display: block; height: 100%; background: linear-gradient(90deg, #4C8F4A, #D9A441);}
.tl {display: flex; width: 100%; height: 34px; border-radius: 8px; overflow: hidden; border: 1px solid #CDBF95; margin: 6px 0 4px 0; position: relative;}
.seg {display: flex; align-items: center; justify-content: center; font-size: .66rem; color: #fff; overflow: hidden; white-space: nowrap; border-right: 1px solid rgba(255,255,255,.55);}
.seg.todo {background: #CDBF95; color: #5B4A25;} .seg.done {background: #6FA06A;} .seg.now {background: #2F6B3F; font-weight: 700;}
.marker {position: absolute; top: -3px; width: 3px; height: 40px; background: #B42318;}
.brief {background: #FFFBF2; border: 1px solid #DDD0A8; border-left: 7px solid #2F6B3F; border-radius: 10px; padding: 18px 22px; margin-bottom: 18px; box-shadow: 0 6px 18px rgba(80,55,20,.08);}
.brief.watch {border-left-color: #C98A1B;} .brief.alert {border-left-color: #B42318;}
.brief .head {font-size: 1.3rem; margin: .3rem 0 .6rem 0;}
.brief h5 {font-size: .74rem; text-transform: uppercase; letter-spacing: .08em; color: #6B5B3A; margin: 14px 0 4px 0;}
.brief ul {margin: 0 0 0 1.1rem; padding: 0;} .brief li {margin-bottom: 3px; line-height: 1.5;}
.brief table {width: 100%; border-collapse: collapse; font-size: .9rem; margin-top: 4px;}
.brief th {text-align: left; color: #6B5B3A; font-weight: 600; border-bottom: 1px solid #DDD0A8; padding: 5px 8px;} .brief td {padding: 6px 8px; border-bottom: 1px solid #EFE6C9; vertical-align: top;}
.brief tr.best td {background: #E8F2E4; font-weight: 600;}
.pips {display: inline-flex; gap: 3px; vertical-align: middle; margin-left: 6px;} .pips i {width: 18px; height: 7px; border-radius: 4px; background: #D9CFAE;} .pips i.on {background: #2F6B3F;}
.week {width: 100%; border-collapse: collapse; background: #FFFBF2; border: 1px solid #DDD0A8; border-radius: 8px; overflow: hidden; font-size: .9rem;}
.week th {background: #ECE2C8; text-align: left; padding: 8px 10px; color: #5B4A25; font-size: .78rem; text-transform: uppercase; letter-spacing: .05em;}
.week td {padding: 9px 10px; border-top: 1px solid #EFE6C9; vertical-align: top;}
.pill {display: inline-block; padding: 2px 9px; border-radius: 10px; font-size: .78rem; margin: 2px 4px 2px 0;}
.pill.task {background: #DDEEDD; color: #1F5130;} .pill.alert {background: #FBD9D4; color: #8A1C12;}
.feature {background: #FFFBF2; border: 1px solid #DDD0A8; border-top: 4px solid #D9A441; border-radius: 8px; padding: 14px 16px; min-height: 120px; margin-bottom: 12px;}
.feature b {font-family: Georgia, 'Noto Serif Devanagari', serif; color: #3B2A1A;} .feature div {font-size: .88rem; color: #3A3A30; margin-top: 4px; line-height: 1.5;}
.divider {height: 22px; margin: 10px 0 14px 0; background-repeat: no-repeat; background-position: center;}
</style>
"""


def inject():
    return CSS.replace("__TILE__", quote(_TILE, safe=""))


def logo(size=38):
    return (f"<svg width='{size}' height='{size}' viewBox='0 0 40 40' xmlns='http://www.w3.org/2000/svg'><circle cx='20' cy='20' r='19' fill='#2F6B3F'/>"
            "<g stroke='#F3D98B' stroke-width='2' stroke-linecap='round' fill='none'><path d='M20 33V13'/><path d='M20 19q-6-2-7-8M20 19q6-2 7-8M20 26q-6-2-7-8M20 26q6-2 7-8M20 12q0-5 0-8'/></g></svg>")


def brand(sub):
    return f'<div class="brand">{logo()}<div><b>FasalRaksha</b><small>{esc(sub)}</small></div></div>'


def divider():
    svg = ("<svg xmlns='http://www.w3.org/2000/svg' width='220' height='22'><g stroke='#C9A24A' stroke-width='1.6' fill='none' stroke-linecap='round'>"
           "<path d='M10 11H92M128 11H210'/><path d='M110 20V6M110 11q-5-1-6-5M110 11q5-1 6-5M110 16q-5-1-6-5M110 16q5-1 6-5'/></g></svg>")
    return f'<div class="divider" style="background-image:url(\'data:image/svg+xml;utf8,{quote(svg, safe="")}\')"></div>'


def crop_color(progress, crop):
    if crop == "mustard" and 0.38 < progress < 0.8:
        return "#E2B92B"
    t = min(1.0, max(0.0, progress))
    g, o = (76, 143, 74), (217, 164, 65)
    return "#%02x%02x%02x" % tuple(int(a + (b - a) * t) for a, b in zip(g, o))


def _cloud(x, y, s, fill):
    return (f"<g transform='translate({x},{y}) scale({s})'><g class='drift'><ellipse cx='0' cy='0' rx='54' ry='19' fill='{fill}'/>"
            f"<ellipse cx='-26' cy='-8' rx='30' ry='17' fill='{fill}'/><ellipse cx='22' cy='-12' rx='34' ry='21' fill='{fill}'/></g></g>")


def hero_svg(kind="clear", night=False, progress=0.3, crop="wheat"):
    key = "night" if night else kind
    top, bot = SKY[key]
    col = crop_color(progress, crop)
    p = [f"<svg viewBox='0 0 1200 280' preserveAspectRatio='xMidYMid slice' xmlns='http://www.w3.org/2000/svg' role='img' aria-label='Farm scene'>",
         f"<defs><linearGradient id='sky' x1='0' y1='0' x2='0' y2='1'><stop offset='0' stop-color='{top}'/><stop offset='1' stop-color='{bot}'/></linearGradient>"
         "<radialGradient id='glow'><stop offset='0' stop-color='#FFF3B8' stop-opacity='.95'/><stop offset='1' stop-color='#FFE08A' stop-opacity='0'/></radialGradient></defs>",
         "<rect width='1200' height='280' fill='url(#sky)'/>"]
    rnd = random.Random(7)
    if night:
        p += [f"<circle cx='{rnd.randint(20, 1180)}' cy='{rnd.randint(8, 110)}' r='{rnd.choice([1, 1.4, 1.8])}' fill='#fff' opacity='.85'/>" for _ in range(40)]
        p.append("<circle cx='1010' cy='70' r='24' fill='#F4EBC8'/><circle cx='1020' cy='64' r='22' fill='#2A4068'/>")
    elif kind in ("clear", "hot"):
        sun = "#FF9F1C" if kind == "hot" else "#FFD45E"
        p.append(f"<circle cx='1010' cy='76' r='78' fill='url(#glow)'/><circle cx='1010' cy='76' r='27' fill='{sun}'/>")
    if kind in ("cloudy", "rain", "storm") and not night:
        shade = {"cloudy": "#F2F4F6", "rain": "#CBD3DA", "storm": "#98A3AE"}[kind]
        p += [_cloud(260, 62, 1.5, shade), _cloud(640, 42, 1.9, shade), _cloud(960, 78, 1.4, shade)]
    elif kind in ("rain", "storm") and night:
        p += [_cloud(300, 60, 1.6, "#3D4F6B"), _cloud(800, 50, 1.9, "#3D4F6B")]
    elif kind == "clear" and not night:
        p.append(_cloud(430, 58, 1.1, "#FFFFFF"))
    p.append("<path d='M0 176Q180 112 370 164T740 150T1080 138T1200 150V280H0Z' fill='#8DB48A'/>")
    p.append("<g transform='translate(110,120)'><rect x='0' y='24' width='58' height='34' fill='#C9A06B'/><polygon points='-7,26 29,0 65,26' fill='#8C4B2F'/><rect x='23' y='38' width='12' height='20' fill='#5B3A29'/></g>")
    p.append("<g transform='translate(250,118)'><rect x='-3' y='14' width='6' height='28' fill='#5B3A29'/><circle cx='0' cy='4' r='19' fill='#3F7A45'/><circle cx='-12' cy='14' r='12' fill='#4C8F4A'/><circle cx='12' cy='14' r='12' fill='#4C8F4A'/></g>")
    p.append("<path d='M0 196Q250 150 520 190T1000 180T1200 184V280H0Z' fill='#6E9C5E'/>")
    p.append("<path d='M0 204H1200V280H0Z' fill='#7B5B3A'/>")
    for i in range(-9, 10):
        x0, y0, x1, y1 = 600 + i * 6, 204, 600 + i * 150, 288
        p.append(f"<line x1='{x0}' y1='{y0}' x2='{x1}' y2='{y1}' stroke='#5E452B' stroke-width='1.4' opacity='.7'/>")
        for t in (0.1, 0.28, 0.48, 0.7, 0.93):
            x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
            h = 7 + 30 * t
            p.append(f"<path d='M{x:.0f} {y:.0f}q{h*0.15:.0f} {-h*0.5:.0f} {h*0.1:.0f} {-h:.0f}' stroke='{col}' stroke-width='{1.2 + 2.2*t:.1f}' fill='none' stroke-linecap='round'/>"
                     f"<ellipse cx='{x + h*0.1:.0f}' cy='{y - h - 2:.0f}' rx='{1.4 + 1.8*t:.1f}' ry='{3 + 4*t:.1f}' fill='{col}'/>")
    if kind in ("rain", "storm"):
        n = 70 if kind == "storm" else 42
        p += [f"<line class='rain' x1='{(x := rnd.randint(0, 1200))}' y1='{(y := rnd.randint(-20, 120))}' x2='{x - 5}' y2='{y + 16}' style='animation-delay:{rnd.random()*1.1:.2f}s'/>" for _ in range(n)]
    p.append("</svg>")
    return "".join(p)


def hero(title, subtitle, kind="clear", night=False, progress=0.3, crop="wheat"):
    return (f'<div class="hero">{hero_svg(kind, night, progress, crop)}<div class="hero-text">'
            f'<div class="hero-title">{esc(title)}</div><div class="hero-sub">{esc(subtitle)}</div></div></div>')


def scene_kind(d):
    r = d.get("risk") if d else None
    if not r:
        return "clear"
    if r["p_heavy_rain"] >= 0.3:
        return "storm"
    if r["p_damaging_rain"] >= 0.5:
        return "rain"
    if r["p_heat_stress"] >= 0.5:
        return "hot"
    if r["p_damaging_rain"] >= 0.25:
        return "cloudy"
    return "clear"


def is_night(d):
    t = (d or {}).get("now_local")
    if not t:
        return False
    h = int(t[11:13])
    return h < 6 or h >= 19
