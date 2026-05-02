<!-- /autoplan restore point: /Users/dan/.gstack/projects/MongoDBhackathon/no-branch-autoplan-restore-20260502-142114.md -->
# OpenSlot NHS Multi-Agent — Plan Review
**Generated:** 2026-05-02 14:00 BST  
**Deadline:** 5:00 PM BST (runway: ~3h)  
**Mode:** HOLD SCOPE | **Approach:** C (auto-fallback)  
**Reviewer:** /plan-ceo-review (gstack v1.25.1.0) + outside voice (Claude subagent)

---

## Tech Stack Coverage

| Technology | Role | Library | Risk Level | Fallback |
|------------|------|---------|------------|---------|
| **MongoDB Atlas** (M10) | Agent state coordination, patient queue | `pymongo` | Medium — IP whitelist required | N/A — core dependency |
| **AWS SNS** | Outbound SMS to patient | `boto3` | High — sandbox mode restrictions | `[FALLBACK: SMS simulated]` |
| **AWS S3** | Audit log storage | `boto3` | Low | `[FALLBACK: logged to file]` |
| **ElevenLabs** | AI voice call generation + playback | `elevenlabs` | Medium — ffplay/mpv dependency | `afplay output.mp3` / `os.startfile` |
| **Python 3.11+** | Runtime | stdlib + venv | Low | — |
| **python-dotenv** | Credential loading from `.env` | `python-dotenv` | Low | — |
| **GitHub (public)** | Open source requirement | git | Low | — |

---

## Architecture

```
SYSTEM ARCHITECTURE
═══════════════════════════════════════════════════════════════

 MongoDB Atlas (nhs_pilot.queue)
       │
       ▼
 ┌─────────────────────────────────────────┐
 │  Agent 1: TriageAgent                   │
 │  find({status:"waiting"})               │
 │  .sort({priority:-1}).limit(2)  ← FIXED │
 │  returns: [primary_patient, backup]     │
 └─────────────────┬───────────────────────┘
                   │ [P1, P2]
                   ▼
 ┌─────────────────────────────────────────┐
 │  Agent 2: OutreachAgent                 │
 │  SNS → SMS to P1 (fallback if fails)    │
 │  input("YES/NO").strip().upper() ← FIXED│
 │  if NO: ElevenLabs voice to P2          │
 │         (fallback: afplay/os.startfile) │
 └─────────────────┬───────────────────────┘
                   │ declined patient_id
                   ▼
 ┌─────────────────────────────────────────┐
 │  Agent 3: ContextAgent                  │
 │  MongoDB: {$set: {status:               │
 │    "retained_priority"}}                │
 │  S3: put_object(transaction_json)       │
 │      (fallback: write audit_log.json)   │
 └─────────────────────────────────────────┘
```

**Data flow shadow paths:**
- **Happy:** DB → P1 → SMS → P1 declines → voice to P2 → DB update → S3
- **Nil:** No waiting patients → `find()` returns [] → clean exit with message
- **Empty:** Collection exists but empty → same as nil path
- **Error:** Any API call fails → Approach C prints `[FALLBACK]` warning and continues

---

## Decision Points

### D1 — Skip /office-hours, start review immediately
**Decision:** Skip  
**Rationale:** Plan is specific and concrete. /office-hours is for fuzzy problem definitions. Deadline makes 10-minute detour counterproductive.

---

### D2 — Implementation approach
**Decision:** Approach C — Auto-fallback  
**Rationale:** Try all live integrations first; if any fail, print a yellow `[FALLBACK]` warning and continue. Demo always completes. If AWS SNS and ElevenLabs both work, judges see the full experience. If either fails, the terminal still tells the story.

| Approach | Description | Completeness |
|----------|-------------|-------------|
| A: Live-or-die | All integrations live, no fallback | 7/10 |
| B: Mock everything | Simulated SMS + pre-recorded audio | 6/10 |
| **C: Auto-fallback** ✅ | Try live, degrade gracefully on failure | **9/10** |

---

### D3 — Review mode
**Decision:** HOLD SCOPE  
**Rationale:** Plan is already lean. Focus is on identifying integration traps and risks, not debating scope.

---

### D4 — Fix P2 data gap in the AI prompt ✅ CRITICAL
**Decision:** Fix the prompt  
**Problem:** TriageAgent fetched only 1 patient (`limit(1)`). OutreachAgent needs P2's name and phone for the ElevenLabs voice call but had no way to get them. The AI would have hallucinated a hardcoded "Patient B" string.  
**Fix:** Change TriageAgent to `.sort('priority', -1).limit(2)` and pass both patients to OutreachAgent.

---

