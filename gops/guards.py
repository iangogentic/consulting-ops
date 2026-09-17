"""Send guards and pacing caps — enforced in code, not in prompts."""
import re
import sqlite3
import time

# Hard caps (per goal contract)
PER_INBOX_DAILY_CAP = 25
MIN_SECONDS_BETWEEN_SENDS = 45  # per inbox, pacing

STOP_FILE = "control/OUTREACH_STOP"

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class GuardError(Exception):
    pass


def check_stop(stop_path=STOP_FILE) -> bool:
    """True = outreach halted globally."""
    from pathlib import Path
    return Path(stop_path).exists()


def validate_inbox_day(conn: sqlite3.Connection, inbox: str, day: str) -> None:
    row = conn.execute(
        "SELECT sent FROM daily_counters WHERE day=? AND inbox=?", (day, inbox)
    ).fetchone()
    if row and row["sent"] >= PER_INBOX_DAILY_CAP:
        raise GuardError(f"daily cap reached for {inbox} on {day} ({row['sent']})")


def validate_email(address: str) -> None:
    if not EMAIL_RE.match(address or ""):
        raise GuardError(f"invalid email address: {address!r}")


def validate_dedupe(conn: sqlite3.Connection, dedupe_key: str) -> None:
    row = conn.execute(
        "SELECT 1 FROM sends WHERE dedupe_key=?", (dedupe_key,)
    ).fetchone()
    if row:
        raise GuardError(f"duplicate send suppressed: {dedupe_key}")


def record_send(conn, *, lead_id, contact_id, channel, inbox, subject,
                body_path, dedupe_key, now_fn=time.time) -> int:
    """Idempotency contract: the send row exists BEFORE delivery happens."""
    conn.execute(
        """INSERT INTO sends (lead_id, contact_id, channel, inbox, subject,
           body_path, dedupe_key, status, created_at)
           VALUES (?,?,?,?,?,?,?,'recorded',?)""",
        (lead_id, contact_id, channel, inbox, subject, body_path, dedupe_key, now_fn()),
    )
    conn.execute(
        """INSERT INTO daily_counters (day, inbox, sent) VALUES (?,?,1)
           ON CONFLICT(day, inbox) DO UPDATE SET sent = sent + 1""",
        (day_key(now_fn()), inbox),
    )
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def mark_sent(conn, send_id: int, sent_at: float) -> None:
    conn.execute("UPDATE sends SET status='sent', sent_at=? WHERE id=?", (sent_at, send_id))
    conn.commit()


def mark_failed(conn, send_id: int) -> None:
    """Failed delivery: refund the counter so caps stay honest."""
    row = conn.execute("SELECT inbox, created_at FROM sends WHERE id=?", (send_id,)).fetchone()
    if row:
        day = day_key(row["created_at"])
        conn.execute(
            "UPDATE daily_counters SET sent = MAX(sent-1, 0) WHERE day=? AND inbox=?",
            (day, row["inbox"]),
        )
    conn.execute("UPDATE sends SET status='failed' WHERE id=?", (send_id,))
    conn.commit()


def day_key(ts: float) -> str:
    # America/Chicago wall clock, from a POSIX timestamp (DST-safe via local time)
    import datetime
    return datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
