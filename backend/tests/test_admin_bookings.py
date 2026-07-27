from datetime import date, time
from conftest import TEST_PASSWORD, make_booking


def _auth(client):
    client.post("/api/admin/login", json={"password": TEST_PASSWORD})


def test_lists_all_bookings(client, app):
    with app.app_context():
        make_booking(reference="IB-A", email="a@x.pt")
        make_booking(reference="IB-B", email="b@x.pt", regime="presencial",
                     local_consulta="Clínica Manus")
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


def test_pagination_defaults(client, app):
    with app.app_context():
        make_booking(reference="IB-PG1")
    _auth(client)
    r = client.get("/api/admin/bookings")
    body = r.get_json()
    assert body["pagination"]["page"] == 1
    assert body["pagination"]["per_page"] == 30
    assert body["pagination"]["total"] == 1
    assert body["pagination"]["pages"] == 1


def test_pagination_paging(client, app):
    with app.app_context():
        for i in range(5):
            make_booking(reference=f"IB-PG{i:03d}")
    _auth(client)
    r1 = client.get("/api/admin/bookings?per_page=2&page=1")
    b1 = r1.get_json()
    assert len(b1["bookings"]) == 2
    assert b1["pagination"]["total"] == 5
    assert b1["pagination"]["pages"] == 3

    r2 = client.get("/api/admin/bookings?per_page=2&page=3")
    b2 = r2.get_json()
    assert len(b2["bookings"]) == 1
    assert b2["pagination"]["page"] == 3

    # Summary reflects ALL filtered rows, not just the page
    assert b1["summary"]["count"] == 5


def test_pagination_per_page_clamped(client, app):
    _auth(client)
    r = client.get("/api/admin/bookings?per_page=999")
    assert r.get_json()["pagination"]["per_page"] == 100