### D5 — Add explicit fallback spec to AI prompt ✅ CRITICAL
**Decision:** Replace "Handle basic exceptions" with explicit per-integration fallback instructions  
**Problem:** "Handle basic exceptions" produces bare `except: pass` or `except: print(e)` — neither has fallback logic. Demo would either swallow errors silently or print ugly tracebacks.  
**Fix:** Each integration gets a named try/except with a colored fallback print statement (see revised AI prompt below).

---

### D6 — Add input normalization to AI prompt ✅
**Decision:** Add `.strip().upper()` and empty string guard  
**Problem:** If user types "yes" (lowercase) or hits Enter with no input during the live demo, the YES/NO logic breaks and ElevenLabs never fires — most visible moment in the demo.  
**Fix:** `reply = input(...).strip().upper()` + `if reply not in ['YES', 'NO']: reply = 'NO'`

---

### D7 — Reorder Non-Coder AWS task sequence ✅ CRITICAL
**Decision:** Resequence tasks; SNS verification at ~minute 25, not last  
**Problem:** SNS sandbox phone number verification must happen before the Coder's code can send a real SMS. If done last, the Coder discovers it's broken 45 minutes into integration.  
**Fix:** See revised Non-Coder task order below.

---

### D8 — Move dry run to 4:00 PM ✅
**Decision:** Dry run at 4:00 PM, fix window 4:00–4:30, final push at 4:30  
**Problem:** Original plan had dry run at 4:30 PM with zero buffer. Any bug found at 4:30 PM is catastrophic.  
**Fix:** Hard cutoff at 4:00 PM for first dry run; 30-minute fix buffer before the GitHub push.

---

### D9 — Outside voice (Claude subagent)
**Decision:** Run  
**Result:** 6 findings. 3 were already covered by D4–D7. 3 were new:
- MongoDB Atlas IP whitelist (new critical finding → D10)
- ElevenLabs email verification delay (additive fix — see Non-Coder tasks)
- S3 scope challenge (rejected — S3 satisfies AWS requirement and is already protected by Approach C)

---

### D10 — Add MongoDB Atlas IP whitelist step ✅ CRITICAL (outside voice catch)
**Decision:** Add 0.0.0.0/0 to Atlas Network Access  
**Problem:** Atlas M10 blocks all connections by default. Without whitelisting, every pymongo connection fails with a timeout. On conference WiFi, dynamic IPs make per-IP whitelisting unreliable.  
**Fix:** Non-Coder adds `0.0.0.0/0` (Allow from Anywhere) in Atlas → Network Access → Add IP Address. Takes 30 seconds. Fine for a demo cluster.

---

## Error & Rescue Registry

| Method/Codepath | What Can Go Wrong | Exception Class | Rescued? | User Sees |
|----------------|-------------------|----------------|----------|-----------|
| `pymongo.connect()` | Wrong URI, network error | `ConnectionFailure` | ✅ | `[ERROR] MongoDB unreachable` |
| `collection.find()` | Empty result (no waiting patients) | Returns `[]` | ✅ | `[INFO] Queue empty — exiting` |
| `boto3.client('sns')` | Wrong credentials | `NoCredentialsError` | ✅ Approach C | `[FALLBACK: SMS simulated]` in yellow |
| `sns.publish()` | Unverified number, sandbox mode | `ClientError (InvalidParameter)` | ✅ Approach C | `[FALLBACK: SMS simulated]` in yellow |
| `elevenlabs.generate()` | Wrong API key | `AuthenticationError` | ✅ Approach C | `[FALLBACK: Voice call simulated]` |
| `elevenlabs.play()` | ffplay/mpv not installed | `EnvironmentError` / `FileNotFoundError` | ✅ Approach C | `afplay output.mp3` used instead |
| `collection.update_one()` | Write conflict / connection drop | `PyMongoError` | ✅ | `[ERROR] State not saved` + retry |
| `s3.put_object()` | Bucket name mismatch, wrong perms | `ClientError (NoSuchBucket)` | ✅ Approach C | `[FALLBACK: logged to file]` |

**Critical gaps after fixes: 0**

---

## Failure Modes Registry

| Codepath | Failure Mode | Rescued? | User Sees | Logged? |
|----------|-------------|----------|-----------|---------|
| `TriageAgent.query()` | Empty queue | ✅ | `[INFO] Queue empty` | N/A |
| `OutreachAgent.sms()` | SNS sandbox unverified | ✅ | Yellow `[FALLBACK]` | No |
| `OutreachAgent.voice()` | ElevenLabs auth failure | ✅ | Yellow `[FALLBACK]` | No |
| `OutreachAgent.voice()` | ffplay missing (Mac) | ✅ | `afplay` used instead | No |
| `ContextAgent.write()` | MongoDB write error | ✅ | `[ERROR]` printed | No |
| `ContextAgent.s3()` | Bucket name wrong | ✅ | Yellow `[FALLBACK]` | `audit_log.json` |

**CRITICAL GAPS (RESCUED=N, USER SEES=Silent): 0**

