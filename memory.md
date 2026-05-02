# OpenSlot — Hackathon Facts

Single-source-of-truth for non-code context. Code agents read this + STATUS.md + Plan/ before starting.

## Deadlines (HARD)
- **Submission:** 17:00 BST 2026-05-02
- **Live demo + Q&A:** 17:15 BST (~3 min)
- **Hard-stop rule:** 16:40 BST — ship whatever is merged. Do not debug into the deadline.
- STATUS.md currently lists 16:35 BST as an internal target — treat that as the buffer, not the real deadline.

## Eligibility constraint
- **MongoDB Atlas Sandbox cluster is mandatory** for finalist eligibility.
- `MONGO_URI` in `.env` MUST come from the participant email link's Atlas Sandbox cluster.
- AWS is NOT required.

## Stack decisions (locked)
- Python, pymongo, ElevenLabs (voice), python-dotenv.
- Dropped: LangGraph, Voyage AI, Next.js dashboard. Explicit FSM + priority+unavailability filter + Atlas Compass cover the demo with less risk.
- Concurrency: 5 threads, `threading.Semaphore(1)` on ElevenLabs playback, atomic `find_one_and_update` for all locks, TTL index as safety net only.
- Patient replies are pre-scripted in `fixtures/replies.json`; `P12` is `manual` so a live human types that reply during the demo.

## Demo narrative (3 min)
1. `python seed.py` — show MongoDB collections in Atlas Compass.
2. `python runner.py` — 5 agents concurrently claim patients, call (ElevenLabs voice), book slots.
3. Show the audit log (`attempts` collection) and the unfilled-primary→pool reallocation.
4. Manual reply for P12 demonstrates the human-in-the-loop path.

## Repo layout (DO NOT reorganize before submission)
- Root: `/Users/dan/Public/*AI/Codex/MongoDB hackathon/`
- App code lives at root: `db.py`, `seed.py`, `runner.py` (planned), `agent.py` (planned), `voice.py` (planned), `fixtures/`, `requirements.txt`, `.env.example`.
- Docs at root: `memory.md`, `STATUS.md`, `Plan/`, `Resources/`.
- Worktrees in `.claude/worktrees/`:
  - `agent-a-seed` (branch `agent-a/seed`) — Sprint A, MERGED to main.
  - `agent-b-loop` (branch `agent-b/loop`) — Sprint B, in progress (agent.py + voice.py).
  - `agent-c-runner` (branch `agent-c/runner`) — Sprint C, not yet created.

## Roles
- **Overseer (this Claude chat):** plans, merges, writes prompts, updates STATUS.md. Does NOT write production code.
- **Coding agents:** GPT-5-codex (Python) and Sonnet 4.6 (glue) write code in worktrees.
- **User:** copy-pastes overseer prompts into coding agents; runs git merges when overseer asks.

## Frozen contracts
See STATUS.md "Frozen contracts" section — db.py public surface, collection schemas, replies.json shape, .env vars. Do not change without overseer approval.
