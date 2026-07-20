from datetime import date, timedelta
import calendar_service

# 2026-08-01 is a Saturday, 08-02 a Sunday, 08-03 a Monday.
SATURDAY = date(2026, 8, 1)
SUNDAY = date(2026, 8, 2)
MONDAY = date(2026, 8, 3)


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