---

## Revised Non-Coder Task Order

### ⚡ IMMEDIATE — before anything else
1. **Create ElevenLabs account** → verify email → copy API key + Voice ID  
   *(Email verification can take 5–10 min; start the clock now)*

### Phase 1: API Wrangling (~40 min)

2. **MongoDB Atlas:**
   - Get connection string (URI)
   - Create database `nhs_pilot`, collection `queue`
   - **Network Access → Add IP Entry → `0.0.0.0/0` (Allow from Anywhere)** ← NEW, critical
   - Insert seed documents:
     ```json
     {"patient_id": "P1", "name": "Patient A", "priority": 9, "status": "waiting", "phone": "+447000000000"}
     {"patient_id": "P2", "name": "Patient B", "priority": 8, "status": "waiting", "phone": "+[YOUR_REAL_PHONE]"}
     ```

3. **AWS (new account):**
   - Create account → set Zero Spend budget in Billing
   - IAM → create user → attach `AmazonSNSFullAccess` + `AmazonS3FullAccess`
   - Generate Access Key ID + Secret Access Key
   - **SNS → Text messaging (SMS) → Sandbox → Verified destination phone numbers → Add your real number + enter OTP** ← do this at ~minute 25, not last
   - S3 → create bucket `openslot-audit-logs-[random-numbers]`

### Phase 2: Handoff & Pitch (remaining time)
4. Send all credentials to Coder: Mongo URI, AWS Key ID, AWS Secret, S3 bucket name, ElevenLabs API key, ElevenLabs Voice ID
5. Draft Devpost project page (can run in parallel with coder)
6. Write 3-minute pitch (structure below)

---

## Pitch Script Structure (3 minutes)

```
0:00–0:20  HOOK
  "15 million NHS appointments are wasted every year.
   The reason no one declines a slot: they'll lose their place.
   We fixed that."

0:20–0:40  DEMO START
  "Let me show you." [Run the script]

0:40–1:30  LIVE WALKTHROUGH (narrate as each agent fires)
  "TriageAgent just found the highest-priority patient in the queue."
  "OutreachAgent is sending a real SMS right now."
  "Patient declined — watch this..."  [voice plays OUT LOUD]
  [Refresh Atlas UI]
  "And there it is: retained_priority. Patient A keeps their place."

1:30–2:00  STACK CALLOUT
  "This is MongoDB Atlas coordinating three AI agents in real time.
   AWS SNS for outbound SMS. AWS S3 for immutable audit logging.
   ElevenLabs for AI-generated voice calls. 200 lines of Python."

2:00–2:30  IMPACT
  "At NHS scale: 10% slot recovery = 1.5 million appointments/year.
   Each appointment saves the NHS £160. That's £240 million."

2:30–3:00  CLOSE
  "Open source, on GitHub, right now. We're looking for an NHS
   Digital partnership to pilot in Q3."
```

---

## Revised AI Prompt for the Coder

Paste this entire block into Claude Pro / Codex:

```
System Context & Constraints:
I need to build a Python CLI MVP for a hackathon. I have 2 hours.
Strict constraints: No web frameworks. Use Python 3.11+.
Must use pymongo, boto3, and elevenlabs.

Architecture:
Build a Multi-Agent system for NHS appointment delegation.
Agents are separate Python classes communicating via a shared
MongoDB collection (nhs_pilot.queue).

Agent 1: TriageAgent
  - Connects to MongoDB via pymongo.
  - Finds the TOP 2 patients sorted by priority descending where
    status == 'waiting': .sort('priority', -1).limit(2)
  - Returns a list [top_patient, second_patient].
  - If fewer than 1 patient found, print an error and exit cleanly.

Agent 2: OutreachAgent
  - Takes [primary_patient, backup_patient] from TriageAgent.
  - Try boto3 SNS to send SMS to primary_patient['phone']:
      "NHS slot available. Reply YES to accept, NO to decline
       but retain queue priority."
    If SNS fails for ANY reason, print yellow warning:
      "[FALLBACK: SMS simulated for {patient_name}]"
    and continue — do NOT exit.
  - reply = input(f"Simulate {primary_patient['name']} reply
    (YES/NO): ").strip().upper()
    If reply is empty or not in ['YES', 'NO'], treat as 'NO'.
  - If reply == 'NO':
      Try elevenlabs.client to generate voice for backup_patient:
        f"Hello {backup_patient['name']}, a slot just opened.
          This is your NHS appointment system. Please call back
          to confirm within 2 hours."
      Try to play with elevenlabs.play().
      If play() fails (missing ffplay/mpv), save as output.mp3
      and play with os.system("afplay output.mp3") on Mac or
      os.startfile("output.mp3") on Windows.
      If ElevenLabs API fails entirely, print yellow warning:
        "[FALLBACK: Voice call simulated for {backup_patient['name']}]"
      and continue — do NOT exit.

Agent 3: ContextAgent
  - Updates declined patient's MongoDB document:
      {"$set": {"status": "retained_priority"}}
  - Try boto3 S3 put_object to upload transaction JSON
    to the configured bucket.
    If S3 fails, print yellow warning:
      "[FALLBACK: Audit log saved to local file]"
    and save to audit_log.json instead.

Terminal Output Style:
  - Use ANSI escape codes. Color scheme:
    Cyan bold (\033[96m\033[1m): agent name headers [TRIAGE AGENT]
    Green (\033[92m): success states
    Yellow (\033[93m): fallback warnings
    Red (\033[91m): errors
    Magenta (\033[95m): status transitions
    Reset with \033[0m after every colored block.
  - Each major step gets its own printed line with agent prefix.
  - Include emoji: 🔍 scanning, ✅ success, ⚠️ fallback, 🎙️ voice, 💾 saving

Load all credentials via python-dotenv from .env:
  MONGO_URI, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY,
  AWS_REGION, S3_BUCKET_NAME, ELEVENLABS_API_KEY, ELEVENLABS_VOICE_ID

Write as a complete single-file main.py.
```

