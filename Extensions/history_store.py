"""Local-only mood history log (Data/history.db).

Never versioned (see .gitignore) and never transmitted anywhere - this is
purely a local journal so the History tab can show a trend over time. See
PRIVACY.md. Delete Data/history.db, or use the in-app "Clear history"
button, to remove it entirely.
"""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import datetime

from Extensions.runtime_paths import app_root

DB_PATH = app_root() / "Data" / "history.db"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    mode TEXT NOT NULL,
    source TEXT NOT NULL DEFAULT 'text',
    result TEXT NOT NULL,
    confidence REAL NOT NULL,
    signal REAL NOT NULL,
    excerpt TEXT NOT NULL
)
"""


@contextmanager
def _connection():
    """A connection that's always closed on exit - sqlite3.Connection's own
    context-manager protocol only commits/rolls back, it doesn't close the
    handle, which leaks file locks (breaks file deletion/renaming on
    Windows) if this is called often, as log_entry() is."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.execute(_SCHEMA)
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def _signal(mode, result, confidence):
    """Map a result onto a -1 (concerning) .. +1 (positive) axis so polarity
    and depression entries plot on one shared trend line."""
    if mode == "depression":
        return -confidence if result == "depressive" else confidence
    if result == "positive":
        return confidence
    if result == "negative":
        return -confidence
    return 0.0


def log_entry(mode, text, result, confidence, source="text"):
    """Record one analysis. Text is truncated to a short excerpt - it never
    leaves the device either way (see PRIVACY.md)."""
    excerpt = (text or "").strip().replace("\n", " ")[:280]
    with _connection() as connection:
        connection.execute(
            "INSERT INTO history (timestamp, mode, source, result, confidence, signal, excerpt) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                datetime.now().isoformat(timespec="seconds"),
                mode,
                source,
                result,
                confidence,
                _signal(mode, result, confidence),
                excerpt,
            ),
        )


def get_recent(limit=50):
    """Most recent entries first: (timestamp, mode, result, confidence, excerpt, signal)."""
    with _connection() as connection:
        cursor = connection.execute(
            "SELECT timestamp, mode, result, confidence, excerpt, signal FROM history "
            "ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return cursor.fetchall()


def get_trend():
    """All (timestamp, signal) pairs in chronological order, for the trend chart."""
    with _connection() as connection:
        cursor = connection.execute("SELECT timestamp, signal FROM history ORDER BY id ASC")
        return cursor.fetchall()


def clear():
    with _connection() as connection:
        connection.execute("DELETE FROM history")
