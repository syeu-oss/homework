"""作业池持久化与合并、提醒状态记录。

两条不变量：
1. 同一作业多次出现只保留一条，且 done 状态永远不被覆盖。
2. 同一天同一类提醒只发一次，cron 抖动不会导致重复打扰。
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from .models import (
    STATUS_DONE,
    STATUS_DROPPED,
    STATUS_OPEN,
    STATUS_PENDING,
    STATUS_RANK,
    SCHEMA_VERSION,
    Assignment,
    now_local,
)


# ---------------------------------------------------------------- 作业池


def load_pool(path: Path) -> list[Assignment]:
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    items = raw.get("assignments") or []
    return [Assignment.from_dict(item) for item in items]


def save_pool(path: Path, items: Iterable[Assignment]) -> bool:
    """写入作业池。返回是否发生了实质变化（用于决定要不要 commit）。"""
    ordered = sorted(
        items,
        key=lambda a: (a.due or date.max, a.course, a.title),
    )
    payload = {
        "version": SCHEMA_VERSION,
        "updated_at": now_local().isoformat(timespec="seconds"),
        "count": len(ordered),
        "assignments": [a.to_dict() for a in ordered],
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    if old == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return True


def merge_pool(existing: list[Assignment], incoming: list[Assignment]) -> tuple[list[Assignment], int]:
    """按 ID 合并，返回 (合并结果, 新增条数)。

    合并规则：
    - status 取优先级更高者，done 不被覆盖
    - due 用新的非空值覆盖（日期是后续才补全的信息）
    - confidence 取较大值，source 保留最近一次提及
    """
    index = {a.id: a for a in existing}
    added = 0
    stamp = now_local().isoformat(timespec="seconds")

    for new in incoming:
        current = index.get(new.id)
        if current is None:
            new.created_at = new.created_at or stamp
            new.updated_at = stamp
            index[new.id] = new
            added += 1
            continue

        current_rank = STATUS_RANK.get(current.status, 1)
        new_rank = STATUS_RANK.get(new.status, 1)
        if new_rank > current_rank:
            current.status = new.status

        if new.due and new.due != current.due:
            current.due = new.due
        if new.due_time and not current.due_time:
            current.due_time = new.due_time
        if new.confidence > current.confidence:
            current.confidence = new.confidence
        if len(new.detail) > len(current.detail):
            current.detail = new.detail
        if new.source:
            current.source = new.source
        current.updated_at = stamp

    return list(index.values()), added


def set_status(items: list[Assignment], assignment_id: str, status: str) -> bool:
    for item in items:
        if item.id == assignment_id:
            item.status = status
            item.updated_at = now_local().isoformat(timespec="seconds")
            return True
    return False


# ---------------------------------------------------------------- 状态


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"version": SCHEMA_VERSION, "docs": {}, "notified": {}}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {"version": SCHEMA_VERSION, "docs": {}, "notified": {}}
    raw.setdefault("docs", {})
    raw.setdefault("notified", {})
    return raw


def save_state(path: Path, state: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def already_processed(state: dict[str, Any], doc_id: str, fingerprint: str) -> bool:
    return state.get("docs", {}).get(doc_id) == fingerprint


def mark_processed(state: dict[str, Any], doc_id: str, fingerprint: str) -> None:
    state.setdefault("docs", {})[doc_id] = fingerprint


def already_notified(state: dict[str, Any], day: date, kind: str) -> bool:
    return kind in state.get("notified", {}).get(day.isoformat(), [])


def mark_notified(state: dict[str, Any], day: date, kind: str) -> None:
    notified = state.setdefault("notified", {})
    bucket = notified.setdefault(day.isoformat(), [])
    if kind not in bucket:
        bucket.append(kind)


def prune_state(state: dict[str, Any], keep_days: int = 30) -> None:
    """裁剪过期的提醒记录，避免 state 无限膨胀。"""
    from datetime import timedelta

    cutoff = (now_local().date() - timedelta(days=keep_days)).isoformat()
    notified = state.get("notified", {})
    for key in [k for k in notified if k < cutoff]:
        notified.pop(key, None)


__all__ = [
    "STATUS_DONE",
    "STATUS_DROPPED",
    "STATUS_OPEN",
    "STATUS_PENDING",
    "already_notified",
    "already_processed",
    "load_pool",
    "load_state",
    "mark_notified",
    "mark_processed",
    "merge_pool",
    "prune_state",
    "save_pool",
    "save_state",
    "set_status",
]
