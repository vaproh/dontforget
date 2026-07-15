from datetime import datetime

from better_dontforget.core.reminder_parser import has_reminder_intent, parse_reminder


def _parse(text, base):
    clean, dt = parse_reminder(text, base)
    assert dt is not None, f"expected a reminder datetime for: {text}"
    return clean, dt


def test_no_intent_returns_none():
    text, dt = parse_reminder("the rust tui library is ratatui")
    assert dt is None
    assert text == "the rust tui library is ratatui"


def test_intent_without_time_defaults_tomorrow():
    base = datetime(2026, 1, 1, 12, 0)
    text, dt = _parse("remind me to buy milk", base)
    assert dt.date().day == 2
    assert dt.hour == 9
    assert "buy milk" == text


def test_tomorrow_at_time():
    base = datetime(2026, 1, 1, 12, 0)
    text, dt = _parse("remind me tomorrow at 9am to call mom", base)
    assert dt.year == 2026 and dt.month == 1 and dt.day == 2
    assert dt.hour == 9
    assert text == "call mom"


def test_in_hours():
    base = datetime(2026, 1, 1, 12, 0)
    _, dt = _parse("remind me in 2 hours to walk dog", base)
    assert dt == datetime(2026, 1, 1, 14, 0)


def test_in_days():
    base = datetime(2026, 1, 1, 12, 0)
    _, dt = _parse("remind me in 3 days to pay bill", base)
    assert dt.date().day == 4


def test_next_weekday():
    base = datetime(2026, 1, 1, 12, 0)
    _, dt = _parse("remind me next monday to standup", base)
    assert dt.weekday() == 0
    assert dt.date().day >= 5


def test_absolute_datetime():
    base = datetime(2026, 1, 1, 12, 0)
    _, dt = _parse("remind me 2026-08-01 15:30 to fly", base)
    assert dt == datetime(2026, 8, 1, 15, 30)


def test_absolute_date_default_hour():
    base = datetime(2026, 1, 1, 12, 0)
    _, dt = _parse("remind me 2026-08-01 to fly", base)
    assert dt == datetime(2026, 8, 1, 9, 0)


def test_tonight():
    base = datetime(2026, 1, 1, 12, 0)
    _, dt = _parse("remind me tonight to lock door", base)
    assert dt.hour == 21


def test_intent_detection():
    assert has_reminder_intent("remind me to x")
    assert has_reminder_intent("set a reminder to x")
    assert not has_reminder_intent("just a normal note")
