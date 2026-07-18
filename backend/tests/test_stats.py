from datetime import date
import stats


def test_net_profit_presencial_is_70pct():
    assert stats.net_profit("presencial", 100) == 70.0


def test_net_profit_online_is_100pct():
    assert stats.net_profit("online", 50) == 50.0


def _b(regime, price, status="confirmado", local=None, d=date(2026, 7, 1)):
    return {"regime": regime, "price": price, "status": status,
            "local_consulta": local, "slot_date": d}


def test_summarize_counts_and_money():
    rows = [
        _b("presencial", 100, local="Clínica Manus"),
        _b("online", 50),
        _b("presencial", 100, status="cancelado", local="Clínica Manus"),
    ]
    s = stats.summarize(rows)
    assert s["count"] == 2
    assert s["cancelled_count"] == 1
    assert s["faturado"] == 150.0
    assert s["lucro_liquido"] == 120.0  # 70 + 50
    assert s["by_regime"]["presencial"]["lucro"] == 70.0
    assert s["by_regime"]["online"]["lucro"] == 50.0
    assert s["by_location"][0]["local_consulta"] == "Clínica Manus"
    assert s["by_location"][0]["lucro"] == 70.0


def test_build_series_weekly_buckets():
    rows = [
        _b("online", 50, d=date(2026, 7, 1)),
        _b("online", 50, d=date(2026, 7, 2)),
        _b("presencial", 100, d=date(2026, 7, 13)),
    ]
    series = stats.build_series(rows, "week")
    assert len(series) == 2
    assert series[0]["count"] == 2
    assert series[0]["lucro_liquido"] == 100.0
    assert series[1]["lucro_liquido"] == 70.0


def test_build_series_monthly_buckets():
    rows = [_b("online", 50, d=date(2026, 6, 30)), _b("online", 50, d=date(2026, 7, 1))]
    series = stats.build_series(rows, "month")
    assert [x["period"] for x in series] == ["2026-06", "2026-07"]
