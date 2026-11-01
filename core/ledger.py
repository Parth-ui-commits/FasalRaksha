from . import db

KINDS = ["sowing", "irrigation", "fertilizer", "spray", "weeding", "labour", "harvest", "other"]


def summary(field_id, area_acre=1.0):
    logs = db.query("SELECT * FROM logs WHERE field_id=? ORDER BY date DESC, id DESC", (field_id,))
    sales = db.query("SELECT * FROM sales WHERE field_id=? ORDER BY date DESC, id DESC", (field_id,))
    cost = sum(float(x["cost_rs"] or 0) for x in logs)
    by_kind = {}
    for x in logs:
        by_kind[x["kind"]] = by_kind.get(x["kind"], 0) + float(x["cost_rs"] or 0)
    revenue = sum(float(s["qty_qtl"]) * float(s["price_rs_qtl"]) for s in sales)
    sold = sum(float(s["qty_qtl"]) for s in sales)
    return {"logs": logs, "sales": sales, "cost": cost, "by_kind": by_kind, "revenue": revenue, "qty_sold": sold,
            "profit": revenue - cost, "cost_per_acre": cost / max(area_acre, 0.01)}
