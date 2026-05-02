from __future__ import annotations

from datetime import datetime, timedelta, timezone
import os

from dotenv import load_dotenv
from pymongo import ASCENDING, MongoClient, ReturnDocument
from pymongo.database import Database


LOCK_SECONDS = 90

load_dotenv()

_client = None


def now_utc():
    return datetime.now(timezone.utc)


def lock_expiry():
    return now_utc() + timedelta(seconds=LOCK_SECONDS)


def get_db() -> Database:
    global _client

    if _client is None:
        mongo_uri = os.getenv("MONGO_URI", "mongodb://localhost:27017")
        _client = MongoClient(mongo_uri, tz_aware=True)

    return _client["nhs_pilot"]


def ensure_indexes():
    db = get_db()
    db.slots.create_index(
        [("reserved_until", ASCENDING)],
        expireAfterSeconds=0,
        name="slots_reserved_until_ttl",
    )
    db.patients.create_index(
        [("locked_until", ASCENDING)],
        expireAfterSeconds=0,
        name="patients_locked_until_ttl",
    )


def claim_patient(
    agent_id: int,
    slot_labels: list[str],
    already_offered_ids: list[str] = None,
) -> dict | None:
    db = get_db()
    return db.patients.find_one_and_update(
        {
            "status": "waiting",
            "unavailability": {"$nin": slot_labels},
            "_id": {"$nin": already_offered_ids or []},
        },
        {
            "$set": {
                "status": "locked",
                "locked_by": agent_id,
                "locked_until": lock_expiry(),
            }
        },
        sort=[("priority", -1), ("_id", 1)],
        return_document=ReturnDocument.AFTER,
    )


def release_patient(patient_id, agent_id, new_status="waiting"):
    db = get_db()
    return db.patients.find_one_and_update(
        {"_id": patient_id, "locked_by": agent_id},
        {
            "$set": {"status": new_status},
            "$unset": {"locked_by": "", "locked_until": ""},
        },
        return_document=ReturnDocument.AFTER,
    )


def reserve_slot(slot_id, agent_id) -> bool:
    db = get_db()
    slot = db.slots.find_one_and_update(
        {"_id": slot_id, "status": "open"},
        {
            "$set": {
                "status": "reserved",
                "reserved_by": agent_id,
                "reserved_until": lock_expiry(),
            }
        },
        return_document=ReturnDocument.AFTER,
    )
    return slot is not None


def claim_pool_slot(agent_id) -> dict | None:
    db = get_db()
    return db.slots.find_one_and_update(
        {"type": "pool", "status": "open"},
        {
            "$set": {
                "status": "reserved",
                "reserved_by": agent_id,
                "reserved_until": lock_expiry(),
            }
        },
        sort=[("datetime_iso", 1)],
        return_document=ReturnDocument.AFTER,
    )


def book_slot(slot_id, agent_id, patient_id) -> bool:
    db = get_db()
    slot = db.slots.find_one_and_update(
        {"_id": slot_id, "reserved_by": agent_id},
        {
            "$set": {"status": "booked"},
            "$unset": {"reserved_by": "", "reserved_until": ""},
        },
        return_document=ReturnDocument.AFTER,
    )
    if slot is None:
        return False

    db.patients.find_one_and_update(
        {"_id": patient_id},
        {
            "$set": {"status": "booked"},
            "$unset": {"locked_by": "", "locked_until": ""},
        },
        return_document=ReturnDocument.AFTER,
    )
    return True


def release_slot(slot_id, agent_id):
    db = get_db()
    return db.slots.find_one_and_update(
        {"_id": slot_id, "reserved_by": agent_id},
        {
            "$set": {"status": "open"},
            "$unset": {"reserved_by": "", "reserved_until": ""},
        },
        return_document=ReturnDocument.AFTER,
    )


def record_attempt(agent_id, patient_id, slot_id, outcome, preference=None):
    db = get_db()
    return db.attempts.insert_one(
        {
            "agent_id": agent_id,
            "patient_id": patient_id,
            "slot_id": slot_id,
            "channel": "voice",
            "outcome": outcome,
            "preference_captured": preference,
            "ts": now_utc(),
        }
    )


def append_unavailability(patient_id, token):
    db = get_db()
    return db.patients.find_one_and_update(
        {"_id": patient_id},
        {
            "$addToSet": {"unavailability": token},
            "$set": {"preferences.last_captured": token},
        },
        return_document=ReturnDocument.AFTER,
    )
