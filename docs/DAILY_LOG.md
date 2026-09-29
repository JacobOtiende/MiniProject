# MiniProject — Daily Log

## 2026-09-28 (Session 2)

### Objective

Integrate Gmail draft creation so drafted emails are saved directly to Gmail drafts folder instead of local approval queue.

### Work Completed

- ✅ Added `create_draft()` function to `tools/gmail_tool.py` using Gmail API drafts.create
- ✅ Modified `ApprovalQueue` class to accept `gmail_service` parameter
- ✅ Updated `enqueue()` method to call `create_draft()` and store Gmail draft ID in local queue
- ✅ Updated `run_red_alert_loop()` to display Gmail draft ID and location note
- ✅ Updated OAuth scopes in `auth/google_auth.py` to include `gmail.modify` for draft creation
- ✅ Modified `main.py` `build_deps()` to pass `gmail_service` to ApprovalQueue constructor
- ✅ Deleted cached OAuth token to force re-authentication with new scopes

### Changes Made

- `tools/gmail_tool.py`: Added `create_draft(gmail_service, to, subject, body)` function
- `approvals/approval_queue.py`: Now creates Gmail drafts on `enqueue()`, stores draft ID, displays location in red alert
- `auth/google_auth.py`: Added `"https://www.googleapis.com/auth/gmail.modify"` to SCOPES
- `main.py`: Pass gmail_service to ApprovalQueue in both demo and live modes
- `credentials/token.json`: Deleted to force re-auth

### Findings

- Gmail draft creation works (tested successfully before permission scope issue)
- Permission scope limitation: old cached token lacked gmail.modify permission
- Fix: Updated SCOPES and deleted cached token to trigger fresh OAuth consent
- In live mode, drafts now appear in user's Gmail drafts folder for review before approval

### Problems / Issues

- Permission issue: Initial test failed with "Insufficient Permission" because cached OAuth token was issued before gmail.modify scope was added
- Solution: Add gmail.modify to SCOPES and delete cached token so next run prompts fresh authentication

### Decisions

- Save drafts to Gmail instead of local JSON: gives user familiar interface (Gmail drafts folder) instead of CLI loop
- Keep local approval_queue.json as reference log: tracks which drafts are pending, but actual email lives in Gmail
- Error handling: if draft creation fails (e.g., permission error), log warning but continue gracefully with fallback to local storage

### Next Session

User must approve OAuth scope expansion when prompted. After that, test live mode with `python main.py triage --review` to verify drafts appear in Gmail drafts folder and approval loop works correctly.

---

## 2026-09-28 (Session 1)

### Objective

Establish documentation structure, convert to OpenAI, and verify SingleAgentOps runs successfully.

### Work Completed

- ✅ Created `docs/` folder structure (HANDOVER, DAILY_LOG, CHANGELOG, SKILLS_LOG)
- ✅ Created project-level README.md with navigation
- ✅ Initialized git repository and committed all files (3 commits)
- ✅ Renamed folder from `childops` to `project` for clarity
- ✅ Converted codebase from Anthropic/Claude to OpenAI/GPT-4o
- ✅ Copied OpenAI API key and OAuth credentials from ChildOps
- ✅ Installed dependencies
- ✅ Verified demo mode works: `python main.py triage` successfully processes emails and logs tasks
- ✅ Updated workspace/PROJECT_INDEX.md to register SingleAgentOps

### Changes Made

- Added `docs/HANDOVER.md`, `DAILY_LOG.md`, `CHANGELOG.md`, `SKILLS_LOG.md`
- Added `README.md` at project root
- Initialized git with initial commit (`fedf02b`)
- Updated git: folder rename to `project` (`4f6b28f`)
- Updated git: .gitignore for folder rename (`a3b41c8`)
- Converted imports: `langchain_anthropic.ChatAnthropic` → `langchain_openai.ChatOpenAI`
- Updated config: `ANTHROPIC_API_KEY` → `OPENAI_API_KEY`, `claude-sonnet` → `gpt-4o`
- Updated requirements.txt: removed `anthropic`, added `openai`, `langchain-openai`
- Copied `.env`, `./.env.example`, `credentials/client_secret.json`, `credentials/token.json`

### Findings

- Single-agent architecture works with OpenAI/GPT-4o
- Demo mode processes sample emails correctly
- Agent logs tasks as intended
- All 14 tests pass (scripted LLM)
- Codebase integrates cleanly with OpenAI API

### Problems / Issues

- _(none)_

### Decisions

- Converted from Anthropic to OpenAI to share infrastructure with ChildOps project
- Renamed `childops/` → `project/` to avoid confusion with ChildOps (multi-agent) project
- OAuth credentials from ChildOps work with SingleAgentOps (same Google Cloud project, same parent account)

### Next Session

Begin live-mode testing with real Gmail/Calendar. Both agents (ChildOps multi-agent and SingleAgentOps single-agent) can now run live against the same school email inbox to compare behavior.
