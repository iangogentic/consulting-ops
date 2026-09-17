# BUILDLOG — consulting-ops

**Any agent (Hermes, Codex, cron) resuming work: READ THIS FILE FIRST.**
Goal: $20K/mo consulting revenue. Full operating rules: README.md.
Wiki mirror: ian-brain `consulting-ops` page (gateway desktop2, ~/Desktop/wiki/consulting-ops.md).

## 2026-09-17 — v1 build (Hermes session)

DONE (all verified by running them):
- [x] Repo initialized, first commit 434d2a3
- [x] SQLite CRM schema: leads, contacts, engagements, sends, replies, calls,
      decisions, approvals, daily_counters (gops/db.py)
- [x] Send guards: 25/inbox/day cap, dedupe idempotency, failed-send refund,
      OUTREACH_STOP check (gops/guards.py)
- [x] Ops layer: add_lead, claim_lead (session locking), set_status,
      pipeline_status, approvals request/decide, log_client_work (gops/ops.py)
- [x] Rate card single source of truth (gops/ratecard.py) — wholesale/retail
- [x] Thin MCP server, 5 tools registered + verified (gops/mcp_server.py):
      pipeline_status, pending_approvals, claim_lead, log_client_work, check_stop
- [x] CLI: tools/ops.py — status, add-lead, claim, status-set, approve-list,
      approve-decide, request-send, stop, resume. End-to-end tested live:
      lead added → send requested → approval queued → caps enforced
- [x] Tests: 7/7 passing
- [x] Site: web/ — index (vertical hero), services, ratecard, about, contact
      (mailto fallback form until CRM intake hooked)
- [x] Docs: RUNBOOK-EMAIL (warmup/burn policy), RUNBOOK-PROSPECTING (bot design
      + scoring), SPEC-VOICE-BOT (speed-to-lead), RATECARD, README
- [x] OUTREACH_STOP file created (outreach halted until Ian approves first batch)
- [x] Wiki page created on ian-brain

IN FLIGHT / NEXT (do these in order):
1. [x] wrangler login DONE (OAuth as ian@gogentic.ai; had to clear stale port 8976
       holder; must run deploy in PTY terminal — non-TTY fails wrangler's check)
2. [x] Site deployed: https://gogentic.pages.dev (200 verified, Pages project
       `gogentic`). Custom domain consult.iangreenberg.com pending dashboard
       access — attach via Pages project → Custom domains when Ian grants it
3. [x] GitHub push DONE: https://github.com/iangogentic/consulting-ops (PUBLIC
       verified, branch master, gh CLI was already authed as iangogentic)
4. [x] Hermes skill `consulting-outreach` created (description must be ≤60 chars —
       skill_manage rejects longer, cost 3 retries)
5. [x] Prospects seeded: 18 leads w/ researched signals (Dallas/DFW agencies
       serving salons/medspas/dental/home-services). NOTE: two searches overlapped
       so it's 18, not 20. Honest count.
6. [x] First outreach batch drafted: leads 2 (Digital Success), 3 (Habanero),
       13 (Dental Growth Ops) → approvals 3/4/5 queued via request-send.
       Ian reviews: `python tools/ops.py approve-list` then `approve-decide --id N --yes`
7. [ ] BEFORE any real send: set up outreach1@gogentic.com inbox (or Ian's choice
       of sending inbox); no send worker exists yet — first sends are manual
8. [ ] Then: prospect scraper worker (RUNBOOK-PROSPECTING), Upwork monitor spec,
       voice bot phase 1 (SPEC-VOICE-BOT), Codex image-gen hero visuals,
       custom domain attach, more variants/landing pages

HOUSEKEEPING DONE: test lead + its 2 test approvals (ids 1-2) purged from DB.

BLOCKERS/NOTES:
- Cloudflare dashboard = bot challenge wall in automation browser; use wrangler CLI only
- Ian granting real domain access "tomorrow" (2026-09-18) — migrate site then
- Vault empty; any account login needed → browser_vault_save_login
- Cron continuity: every 30min a Hermes cron re-feeds this goal; build log +
  wiki are the memory. Keep them current or the loop degrades.
