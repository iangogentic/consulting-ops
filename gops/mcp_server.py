"""Thin MCP server — state + discovery only.

Philosophy (locked in design discussions):
- MCP for mutable shared STATE and discovery
- procedures -> Hermes skills
- actions    -> CLI tools (tools/*.py)
- facts      -> wiki
This server NEVER sends email, never calls external APIs. It reads/writes the CRM.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from mcp.server.mcpserver import MCPServer

from gops import db as gdb
from gops import guards, ops

DB_PATH = os.environ.get(
    "GOP_DB", str(Path(__file__).resolve().parent.parent / "db" / "consulting.db")
)

server = MCPServer(
    name="consulting-ops",
    instructions=(
        "Consulting-ops state + discovery. Read pipeline, list approvals, claim "
        "leads, log engagements. Sending/spending happens via CLI tools, not here."
    ),
)

_conn = gdb.connect(DB_PATH)


@server.tool()
def pipeline_status() -> str:
    """Snapshot of the whole funnel: leads by status, sends, revenue, pending approvals."""
    return json.dumps(ops.pipeline_status(_conn), indent=2)


@server.tool()
def pending_approvals() -> str:
    """List approvals waiting for Ian (sends, spends, client work)."""
    rows = ops.pending_approvals(_conn)
    return json.dumps([dict(r) for r in rows], indent=2, default=str)


@server.tool()
def claim_lead(lead_id: int, claimed_by: str) -> str:
    """Claim a lead for a session/agent so two workers never work it at once."""
    ops.claim_lead(_conn, lead_id, claimed_by=claimed_by)
    return f"lead {lead_id} claimed by {claimed_by}"


@server.tool()
def log_client_work(client_name: str, kind: str, service: str, amount_cents: int = 0) -> str:
    """Record an engagement (pilot/white_label/retainer/gig) for a client."""
    eid = ops.log_client_work(_conn, client_name=client_name, kind=kind,
                              service=service, amount_cents=amount_cents)
    return f"engagement {eid} logged"


@server.tool()
def check_stop() -> str:
    """Is outreach halted? (control/OUTREACH_STOP present = halt)."""
    halted = guards.check_stop(str(Path(DB_PATH).parent.parent / guards.STOP_FILE))
    return json.dumps({"outreach_halted": halted})


if __name__ == "__main__":
    import anyio
    anyio.run(server.run_stdio_async)
