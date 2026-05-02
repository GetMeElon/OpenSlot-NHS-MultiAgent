from __future__ import annotations

from datetime import datetime
from db import get_db

RESET, GREEN, YELLOW, RED, CYAN = "\033[0m", "\033[32m", "\033[33m", "\033[31m", "\033[36m"
COLORS = {"booked": GREEN, "reserved": YELLOW, "locked": YELLOW, "open": RED, "waiting": RED, "follow_up": RED}
SLOT_AGENTS = {}

def stamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


def color_for(status: str) -> str:
    return COLORS.get(status, "")


def agent_text(doc: dict, field: str) -> str:
    agent_id = doc.get(field)
    return f" by agent {agent_id}" if agent_id is not None else ""


def line(text: str, color: str = RESET) -> None:
    print(f"{color}[{stamp()}]  {text}{RESET}", flush=True)


def attempt_insert(doc: dict) -> None:
    line(
        "attempt new           "
        f"agent {doc.get('agent_id')} -> {doc.get('patient_id')} / "
        f"{doc.get('slot_id')} -> {doc.get('outcome')}",
        CYAN,
    )


def slot_update(doc: dict) -> None:
    slot_id = doc.get("_id")
    status = doc.get("status", "updated")
    agent_id = doc.get("reserved_by") or SLOT_AGENTS.get(slot_id)
    if doc.get("reserved_by") is not None:
        SLOT_AGENTS[slot_id] = doc["reserved_by"]
    line(f"slot   {slot_id}  {status:<8}{f' by agent {agent_id}' if agent_id else ''}", color_for(status))
    if status in {"booked", "open"}:
        SLOT_AGENTS.pop(slot_id, None)


def patient_update(doc: dict) -> None:
    status = doc.get("status", "updated")
    line(f"patient {doc.get('_id')} {status:<8}{agent_text(doc, 'locked_by')}", color_for(status))


def handle(change: dict) -> None:
    collection = change.get("ns", {}).get("coll")
    operation = change.get("operationType")
    doc = change.get("fullDocument") or {}

    if operation == "insert" and collection == "attempts":
        attempt_insert(doc)
    elif operation == "update" and collection == "slots":
        slot_update(doc)
    elif operation == "update" and collection == "patients":
        patient_update(doc)


def main() -> None:
    print("OpenSlot — live change stream")
    print("-----------------------------")

    db = get_db()
    try:
        with db.watch(full_document="updateLookup") as stream:
            for change in stream:
                handle(change)
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
