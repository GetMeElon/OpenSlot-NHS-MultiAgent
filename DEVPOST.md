# OpenSlot — Devpost submission

**Team:** D&N Cares

**Tagline:** Five AI agents that fill cancelled NHS appointment slots in parallel, coordinated entirely through MongoDB. No Redis, no message queue, no orchestrator.

## Inspiration

The NHS loses something like 8 million appointment slots a year to no-shows and last-minute cancellations. Right now most surgeries deal with this by having a receptionist work down a paper waiting list, calling patients one at a time. Slots go cold while they're still on the phone with patient #1. We wanted to see how much of that coordination problem we could solve with just MongoDB doing the heavy lifting.

## What it does

OpenSlot spins up five agents at once. Each one owns a specific cancelled slot and starts working through the waiting list in priority order. There's also a shared pool of slots they can grab if their primary fills early. The agents call patients with a synthesised voice (ElevenLabs), capture the reply — YES, NO, or "I can't do Mondays" — and book, release, or schedule a follow-up. Every call gets written to an audit log, so there's a record of who was contacted about what slot and how it went.

## How we built it

MongoDB Atlas does basically all the coordination work. `findOneAndUpdate` is the trick — it does the patient claim and the lock in one round-trip, so two agents physically cannot grab the same patient or reserve the same slot. We added TTL indexes on the lock fields so if an agent crashes mid-call, the lock just expires after 90 seconds and someone else picks the patient back up.

Concurrency is plain Python threading — five named threads, one per agent. We put a `Semaphore(1)` around the ElevenLabs playback so the demo laptop doesn't try to talk over itself.

Each agent runs a small explicit state machine: claim a patient → reserve a slot → call them → interpret the reply → book or release. We started with LangGraph and ripped it out after about an hour. With five states it just wasn't earning its keep.

Patient replies during the demo come from a JSON fixture so the run is deterministic, except for one patient (P12) who's flagged as `manual` — we type that reply live to show the human-in-the-loop path is real.

## Challenges

We registered our AWS account this morning and couldn't get SNS approved for SMS in time, so we pivoted the reply channel to voice plus a scripted fixture. Honestly the demo is stronger this way.

The ElevenLabs Python SDK wants `mpv` or `ffmpeg` for playback, neither of which macOS has out of the box. Took us longer than we'd like to admit to figure out we could just write the mp3 to a tempfile and use `afplay`.

We split the build across three coding agents working in parallel git worktrees against frozen interface contracts. That worked, but only because we wrote the contracts down before any code got written.

## What we're proud of

Watching five agents hammer a real Atlas cluster concurrently and never produce a duplicate lock is genuinely satisfying. The whole coordination story is two MongoDB features: atomic update and TTL indexes. That's it.

The end-to-end demo run is reproducible: 5 primary slots booked, 1 pool slot booked, 3 patients moved to follow-up with new constraints captured, 0 unfilled. We can re-seed and run it again and get the same numbers.

## What we learned

`findOneAndUpdate` with a filter, update, and sort in one call is a really nice primitive for distributed locking — cleaner than most of the Redis recipes we've used. TTL indexes turned "what if a worker dies" from an actual problem into a 60-second wait. And for something this small, an explicit FSM beat the agent framework we started with.

## What's next

Real telephony (Twilio probably) instead of the scripted fixture. Learning patient preferences over time — the audit log already captures the data. A receptionist dashboard. Eventually FHIR integration with EMIS or SystmOne.

## Built with

Python, MongoDB Atlas, pymongo, ElevenLabs, threading, python-dotenv

## Repo

https://github.com/GetMeElon/OpenSlot-NHS-MultiAgent
