# OpenSlot - Build Status

**This file is the single source of truth for build progress. Every coding agent MUST read this file before starting work and append a `## Sprint <ID> - completion log` section as the LAST step of their commit.**

The overseer (the planning chat) updates the top-of-file checklist after each merge.

---

## Submission

- **Deadline:** 16:35 BST 2026-05-02
- **Plan:** [Plan/v1-v2-sprint-plan.md](Plan/v1-v2-sprint-plan.md)
- **Demo entrypoint (target):** `python seed.py && python runner.py`

---

## Sprint checklist (overseer updates this on merge)

| Sprint | Status | Owner | Branch | Merged at | Notes |
|--------|--------|-------|--------|-----------|-------|
| A - Seed + atomic db primitives | not started | Sonnet 4.6 | `agent-a/seed` | - | Blocks B and C |
| B - Per-agent state machine + voice | blocked on A | GPT-5-codex | `agent-b/loop` | - | Blocks C |
| C - Concurrent runner + audio gate | blocked on B | GPT-5-codex | `agent-c/runner` | - | Final integration |
| (Dry run + final commit) | - | overseer | main | - | 16:20-16:25 |
| (Push + Devpost) | - | overseer | main | - | 16:25-16:35 |

Status legend: pending / in progress / merged / blocked / abandoned

---

## Frozen contracts (do not change without overseer approval)

### Collection schemas (in `db.py` after Sprint A)

```python
# slots
{ "_id", "type": "primary"|"pool", "owner_agent": int|None, "datetime_iso": str,
  "labels": list[str], "status": "open"|"reserved"|"booked",
  "reserved_by": int|None, "reserved_until": datetime|None }

# patients
{ "_id", "name", "phone", "priority": int, "unavailability": list[str],
  "status": "waiting"|"locked"|"booked"|"follow_up",
  "locked_by": int|None, "locked_until": datetime|None,
  "preferences": dict, "offered_slots": list[str] }

# attempts
{ "_id": ObjectId, "agent_id", "patient_id", "slot_id",
  "channel", "outcome", "preference_captured": str|None, "ts" }
```

### db.py public surface (Sprint B and C must use these - do NOT inline pymongo calls)

- `get_db()`
- `ensure_indexes()`
- `now_utc()`, `lock_expiry()`, `LOCK_SECONDS = 90`
- `claim_patient(agent_id, slot_labels, already_offered_ids=None) -> dict | None`
- `release_patient(patient_id, agent_id, new_status="waiting")`
- `reserve_slot(slot_id, agent_id) -> bool`
- `claim_pool_slot(agent_id) -> dict | None`
- `book_slot(slot_id, agent_id, patient_id) -> bool`
- `release_slot(slot_id, agent_id)`
- `record_attempt(agent_id, patient_id, slot_id, outcome, preference=None)`
- `append_unavailability(patient_id, token)`

### fixtures/replies.json shape

```json
{ "manual": ["P12"], "replies": { "P03:S1": "YES", "P07:S2": "NO", ... } }
```

### Environment variables (`.env.example` after Sprint A)

`MONGO_URI`, `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`, `DEMO_PHONE`

---

## Open issues / blockers

_(Agents append here when they hit something they can't resolve. Overseer triages.)_

- _none yet_

---

## Decisions log

_(One line per architectural decision made during the build. Helps the next agent understand "why".)_

- 2026-05-02 14:55 - **Drop LangGraph, Voyage AI, Next.js dashboard.** Explicit FSM + priority+unavailability filter + Atlas Compass cover the demo with less risk in the time budget.
- 2026-05-02 14:55 - **Concurrency model:** 5 threads, `threading.Semaphore(1)` on ElevenLabs playback, atomic `find_one_and_update` for all locks, TTL index as safety net only.
- 2026-05-02 14:55 - **Patient replies are pre-scripted** in `fixtures/replies.json`; one patient (`P12`) is `manual` so the live human types that reply during the demo.

---

## Sprint completion logs

_(Each agent appends one section here as their final commit step.)_

<!-- Sprint A appends below this line -->

## Sprint A - completion log (2026-05-02 15:37)
- Built: `requirements.txt` declares `pymongo`, `python-dotenv`, `elevenlabs`, and `boto3`.
- Built: `.env.example` documents `MONGO_URI`, `ELEVENLABS_API_KEY`, `ELEVENLABS_VOICE_ID`, and `DEMO_PHONE`.
- Built: `.gitignore` excludes local env files, virtualenv/cache output, generated audio, audit logs, and `.DS_Store`.
- Built: `db.py` exposes the frozen MongoDB data-layer helpers, TTL indexes, lock timing helpers, and atomic `find_one_and_update` primitives.
- Built: `seed.py` idempotently drops and recreates slots, patients, attempts, validates primary eligibility, and prints markdown tables.
- Built: `fixtures/replies.json` provides deterministic scripted replies with `P12` reserved for manual input.
- Decisions: `record_attempt()` writes `channel: "voice"` because the frozen signature does not accept a channel argument.
- Decisions: `get_db()` falls back to `mongodb://localhost:27017` when `MONGO_URI` is unset so local demos can work without editing code.
- Gotchas for Sprint B: `MONGO_URI` was not set in this shell, and no local MongoDB service was listening on `localhost:27017`; database-backed acceptance commands need a reachable Atlas/local URI.
- Gotchas for Sprint B: `fixtures/replies.json` includes multiple fallback patient/slot keys so priority-ordered claims can still drive 4 primary bookings, 1 unfilled primary, 2 pool bookings, and at least 3 follow-ups.
- Files touched: `requirements.txt`, `.env.example`, `.gitignore`, `db.py`, `seed.py`, `fixtures/replies.json`, `STATUS.md`.

<!-- Sprint B appends below this line -->

<!-- Sprint C appends below this line -->

## Sprint C - completion log (2026-05-02 16:15)
- Built: `runner.py` calls `db.ensure_indexes()` at startup, launches five threads for `agent.run_agent(1..5)`, joins every worker, and prints the final demo summary counts.
- Built: runner captures per-thread exceptions, prints their tracebacks after the summary, and exits non-zero if any agent failed.
- Decisions: summary counts read directly from MongoDB via `get_db()` after all workers finish: booked primary slots, booked pool slots, patients in `follow_up`, and primary slots not booked.
- Gotchas for integration: `agent.py` is expected to provide the frozen `run_agent(agent_id: int) -> None` contract before running `python runner.py`.
- Files touched: `runner.py`, `STATUS.md`.
