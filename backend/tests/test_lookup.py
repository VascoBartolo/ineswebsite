from conftest import make_booking


def _lookup(client, **body):
    return client.post("/api/bookings/lookup", json=body)


def test_lookup_finds_booking_by_reference_and_email(client, app):
    with app.app_context():
        make_booking(reference="IB-LOOK1", email="cliente@teste.pt")
    r = _lookup(client, reference="ib-look1", email="Cliente@Teste.pt")
    assert r.status_code == 200
    assert r.get_json()["booking"]["reference"] == "IB-LOOK1"


def test_lookup_wrong_email_is_not_found(client, app):
    with app.app_context():
        make_booking(reference="IB-LOOK2", email="cliente@teste.pt")
    assert _lookup(client, reference="IB-LOOK2", email="outro@teste.pt").status_code == 404


def test_lookup_requires_both_fields(client):
    assert _lookup(client, reference="IB-LOOK3").status_code == 400
    assert _lookup(client, email="cliente@teste.pt").status_code == 400


def test_lookup_no_longer_accepts_email_in_the_url(client, app):
    """The old GET form put the client's email in the query string."""
    with app.app_context():
        make_booking(reference="IB-LOOK4", email="cliente@teste.pt")
    r = client.get("/api/bookings/lookup?reference=IB-LOOK4&email=cliente@teste.pt")
    assert r.status_code == 405
