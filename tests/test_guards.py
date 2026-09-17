"""Tests for send guards, caps, and idempotency — the discipline that keeps accounts alive."""
import time

import pytest

from gops import db, guards


@pytest.fixture()
def conn(tmp_path):
    return db.connect(tmp_path / "test.db")


def test_daily_cap_enforced(conn):
    day = guards.day_key(time.time())
    for i in range(guards.PER_INBOX_DAILY_CAP):
        guards.validate_inbox_day(conn, "a@x.com", day)
        guards.record_send(conn, lead_id=None, contact_id=None, channel="email",
                           inbox="a@x.com", subject="s", body_path="b.md",
                           dedupe_key=f"k{i}")
    with pytest.raises(guards.GuardError, match="daily cap"):
        guards.validate_inbox_day(conn, "a@x.com", day)


def test_idempotent_dedupe(conn):
    guards.record_send(conn, lead_id=None, contact_id=None, channel="email",
                       inbox="a@x.com", subject="s", body_path="b.md", dedupe_key="dup-1")
    with pytest.raises(guards.GuardError, match="duplicate"):
        guards.validate_dedupe(conn, "dup-1")
    guards.validate_dedupe(conn, "dup-2")  # fresh key passes


def test_failed_send_refunds_counter(conn):
    day = guards.day_key(time.time())
    sid = guards.record_send(conn, lead_id=None, contact_id=None, channel="email",
                             inbox="a@x.com", subject="s", body_path="b.md", dedupe_key="k1")
    assert conn.execute("SELECT sent FROM daily_counters WHERE day=? AND inbox=?",
                        (day, "a@x.com")).fetchone()["sent"] == 1
    guards.mark_failed(conn, sid)
    assert conn.execute("SELECT sent FROM daily_counters WHERE day=? AND inbox=?",
                        (day, "a@x.com")).fetchone()["sent"] == 0
    assert conn.execute("SELECT status FROM sends WHERE id=?", (sid,)).fetchone()["status"] == "failed"


def test_email_validation(conn):
    with pytest.raises(guards.GuardError):
        guards.validate_email("not-an-email")
    guards.validate_email("owner@agency.com")


def test_stop_file(tmp_path):
    stop = tmp_path / "STOP"
    assert guards.check_stop(str(stop)) is False
    stop.write_text("halt")
    assert guards.check_stop(str(stop)) is True


def test_lead_claim_and_status(conn):
    import gops.ops as ops
    lead_id = ops.add_lead(conn, company="Web Shop Dallas", kind="partner",
                           segment="webshop", signal="hiring 'AI automation' role")
    ops.claim_lead(conn, lead_id, claimed_by="hermes-session-1")
    row = conn.execute("SELECT claimed_by, status FROM leads WHERE id=?", (lead_id,)).fetchone()
    assert row["claimed_by"] == "hermes-session-1"
    with pytest.raises(ops.OpError):
        ops.claim_lead(conn, lead_id, claimed_by="other-session")  # already claimed


def test_rate_card_total():
    from gops.ratecard import SERVICES
    assert all(s["wholesale_cents"] < s["retail_cents"] for s in SERVICES.values())
