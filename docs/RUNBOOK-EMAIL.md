# Email Infrastructure Runbook — Domain Setup & Warmup

Never cold-send from gogentic.com or iangreenberg.com. Buy separate sending domains.

## 1. Buy sending domains (consumables, ~$10/yr each)
- 3 domains to start, e.g. `gogenticconsulting.com`, `getgogentic.com`, `gogenticai.com`
- Registrar: Namecheap (already used) or Cloudflare Registrar
- These are BURNABLE. If reputation dies, retire and buy new.

## 2. Mailboxes
- Google Workspace ($7/user/mo) — best deliverability, 2-3 inboxes per domain
- NEVER mix personal/company inboxes with cold outreach

## 3. DNS records per domain (non-negotiable, Google/Yahoo bulk-sender rules)
| Record | Purpose |
|---|---|
| SPF (`v=spf1 include:_spf.google.com ~all`) | authorized senders |
| DKIM (via Workspace admin) | cryptographic signing |
| DMARC (`v=DMARC1; p=none; rua=mailto:...`) start, tighten to `p=quarantine` later | policy + reports |
| MX | receiving (needed for replies) |
| Tracking domain CNAME (per sending tool) | click/open tracking on subdomain, not root |

Verify: https://postmaster.google.com + mail-tester.com before first campaign.

## 4. Warmup schedule (3 weeks minimum, per goal contract)
| Days | Volume per inbox |
|---|---|
| 1-3   | 5-10/day, high open+reply rate (warmup network or manual) |
| 4-7   | 10-15/day |
| 8-14  | 15-20/day |
| 15-21 | 20-25/day (hard cap 25 enforced in gops.guards) |
- Keep warmup running at maintenance level forever
- Watch: bounce <2%, spam complaints <0.1%, open rate sanity-check

## 5. Sending rules (enforced in code)
- 25/inbox/day hard cap (`gops.guards.PER_INBOX_DAILY_CAP`)
- Every send recorded BEFORE delivery (idempotent dedupe keys)
- Failed sends refund the daily counter
- `tools/ops.py stop` = instant global halt (control/OUTREACH_STOP)
- Send window: business hours in recipient timezone, no weekend blasts

## 6. Sequence template (partner pitch)
1. Day 0: signal-based opener (their agency + specific why-now)
2. Day 3: value bump (one concrete result/case)
3. Day 7: pilot offer with de-risk terms
4. Day 14: breakup / door-open
- Reply-rate targets: generic <3.5% = fix list/copy; signal-based target 10%+

## 7. Burn policy
- Domain flagged (opens collapse, tests land spam): stop sending from it same day,
  migrate sequence to next domain, log in decisions table
- Never re-warm a burnt domain; $10 lesson, move on
