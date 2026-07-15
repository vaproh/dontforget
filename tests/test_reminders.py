from datetime import datetime, timedelta

from better_dontforget.core import db as dbmod
from better_dontforget.core.reminders import process_pending


def test_due_reminder_detected(xdg_tmp, past_dt):
    conn = dbmod.open_db()
    nid = dbmod.add_note(conn, raw_text="past reminder", reminder_at=past_dt)
    due = dbmod.get_due_reminders(conn)
    assert any(n.id == nid for n in due)
    dbmod.close_db(conn)


def test_future_reminder_not_due(xdg_tmp, future_dt):
    conn = dbmod.open_db()
    dbmod.add_note(conn, raw_text="future reminder", reminder_at=future_dt)
    assert dbmod.get_due_reminders(conn) == []
    dbmod.close_db(conn)


def test_process_pending_delivers_and_marks(xdg_tmp, past_dt, fake_notifier):
    conn = dbmod.open_db()
    nid = dbmod.add_note(conn, raw_text="buy milk", reminder_at=past_dt)
    delivered = process_pending(conn, fake_notifier)
    assert delivered == [nid]
    assert fake_notifier.sent
    # not re-delivered
    assert process_pending(conn, fake_notifier) == []
    note = dbmod.get_note(conn, nid)
    assert note is not None and note.notified is True
    dbmod.close_db(conn)


def test_missed_reminder_recovered_after_downtime(xdg_tmp, fake_notifier):
    # Simulate a reminder that became due while the machine was off.
    conn = dbmod.open_db()
    due = datetime.now() - timedelta(days=2)
    nid = dbmod.add_note(conn, raw_text="overdue task", reminder_at=due)
    # "machine off" -> notify-pending not run until now
    delivered = process_pending(conn, fake_notifier)
    assert delivered == [nid]
    dbmod.close_db(conn)


def test_notification_failure_keeps_pending(xdg_tmp, past_dt, fake_notifier):
    fake_notifier.fail = True
    conn = dbmod.open_db()
    nid = dbmod.add_note(conn, raw_text="flaky", reminder_at=past_dt)
    assert process_pending(conn, fake_notifier) == []
    note = dbmod.get_note(conn, nid)
    assert note is not None and note.notified is False
    dbmod.close_db(conn)


def test_no_duplicate_on_repeat(xdg_tmp, past_dt, fake_notifier):
    conn = dbmod.open_db()
    dbmod.add_note(conn, raw_text="once", reminder_at=past_dt)
    process_pending(conn, fake_notifier)
    fake_notifier.sent.clear()
    process_pending(conn, fake_notifier)
    assert fake_notifier.sent == []
    dbmod.close_db(conn)
