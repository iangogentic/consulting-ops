# Partner Prospecting Bot — Design

## Goal
Feed the CRM with qualified agency leads + why-now signals, so outreach is
signal-based (10%+ reply territory), not generic (3.4%).

## Sources (free-first)
1. **Google Maps / Overture-style scraping** — agencies by segment in target metros
   (web design, marketing, MSPs). Reuse nail-salon-DB pipeline patterns.
2. **Clutch / UpCity directories** — agencies with reviews, size, service lines
   (respect robots; use modest pacing)
3. **Job postings** (Indeed, LinkedIn public, agency own /careers pages) —
   "AI automation specialist" postings = budget-approved pain
4. **Agency websites** — check for /ai or /automation service pages (disqualifier:
   already selling AI), tech stack hints, contact pages

## Qualification scoring (0-100)
| Signal | Points |
|---|---|
| No existing AI service line | +20 |
| Serving local-services verticals (salons/clinics/home) | +25 (our proof fits) |
| 5-50 employees (big enough to pay, small enough to move) | +15 |
| Job posting mentioning AI/automation | +20 |
| Recently funded / new office / new service launch | +10 |
| Contact discoverable (form/name/email) | +10 |

Score >= 60 → status `qualified`, auto-claimed by research agent.
Score < 40 → `dead` with reason.

## Bot implementation (phase 2)
- Worker: `workers/prospect.py` on cron (Razer or desktop2, systemd user unit)
- Writes only via `gops.ops.add_lead` — never direct SQL
- Respect per-source pacing: 1 req/2s, stop on 429s, cache raw HTML to artifacts
- Each run: 50-100 candidates scored, 10-20 qualified leads appended
- Report: counts by source/segment into decisions table

## Seed list (first 20, manual-assist mode)
Metro priority: Dallas first (local presence + chamber angle), then Austin/Houston,
then remote-friendly (any US).
