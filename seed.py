from datetime import datetime
import os

from dotenv import load_dotenv

from db import ensure_indexes, get_db


PRIORITIES = [9, 9, 8, 8, 7, 7, 7, 6, 6, 6, 5, 5, 5, 4, 4, 4, 3, 3, 2, 2]
DEFAULT_PHONE = "+447000000000"


SLOT_TIMES = [
    ("S1", "primary", 1, "2026-05-11T10:00:00Z"),
    ("S2", "primary", 2, "2026-05-12T14:00:00Z"),
    ("S3", "primary", 3, "2026-05-13T16:00:00Z"),
    ("S4", "primary", 4, "2026-05-14T10:00:00Z"),
    ("S5", "primary", 5, "2026-05-15T14:00:00Z"),
    ("S6", "pool", None, "2026-05-11T16:00:00Z"),
    ("S7", "pool", None, "2026-05-12T10:00:00Z"),
    ("S8", "pool", None, "2026-05-13T14:00:00Z"),
    ("S9", "pool", None, "2026-05-14T16:00:00Z"),
    ("S10", "pool", None, "2026-05-15T10:00:00Z"),
]


UNAVAILABILITY = {
    "P01": ["tuesday"],
    "P02": ["monday"],
    "P03": [],
    "P04": ["wednesday"],
    "P05": ["thursday"],
    "P06": ["friday"],
    "P07": [],
    "P08": ["morning"],
    "P09": ["afternoon"],
    "P10": ["monday", "afternoon"],
    "P11": ["tuesday", "morning"],
    "P12": [],
    "P13": ["wednesday", "afternoon"],
    "P14": ["thursday", "morning"],
    "P15": ["friday", "afternoon"],
    "P16": ["evening"],
    "P17": ["monday"],
    "P18": [],
    "P19": ["afternoon"],
    "P20": [],
}


def parse_slot_datetime(datetime_iso):
    return datetime.fromisoformat(datetime_iso.replace("Z", "+00:00"))


def labels_for(datetime_iso):
    dt = parse_slot_datetime(datetime_iso)
    daypart = "morning" if dt.hour < 12 else "afternoon" if dt.hour < 17 else "evening"
    return [dt.strftime("%A").lower(), daypart]


def build_slots():
    return [
        {
            "_id": slot_id,
            "type": slot_type,
            "owner_agent": owner_agent,
            "datetime_iso": datetime_iso,
            "labels": labels_for(datetime_iso),
            "status": "open",
            "reserved_by": None,
            "reserved_until": None,
        }
        for slot_id, slot_type, owner_agent, datetime_iso in SLOT_TIMES
    ]


def build_patients():
    demo_phone = os.getenv("DEMO_PHONE", DEFAULT_PHONE)
    patients = []

    for index, priority in enumerate(PRIORITIES, start=1):
        patient_id = f"P{index:02d}"
        patients.append(
            {
                "_id": patient_id,
                "name": f"Patient {index:02d}",
                "phone": demo_phone if patient_id == "P03" else DEFAULT_PHONE,
                "priority": priority,
                "unavailability": UNAVAILABILITY[patient_id],
                "status": "waiting",
                "locked_by": None,
                "locked_until": None,
                "preferences": {},
                "offered_slots": [],
            }
        )

    return patients


def validate_primary_eligibility(slots, patients):
    failures = []
    for slot in slots:
        if slot["type"] != "primary":
            continue

        eligible = [
            patient["_id"]
            for patient in patients
            if not set(patient["unavailability"]).intersection(slot["labels"])
        ]
        if not eligible:
            failures.append(slot["_id"])

    if failures:
        raise RuntimeError(f"Primary slots without eligible patients: {', '.join(failures)}")


def print_table(title, columns, rows):
    print(f"\n## {title}\n")
    print("| " + " | ".join(columns) + " |")
    print("| " + " | ".join(["---"] * len(columns)) + " |")
    for row in rows:
        print("| " + " | ".join(str(row[column]) for column in columns) + " |")


def main():
    load_dotenv()

    db = get_db()
    db.slots.drop()
    db.patients.drop()
    db.attempts.drop()
    ensure_indexes()

    slots = build_slots()
    patients = build_patients()
    validate_primary_eligibility(slots, patients)

    db.slots.insert_many(slots)
    db.patients.insert_many(patients)

    print_table(
        "Slots",
        ["_id", "type", "owner_agent", "datetime_iso", "labels", "status"],
        slots,
    )
    print_table(
        "Patients",
        ["_id", "name", "phone", "priority", "unavailability", "status"],
        patients,
    )


if __name__ == "__main__":
    main()
