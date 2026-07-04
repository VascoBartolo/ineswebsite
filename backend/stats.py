PRESENCIAL_NET_RATE = 0.70
ONLINE_NET_RATE = 1.00


def net_profit(regime, price):
    price = float(price)
    if (regime or "").lower() == "presencial":
        return round(price * PRESENCIAL_NET_RATE, 2)
    return round(price * ONLINE_NET_RATE, 2)


def summarize(rows):
    confirmed = [r for r in rows if r["status"] == "confirmado"]
    faturado = round(sum(float(r["price"]) for r in confirmed), 2)
    lucro = round(sum(net_profit(r["regime"], r["price"]) for r in confirmed), 2)

    by_regime = {}
    for reg in ("presencial", "online"):
        subset = [r for r in confirmed if (r["regime"] or "").lower() == reg]
        by_regime[reg] = {
            "count": len(subset),
            "faturado": round(sum(float(r["price"]) for r in subset), 2),
            "lucro": round(sum(net_profit(r["regime"], r["price"]) for r in subset), 2),
        }

    loc_map = {}
    for r in confirmed:
        if (r["regime"] or "").lower() != "presencial":
            continue
        key = r.get("local_consulta") or "—"
        e = loc_map.setdefault(key, {"local_consulta": key, "count": 0, "faturado": 0.0, "lucro": 0.0})
        e["count"] += 1
        e["faturado"] = round(e["faturado"] + float(r["price"]), 2)
        e["lucro"] = round(e["lucro"] + net_profit(r["regime"], r["price"]), 2)
    by_location = sorted(loc_map.values(), key=lambda e: e["lucro"], reverse=True)

    return {
        "count": len(confirmed),
        "cancelled_count": sum(1 for r in rows if r["status"] == "cancelado"),
        "faturado": faturado,
        "lucro_liquido": lucro,
        "by_regime": by_regime,
        "by_location": by_location,
    }


def _period_key(d, group_by):
    if group_by == "day":
        return d.isoformat()
    if group_by == "month":
        return f"{d.year}-{d.month:02d}"
    iso = d.isocalendar()  # (year, week, weekday)
    return f"{iso[0]}-W{iso[1]:02d}"


def build_series(rows, group_by):
    confirmed = [r for r in rows if r["status"] == "confirmado"]
    buckets = {}
    for r in confirmed:
        k = _period_key(r["slot_date"], group_by)
        e = buckets.setdefault(k, {"period": k, "count": 0, "lucro_liquido": 0.0})
        e["count"] += 1
        e["lucro_liquido"] = round(e["lucro_liquido"] + net_profit(r["regime"], r["price"]), 2)
    return [buckets[k] for k in sorted(buckets)]
