"""Structured memory capture helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Any, cast

from .store import Memory


MAX_GOAL_CHARS = 300
MAX_ITEM_CHARS = 300
MAX_SUMMARY_CHARS = 800

MAX_COUNTS = {
    "constraint": 5,
    "decision": 5,
    "open_loop": 5,
    "recent_change": 20,
    "session_summary": 10,  # Keep last 10 session summaries
}


def _truncate(text: str, max_len: int) -> str:
    if max_len <= 0:
        return text
    if len(text) <= max_len:
        return text
    return text[:max_len].rstrip()


def _coerce_list(value: Any, max_items: int | None = None, max_len: int = MAX_ITEM_CHARS) -> list[str]:
    if value is None:
        return []
    items: list[str]
    if isinstance(value, list):
        items = [str(v).strip() for v in cast(list[Any], value) if str(v).strip()]
    elif isinstance(value, str):
        items = [value.strip()] if value.strip() else []
    else:
        items = [str(value).strip()]
    cleaned = [_truncate(item, max_len) for item in items if item]
    if max_items is not None:
        cleaned = cleaned[:max_items]
    return cleaned


def _get_payload_value(payload: dict[str, Any], keys: list[str]) -> tuple[bool, Any]:
    for key in keys:
        if key in payload:
            return True, payload[key]
    return False, None


def capture_memory(
    project_path: str,
    payload: dict[str, Any],
    source: str = "capture",
    session_id: str | None = None,
) -> dict[str, dict[str, int]]:
    """Capture structured memory entries from a payload.

    Returns a dict with counts of added and cleared entries.
    """
    memory = Memory(project_path)
    try:
        now = datetime.now().isoformat()

        meta_base: dict[str, Any] = {"source": source, "timestamp": now}
        if session_id:
            meta_base["session_id"] = session_id

        if isinstance(payload.get("git_base"), str) and payload["git_base"].strip():
            meta_base["git_base"] = payload["git_base"].strip()

        added: dict[str, int] = {}
        cleared: dict[str, int] = {}

        def add_entries(
            category: str,
            values: list[str],
            clear_first: bool = False,
            extra_meta: dict[str, Any] | None = None,
            max_keep: int | None = None,
        ) -> None:
            if clear_first:
                cleared[category] = memory.clear(category)
            if not values:
                return
            count = 0
            for item in values:
                if not item:
                    continue
                meta = dict(meta_base)
                if extra_meta:
                    meta.update(extra_meta)
                memory.add(category=category, content=item, metadata=meta)
                count += 1
            if count:
                added[category] = added.get(category, 0) + count

            # Prune old entries if max_keep is set (for append-mode categories)
            if max_keep is not None and not clear_first:
                entries = memory.get_by_category(category)
                if len(entries) > max_keep:
                    # Entries are returned oldest first, delete the oldest
                    to_delete = entries[:-max_keep]
                    for entry in to_delete:
                        entry_id = entry.get("id")
                        if entry_id:
                            memory.delete(entry_id)
                            cleared[category] = cleared.get(category, 0) + 1

        goal_present, goal_value = _get_payload_value(payload, ["goal", "current_goal", "objective"])
        if goal_present:
            goal_list = _coerce_list(goal_value, max_items=1, max_len=MAX_GOAL_CHARS)
            add_entries("goal", goal_list, clear_first=True)

        constraints_present, constraints_value = _get_payload_value(
            payload, ["constraints", "key_constraints"]
        )
        if constraints_present:
            add_entries(
                "constraint",
                _coerce_list(
                    constraints_value,
                    max_items=MAX_COUNTS["constraint"],
                    max_len=MAX_ITEM_CHARS,
                ),
                clear_first=True,
            )

        decisions_present, decisions_value = _get_payload_value(
            payload, ["decisions", "recent_decisions"]
        )
        if decisions_present:
            add_entries(
                "decision",
                _coerce_list(
                    decisions_value,
                    max_items=MAX_COUNTS["decision"],
                    max_len=MAX_ITEM_CHARS,
                ),
                clear_first=False,
                max_keep=MAX_COUNTS["decision"] * 3,  # Keep last 15 decisions
            )

        open_loops_present, open_loops_value = _get_payload_value(
            payload, ["open_loops", "open_loop"]
        )
        if open_loops_present:
            add_entries(
                "open_loop",
                _coerce_list(
                    open_loops_value,
                    max_items=MAX_COUNTS["open_loop"],
                    max_len=MAX_ITEM_CHARS,
                ),
                clear_first=True,
                extra_meta={"status": "active"},
            )

        changes_present, changes_value = _get_payload_value(
            payload, ["recent_changes", "changes"]
        )
        if changes_present:
            add_entries(
                "recent_change",
                _coerce_list(
                    changes_value,
                    max_items=MAX_COUNTS["recent_change"],
                    max_len=MAX_ITEM_CHARS,
                ),
                clear_first=True,
            )

        summary_present, summary_value = _get_payload_value(
            payload, ["summary", "session_summary"]
        )
        if summary_present:
            add_entries(
                "session_summary",
                _coerce_list(summary_value, max_items=1, max_len=MAX_SUMMARY_CHARS),
                clear_first=False,
                max_keep=MAX_COUNTS["session_summary"],
            )

        return {"added": added, "cleared": cleared}
    finally:
        memory.close()
