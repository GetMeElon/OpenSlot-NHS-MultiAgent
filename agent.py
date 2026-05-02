from __future__ import annotations

import json
from pathlib import Path

import db
import voice


_FIXTURE_PATH = Path(__file__).parent / "fixtures" / "replies.json"
with _FIXTURE_PATH.open() as fixture_file:
    _FIXTURE = json.load(fixture_file)

_MANUAL_PATIENTS = set(_FIXTURE.get("manual", []))
_REPLIES = _FIXTURE.get("replies", {})


def _reply_for(patient_id: str, slot_id: str) -> str:
    if patient_id in _MANUAL_PATIENTS:
        reply = input(f"Manual reply for {patient_id}: ").strip()
        return reply.upper() if reply.upper() in ("YES", "NO") else reply
    return _REPLIES.get(f"{patient_id}:{slot_id}", "NO")


def _offer(agent_id: int, patient: dict, slot: dict) -> str:
    patient_id = patient["_id"]
    slot_id = slot["_id"]
    voice.speak(
        f"Hello {patient['name']}, this is OpenSlot calling about "
        f"{slot['datetime_iso']}. Reply YES, NO, or a day you can't do."
    )
    reply = _reply_for(patient_id, slot_id)
    preference = None if reply in ("YES", "NO") else reply
    db.record_attempt(agent_id, patient_id, slot_id, outcome=reply, preference=preference)

    if reply == "YES":
        db.book_slot(slot_id, agent_id, patient_id)
        print(f"[agent {agent_id}] claimed {patient_id} -> reserved {slot_id} -> reply YES -> booked")
        return "booked"

    db.release_slot(slot_id, agent_id)
    if reply == "NO":
        db.release_patient(patient_id, agent_id, "waiting")
        print(f"[agent {agent_id}] claimed {patient_id} -> reserved {slot_id} -> reply NO -> released")
        return "declined"

    db.append_unavailability(patient_id, reply)
    db.release_patient(patient_id, agent_id, "follow_up")
    print(
        f"[agent {agent_id}] claimed {patient_id} -> reserved {slot_id} "
        f"-> reply {reply} -> follow_up"
    )
    return "follow_up"


def _primary_slot(agent_id: int) -> dict | None:
    return db.get_db().slots.find_one({"owner_agent": agent_id, "type": "primary"})


def _run_primary(agent_id: int) -> None:
    already_offered_ids: list[str] = []
    slot = _primary_slot(agent_id)

    while slot and slot.get("status") == "open":
        patient = db.claim_patient(agent_id, slot["labels"], already_offered_ids=already_offered_ids)
        if patient is None:
            break

        if not db.reserve_slot(slot["_id"], agent_id):
            db.release_patient(patient["_id"], agent_id, "waiting")
            slot = _primary_slot(agent_id)
            continue

        outcome = _offer(agent_id, patient, slot)
        if outcome == "booked":
            break
        if outcome == "declined":
            already_offered_ids.append(patient["_id"])
        slot = _primary_slot(agent_id)


def _run_pool_once(agent_id: int) -> None:
    slot = db.claim_pool_slot(agent_id)
    if slot is None:
        return

    patient = db.claim_patient(agent_id, slot["labels"])
    if patient is None:
        db.release_slot(slot["_id"], agent_id)
        print(f"[agent {agent_id}] claimed pool {slot['_id']} -> no waiting patient -> released")
        return

    _offer(agent_id, patient, slot)


def run_agent(agent_id: int) -> None:
    _run_primary(agent_id)
    _run_pool_once(agent_id)
