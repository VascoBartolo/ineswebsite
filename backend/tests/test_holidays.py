"""The holiday table is hand-written, so these tests are its proof.

The movable-feast test re-derives every date from Easter independently; if a
line in holidays_pt.py is mistyped or a year is added by hand, it fails here
rather than silently closing (or opening) a working day.
"""
from datetime import date, timedelta

import pytest

import calendar_service
import holidays_pt


def _easter(year):
    """Anonymous Gregorian algorithm — deliberately not the code under test."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


# offset from Easter -> the name the table must carry on that date
MOVABLE = {
    -47: "Terça-feira de Carnaval",
    -2: "Sexta-feira Santa",
    0: "Páscoa",
    50: "Dia da Região Autónoma dos Açores",
    60: "Corpo de Deus",
}

FIXED = [
    (1, 1, "Ano Novo"), (4, 25, "Dia da Liberdade"), (5, 1, "Dia do Trabalhador"),
    (6, 10, "Dia de Portugal"), (8, 15, "Assunção de Nossa Senhora"),
    (10, 5, "Implantação da República"), (11, 1, "Todos os Santos"),
    (12, 1, "Restauração da Independência"), (12, 8, "Imaculada Conceição"),
    (12, 25, "Natal"),
]


@pytest.mark.parametrize("year", holidays_pt.COVERED_YEARS)
def test_movable_feasts_match_easter(year):
    easter = _easter(year)
    for offset, name in MOVABLE.items():
        d = easter + timedelta(days=offset)
        assert holidays_pt.holiday_name(d) == name, f"{d} should be {name}"


@pytest.mark.parametrize("year", holidays_pt.COVERED_YEARS)
def test_fixed_feasts_present(year):
    for month, day, name in FIXED:
        d = date(year, month, day)
        assert holidays_pt.holiday_name(d) == name, f"{d} should be {name}"


@pytest.mark.parametrize("year", holidays_pt.COVERED_YEARS)
def test_no_extra_dates_in_year(year):
    """Every covered year holds exactly the fixed + movable set and nothing else."""
    expected = {date(year, m, d) for m, d, _ in FIXED}
    expected |= {_easter(year) + timedelta(days=o) for o in MOVABLE}
    actual = {d for d in holidays_pt.HOLIDAYS if d.year == year}
    assert actual == expected


def test_table_covers_only_declared_years():
    assert {d.year for d in holidays_pt.HOLIDAYS} == set(holidays_pt.COVERED_YEARS)


def _first_future(pred):
    """First date matching `pred` that clears get_available_slots' 24h lead time.

    Dates are chosen relative to today rather than hardcoded: a fixed date drifts
    into the past and makes these assertions pass for the wrong reason, since a
    past day has no slots either.
    """
    start = date.today() + timedelta(days=2)
    for offset in range((date(max(holidays_pt.COVERED_YEARS), 12, 31) - start).days + 1):
        d = start + timedelta(days=offset)
        if pred(d):
            return d
    return None


def _future_holiday_on_a_working_weekday():
    # Sundays are already closed by WORK_WINDOWS, so they prove nothing here.
    return _first_future(lambda d: holidays_pt.is_holiday(d) and d.weekday() != 6)


def test_holiday_closes_a_day_that_would_otherwise_be_open(monkeypatch):
    """Proves causation: the same date opens up once the table is emptied."""
    d = _future_holiday_on_a_working_weekday()
    if d is None:
        pytest.skip("holiday table no longer reaches into the future")
    assert calendar_service.get_available_slots(d, 60, []) == []
    monkeypatch.setattr(holidays_pt, "HOLIDAYS", {})
    assert calendar_service.get_available_slots(d, 60, []) != []


def test_holiday_blocks_online_too():
    """Feriados close the whole day, not just the clinics."""
    d = _future_holiday_on_a_working_weekday()
    if d is None:
        pytest.skip("holiday table no longer reaches into the future")
    assert calendar_service.get_available_slots(d, 60, [], ("online", None)) == []


def test_ordinary_day_is_unaffected():
    """A weekday that is not a feriado still offers its usual slots."""
    d = _first_future(lambda x: not holidays_pt.is_holiday(x) and x.weekday() == 0)
    assert d is not None
    assert calendar_service.get_available_slots(d, 60, []) != []


def test_municipal_table_is_empty_pending_confirmation():
    """Guards the deliberate gap: if dates are added, this test must be updated
    along with them, so they cannot be dropped in unreviewed."""
    assert holidays_pt.MUNICIPAL_TERCEIRA == {}
