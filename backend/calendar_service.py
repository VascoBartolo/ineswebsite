import os
import re
import pytz
from datetime import datetime, date, time, timedelta

TIMEZONE = "Atlantic/Azores"
CALENDAR_ID = os.environ.get("GOOGLE_CALENDAR_ID", "primary")
CREDENTIALS_FILE = os.environ.get("GOOGLE_CREDENTIALS_FILE", "/app/credentials.json")

WORK_START = time(16, 0)
WORK_END = time(19, 0)
SLOT_INTERVAL_MINUTES = 30
TRAVEL_BUFFER = timedelta(minutes=30)


def _get_service():
    if not os.path.exists(CREDENTIALS_FILE):
        return None
    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build

        creds = Credentials.from_service_account_file(
            CREDENTIALS_FILE, scopes=["https://www.googleapis.com/auth/calendar"]
        )
        return build("calendar", "v3", credentials=creds)
    except Exception as e:
        print(f"[Calendar] Failed to build service: {e}")
        return None


def _normalize_clinic(name):
    """Lowercase, strip city in parentheses, strip whitespace."""
    name = re.sub(r'\s*\([^)]*\)', '', name or '')
    return name.strip().lower()


# Keyword lists are lowercase; _normalize_clinic output is compared against them.
# Include accent variants so the nutritionist doesn't need to be precise.
_CLINIC_KEYWORDS = [
    ('manus',            ['manus']),
    ('psicologia_bessa', ['psicologia', 'flávia', 'flavia', 'bessa']),
]


def _resolve_clinic(name):
    """Map a clinic string to a canonical ID via keyword matching.

    Falls back to the normalized string itself if no keyword matches,
    so unknown clinics still compare equal to themselves.
    """
    normalized = _normalize_clinic(name)
    for clinic_id, keywords in _CLINIC_KEYWORDS:
        if any(kw in normalized for kw in keywords):
            return clinic_id
    return normalized


def parse_location_from_event(event):
    """
    Reads the 'Regime:' line from a Google Calendar event description.
    Returns a (regime, clinic) tuple, or None if not found.

    Accepted formats (case-insensitive, city in () optional):
        Regime: presencial — Clínica Manus (Angra do Heroísmo)
        Regime: Presencial - Clínica Manus
        Regime: online
    """
    description = (event.get("description") or "").strip()
    for line in description.split("\n"):
        line = line.strip()
        if line.lower().startswith("regime:"):
            value = line[7:].strip()
            lower_val = value.lower()
            if "presencial" in lower_val:
                # Split on em-dash, en-dash, or plain hyphen
                parts = re.split(r'\s*[—–\-]\s*', value, maxsplit=1)
                clinic = parts[1].strip() if len(parts) > 1 else None
                return ("presencial", clinic)
            if "online" in lower_val:
                return ("online", None)
    return None  # unknown — treated conservatively (buffer applied)


def needs_buffer(loc1, loc2):
    """
    Returns True when a 30-min travel buffer is required between two adjacent
    consultations with locations loc1 and loc2 (each a (regime, clinic) tuple
    or None for unknown).
    """
    if loc1 is None or loc2 is None:
        return True  # conservative: unknown location → assume travel needed
    regime1, clinic1 = loc1
    regime2, clinic2 = loc2
    if regime1 != regime2:
        return True  # presencial ↔ online always needs buffer
    if regime1 == "online":
        return False  # both online → no travel
    # both presencial: buffer only if different clinic (keyword-resolved comparison)
    return _resolve_clinic(clinic1) != _resolve_clinic(clinic2)


def get_gcal_events(query_date):
    """
    Returns Google Calendar events for the given date as a list of dicts:
      {start_dt: datetime, end_dt: datetime, location: tuple|None}
    """
    service = _get_service()
    if not service:
        return []

    tz = pytz.timezone(TIMEZONE)
    day_start = tz.localize(datetime.combine(query_date, time(0, 0)))
    day_end = tz.localize(datetime.combine(query_date, time(23, 59, 59)))

    try:
        result = (
            service.events()
            .list(
                calendarId=CALENDAR_ID,
                timeMin=day_start.isoformat(),
                timeMax=day_end.isoformat(),
                singleEvents=True,
                orderBy="startTime",
            )
            .execute()
        )
    except Exception as e:
        print(f"[Calendar] API error: {e}")
        return []

    events = []
    for event in result.get("items", []):
        start_str = event["start"].get("dateTime")
        end_str = event["end"].get("dateTime")
        if not start_str or not end_str:
            continue
        try:
            start_dt = datetime.fromisoformat(start_str).astimezone(tz).replace(tzinfo=None)
            end_dt = datetime.fromisoformat(end_str).astimezone(tz).replace(tzinfo=None)
            events.append({
                "start_dt": start_dt,
                "end_dt": end_dt,
                "location": parse_location_from_event(event),
            })
        except Exception:
            continue

    return events


