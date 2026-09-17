#!/usr/bin/env python3
"""ops.py — CLI actions over the consulting CRM.

Usage:
  python tools/ops.py status
  python tools/ops.py add-lead --company "Web Shop Dallas" --kind partner --segment webshop --signal "hiring AI role"
  python tools/ops.py claim --id 1 --by hermes
  python tools/ops.py status-set --id 1 --status contacted
  python tools/ops.py approve-list
  python tools/ops.py approve-decide --id 2 --yes
  python tools/ops.py request-send --lead 1 --inbox a@x.com --subject "Hi" --body drafts/1.md
  python tools/ops.py stop            # create OUTREACH_STOP
  python tools/ops.py resume          # remove OUTREACH_STOP
"""
from __future__ import annotations

import argparse
import json
import sys
import time
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from gops import db as gdb  # noqa: E402
from gops import guards, ops  # noqa: E402

DB = ROOT / "db" / "consulting.db"


def get_conn():
    return gdb.connect(DB)


def main():
    ap = argparse.ArgumentParser(prog="ops")
    sub = ap.add_subparsers(dest="cmd", required=True)

    sub.add_parser("status")

    p = sub.add_parser("add-lead")
    p.add_argument("--company", required=True)
    p.add_argument("--kind", default="partner")
    p.add_argument("--segment")
    p.add_argument("--website")
    p.add_argument("--city")
    p.add_argument("--signal")
    p.add_argument("--source", default="manual")

    p = sub.add_parser("claim")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--by", required=True)

    p = sub.add_parser("status-set")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--status", required=True)

    sub.add_parser("approve-list")

    p = sub.add_parser("approve-decide")
    p.add_argument("--id", type=int, required=True)
    p.add_argument("--yes", action="store_true")

    p = sub.add_parser("request-send")
    p.add_argument("--lead", type=int, required=True)
    p.add_argument("--inbox", required=True)
    p.add_argument("--subject", required=True)
    p.add_argument("--body", required=True)
    p.add_argument("--auto", action="store_true",
                   help="record+send directly if approved already; else queue approval")

    sub.add_parser("stop")
    sub.add_parser("resume")

    args = ap.parse_args()
    conn = get_conn()

    if args.cmd == "status":
        print(json.dumps(ops.pipeline_status(conn), indent=2))

    elif args.cmd == "add-lead":
        lid = ops.add_lead(conn, company=args.company, kind=args.kind,
                           segment=args.segment, website=args.website,
                           city=args.city, source=args.source, signal=args.signal)
        print(f"lead {lid} added")

    elif args.cmd == "claim":
        ops.claim_lead(conn, args.id, claimed_by=args.by)
        print(f"lead {args.id} claimed by {args.by}")

    elif args.cmd == "status-set":
        ops.set_status(conn, args.id, args.status)
        print(f"lead {args.id} -> {args.status}")

    elif args.cmd == "approve-list":
        for r in ops.pending_approvals(conn):
            print(f"[{r['id']}] {r['kind']}: {r['payload'][:140]}")

    elif args.cmd == "approve-decide":
        ops.decide_approval(conn, args.id, approved=args.yes, decided_by="ian")
        print(f"approval {args.id} -> {'approved' if args.yes else 'rejected'}")

    elif args.cmd == "request-send":
        guards.validate_inbox_day(conn, args.inbox, guards.day_key(time.time()))
        body_path = str(Path(args.body).resolve())
        dedupe = uuid.uuid4().hex[:16]
        payload = {"lead_id": args.lead, "inbox": args.inbox,
                   "subject": args.subject, "body_path": body_path,
                   "dedupe_key": dedupe}
        aid = ops.request_approval(conn, kind="send", payload=payload)
        print(f"approval {aid} queued for send {dedupe}")

    elif args.cmd == "stop":
        (ROOT / "control").mkdir(exist_ok=True)
        (ROOT / guards.STOP_FILE).write_text("halted")
        print("outreach STOPPED")

    elif args.cmd == "resume":
        f = ROOT / guards.STOP_FILE
        if f.exists():
            f.unlink()
        print("outreach resumed")


if __name__ == "__main__":
    main()
