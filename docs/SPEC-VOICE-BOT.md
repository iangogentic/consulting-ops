# Voice Bot Spec — Speed-to-Lead (Vapi or Retell)

## Why
Calling a positive-reply or inbound lead within 60 seconds = 40-70% connection
vs 8-15% cold. This is the strongest documented ROI play in the stack and the
differentiator vs every solo consultant.

## Trigger
- Inbound: lead form on site → webhook → call within 60s
- Outbound-warm: email reply classified `positive` in CRM → call within 5 min
- NEVER cold-call from purchased lists (TCPA + terrible conversion)

## Stack
| Layer | Choice | Cost |
|---|---|---|
| Voice platform | Vapi (dev control) or Retell (fastest to prod) | ~$0.07-0.15/min |
| Telephony | Twilio number(s), local-presence Dallas area code | ~$1/mo + usage |
| LLM | hosted GLM-5.3-Flash or provider default | pennies/call |
| Calendar | Cal.com booking link → CRM call row | free |

## Call flow (qualification, 3-5 min)
1. Confirm identity/context ("calling about your inquiry")
2. Qualify: business type, current pain (missed calls? follow-up?), timeline
3. Book: offer 2 concrete slots (Cal.com), confirm email
4. Route: qualified → Ian's calendar + SMS; not-ready → nurture tag in CRM

## Guardrails
- Voice bot NEVER quotes prices; scheduling + qualification only
- Record calls (consent per state; Texas = one-party, still announce)
- Voicemail: 15s script, drop + retry next day
- Escalation keyword ("human", "manager") → immediate transfer/take-message
- All calls logged to `calls` table w/ recording path + outcome

## Build order
1. Inbound missed-call text-back (simplest, ships in a day)
2. Inbound answering + booking (week 1-2)
3. Speed-to-lead outbound on positive replies (week 2-3)

## KPI
Connection rate >40% on warm triggers; booked-call rate >20% of connected;
cost per qualified call <$8.
