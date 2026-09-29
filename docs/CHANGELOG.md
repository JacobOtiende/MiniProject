# MiniProject — Changelog

## [2026-09-28] Gmail Draft Integration

### Added
- Email drafts now saved directly to Gmail drafts folder (gmail_tool.py: create_draft function)
- ApprovalQueue now accepts gmail_service and creates real Gmail drafts on enqueue

### Changed
- OAuth scopes expanded to include gmail.modify for draft creation
- ApprovalQueue stores Gmail draft ID in local queue for reference
- Red alert loop displays Gmail draft location and ID

### Fixed
- Permission scope issue: updated SCOPES in auth/google_auth.py to include gmail.modify

---

## [2026-09-28] Unified Release

### Added
- Harmonized ChildOps (multi-agent) and SingleAgentOps (single-agent) into one unified project
- Complete documentation structure: HANDOVER.md, DAILY_LOG.md, CHANGELOG.md, SKILLS_LOG.md
- Project-level README.md with architecture overview
- Git repository with full history

### Changed
- Consolidated on single-agent architecture (simpler, clearer autonomy)
- Standardized on OpenAI/GPT-4o for all inference

### Removed
- ChildOps (multi-agent version with Control Tower) — no longer maintained
- SingleAgentOps (experimental) — no longer maintained
- Multi-agent coordination logic

## [Initial Implementation]

### Added
- Single-agent architecture (agent/build_agent.py)
- 12 tools: email triage, calendar conflict detection, calendar event creation, task logging, approval queue, achievements
- Three CLI modes: triage, rundown, achievements
- Demo mode with sample email data (data/sample_emails.json)
- OAuth setup for Gmail and Google Calendar (auth/google_auth.py)
- System prompt with clear policy boundaries (agent/system_prompt.py)
- Full test suite: 14 tests with scripted LLM
- Approval gate: all drafts require human review before sending
- Config-driven settings (config.py, .env.example)
- Comprehensive README with architecture, quickstart, testing guide

### Design Decisions
- **Single-agent over multi-agent:** Removed Control Tower's second opinion in favor of architectural simplicity
- **Policy as instruction:** System prompt states behavior; not enforced in code
- **Hard safety boundary:** No send tool; approval queue requires explicit human approval outside the agent

### Known Limitations
- Demo mode reprocesses sample emails on repeated runs
- OAuth token expires every 7 days in Testing mode
- Scripted tests prove tool flow, not model judgment
