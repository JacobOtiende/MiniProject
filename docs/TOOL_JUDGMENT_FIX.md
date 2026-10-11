# Tool Judgment Fix: `propose_alternate_times`

**Date:** 2026-10-11  
**Issue:** Tool was making scheduling decisions instead of agent  
**Status:** ✅ Fixed

---

## The Problem

The `propose_alternate_times` tool had **hard-coded constraints** that should have been the agent's decisions:

```python
# BEFORE: Tool decided these constraints
def propose_alternate_times(desired_start_iso: str, duration_minutes: int = 60):
    return calendar_tool.propose_alternates(
        ...,
        search_window_days=5,       # Always 5 days
        earliest_hour=8,            # Always 8 AM
        latest_hour=18,             # Always 6 PM
        blocked_weekdays=(5, 6),    # Never weekends
        max_candidates=3,           # Always 3 options
    )
```

**Violates the agent benchmark principle:**
> "Your tools return facts. Your agent makes the call."

The tool was making the call (imposing business hours, weekday-only) instead of returning facts and letting the agent decide.

---

## The Fix

Exposed the scheduling constraints as agent-controlled parameters:

```python
# AFTER: Agent decides these constraints
@tool
def propose_alternate_times(
    desired_start_iso: str,
    duration_minutes: int = 60,
    search_days_ahead: int = 5,           # ← Agent can change
    earliest_hour: int = 8,               # ← Agent can change
    latest_hour: int = 18,                # ← Agent can change
    allow_weekends: bool = False,         # ← Agent can change
) -> list[str]:
    """Find conflict-free alternate start times near a desired time.
    
    By default: weekdays only, 8 AM - 6 PM, search 5 days ahead.
    Adjust parameters if you need flexibility:
    - search_days_ahead: how many days to search forward (default 5)
    - earliest_hour: earliest acceptable time, 24-hour (default 8 = 8 AM)
    - latest_hour: latest acceptable time, 24-hour (default 18 = 6 PM)
    - allow_weekends: if True, include Saturday and Sunday (default False)
    """
    blocked_weekdays = () if allow_weekends else (5, 6)
    return calendar_tool.propose_alternates(
        deps.calendar_service,
        deps.calendar_id,
        desired_start_iso,
        duration_minutes,
        search_window_days=search_days_ahead,
        earliest_hour=earliest_hour,
        latest_hour=latest_hour,
        blocked_weekdays=blocked_weekdays,
        max_candidates=3,
    )
```

---

## What Changed

### Tool Behavior

| Aspect | Before | After |
|---|---|---|
| Weekday-only search | Hard-coded | Agent controls via `allow_weekends` |
| Business hours (8 AM - 6 PM) | Hard-coded | Agent controls via `earliest_hour`, `latest_hour` |
| Search window | Always 5 days | Agent controls via `search_days_ahead` |
| Agent flexibility | None | Full control over constraints |

### System Prompt Update

Added guidance to the agent:

```
If the default business hours or weekday-only constraint doesn't work,
adjust the parameters: allow_weekends=True for more flexibility,
earliest_hour and latest_hour to search outside 8 AM–6 PM, or
search_days_ahead to look further out.
```

---

## Example Usage

### Default behavior (unchanged)
```python
# Finds 3 slots within Mon-Fri, 8 AM - 6 PM, next 5 days
propose_alternate_times(
    desired_start_iso="2026-10-13T14:00:00",
    duration_minutes=60
)
```

### Flexibility: include weekends
```python
# Finds 3 slots including Saturday/Sunday
propose_alternate_times(
    desired_start_iso="2026-10-13T14:00:00",
    duration_minutes=60,
    allow_weekends=True
)
```

### Flexibility: early morning
```python
# Finds 3 slots starting at 6 AM (for urgent items)
propose_alternate_times(
    desired_start_iso="2026-10-13T14:00:00",
    duration_minutes=60,
    earliest_hour=6
)
```

### Flexibility: evening + weekends
```python
# Finds 3 slots, any weekday/weekend, 7 AM - 8 PM, next 10 days
propose_alternate_times(
    desired_start_iso="2026-10-13T14:00:00",
    duration_minutes=60,
    search_days_ahead=10,
    earliest_hour=7,
    latest_hour=20,
    allow_weekends=True
)
```

---

## Compliance with Agent Benchmark

**Principle:** "Your tools return facts. Your agent makes the call."

**Before:** ❌ Tool decided acceptable hours/days  
**After:** ✅ Tool returns available times; agent decides constraints

The tool now:
- Returns facts (list of available slots)
- Doesn't interpret them (doesn't say "these are good slots")
- Doesn't enforce business rules (doesn't reject 7 PM because it's outside hours)
- Lets the agent decide what constraints matter

---

## Files Modified

- `agent/tools.py` — Updated `propose_alternate_times` tool signature
- `agent/system_prompt.py` — Added guidance about new parameters

## Testing

The fix is backward-compatible. Existing calls without the new parameters work:

```python
# Still works (uses defaults)
propose_alternate_times(desired_start_iso, duration_minutes=60)
```

New calls can override defaults:

```python
# Also works (uses custom values)
propose_alternate_times(
    desired_start_iso,
    duration_minutes=60,
    allow_weekends=True,
    earliest_hour=6
)
```
