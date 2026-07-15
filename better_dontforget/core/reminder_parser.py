"""Deterministic natural-language reminder-time parsing.

Used when a note expresses reminder intent (e.g. "remind me tomorrow to …").
This is intentionally heuristic and dependency-free so that capture works
offline and is fully testable. AI-based parsing is intentionally not required.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta

_INTENT_RE = re.compile(
    r"\b(remind me to|remind me|set a reminder to|set reminder to|reminder to|reminder)\b",
    re.IGNORECASE,
)

_WEEKDAYS = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

_ABS_RE = re.compile(r"(\d{4}-\d{2}-\d{2})(?:[ T](\d{1,2}):(\d{2}))?")
_IN_RE = re.compile(
    r"\bin\s+(\d+)\s*(min|mins|minute|minutes|h|hr|hrs|hour|hours|d|day|days|w|week|weeks)\b",
    re.IGNORECASE,
)
_NEXT_WD_RE = re.compile(
    r"\bnext\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.IGNORECASE
)
_WD_RE = re.compile(
    r"\b(on\s+)?(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b", re.IGNORECASE
)
_TOMORROW_RE = re.compile(r"\btomorrow\b", re.IGNORECASE)
_TODAY_RE = re.compile(r"\btoday\b", re.IGNORECASE)
_DAYPART_RE = re.compile(
    r"\b(tonight|this evening|evening|afternoon|this morning|morning)\b", re.IGNORECASE
)
_AT_RE = re.compile(r"\bat\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", re.IGNORECASE)
_TIME_RE = re.compile(r"\b(\d{1,2}):(\d{2})\s*(am|pm)?", re.IGNORECASE)

_DEFAULT_HOUR = 9


def has_reminder_intent(text: str) -> bool:
    return bool(_INTENT_RE.search(text))


def _apply_time(dt: datetime, hour: int, minute: int) -> datetime:
    return dt.replace(hour=hour, minute=minute, second=0, microsecond=0)


def _parse_time_expr(text: str, now: datetime) -> tuple[datetime | None, tuple[int, int] | None]:
    # Absolute date/time
    m = _ABS_RE.search(text)
    if m:
        y, mo, d = (int(x) for x in m.group(1).split("-"))
        if m.group(2):
            dt = datetime(y, mo, d, int(m.group(2)), int(m.group(3)))
        else:
            dt = datetime(y, mo, d, _DEFAULT_HOUR, 0)
        return dt, (m.start(), m.end())

    # "in N <unit>"
    m = _IN_RE.search(text)
    if m:
        amount = int(m.group(1))
        unit = m.group(2).lower()
        if unit.startswith(("min",)):
            delta = timedelta(minutes=amount)
        elif unit.startswith(("h",)):
            delta = timedelta(hours=amount)
        elif unit.startswith(("d",)):
            delta = timedelta(days=amount)
        else:
            delta = timedelta(weeks=amount)
        return now + delta, (m.start(), m.end())

    # "next <weekday>"
    m = _NEXT_WD_RE.search(text)
    if m:
        return _next_weekday(now, _WEEKDAYS[m.group(1).lower()], skip_weeks=1), (m.start(), m.end())

    # "tomorrow"
    m = _TOMORROW_RE.search(text)
    if m:
        base = now + timedelta(days=1)
        return _apply_default_or_explicit(text, base, m), (m.start(), m.end())

    # "today"
    m = _TODAY_RE.search(text)
    if m:
        return _apply_default_or_explicit(text, now, m), (m.start(), m.end())

    # weekday (standalone)
    m = _WD_RE.search(text)
    if m:
        return _next_weekday(now, _WEEKDAYS[m.group(2).lower()], skip_weeks=0), (m.start(), m.end())

    # day-part words
    m = _DAYPART_RE.search(text)
    if m:
        part = m.group(1).lower()
        hour = {
            "tonight": 21,
            "this evening": 19,
            "evening": 19,
            "afternoon": 15,
            "this morning": 9,
            "morning": 9,
        }[part]
        dt = _apply_time(now, hour, 0)
        if dt <= now:
            dt = _apply_time(now + timedelta(days=1), hour, 0)
        return dt, (m.start(), m.end())

    # "at HH:MM" or "at HH" with am/pm
    m = _AT_RE.search(text)
    if m:
        hour, minute = _resolve_clock(int(m.group(1)), m.group(3))
        dt = _apply_time(now, hour, minute)
        if dt <= now:
            dt = _apply_time(now + timedelta(days=1), hour, minute)
        return dt, (m.start(), m.end())

    return None, None


def _apply_default_or_explicit(text: str, base: datetime, intent_match) -> datetime:
    # If an explicit clock follows, use it; otherwise default hour.
    m = _AT_RE.search(text)
    if m:
        hour, minute = _resolve_clock(int(m.group(1)), m.group(3))
        return _apply_time(base, hour, minute)
    m = _TIME_RE.search(text)
    if m:
        hour, minute = _resolve_clock(int(m.group(1)), m.group(3))
        return _apply_time(base, hour, minute)
    return _apply_time(base, _DEFAULT_HOUR, 0)


def _resolve_clock(hour: int, ampm: str | None) -> tuple[int, int]:
    minute = 0
    if ampm:
        ampm = ampm.lower()
        if ampm == "pm" and hour < 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
    return hour, minute


def _next_weekday(now: datetime, target: int, skip_weeks: int) -> datetime:
    days_ahead = (target - now.weekday()) % 7
    if days_ahead == 0:
        days_ahead = 7
    days_ahead += skip_weeks * 7
    return _apply_time(now + timedelta(days=days_ahead), _DEFAULT_HOUR, 0)


def parse_reminder(text: str, now: datetime | None = None) -> tuple[str, datetime | None]:
    """Return ``(clean_text, remind_at)``.

    ``remind_at`` is ``None`` when no reminder intent is present. When intent is
    present but no explicit time is found, a sensible default (next day 09:00) is
    used so "remind me to …" still produces a reminder.
    """
    now = now or datetime.now()
    if not has_reminder_intent(text):
        return text.strip(), None

    dt, span = _parse_time_expr(text, now)
    if dt is None:
        dt = _apply_time(now + timedelta(days=1), _DEFAULT_HOUR, 0)

    clean = text
    if span:
        clean = clean[: span[0]] + clean[span[1] :]
    clean = _INTENT_RE.sub("", clean)
    clean = _AT_RE.sub("", clean)
    clean = _TIME_RE.sub("", clean)
    clean = _DAYPART_RE.sub("", clean)
    clean = _WD_RE.sub("", clean)
    clean = _TOMORROW_RE.sub("", clean)
    clean = _TODAY_RE.sub("", clean)
    clean = re.sub(r"^\s*to\b\s+", "", clean)
    clean = re.sub(r"\b(set a reminder|set reminder)\b", "", clean, flags=re.IGNORECASE)
    clean = re.sub(r"\s{2,}", " ", clean).strip(" :,-")
    return clean or text.strip(), dt
