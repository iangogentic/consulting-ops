# Upwork Monitor Spec

## Goal
Surface async gig postings that match the lane (AI automation, voice agents,
chatbots, MCP/integration work) within minutes of posting, so GoGentic can
bid early (first 10 bids get ~5x the interview rate of late bids).

## Architecture (3 pieces, all local, no paid APIs)
1. **search_worker** (every 30 min, cron): RSS is dead on Upwork; use the
   public search page `https://www.upwork.com/nx/search/talent/?q=...` via
   plain HTTP fetch. If blocked (403), fall back to logged-in browser (CDP
   on Razer Chrome, port 9222) — NOT headless (bot detection).
2. **classifier**: keyword score per posting
   - +3 voice|receptionist|phone agent|Vapi|Retell|Bland
   - +3 chatbot|booking automation|appointment
   - +2 n8n|Make.com|Zapier|API integration
   - +2 MCP|agent|LLM|GPT-4|Claude
   - -5 assistant|VA|data entry|admin (wrong kind of "assistant")
   Score >= 5 → notify Ian (draft bid), 3-4 → log for review.
3. **bid_drafter**: for scored postings, draft a 3-line proposal into
   `drafts/upwork/<jobid>.md` + queue approval. Ian approves → manual paste
   (Upwork TOS: no auto-submit; keep account clean).

## State
`db/upwork_seen` table: job_id PK, title, score, first_seen, notified, bid_status.
Idempotent: a job seen once is never re-notified.

## Account rules (keeper account)
- Bids: max 8/day (uses/connects conservation)
- Profile: GoGentic-branded, rate $45/hr floor, white-listed portfolio pieces
- STOP file: `control/UPWORK_STOP` halts the whole lane
