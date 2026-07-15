"""Reminder processing: detect due/overdue reminders and deliver notifications.

A reminder is considered ready when ``reminder_at <= now`` and it has not yet
been marked notified. Notifications are delivered only for ready reminders, and
a reminder is marked notified only after a successful delivery, so a machine
that is off when a reminder is due will still notify it once processing resumes.
"""

from __future__ import annotations

from datetime import datetime

from .db import get_due_reminders, mark_notified
from .models import Note
from .notifications import Notifier


def build_message(note: Note) -> str:
    if note.encrypted:
        return "(encrypted note — unlock in the TUI to view)"
    return note.raw_text


def process_pending(
    conn,
    notifier: Notifier,
    now: datetime | None = None,
    max_notify: int = 100,
) -> list[int]:
    """Deliver notifications for due, unnotified reminders.

    Returns the list of note ids successfully notified this run.
    """
    now = now or datetime.now()
    due = get_due_reminders(conn, now)
    delivered: list[int] = []
    for note in due[:max_notify]:
        message = build_message(note)
        title = "Better Dontforget reminder"
        if note.reminder_at:
            title = f"Reminder ({note.reminder_at})"
        if notifier.notify(title, message):
            delivered.append(note.id)
    if delivered:
        mark_notified(conn, delivered)
    return delivered
