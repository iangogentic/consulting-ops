#!/usr/bin/env python3
"""send_worker.py — executes APPROVED sends over SMTP with all guards applied.

Run after Ian approves items in the queue:
    python tools/ops.py approve-list
    python tools/ops.py approve-decide --id N --yes
    python workers/send_worker.py --apply          # actually send
    python workers/send_worker.py                  # dry-run, shows what would send

Guards (all enforced here, not in prompts):
- global OUTREACH_STOP file halts everything
- per-inbox daily cap 25 (checks + increments via gops.guards)
- sends recorded in `sends` table BEFORE delivery (idempotency: dedupe_key unique)
- SMTP creds from env: OUTREACH_SMTP_HOST, OUTREACH_SMTP_USER_<LANE>,
  OUTREACH_SMTP_PASS_<LANE> where LANE = inbox local part convention
"""
from __future__ import annotations

import json
import smtplib
import sys
import time
from email.message import EmailMessage
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from gops import db, guards, ops  # noqa: E402


def approved_sends(conn) -> list[dict]:
    out = []
    for r in conn.execute(
        "SELECT id, payload FROM approvals WHERE status='approved' AND kind='send'"
    ).fetchall():
        p = r["payload"]
        if isinstance(p, str):
            p = json.loads(p)
        p["approval_id"] = r["id"]
        out.append(p)
    return out


def send_one(conn, item: dict, dry: bool) -> dict:
    lead_id = item["lead_id"]
    inbox = item["inbox"]

    lead = conn.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
    if not lead:
        return {**item, "error": f"lead {lead_id} not found"}
    if lead["stop"]:
        return {**item, "skipped": "lead has do-not-contact flag"}
    # primary contact carries the email; fallback: any contact for this lead
    addr = None
    if lead["company"]:
        c = conn.execute(
            "SELECT email FROM contacts WHERE lead_id=? AND email IS NOT NULL"
            " ORDER BY is_primary DESC LIMIT 1", (lead_id,)).fetchone()
        addr = c["email"] if c else None
    if not addr:
        return {**item, "error": "no contact email on lead — enrich first (contacts table)"}

    # record send BEFORE delivery (idempotent; guards raise on cap breach)
    try:
        send_id = guards.record_send(conn, lead_id=lead_id, contact_id=None,
                                     channel="email", inbox=inbox,
                                     subject=item["subject"],
                                     body_path=item["body_path"],
                                     dedupe_key=item["dedupe_key"])
    except Exception as e:
        return {**item, "error": str(e)}

    if dry:
        return {**item, "send_id": send_id, "dry_run": True,
                "to": addr, "subject": item["subject"]}

    body = Path(item["body_path"]).read_text(encoding="utf-8")
    msg = EmailMessage()
    msg["From"] = inbox
    msg["To"] = addr
    msg["Subject"] = item["subject"]
    msg.set_content(body)

    host = "smtp.gmail.com"  # Workspace
    user = inbox
    password = Path(ROOT / "secrets" / f"smtp_{inbox}.txt").read_text().strip() \
        if (ROOT / "secrets" / f"smtp_{inbox}.txt").exists() else \
        __import__("os").environ.get(f"OUTREACH_SMTP_PASS_{inbox.split('@')[0]}", "")

    try:
        with smtplib.SMTP_SSL(host, 465, timeout=30) as s:
            s.login(user, password)
            s.send_message(msg)
        guards.mark_sent(conn, send_id, time.time())
        return {**item, "send_id": send_id, "sent_to": lead["email"], "status": "sent"}
    except Exception as e:
        guards.mark_failed(conn, send_id)  # failed delivery refunds the counter
        return {**item, "send_id": send_id, "error": f"smtp: {e}", "status": "failed"}


def main():
    dry = "--apply" not in sys.argv
    stop = (ROOT / guards.STOP_FILE).exists()
    conn = db.connect(ROOT / "db" / "consulting.db")
    if stop:
        print(json.dumps({"halted": True, "reason": "OUTREACH_STOP present"}, indent=2))
        return
    items = approved_sends(conn)
    results = [send_one(conn, i, dry) for i in items]
    print(json.dumps({"dry_run": dry, "count": len(results), "results": results}, indent=2))


if __name__ == "__main__":
    main()
