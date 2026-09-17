"""GoGentic wholesale rate card — the document everything hangs on.

wholesale = what the agency pays us (their cost)
retail   = what we suggest they charge their client (their markup 2-3x)
"""

SERVICES = {
    "ai_receptionist_setup": {
        "name": "AI Receptionist & Booking (setup)",
        "desc": "24/7 voice agent answering calls, booking appointments, capturing missed-call leads. Trained on the business's services, hours, and calendar.",
        "wholesale_cents": 150000,   # $1,500
        "retail_cents": 400000,      # $4,000 suggested
        "recurring": False,
    },
    "ai_receptionist_retainer": {
        "name": "AI Receptionist — managed monthly",
        "desc": "Monitoring, prompt tuning, monthly call-quality report, changes included.",
        "wholesale_cents": 40000,    # $400/mo
        "retail_cents": 100000,      # $1,000/mo suggested
        "recurring": True,
    },
    "agent_workflow_build": {
        "name": "Custom Agent Workflow (one build)",
        "desc": "One automated workflow end-to-end: intake, follow-up, reporting, or document processing. Scoped fixed-price.",
        "wholesale_cents": 250000,   # $2,500
        "retail_cents": 600000,      # $6,000 suggested
        "recurring": False,
    },
    "agent_readiness_package": {
        "name": "Agent-Ready Business Package",
        "desc": "Make the client's stack AI-operable: integrations, scoped credentials, audit trail, one working agent workflow live.",
        "wholesale_cents": 400000,   # $4,000
        "retail_cents": 1200000,     # $12,000 suggested
        "recurring": False,
    },
    "ops_retainer": {
        "name": "AI Operations Retainer",
        "desc": "Ongoing agent maintenance, improvements, and one new automation per month.",
        "wholesale_cents": 100000,   # $1,000/mo
        "retail_cents": 250000,      # $2,500/mo suggested
        "recurring": True,
    },
    "pilot_project": {
        "name": "Paid Pilot (de-risk first project)",
        "desc": "One small fixed-scope build so the agency can vet delivery before committing. Credited toward first full project.",
        "wholesale_cents": 100000,   # $1,000
        "retail_cents": 200000,      # $2,000 suggested
        "recurring": False,
    },
}

PILOT_TERMS = (
    "50% upfront, 50% on delivery. Fixed scope agreed in writing before start. "
    "Pilot fee credited 1:1 toward a full project signed within 30 days. "
    "White-label: we are invisible to your client; you own the relationship."
)
