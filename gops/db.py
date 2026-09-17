"""SQLite CRM schema for consulting-ops.

CP-pattern: one database, everything reads/writes through it.
State only — knowledge lives in the wiki, procedures in skills.
"""
import sqlite3
import time
from pathlib import Path

SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL DEFAULT 'partner',        -- partner | direct | gig
    company TEXT NOT NULL,
    segment TEXT,                                -- webshop | marketing | msp | vertical-local
    website TEXT,
    city TEXT,
    source TEXT,                                 -- scraper | manual | inbound
    signal TEXT,                                 -- why-now evidence, plain language
    status TEXT NOT NULL DEFAULT 'new',          -- new|qualified|contacted|replied|call_booked|won|lost|dead
    score INTEGER DEFAULT 0,
    claimed_by TEXT,                             -- agent/session holding the lead
    claimed_at REAL,
    stop INTEGER NOT NULL DEFAULT 0,             -- 1 = do not contact
    created_at REAL NOT NULL,
    updated_at REAL NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_leads_company ON leads(company);

CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER NOT NULL REFERENCES leads(id),
    name TEXT, role TEXT, email TEXT, phone TEXT, linkedin TEXT,
    is_primary INTEGER NOT NULL DEFAULT 0,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS engagements (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER REFERENCES leads(id),
    client_name TEXT NOT NULL,
    kind TEXT NOT NULL,                          -- pilot | white_label | retainer | gig
    service TEXT NOT NULL,                       -- rate-card service key
    amount_cents INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'active',       -- active|delivered|paid|cancelled
    started_at REAL, delivered_at REAL, paid_at REAL,
    notes TEXT,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS sends (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER REFERENCES leads(id),
    contact_id INTEGER REFERENCES contacts(id),
    channel TEXT NOT NULL,                       -- email | upwork | linkedin | form
    inbox TEXT NOT NULL,                         -- sending mailbox identity
    subject TEXT, body_path TEXT,
    dedupe_key TEXT NOT NULL UNIQUE,             -- idempotency: recorded BEFORE delivery
    status TEXT NOT NULL DEFAULT 'recorded',     -- recorded|sent|failed|draft_approved|draft_rejected
    sent_at REAL,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS replies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    send_id INTEGER NOT NULL REFERENCES sends(id),
    lead_id INTEGER REFERENCES leads(id),
    received_at REAL NOT NULL,
    classification TEXT,                         -- positive|question|objection|noise
    summary TEXT, raw_path TEXT,
    handled INTEGER NOT NULL DEFAULT 0           -- 1 = queued to Ian / actioned
);

CREATE TABLE IF NOT EXISTS calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id INTEGER REFERENCES leads(id),
    scheduled_at REAL, happened_at REAL,
    outcome TEXT,                                -- booked|held|no_show|closed_won|closed_lost
    amount_cents INTEGER, notes TEXT,
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    what TEXT NOT NULL, why TEXT NOT NULL,
    made_by TEXT NOT NULL DEFAULT 'agent',
    created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS approvals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kind TEXT NOT NULL,                          -- send | spend | client_work
    payload TEXT NOT NULL,                       -- JSON
    status TEXT NOT NULL DEFAULT 'pending',      -- pending|approved|rejected
    requested_by TEXT, decided_by TEXT,
    created_at REAL NOT NULL, decided_at REAL
);

CREATE TABLE IF NOT EXISTS daily_counters (
    day TEXT NOT NULL,                           -- YYYY-MM-DD (America/Chicago)
    inbox TEXT NOT NULL,
    sent INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (day, inbox)
);
"""


def connect(db_path: str | Path) -> sqlite3.Connection:
    p = Path(db_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(p))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(SCHEMA)
    return conn


def now() -> float:
    return time.time()