---

## Coder Timing Schedule

| Time | Task |
|------|------|
| **Now → 2:10 PM** | Repo setup: `git init`, `python -m venv`, `pip install`, create `.env` + `.gitignore` |
| **2:10 → 2:30 PM** | Write skeleton agent classes while waiting for credentials |
| **2:30 → 2:40 PM** | Receive credentials from Non-Coder, populate `.env` |
| **2:40 → 3:30 PM** | Paste AI prompt → integrate and test each agent in sequence |
| **3:30 → 4:00 PM** | Final integration + squash any remaining issues |
| **4:00 PM** | ⚡ FIRST DRY RUN — full end-to-end |
| **4:00 → 4:30 PM** | Fix buffer (30 min for anything the dry run reveals) |
| **4:30 PM** | Final commit + `git push` to public GitHub |
| **4:30 → 5:00 PM** | Non-Coder finishes Devpost submission |

---

## Demo Dry Run Checklist (run at 4:00 PM)

- [ ] `python main.py` launches without import errors
- [ ] MongoDB connection succeeds (TriageAgent prints P1 found)
- [ ] SNS SMS: either real text received OR yellow `[FALLBACK]` shown
- [ ] `input()` prompt appears correctly
- [ ] Type `no` (lowercase) → script handles it (normalized to NO)
- [ ] ElevenLabs: either audio plays OR yellow `[FALLBACK]` shown
- [ ] MongoDB Atlas UI: P1 status = `"retained_priority"` (manual refresh)
- [ ] S3 bucket: new object appears OR `[FALLBACK: logged to file]` shown
- [ ] Script exits cleanly (no traceback)
- [ ] Total runtime < 30 seconds

---

## Demo Setup (judges present)

**Split screen:**
- **Left:** VS Code terminal
- **Right:** MongoDB Atlas web UI (nhs_pilot.queue collection, sorted by priority)

**Flow:**
1. Run `python main.py`
2. Let terminal output scroll — narrate each agent step
3. When prompted, type `NO`
4. Let the voice play **out loud**
5. Manually refresh Atlas UI — show `retained_priority` live
6. Point to GitHub repo in browser tab

---

## What Is NOT in Scope

| Item | Rationale |
|------|-----------|
| Frontend / web UI | Correctly excluded — CLI avoids all demo-day browser bugs |
| Real two-way SMS reply | Terminal simulation is sufficient for demo |
| Patient authentication | Demo only; fake data is fine |
| EHR/PAS integration | Pitch story, not code |
| Multi-hospital deployment | Pitch story, not code |
| Formal unit tests | Hackathon timeline doesn't warrant it |

---

## Review Summary

| Section | Findings | Status |
|---------|----------|--------|
| Architecture | 1 critical gap (P2 data) | Fixed — D4 |
| Error & Rescue | 8 paths mapped | 0 gaps after D5 |
| Security | 1 advisory (new AWS account risk) | Noted |
| Data/UX edge cases | 2 issues (null check + input sanitization) | Fixed — D4, D6 |
| Code quality | No issues | OK |
| Tests | No formal tests; dry run checklist produced | OK |
| Performance | 15–25s total demo runtime | Excellent |
| Observability | Terminal narrative suggested | Non-blocking |
| Deployment | 2 issues (task order + timing) | Fixed — D7, D8 |
| Long-term trajectory | Reversibility 5/5; pitch structure added | OK |
| Design/UX | Skipped — CLI only | N/A |
| **Outside voice** | Atlas IP whitelist gap (D10) | Fixed |

**Decisions made:** 10  
**Unresolved:** 0  
**Critical gaps remaining:** 0
