# MiniProject — Skills Log

| Date | Category | Skill | Level | Evidence |
|---|---|---|---|---|
| 2026-09-28 | AI/ML | Single-Agent Tool-Use Architecture | Demonstrated | Built agent/build_agent.py with LangChain create_agent loop, 12 tool integrations, and scripted tests proving tool sequences |
| 2026-09-28 | Python | Google API Integration | Demonstrated | Implemented Gmail API (tools/gmail_tool.py) and Google Calendar API (tools/calendar_tool.py) with OAuth authentication |
| 2026-09-28 | Python | OAuth & Authentication | Demonstrated | auth/google_auth.py with token caching, OAuth consent flow, and scope management for Gmail/Calendar |
| 2026-09-28 | AI/ML | System Prompt Design | Demonstrated | agent/system_prompt.py with clear policy boundaries, tool usage guidelines, and behavioral constraints |
| 2026-09-28 | Python | Testing Autonomous Agents | Demonstrated | 14 tests in tests/test_agent_loop.py using scripted LLM to verify tool sequences, not just individual tool functionality |
| 2026-09-28 | Python | Persistent State Management | Demonstrated | tasks/task_log.py for cross-run task and achievement logging; approvals/approval_queue.py for disk-backed approval workflow |
| 2026-09-28 | Python | Demo Mode / Fake Backends | Demonstrated | tools/demo_email.py and tools/demo_calendar.py providing in-memory implementations for testing without real APIs |
| 2026-09-28 | Python | Config Management | Demonstrated | config.py with environment-driven settings (CHILDOPS_MODE, SCHOOL_SENDER_ALLOWLIST, etc.) |
| 2026-09-28 | Architecture | Trade-off Analysis | Demonstrated | README §57 articulates single-agent vs. multi-agent trade-off and documents the removed Control Tower second opinion |
| 2026-09-29 | Python | Concurrency / Thread Safety | Demonstrated | Traced `ssl.SSLError WRONG_VERSION_NUMBER` to parallel tool calls sharing one `httplib2` connection; per-request clients in `auth/google_auth.py`, verified with 12 parallel live calls. Fixed racing JSON writes with locks + atomic saves (`jsonstore.py`), covered by an 80-write parallel test |
| 2026-09-29 | Python | Debugging | Demonstrated | Found the approval-queue loader bug (`json.load` after `f.read()`), the Calendar `400` from naive datetimes (verified against live Calendar), and an OAuth scope check that always passed (`from_authorized_user_file` overwriting granted scopes) |
| 2026-09-29 | Integration | Google Tasks API | Practiced | `tools/tasks_tool.py`: task lists, `previous`-based due-date ordering, de-duplication, in-place daily summary upsert; tested against an in-memory fake. Not yet verified live (API disabled in the Cloud project) |
| 2026-09-29 | AI/ML | Agent Reliability Design | Demonstrated | Tool errors returned to the model instead of aborting (`agent/tools.py`); deterministic after-triage sweep added after a live run showed the model skipping `mark_email_read`; today's date injected so relative dates resolve |

## Notes

- Skills are based on actual code implementation in `MiniProject/project/` (originally SingleAgentOps/childops/), verified by source inspection, tests, and live runs where noted.
- "Demonstrated" means the skill was used in the project; not claimed based solely on imports or dependencies.
- Next skill to verify: Google Tasks API live (moves from Practiced to Demonstrated once tasks appear in the real account).
