"""Ops actions — CLI-callable operations over the CRM."""
import sqlite3
import time


class OpError(Exception):
    pass


def add_lead(conn: sqlite3.Connection, *, company: str, kind: str = "partner",
             segment: str | None = None, website: str | None = None,
             city: str | None = None, source: str = "manual",
             signal: str | None = None, now_fn=time.time) -> int:
    ts = now_fn()
    try:
        conn.execute(
            """INSERT INTO leads (company, kind, segment, website, city, source,
               signal, status, created_at, updated_at)
               VALUES (?,?,?,?,?,?,?,'new',?,?)""",
            (company, kind, segment, website, city, source, signal, ts, ts),
        )
        conn.commit()
    except sqlite3.IntegrityError:
        raise OpError(f"lead already exists: {company}")
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def claim_lead(conn: sqlite3.Connection, lead_id: int, *, claimed_by: str,
               now_fn=time.time) -> None:
    row = conn.execute("SELECT claimed_by, status FROM leads WHERE id=?", (lead_id,)).fetchone()
    if not row:
        raise OpError(f"no lead {lead_id}")
    if row["claimed_by"] and row["claimed_by"] != claimed_by:
        raise OpError(f"lead {lead_id} already claimed by {row['claimed_by']}")
    conn.execute(
        "UPDATE leads SET claimed_by=?, claimed_at=?, status=CASE WHEN status='new' THEN 'qualified' ELSE status END, updated_at=? WHERE id=?",
        (claimed_by, now_fn(), now_fn(), lead_id),
    )
    conn.commit()


def set_status(conn: sqlite3.Connection, lead_id: int, status: str) -> None:
    if status not in {"new", "qualified", "contacted", "replied", "call_booked",
                      "won", "lost", "dead"}:
        raise OpError(f"bad status {status}")
    conn.execute("UPDATE leads SET status=?, updated_at=? WHERE id=?",
                 (status, time.time(), lead_id))
    conn.commit()


def record_reply(conn: sqlite3.Connection, *, lead_id: int, classification: str,
                 from_addr: str, subject: str, raw: str = "") -> int:
    """Record an inbound reply and move the lead. classified by reply_worker."""
    if classification not in {"positive", "negative", "ooo", "unclassified"}:
        raise OpError(f"bad classification {classification}")
    send = conn.execute(
        "SELECT id FROM sends WHERE lead_id=? ORDER BY id DESC LIMIT 1",
        (lead_id,)).fetchone()
    summary = f"{from_addr}: {subject}"[:240]
    cur = conn.execute(
        "INSERT INTO replies (send_id, lead_id, received_at, classification, summary, raw_path, handled)"
        " VALUES (?,?,?,?,?,?,0)",
        (send["id"] if send else 0, lead_id, time.time(), classification, summary,
         raw or None))
    status_map = {"positive": "replied", "negative": "dead",
                  "ooo": "contacted", "unclassified": "replied"}
    conn.execute("UPDATE leads SET status=?, updated_at=? WHERE id=?",
                 (status_map[classification], time.time(), lead_id))
    conn.commit()
    return cur.lastrowid


def pipeline_status(conn: sqlite3.Connection) -> dict:
    by_status = dict(
        conn.execute("SELECT status, COUNT(*) FROM leads GROUP BY status").fetchall()
    )
    sent_today = conn.execute(
        "SELECT COUNT(*) FROM sends WHERE status='sent' AND sent_at >= ?", 
        (time.time() - 86400,),
    ).fetchone()[0]
    revenue_cents = conn.execute(
        "SELECT COALESCE(SUM(amount_cents),0) FROM engagements WHERE status='paid'"
    ).fetchone()[0]
    pending = conn.execute(
        "SELECT COUNT(*) FROM approvals WHERE status='pending'"
    ).fetchone()[0]
    return {
        "leads_by_status": by_status,
        "sends_last_24h": sent_today,
        "revenue_paid_cents": revenue_cents,
        "pending_approvals": pending,
    }


def pending_approvals(conn: sqlite3.Connection) -> list[sqlite3.Row]:
    return conn.execute(
        "SELECT * FROM approvals WHERE status='pending' ORDER BY created_at"
    ).fetchall()


def request_approval(conn: sqlite3.Connection, *, kind: str, payload: dict,
                     requested_by: str = "agent", now_fn=time.time) -> int:
    import json
    if kind not in {"send", "spend", "client_work"}:
        raise OpError(f"bad approval kind {kind}")
    conn.execute(
        "INSERT INTO approvals (kind, payload, status, requested_by, created_at) VALUES (?,?,'pending',?,?)",
        (kind, json.dumps(payload), requested_by, now_fn()),
    )
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]


def decide_approval(conn: sqlite3.Connection, approval_id: int, *, approved: bool,
                    decided_by: str) -> None:
    status = "approved" if approved else "rejected"
    conn.execute("UPDATE approvals SET status=?, decided_by=?, decided_at=? WHERE id=?",
                 (status, decided_by, time.time(), approval_id))
    conn.commit()


def log_client_work(conn: sqlite3.Connection, *, client_name: str, kind: str,
                    service: str, amount_cents: int = 0, lead_id: int | None = None,
                    now_fn=time.time) -> int:
    conn.execute(
        """INSERT INTO engagements (lead_id, client_name, kind, service,
           amount_cents, status, started_at, created_at)
           VALUES (?,?,?,?,?,'active',?,?)""",
        (lead_id, client_name, kind, service, amount_cents, now_fn(), now_fn()),
    )
    conn.commit()
    return conn.execute("SELECT last_insert_rowid()").fetchone()[0]
