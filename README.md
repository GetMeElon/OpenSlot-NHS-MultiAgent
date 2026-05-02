# OpenSlot

Five AI agents race in parallel to fill cancelled NHS appointment slots, using MongoDB atomic primitives for coordination — no Redis, no message queue, no orchestrator.

Built in 4 hours for the MongoDB Hackathon, May 2026.

## The problem

NHS England loses ~8 million appointment slots per year to no-shows and last-minute cancellations. Today, receptionists call patients one by one off paper waiting lists. Slots go cold, doctors sit idle, patients wait months.

## The approach

Each agent owns one primary slot and races concurrently to fill it from a shared waiting list. A pool of unowned slots lets agents grab extra capacity when their primary is filled. MongoDB's `findOneAndUpdate` provides atomic claim-and-lock: two agents can never reserve the same patient or the same slot. TTL indexes on `locked_until` and `reserved_until` automatically reclaim orphaned locks if a thread dies mid-call.

## Architecture

- **`db.py`** — MongoDB data layer. Atomic `claim_patient`, `reserve_slot`, `claim_pool_slot`, `book_slot`, `release_*`, `record_attempt`. All higher-level code goes through these functions; no inline pymongo.
- **`agent.py`** — Per-agent state machine. `run_agent(id)` loops: claim highest-priority compatible patient → reserve slot → call (voice synth) → interpret reply → book / release / mark follow-up.
- **`voice.py`** — ElevenLabs synth, serialized via `threading.Semaphore(1)` so concurrent agents don't talk over each other on the demo machine. Falls back to console output on any error.
- **`runner.py`** — Spawns 5 named threads, joins, prints final summary.
- **`seed.py`** — Idempotent reset: drops `nhs_pilot`, recreates 10 slots + 20 patients with priorities and unavailability constraints.
- **`fixtures/replies.json`** — Pre-scripted patient replies for deterministic demo runs. One patient (`P12`) is `manual` — a live human types that reply during the demo to show the human-in-the-loop path.

## Collections

```
slots:    { _id, type: primary|pool, owner_agent, datetime_iso, labels, status, reserved_by, reserved_until }
patients: { _id, name, phone, priority, unavailability, status, locked_by, locked_until, preferences }
attempts: { _id, agent_id, patient_id, slot_id, channel, outcome, preference_captured, ts }
```

`attempts` is an append-only audit log: every call attempt is recorded for compliance and replay.

## Run it

Requires Python 3.9+, a MongoDB Atlas cluster (or local mongod), and macOS for built-in `afplay` audio playback (the voice layer falls back to console output otherwise).

```bash
pip3 install -r requirements.txt
cp .env.example .env
# fill in MONGO_URI, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID

python3 seed.py        # reset + seed
python3 runner.py      # run 5 agents concurrently
```

When prompted `Manual reply for P12:`, type `YES` and press Enter — that's the live human-in-the-loop step.

## Demo outcome (deterministic)

```
booked primaries: 5
booked pool:      1
follow_ups:       3
unfilled:         0
```

The follow-up patients gave us a new unavailability token (e.g., "monday") via the voice channel — the system records it on the patient document for future matching.

## Design decisions

- **Explicit FSM over LangGraph.** Five states; an agent loop is more debuggable than a graph DSL at this scale.
- **MongoDB atomic ops over Redis locks.** `findOneAndUpdate` with filter+update in one round-trip replaces SELECT…FOR UPDATE plus row-locking. TTL indexes are the safety net.
- **Pre-scripted replies for the demo.** In production, replies arrive via SMS/DTMF callback. For a 3-minute demo, `fixtures/replies.json` makes the run deterministic; `P12` is manual to demonstrate the human path.
- **No AWS dependency.** Voice synth is ElevenLabs direct; no SNS, no Twilio.

## Repository

This is a 4-hour hackathon build. Production-readiness items omitted: real telephony, retry/backoff, observability, multi-tenant isolation, GP-system integration. See `STATUS.md` for sprint history and `memory.md` for hackathon constraints.
