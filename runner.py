from __future__ import annotations

import threading
import traceback

import agent
from db import ensure_indexes, get_db


AGENT_COUNT = 5


def _run_agent(agent_id: int, failures: list[tuple[int, Exception, str]]) -> None:
    try:
        agent.run_agent(agent_id)
    except Exception as exc:
        failures.append((agent_id, exc, traceback.format_exc()))


def _count_documents(collection_name: str, query: dict) -> int:
    db = get_db()
    return db[collection_name].count_documents(query)


def print_summary() -> None:
    booked_primaries = _count_documents(
        "slots",
        {"type": "primary", "status": "booked"},
    )
    booked_pool = _count_documents(
        "slots",
        {"type": "pool", "status": "booked"},
    )
    follow_ups = _count_documents("patients", {"status": "follow_up"})
    unfilled_primaries = _count_documents(
        "slots",
        {"type": "primary", "status": {"$ne": "booked"}},
    )

    print("\n## Final summary\n")
    print(f"booked primaries: {booked_primaries}")
    print(f"booked pool: {booked_pool}")
    print(f"follow_ups: {follow_ups}")
    print(f"unfilled primaries: {unfilled_primaries}")


def main() -> None:
    ensure_indexes()

    failures: list[tuple[int, Exception, str]] = []
    threads = [
        threading.Thread(
            target=_run_agent,
            args=(agent_id, failures),
            name=f"agent-{agent_id}",
        )
        for agent_id in range(1, AGENT_COUNT + 1)
    ]

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    print_summary()

    if failures:
        print("\n## Agent failures\n")
        for agent_id, exc, formatted_traceback in failures:
            print(f"agent {agent_id} failed: {exc!r}")
            print(formatted_traceback)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
