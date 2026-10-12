# MiniProject — AI School Operations Assistant

**What is this?** A single AI agent that manages your school-related emails, calendar, and tasks automatically — reviewing emails, creating calendar events, logging follow-up tasks, and sending you a daily summary.

**The goal:** One command (`python main.py`) reviews your school emails, acts on what needs action, and keeps you on top of deadlines and follow-ups.

## What It Does

Each time you run the agent, it:

1. **Triages new emails** — Reviews unread school emails, decides what action is needed
2. **Creates calendar events** — Schedules school events (field trips, parent nights, picture days, etc.)
3. **Logs tasks** — Records action items that need follow-up (submit forms, RSVP, etc.) into your task list
4. **Drafts email replies** — Writes responses for you to review and send
5. **Produces daily summary** — Creates a "Start of day" briefing and "End of day" wrap-up in your task list
6. **Requests your approval** — Shows you all drafted emails before they're sent (nothing goes out without your OK)

## Status

✅ **Fully operational** — Runs end-to-end with real Gmail, Calendar, and Google Tasks APIs. All 24 tests passing.

## Quick Links

- **[Full Technical Details](project/README.md)** — Architecture, tools, testing
- **[Current Status & Next Steps](docs/HANDOVER.md)** — What's done, what's next
- **[Work Log](docs/DAILY_LOG.md)** — Session notes
- **[Project Changes](docs/CHANGELOG.md)** — What's been built

## How It Works

**One AI agent. 13 tools. One command.**

The agent runs in a loop:
1. Reads unread school emails
2. For each email, decides what to do (create event? Log task? Draft reply?)
3. Takes action using its tools
4. Produces daily briefing and wrap-up summaries
5. Shows you all drafted emails for approval before sending

**What the agent can do:**
- 📧 Read and understand school emails
- 📅 Check your calendar and spot conflicts
- 📅 Create new calendar events (field trips, picture days, etc.)
- ✓ Mark emails as handled when done with them
- 📋 Log tasks into your Google Tasks list with priorities (🔴 HIGH, 🟠 MEDIUM, 🟢 LOW)
- ✉️ Draft email replies for you to review
- 💬 Write daily "Start of day" and "End of day" summaries
- 🚫 Never sends anything without your approval

**Key constraint:** The agent cannot send emails directly. Every reply goes to you for review first. Nothing goes out without your OK.

**Tech Stack:**
- Python backend
- OpenAI GPT-4o for the agent's "brain"
- Google APIs (Gmail, Calendar, Tasks) for real data
- LangChain/LangGraph for agent orchestration
- OAuth for secure Google authentication

## Quick Start

### Option 1: Try It Out (Demo Mode — No Setup Needed)

```bash
# Install dependencies
cd project
pip install -r requirements.txt

# Copy example environment file
cp .env.example .env

# Run the agent with fake data (sample emails, events, tasks)
python main.py
```

This runs through the full cycle with demo data — great for understanding what the agent does.

### Option 2: Connect to Your Real Email (Live Mode)

To run against your actual Gmail, Calendar, and Google Tasks:

1. Follow the setup in [project/README.md](project/README.md) to create a Google Cloud project and OAuth credentials
2. Set your `.env` to `MYAGENT_MODE=live`
3. Run `python main.py` — it will ask for permission the first time, then use your real data

See [docs/HANDOVER.md](docs/HANDOVER.md) for the current setup status.

## File Structure

```
MiniProject/
├── README.md ← You are here
├── docs/
│   ├── HANDOVER.md ← Current status & what's next
│   ├── DAILY_LOG.md ← Work session notes
│   ├── CHANGELOG.md ← What's been built
│   └── SKILLS_LOG.md ← Capabilities demonstrated
│
└── project/ ← The actual application
    ├── README.md ← Full technical documentation
    ├── main.py ← START HERE: Run with `python main.py`
    ├── config.py ← Environment settings (.env)
    │
    ├── agent/ ← The AI agent and its tools
    │   ├── build_agent.py ← Creates the agent
    │   ├── system_prompt.py ← Agent's instructions and constraints
    │   ├── tools.py ← Defines the 13 tools the agent can use
    │   └── deps.py ← Dependencies (Gmail, Calendar, Tasks services)
    │
    ├── tools/ ← Implementation of email, calendar, task tools
    ├── auth/ ← Google OAuth authentication
    ├── approvals/ ← Email approval queue (human gate)
    ├── tasks/ ← Local task logging
    ├── observability/ ← Logging and metrics
    ├── tests/ ← 24 unit tests
    └── data/ ← Sample data for demo mode
```

**To run the agent:** `cd project && python main.py`

## Design Decisions

**Why one agent instead of multiple?**
- **Simpler:** One model makes decisions autonomously, not coordinating between multiple agents
- **Clearer:** You see one coherent set of actions per run, not scattered outputs from different agents
- **Safer:** All email replies go through a human approval gate before sending
- **Easier to debug:** No complex multi-agent coordination to troubleshoot

**Why no auto-send?**
- Safety first: No email leaves your account without your explicit approval
- All drafts are written for you to review, edit, and send via the review phase
- You stay in control

**How are emails handled?**
- Agent only sees unread emails once
- Agent marks emails as "reviewed" (even if leaving unread) so it doesn't re-process them
- If you need the agent to revisit an email, mark it unread again

## What's Next?

See [docs/HANDOVER.md](docs/HANDOVER.md) for current status and next steps.

## Questions?

- **Technical details:** See [project/README.md](project/README.md)
- **How to set up with real Gmail:** See [project/README.md](project/README.md) § Setup
- **What the agent has done:** See [docs/DAILY_LOG.md](docs/DAILY_LOG.md)
- **Recent changes:** See [docs/CHANGELOG.md](docs/CHANGELOG.md)
