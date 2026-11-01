"""Builds a real price history over time: every live Agmarknet fetch is stored once per market and day.
The trend becomes meaningful after a few days of use, so it is shown honestly as 'collecting' until then."""
from datetime import datetime, timedelta
import numpy as np
from . import db


def _d(s):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(s, fmt)
        except (TypeError, ValueError):
            pass
    return None


def record(state, commodity, rows):
    seq = []
    for r in rows:
        d = _d(r.get("date"))
        if d and r.get("modal"):
            seq.append((d.strftime("%Y-%m-%d"), state, commodity, r.get("market"), r.get("district"), float(r["modal"])))
    if seq:
        db.executemany("INSERT OR REPLACE INTO prices VALUES(?,?,?,?,?,?)", seq)
    return len(seq)


def trend(commodity, states, days=14):
    since = (datetime.utcnow() - timedelta(days=days)).strftime("%Y-%m-%d")
    marks = ",".join("?" * len(states))
    rows = db.query(f"SELECT date, AVG(modal) AS price, COUNT(*) AS markets FROM prices "
                    f"WHERE commodity=? AND state IN ({marks}) AND date>=? GROUP BY date ORDER BY date",
                    (commodity, *states, since))
    out = {"n_days": len(rows), "series": rows, "pct_change": None, "last": rows[-1]["price"] if rows else None}
    if len(rows) >= 3:
        x = np.array([(datetime.strptime(r["date"], "%Y-%m-%d") - datetime.strptime(rows[0]["date"], "%Y-%m-%d")).days for r in rows], float)
        y = np.array([r["price"] for r in rows], float)
        slope = float(np.polyfit(x, y, 1)[0])
        out["pct_change"] = round(slope * (x[-1] - x[0]) / float(y.mean()) * 100, 1)
    return out
