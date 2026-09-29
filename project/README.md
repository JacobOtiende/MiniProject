# MyAgent — single-agent school operations assistant

One autonomous agent that handles a parent's school operations: it triages
school email, keeps the calendar conflict-free, tracks open tasks across
runs, writes a **daily rundown** (today's calendar + important email), and
writes **achievement summaries** (what actually got done). It is one LLM in
a tool-use loop — not a chatbot (it acts, unprompted by follow-up
questions, across multiple tool calls) and not a script (no fixed order;
the model chooses which tools to call, how many times, in what sequence).

## Architecture

```
main.py <triage|rundown|achievements>
   └── agent/build_agent.py     one model + one toolbelt + one system prompt,
                                 run through langchain's create_agent loop
        ├── agent/system_prompt.py   the mandate and hard boundaries
        ├── agent/tools.py           12 tools the model can choose from
        └── agent/deps.py            injected services (Gmail, Calendar, stores)
```

The loop: call the model → if it requested tools, run them and feed the
results back → repeat until it returns a plain-text final answer. That
final answer is what you read. Nothing in the code dictates what order the
tools run in.

### The 12 tools

| Tool | Real or fake in demo mode | What it does |
|---|---|---|
| `list_new_school_emails` | in-memory store | unread school email (triage trigger) |
| `list_recent_school_emails` | in-memory store | all school email, last N days (rundown/achievements) |
| `list_todays_calendar_events` | in-memory calendar | what's on today |
| `check_calendar_conflict` | in-memory calendar | does a window collide with something |
| `propose_alternate_times` | in-memory calendar | real slot search around a conflict |
| `create_calendar_event` | in-memory calendar | writes an event |
| `queue_email_for_approval` | real, disk-backed | drafts a reply into the approval queue |
| `log_task` / `list_open_tasks` / `mark_task_done` | real, disk-backed | memory across runs |
| `log_achievement` / `list_recent_achievements` | real, disk-backed | what makes the summaries possible |

In `MYAGENT_MODE=live`, the email and calendar tools hit your real Gmail
and Google Calendar instead; the rest are identical.

### Three ways to run it

```bash
python main.py triage        # check new school email, act on it
python main.py rundown       # "here's your day": calendar + important email
python main.py achievements  # "here's what got done"
python main.py rundown --review   # then open the approval review loop
```

Same agent, same tools, same policy each time — only the instruction
differs. That's deliberate: it's one general agent that decides how to
fulfil whatever it's asked, not three single-purpose scripts.

## The design trade-off you should say out loud in your writeup

The earlier multi-agent version had a **second opinion**: Control Tower
existed to catch School Agent's misclassifications and quality-check
proposals before anything happened. This version has none — one agent is
grading its own work. That's a real weakness of single-agent designs, and
the honest framing is that you traded a checks-and-balances property for
simplicity and a cleaner autonomy story.

What survives regardless of whether the model behaves well:

- **Nothing can be sent without you.** There is no send tool.
  `queue_email_for_approval` writes to a disk queue and stops;
  `approvals/approval_queue.py` requires you to explicitly `approve()` it
  outside the agent. A model that ignores its whole system prompt still
  can't send an email.
- **Policies are stated, not enforced.** Everything else — check conflicts
  before scheduling, try alternates before bothering you, log follow-ups,
  be honest about vague emails — lives in `agent/system_prompt.py` as
  instructions. A live model can violate those. Running it against real
  inboxes and reading what it actually did is how you'd measure that, and
  is worth a section in the writeup.

## Quickstart (demo mode — no Google setup)

```bash
pip install -r requirements.txt
cp .env.example .env         # set ANTHROPIC_API_KEY
python main.py rundown
python main.py triage --review
python main.py achievements
```

Demo mode makes real OpenAI calls (the reasoning is real) but the
Google side is an in-memory calendar seeded with a couple of conflicting
events and three sample emails from `data/sample_emails.json`. Task and
achievement state persist in `data/task_log.json` between runs, so run
`triage` first — the agent logs achievements as it works, and
`achievements` summarizes whatever's there.

## Testing against a real fake Gmail inbox (live mode)

1. Do the Google Cloud setup below for a fake "parent" Gmail account.
2. Set up a second throwaway Gmail account as the sender (2-Step
   Verification + an App Password, `myaccount.google.com/apppasswords`) and
   fill in `TEST_SENDER_EMAIL`, `TEST_SENDER_APP_PASSWORD`,
   `TEST_RECIPIENT_EMAIL` in `.env`. Add the sender to
   `SCHOOL_SENDER_ALLOWLIST` or the agent's Gmail query won't see it.
3. Send test mail:

```bash
python testing/send_test_email.py --list
python testing/send_test_email.py --scenario doctor_note
python testing/send_test_email.py --all --delay 20
```

`testing/send_test_email.py` is a plain script — it's a fixture generator,
not part of the agent. Five scenarios in `testing/scenarios.json`,
deliberately not all easy: a reply-needed email (should end in the
approval queue, never sent), an ambiguous one with no date or category
(should end as a logged task for you, not a guessed action), and a
short-notice event likely to collide with something on your real calendar
(watch whether it tries alternates before giving up).

4. `CHILDOPS_MODE=live python main.py triage`

### Google Cloud setup for live mode

1. console.cloud.google.com → create a project.
2. APIs & Services → Library: enable **Gmail API** and **Google Calendar API**.
3. OAuth consent screen: External, add your fake parent account as a test user.
4. Credentials → Create Credentials → OAuth client ID → **Desktop app**;
   download the JSON to `credentials/client_secret.json`.
5. `CHILDOPS_MODE=live`, set `SCHOOL_SENDER_ALLOWLIST`, run any mode. First
   run opens a browser consent screen; the token is cached after that.

Polling, not push: Gmail push notifications need a public HTTPS endpoint
and a verified domain. This project polls when you run it — schedule
`python main.py triage` with cron/Task Scheduler if you want it recurring.

## Tests

```bash
pytest tests/ -v
```

14 tests, none touching a real API. The important ones
(`tests/test_agent_loop.py`) drive the real `create_agent` loop with a
scripted chat model standing in for the LLM and assert that the **real
tools execute and their results flow back**: triage queues a draft and
never approves it; the rundown reads calendar and email and summarizes;
the achievement summary reads the log; and a calendar conflict leads the
agent through `check_calendar_conflict` → `propose_alternate_times` (a real
search that returned 10am as free) → `create_calendar_event` at 10am,
rather than double-booking 9am.

**What this does not prove:** that a real model *chooses* those sequences.
The scripts play "what a good model would do." Whether GPT actually does
it is what running live shows — treat that as the evaluation.

## Layout

```
main.py                     CLI: triage / rundown / achievements
config.py                   env-driven settings
agent/                      the single agent (prompt, tools, deps, builder)
tools/gmail_tool.py         real Gmail API
tools/calendar_tool.py      real Google Calendar API
tools/demo_calendar.py      in-memory calendar (demo mode)
tools/demo_email.py         in-memory inbox (demo mode)
tasks/task_log.py           persistent tasks + achievements
approvals/approval_queue.py disk-backed approval gate + review loop
auth/google_auth.py         OAuth for Gmail + Calendar
testing/send_test_email.py  plain script that sends fixture emails
data/sample_emails.json     demo inbox seed
tests/                      14 tests, scripted model, no live calls
```
