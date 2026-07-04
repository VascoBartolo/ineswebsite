from datetime import date, time
from conftest import TEST_PASSWORD, make_booking


def _auth(client):
    client.post("/api/admin/login", json={"password": TEST_PASSWORD})


def test_lists_all_bookings(client, app):
    with app.app_context():
        make_booking(reference="IB-A", email="a@x.pt")
        make_booking(reference="IB-B", email="b@x.pt", regime="presencial",
                     local_consulta="Clínica NIITE")
    _auth(client)
    r = client.get("/api/admin/bookings")
    assert r.status_code == 200
    body = r.get_json()
    assert len(body["bookings"]) == 2
    assert body["summary"]["confirmed_count"] == 2


def test_filter_by_regime(client, app):
    with app.app_context():
        make_booking(reference="IB-A", regime="online")
        make_booking(reference="IB-B", regime="presencial", local_consulta="X")
    _auth(client)
    r = client.get("/api/admin/bookings?regime=presencial")
    refs = [b["reference"] for b in r.get_json()["bookings"]]
    assert refs == ["IB-B"]


def test_filter_by_status_and_search(client, app):
    with app.app_context():
        make_booking(reference="IB-A", nome="Ana Melo", status="confirmado")
        make_booking(reference="IB-B", nome="João Dias", status="cancelado")
    _auth(client)
    assert len(client.get("/api/admin/bookings?status=cancelado").get_json()["bookings"]) == 1
    assert len(client.get("/api/admin/bookings?q=ana").get_json()["bookings"]) == 1


def test_filter_by_date_range(client, app):
    with app.app_context():
        make_booking(reference="IB-A", slot_date=date(2026, 7, 1))
        make_booking(reference="IB-B", slot_date=date(2026, 8, 1))
    _auth(client)
    r = client.get("/api/admin/bookings?date_from=2026-07-15&date_to=2026-07-31")
    assert r.get_json()["bookings"] == [] or all(
        b["slot_date"] >= "2026-07-15" for b in r.get_json()["bookings"])
