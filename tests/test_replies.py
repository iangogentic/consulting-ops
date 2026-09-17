"""Tests for reply recording + reply_worker classification."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from gops import db, ops  # noqa: E402
from workers.reply_worker import classify  # noqa: E402


def test_classify_positive():
    assert classify("Re: missed calls", "lets schedule a call", {}) == "positive"


def test_classify_negative_unsub_header():
    assert classify("Re: hi", "thanks", {"List-Unsubscribe": "1"}) == "negative"


def test_classify_ooo():
    assert classify("Re: x", "I am out of office until Monday", {}) == "ooo"


def test_classify_unclassified():
    assert classify("Re: x", "maybe later, busy quarter", {}) == "unclassified"


def test_record_reply_roundtrip(tmp_path):
    conn = db.connect(tmp_path / "t.db")
    lid = ops.add_lead(conn, company="Acme", kind="partner")
    rid = ops.record_reply(conn, lead_id=lid, classification="positive",
                           from_addr="a@b.co", subject="Re: x")
    assert rid > 0
    row = conn.execute("SELECT classification, summary FROM replies WHERE id=?", (rid,)).fetchone()
    assert row["classification"] == "positive"
    assert "a@b.co" in row["summary"]
    # lead moved to replied
    assert conn.execute("SELECT status FROM leads WHERE id=?", (lid,)).fetchone()[0] == "replied"
    # negative moves to dead
    ops.record_reply(conn, lead_id=lid, classification="negative",
                     from_addr="a@b.co", subject="no")
    assert conn.execute("SELECT status FROM leads WHERE id=?", (lid,)).fetchone()[0] == "dead"


def test_record_reply_bad_classification(tmp_path):
    import pytest
    conn = db.connect(tmp_path / "t.db")
    lid = ops.add_lead(conn, company="Acme", kind="partner")
    with pytest.raises(ops.OpError):
        ops.record_reply(conn, lead_id=lid, classification="banana",
                         from_addr="a@b.co", subject="x")
