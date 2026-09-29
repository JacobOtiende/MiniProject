# MiniProject

A unified single-agent school operations assistant. One autonomous agent with a comprehensive toolbelt that handles email triage, calendar management, task tracking, and daily briefings.

**MiniProject harmonizes ChildOps (multi-agent) and SingleAgentOps (single-agent) into one clean, unified implementation** using the proven single-agent architecture with an expanded tool set.

## Quick Links

- **[Full Technical README](project/README.md)** — Architecture, tools, quickstart, testing guide
- **[Handover & Next Steps](docs/HANDOVER.md)** — Current status and immediate next action
- **[Daily Log](docs/DAILY_LOG.md)** — Work session record
- **[Changelog](docs/CHANGELOG.md)** — Project milestones
- **[Skills Log](docs/SKILLS_LOG.md)** — Demonstrated capabilities

## Status

🟢 **Ready for Testing** — Single-agent architecture verified in demo mode. All tools functional. OAuth credentials configured for live mode.

## Architecture

**One Agent, 12 Tools:**
- Email triage (Gmail API)
- Calendar conflict detection & resolution
- Calendar event creation
- Task logging & tracking
- Achievement logging
- Approval queue (human gate)
- Demo/live mode backends

**Tech Stack:**
- Python + LangChain + LangGraph
- OpenAI GPT-4o
- Google Gmail & Calendar APIs
- OAuth authentication

## Getting Started

**Demo mode (no Google setup needed):**

```bash
cd project
pip install -r requirements.txt
cp .env.example .env
python main.py triage
python main.py rundown
python main.py achievements
```

**Live mode (Google Cloud setup required):**

See [project/README.md](project/README.md) § "Testing against a real fake Gmail inbox" and § "Google Cloud setup for live mode".

## What's Inside

```
MiniProject/
├── README.md (this file)
├── docs/
│   ├── HANDOVER.md
│   ├── DAILY_LOG.md
│   ├── CHANGELOG.md
│   └── SKILLS_LOG.md
└── project/
    ├── README.md (full technical guide)
    ├── main.py (CLI entry point)
    ├── config.py (environment settings)
    ├── agent/
    │   ├── build_agent.py (single agent + 12 tools)
    │   ├── system_prompt.py (policy boundaries)
    │   ├── tools.py (tool definitions)
    │   └── deps.py (Gmail, Calendar, stores)
    ├── tools/ (real API implementations)
    ├── auth/ (OAuth setup)
    ├── approvals/ (human approval gate)
    ├── tasks/ (persistent task log)
    ├── testing/ (test fixture sender)
    ├── tests/ (14 tests, scripted LLM)
    └── data/ (sample emails for demo mode)
```

## Why Single Agent?

- **Simpler:** One model, one toolbelt, one loop (vs. coordinating multiple agents)
- **Clearer autonomy:** Model decides its own sequence (not a fixed pipeline)
- **Safer:** Human approval gate prevents any email from being sent without review
- **Easier to debug:** No multi-agent coordination issues

## Next Action

See [docs/HANDOVER.md](docs/HANDOVER.md) § "Immediate Next Action" for the concrete next step.
