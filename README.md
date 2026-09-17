# GoGentic — Consulting Operations

AI implementation partner for agencies. White-label delivery: agencies sell AI
services under their brand; GoGentic is the production engine.

**Operator:** Ian Greenberg (AI researcher, SMU) — human closer.
**System:** this repo + Hermes/Codex agents + thin MCP + SQLite CRM.

## Architecture (locked decisions)

| Layer | Holds | Where |
|---|---|---|
| State | leads, sends, engagements, approvals | SQLite (`db/consulting.db`) |
| Discovery | MCP tools for any agent | `gops/mcp_server.py` (state + discovery ONLY) |
| Actions | CLI with guards/caps | `tools/ops.py` |
| Procedures | how to execute (warmup, sequences, lanes) | Hermes skills + `docs/` |
| Facts | durable knowledge, decisions record | ian-brain wiki `consulting-ops` page |

## Quick start
```bash
python -m pytest tests/ -q          # 7 guard tests
python tools/ops.py status          # funnel snapshot
python tools/ops.py add-lead --company "X" --kind partner --signal "why now"
python tools/ops.py stop            # global outreach halt (file-based)
```

MCP server (stdio): `python gops/mcp_server.py` — tools: `pipeline_status`,
`pending_approvals`, `claim_lead`, `log_client_work`, `check_stop`.

## Guardrails (enforced in code, not prompts)
- 25 sends/inbox/day hard cap; every send recorded BEFORE delivery (dedupe keys)
- Failed sends refund the daily counter; `control/OUTREACH_STOP` halts everything
- Approvals queue for anything that sends/spends/touches client work
- Keeper accounts (main domains, GitHub, Mercury) never used for outreach

## Rate card
See `gops/ratecard.py` (single source of truth) and `docs/RATECARD.md`.
Wholesale for agency partners; retail = our suggested client price.

## Docs
- `docs/RUNBOOK-EMAIL.md` — domain setup, warmup, burn policy
- `docs/RUNBOOK-PROSPECTING.md` — partner bot design + scoring
- `docs/SPEC-VOICE-BOT.md` — speed-to-lead Vapi/Retell spec
- `docs/RATECARD.md` — client-facing pricing

## Secrets policy
Secrets/lead data/runtime config NEVER enter this public repo.
`.env` + `db/*.db` + `control/` are gitignored.
