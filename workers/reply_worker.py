#!/usr/bin/env python3
"""reply_worker.py — polls an inbox (IMAP), classifies replies, moves leads.

Runs on cron (every 15-30 min). Uses the same guards as sends:
- never mutates leads directly; goes through gops.ops
- IMAP creds come from env (OUTREACH_IMAP_HOST/USER/PASS per inbox lane)
- dry-run mode prints classification without mutating (default)

Classification rules (keyword-first, cheap + auditable):
  positive : books/call/schedule/interested/yes + question about pricing/demo
  negative : not interested/unsubscribe/remove
  ooo      : out of office/vacation
  else     : unclassified (surfaces in status for manual read)
"""
from __future__ import annotations

import imaplib
import json
import os
import re
import sys
from email import policy
from email.parser import BytesParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from gops import db, ops  # noqa: E402

POSITIVE = re.compile(
    r"\b(interested|tell me more|sounds good|let'?s (talk|schedule|book)|"
    r"schedule a call|book a (call|demo)|happy to (jump|hop) on|pricing|"
    r"how much|demo|available (this|next)|works for me)\b", re.I)
NEGATIVE = re.compile(
    r"\b(not interested|no thanks|unsubscribe|remove me|stop emailing|"
    r"take me off|do not contact)\b", re.I)
OOO = re.compile(r"\b(out of (the )?office|on vacation|pto|away until|"
                 r"automatic reply|auto-?reply)\b", re.I)
UNSUB_HEADER = ("List-Unsubscribe",)


def classify(subject: str, body: str, headers: dict) -> str:
    if UNSUB_HEADER[0] in headers or NEGATIVE.search(subject or ""):
        return "negative"
    text = f"{subject}\n{body}"
    if OOO.search(text):
        return "ooo"
    if POSITIVE.search(text):
        return "positive"
    if NEGATIVE.search(text):
        return "negative"
    return "unclassified"


def fetch_unread(host: str, user: str, password: str, limit: int = 20) -> list[dict]:
    out = []
    imap = imaplib.IMAP4_SSL(host)
    try:
        imap.login(user, password)
        imap.select("INBOX")
        _, data = imap.search(None, "UNSEEN")
        ids = data[0].split()[-limit:]
        for mid in ids:
            _, msg_data = imap.fetch(mid, "(RFC822)")
            msg = BytesParser(policy=policy.default).parsebytes(msg_data[0][1])
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_content()
                        break
            else:
                body = msg.get_content()
            out.append({
                "from": msg.get("From", ""),
                "subject": msg.get("Subject", ""),
                "body": body[:4000],
                "list_unsub": bool(msg.get("List-Unsubscribe")),
            })
    finally:
        try:
            imap.logout()
        except Exception:
            pass
    return out


def process(conn, inbox_lane: str, messages: list[dict], dry_run: bool = True) -> list[dict]:
    results = []
    for m in messages:
        label = classify(m["subject"], m["body"],
                         {"List-Unsubscribe": "1"} if m["list_unsub"] else {})
        # match lead by email address (contacts table or lead email field)
        addr_m = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", m["from"] or "")
        addr = addr_m.group(0).lower() if addr_m else None
        lead_id = None
        if addr:
            row = conn.execute(
                "SELECT lead_id FROM contacts WHERE email=? LIMIT 1", (addr,)).fetchone()
            if not row:
                row = conn.execute(
                    "SELECT id AS lead_id FROM leads WHERE email=? LIMIT 1", (addr,)).fetchone()
            lead_id = row["lead_id"] if row else None
        results.append({"inbox": inbox_lane, "from": m["from"], "subject": m["subject"],
                        "classification": label, "lead_id": lead_id})
        if dry_run or not lead_id:
            continue
        status_map = {"positive": "replied", "negative": "dead",
                      "ooo": "contacted", "unclassified": "replied"}
        ops.set_status(conn, lead_id, status_map[label])
        ops.record_reply(conn, lead_id=lead_id, classification=label,
                         from_addr=m["from"], subject=m["subject"])
    return results


def main():
    dry = "--apply" not in sys.argv
    conn = db.connect(ROOT / "db" / "consulting.db")
    lanes = []
    for k, v in os.environ.items():
        if k.startswith("OUTREACH_IMAP_HOST_"):
            lane = k.rsplit("_", 1)[-1]
            lanes.append((lane, v, os.environ.get(f"OUTREACH_IMAP_USER_{lane}", ""),
                          os.environ.get(f"OUTREACH_IMAP_PASS_{lane}", "")))
    if not lanes:
        print(json.dumps({"error": "no OUTREACH_IMAP_HOST_* env lanes configured"}, indent=2))
        return
    all_results = []
    for lane, host, user, password in lanes:
        try:
            msgs = fetch_unread(host, user, password)
            all_results += process(conn, lane, msgs, dry_run=dry)
        except Exception as e:
            all_results.append({"inbox": lane, "error": str(e)})
    print(json.dumps({"dry_run": dry, "results": all_results}, indent=2))


if __name__ == "__main__":
    main()
