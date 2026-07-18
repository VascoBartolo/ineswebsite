from datetime import date
from conftest import TEST_PASSWORD, make_booking


def _auth(client):
    client.post("/api/admin/login", json={"password": TEST_PASSWORD})


def test_stats_totals(client, app):
    with app.app_context():
        make_booking(reference="IB-A", regime="presencial", price=100,
                     local_consulta="Clínica Manus", slot_date=date(2026, 7, 1))
        make_booking(reference="IB-B", regime="online", price=50, slot_date=date(2026, 7, 2))
        make_booking(reference="IB-C", regime="online", price=50,
                     status="cancelado", slot_date=date(2026, 7, 3))
    _auth(client)
    body = client.get("/api/admin/stats?group_by=week").get_json()
    assert body["count"] == 2
    assert body["faturado"] == 150.0
    assert body["lucro_liquido"] == 120.0
    assert body["cancelled_count"] == 1
    assert len(body["series"]) >= 1


def test_stats_regime_filter(client, app):
    with app.app_context():
        make_booking(reference="IB-A", regime="presencial", price=100, local_consulta="X")
        make_booking(reference="IB-B", regime="online", price=50)
    _auth(client)
    body = client.get("/api/admin/stats?regime=online").get_json()
    assert body["count"] == 1
    assert body["lucro_liquido"] == 50.0


def test_locations_endpoint(client, app):
    with app.app_context():
        make_booking(reference="IB-A", regime="presencial", local_consulta="Clínica Manus")
        make_booking(reference="IB-B", regime="presencial", local_consulta="Angra")
    _auth(client)
    locs = client.get("/api/admin/locations").get_json()["locations"]
    assert set(locs) == {"Clínica Manus", "Angra"}
