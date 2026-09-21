// Every slot the booking API returns is wall-clock time at the practice, in the
// Azores. These helpers state that offset honestly — it is UTC−1 in winter and
// UTC+0 in summer — and translate it for visitors whose clocks differ.
export const PRACTICE_TZ = 'Atlantic/Azores';

// Minutes east of UTC that `timeZone` observes at `instant`.
function tzOffsetMinutes(timeZone, instant) {
  const p = Object.fromEntries(
    new Intl.DateTimeFormat('en-US', {
      timeZone, hourCycle: 'h23',
      year: 'numeric', month: 'numeric', day: 'numeric', hour: 'numeric', minute: 'numeric',
    }).formatToParts(instant).map(({ type, value }) => [type, value]),
  );
  const wall = Date.UTC(p.year, p.month - 1, p.day, p.hour, p.minute);
  return Math.round((wall - Math.floor(instant.getTime() / 60000) * 60000) / 60000);
}

// Noon UTC on a YYYY-MM-DD date is clear of the 01:00 UTC summer-time switch, so
// it yields that day's offset. Without a date, the current instant.
function referenceInstant(dateStr) {
  return dateStr ? new Date(`${dateStr}T12:00:00Z`) : new Date();
}

export function practiceOffset(dateStr) {
  return tzOffsetMinutes(PRACTICE_TZ, referenceInstant(dateStr));
}

// Minutes the visitor's own clock runs ahead (+) or behind (−) the practice's.
export function localMinusPractice(dateStr) {
  const at = referenceInstant(dateStr);
  return (-at.getTimezoneOffset() - tzOffsetMinutes(PRACTICE_TZ, at)) || 0;
}

export function fmtUtcOffset(min) {
  const sign = min < 0 ? '−' : '+';
  const a = Math.abs(min);
  return `UTC${sign}${Math.floor(a / 60)}${a % 60 ? `:${String(a % 60).padStart(2, '0')}` : ''}`;
}

export function fmtOffsetDiff(min) {
  const a = Math.abs(min);
  const h = Math.floor(a / 60);
  const m = a % 60;
  if (m) return `${h} h ${m} min`;
  return h === 1 ? '1 hora' : `${h} horas`;
}

// "HH:MM" moved by `min` minutes, wrapping past midnight.
export function shiftTime(hhmm, min) {
  const [h, m] = hhmm.split(':').map(Number);
  const t = (((h * 60 + m + min) % 1440) + 1440) % 1440;
  return `${String(Math.floor(t / 60)).padStart(2, '0')}:${String(t % 60).padStart(2, '0')}`;
}

// The instant a practice-time slot starts, comparable with the current time.
export function slotInstant(dateStr, hhmm) {
  const [y, mo, d] = dateStr.split('-').map(Number);
  const [h, m] = hhmm.split(':').map(Number);
  return new Date(Date.UTC(y, mo - 1, d, h, m) - practiceOffset(dateStr) * 60000);
}
