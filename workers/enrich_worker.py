#!/usr/bin/env python3
"""enrich_worker.py — finds contact emails for leads from their websites.

Phase 1 (this): fetch lead website homepage + /contact, extract emails that
aren't common webmaster/junk addresses, store as contacts rows.
Phase 2 (later): hunter.io / Apollo API enrichment behind the same interface.

Pacing: 1 req / 2s per host, 10s timeout, 40 leads/run max.
Every fetch cached to artifacts/enrich/<domain>.html for audit.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from gops import db, ops  # noqa: E402

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
JUNK = re.compile(
    r"(example|domain\.com|yourname|sentry|wixpress|@2x|\.png|\.jpg|\.webp|"
    r"godaddy|squarespace|u003e|noreply|no-reply)", re.I)
GOOD_ROLES = re.compile(
    r"(info|hello|contact|team|office|sales|admin|hi|owner|founder)@", re.I)
UA = {"User-Agent": "Mozilla/5.0 (compatible; GoGenticEnricher/0.1; +https://gogentic.pages.dev)"}


def fetch(url: str, cache_dir: Path) -> str | None:
    cache = cache_dir / (re.sub(r"[^\w]", "_", url)[:120] + ".html")
    if cache.exists():
        return cache.read_text(encoding="utf-8", errors="ignore")[:200_000]
    try:
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read(300_000).decode("utf-8", errors="ignore")
        cache.write_text(html, encoding="utf-8")
        time.sleep(2)  # pacing
        return html
    except Exception:
        return None


def contact_urls(html: str, base: str) -> list[str]:
    m = re.search(r'href=["\']([^"\']*(contact|about|team)[^"\']*)["\']', html, re.I)
    if not m:
        return []
    href = m.group(1)
    if href.startswith("http"):
        return [href]
    if href.startswith("/"):
        return [base.rstrip("/") + href]
    return [base.rstrip("/") + "/" + href]


def extract_emails(html: str) -> list[str]:
    found = set()
    for e in EMAIL_RE.findall(html):
        if JUNK.search(e):
            continue
        found.add(e.lower().rstrip("."))
    # prefer role addresses
    ordered = sorted(found, key=lambda e: (0 if GOOD_ROLES.match(e) else 1, len(e)))
    return ordered[:3]


def mailto_decode(html: str) -> list[str]:
    # cloudflare email-protected / simple obfuscation: look for data-cfemail
    out = []
    for m in re.finditer(r'data-cfemail="([0-9a-f]+)"', html):
        code = m.group(1)
        key = int(code[:2], 16)
        out.append("".join(chr(int(code[i:i+2], 16) ^ key) for i in range(2, len(code), 2)))
    return out


def enrich_lead(conn, lead_row, cache_dir: Path) -> dict:
    site = lead_row["website"]
    if not site:
        return {"lead_id": lead_row["id"], "company": lead_row["company"],
                "result": "no website"}
    base = site if site.startswith("http") else f"https://{site}"
    html = fetch(base, cache_dir)
    emails: list[str] = []
    if html:
        emails = extract_emails(html) or mailto_decode(html)
        if not emails:
            for cu in contact_urls(html, base)[:2]:
                ch = fetch(cu, cache_dir)
                if ch:
                    emails = extract_emails(ch) or mailto_decode(ch)
                    if emails:
                        break
    if not emails:
        return {"lead_id": lead_row["id"], "company": lead_row["company"],
                "result": "no email found"}
    added = []
    existing = {r["email"] for r in conn.execute(
        "SELECT email FROM contacts WHERE lead_id=?", (lead_row["id"],)).fetchall()}
    for e in emails:
        if e in existing:
            continue
        conn.execute(
            "INSERT INTO contacts (lead_id, name, email, is_primary, created_at)"
            " VALUES (?,?,?,?,?)",
            (lead_row["id"], None, e, 1 if not added else 0, time.time()))
        added.append(e)
    conn.commit()
    # a lead with a reachable contact is qualified
    if added:
        ops.set_status(conn, lead_row["id"], "qualified")
    return {"lead_id": lead_row["id"], "company": lead_row["company"],
            "result": f"+{len(added)} emails", "emails": added}


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=10)
    args = ap.parse_args()
    cache_dir = ROOT / "artifacts" / "enrich"
    cache_dir.mkdir(parents=True, exist_ok=True)
    conn = db.connect(ROOT / "db" / "consulting.db")
    leads = conn.execute(
        "SELECT * FROM leads WHERE website IS NOT NULL AND status='new'"
        " LIMIT ?", (args.limit,)).fetchall()
    results = [enrich_lead(conn, l, cache_dir) for l in leads]
    print(json.dumps({"processed": len(results), "results": results}, indent=2))


if __name__ == "__main__":
    main()