def get_available_slots(query_date, duration_minutes, all_events, new_location=None):
    """
    Returns list of available 'HH:MM' slot strings.

    all_events: list of {start_dt, end_dt, location} dicts (DB + GCal combined)
    new_location: (regime, clinic) tuple for the booking being checked, or None
    """
    if query_date.weekday() >= 5:
        return []

    window_start = datetime.combine(query_date, WORK_START)
    window_end = datetime.combine(query_date, WORK_END)

    candidates = []
    current = window_start
    while current + timedelta(minutes=duration_minutes) <= window_end:
        candidates.append(current)
        current += timedelta(minutes=SLOT_INTERVAL_MINUTES)

    available = []
    for slot_start in candidates:
        slot_end = slot_start + timedelta(minutes=duration_minutes)

        # 1. Direct overlap with any existing event
        if any(slot_start < ev["end_dt"] and slot_end > ev["start_dt"] for ev in all_events):
            continue

        # 2. Travel buffer: last event ending before this slot
        prev_events = [ev for ev in all_events if ev["end_dt"] <= slot_start]
        if prev_events:
            last_prev = max(prev_events, key=lambda e: e["end_dt"])
            if needs_buffer(last_prev["location"], new_location):
                if slot_start - last_prev["end_dt"] < TRAVEL_BUFFER:
                    continue

        # 3. Travel buffer: first event starting after this slot
        next_events = [ev for ev in all_events if ev["start_dt"] >= slot_end]
        if next_events:
            first_next = min(next_events, key=lambda e: e["start_dt"])
            if needs_buffer(new_location, first_next["location"]):
                if first_next["start_dt"] - slot_end < TRAVEL_BUFFER:
                    continue

        available.append(slot_start.strftime("%H:%M"))

    return available


def _event_body(booking):
    tz = pytz.timezone(TIMEZONE)
    start_dt = tz.localize(datetime.combine(booking.slot_date, booking.slot_time))
    end_dt = start_dt + timedelta(minutes=int(booking.duration_minutes))
    regime_info = booking.regime
    if booking.local_consulta:
        regime_info = f"{booking.regime} — {booking.local_consulta}"
    return {
        "summary": f"[IB] {booking.nome} — {booking.tipo_consulta}",
        "description": (
            f"Referência: {booking.reference}\n"
            f"Email: {booking.email}\n"
            f"Contacto: {booking.contacto}\n"
            f"Regime: {regime_info}\n"
            f"Preço: {float(booking.price):.0f}€\n"
            f"Duração: {booking.duration_minutes} min\n\n"
            f"Contexto: {booking.contexto or 'Sem contexto adicional'}"
        ),
        "start": {"dateTime": start_dt.isoformat(), "timeZone": TIMEZONE},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": TIMEZONE},
    }


def create_event(booking):
    service = _get_service()
    if not service:
        return None
    try:
        result = service.events().insert(calendarId=CALENDAR_ID, body=_event_body(booking)).execute()
        return result.get("id")
    except Exception as e:
        print(f"[Calendar] Create event error: {e}")
        return None


def delete_event(event_id):
    service = _get_service()
    if not service or not event_id:
        return
    try:
        service.events().delete(calendarId=CALENDAR_ID, eventId=event_id).execute()
    except Exception as e:
        print(f"[Calendar] Delete event error: {e}")


def update_event(event_id, booking):
    """Patch an existing event to match the booking. Falls back to creating
    a new event if the old one is missing. Returns the (possibly new) event id."""
    service = _get_service()
    if not service:
        return event_id
    if not event_id:
        return create_event(booking)
    try:
        result = service.events().update(
            calendarId=CALENDAR_ID, eventId=event_id, body=_event_body(booking)
        ).execute()
        return result.get("id")
    except Exception as e:
        print(f"[Calendar] Update event error: {e}; recreating.")
        return create_event(booking)
