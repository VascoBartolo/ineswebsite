from datetime import date, timedelta
import calendar_service

# Dates must stay in the future: get_available_slots only offers slots ≥24h ahead,
# so hardcoded past dates would return no slots. Compute the next Saturday at least
# 3 days out, then the Sunday/Monday that follow it.
_today = date.today()
_to_sat = (5 - _today.weekday()) % 7
if _to_sat < 3:
    _to_sat += 7
SATURDAY = _today + timedelta(days=_to_sat)
SUNDAY = SATURDAY + timedelta(days=1)
MONDAY = SATURDAY + timedelta(days=2)


def test_reference_dates_are_the_weekdays_we_expect():
    assert SATURDAY.weekday() == 5
    assert SUNDAY.weekday() == 6
    assert MONDAY.weekday() == 0


def test_weekday_window_unchanged():
    """Mon-Fri stays 16:00-19:00."""
    assert calendar_service.get_available_slots(MONDAY, 60, []) == [
        "16:00", "16:30", "17:00", "17:30", "18:00",
    ]


def test_saturday_has_morning_and_afternoon_windows():
    """Saturday: 09:00-12:00 and 13:00-14:30."""
    assert calendar_service.get_available_slots(SATURDAY, 60, []) == [
        "09:00", "09:30", "10:00", "10:30", "11:00", "13:00", "13:30",
    ]


def test_saturday_90min_fits_the_afternoon_window():
    """A 90-min first consultation fits 13:00-14:30 exactly."""
    assert calendar_service.get_available_slots(SATURDAY, 90, []) == [
        "09:00", "09:30", "10:00", "10:30", "13:00",
    ]


def test_sunday_closed():
    assert calendar_service.get_available_slots(SUNDAY, 60, []) == []


def test_saturday_respects_existing_bookings():
    """An existing 09:00-10:00 booking removes the overlapping morning slots."""
    from datetime import datetime
    events = [{
        "start_dt": datetime.combine(SATURDAY, __import__("datetime").time(9, 0)),
        "end_dt": datetime.combine(SATURDAY, __import__("datetime").time(10, 0)),
        "location": ("online", None),
    }]
    slots = calendar_service.get_available_slots(SATURDAY, 60, events, ("online", None))
    assert "09:00" not in slots
    assert "09:30" not in slots
    assert "13:00" in slots


MANUS = "Clínica Manus (Angra do Heroísmo)"
BESSA = "Centro de Psicologia Flávia Bessa (Angra do Heroísmo)"


def test_bessa_closed_on_saturday():
    """Flávia Bessa does not open on Saturdays — no presencial slot is offered."""
    assert calendar_service.get_available_slots(SATURDAY, 60, [], ("presencial", BESSA)) == []


def test_bessa_weekdays_unchanged():
    """Mon-Fri at Flávia Bessa keeps the normal 16:00-19:00 window."""
    assert calendar_service.get_available_slots(MONDAY, 60, [], ("presencial", BESSA)) == [
        "16:00", "16:30", "17:00", "17:30", "18:00",
    ]


def test_saturday_unchanged_for_other_options():
    """The Saturday closure is scoped to Flávia Bessa only."""
    full_saturday = ["09:00", "09:30", "10:00", "10:30", "11:00", "13:00", "13:30"]
    assert calendar_service.get_available_slots(SATURDAY, 60, [], ("presencial", MANUS)) == full_saturday
    assert calendar_service.get_available_slots(SATURDAY, 60, [], ("online", None)) == full_saturday
    # No location narrowed yet (clinic not picked): still the full Saturday.
    assert calendar_service.get_available_slots(SATURDAY, 60, [], None) == full_saturday
    assert calendar_service.get_available_slots(SATURDAY, 60, [], ("presencial", None)) == full_saturday


def test_bessa_matching_tolerates_name_variants():
    """The clinic is matched by keyword, so accent/spelling variants still close."""
    for name in ["Centro de Psicologia Flavia Bessa", "flávia bessa", "Bessa"]:
        assert calendar_service.get_available_slots(SATURDAY, 60, [], ("presencial", name)) == [], name


def test_bessa_saturday_rejected_by_booking_endpoint(client):
    """The closure is enforced server-side, not only hidden in the calendar UI."""
    res = client.post("/api/bookings", json={
        "sujeito": "adulto",
        "tipo_consulta": "consulta na gravidez",
        "regime": "presencial",
        "local_consulta": BESSA,
        "nome": "Teste",
        "idade": "30",
        "email": "teste@example.com",
        "contacto": "912345678",
        "slot_date": SATURDAY.isoformat(),
        "slot_time": "09:00",
        "is_first": False,
    })
    assert res.status_code == 409
    assert res.get_json()["error"] == "slot_unavailable"


def test_month_availability_zero_for_bessa_saturdays(client):
    """Every Saturday of the month shows no availability for Flávia Bessa."""
    base = date.today().replace(day=1) + timedelta(days=62)
    params = f"year={base.year}&month={base.month}&duration=60&regime=presencial&local_consulta={BESSA}"
    days = client.get(f"/api/availability/month?{params}").get_json()["days"]
    saturdays = [d for d in days if date.fromisoformat(d).weekday() == 5]
    assert saturdays, "month should contain at least one Saturday"
    assert all(days[d] == 0 for d in saturdays)

    mondays = [d for d in days if date.fromisoformat(d).weekday() == 0]
    assert all(days[d] == 5 for d in mondays)


def test_month_availability_counts(client):
    """The month endpoint returns a slot count per day, batched in one call."""
    base = date.today().replace(day=1) + timedelta(days=62)  # a fully-future month
    y, m = base.year, base.month
    body = client.get(f"/api/availability/month?year={y}&month={m}&duration=60").get_json()
    days = body["days"]
    assert len(days) >= 28

    sat = next(d for d in days if date.fromisoformat(d).weekday() == 5)
    sun = next(d for d in days if date.fromisoformat(d).weekday() == 6)
    mon = next(d for d in days if date.fromisoformat(d).weekday() == 0)

    assert days[sat] == 7
    assert days[sun] == 0
    assert days[mon] == 5


def test_month_availability_marks_past_days_zero(client):
    """Days before today are never offered."""
    today = date.today()
    body = client.get(f"/api/availability/month?year={today.year}&month={today.month}&duration=60").get_json()
    days = body["days"]
    past = [d for d in days if date.fromisoformat(d) < today]
    assert all(days[d] == 0 for d in past)
