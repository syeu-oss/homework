"""数据模型：Doc（输入文档）与 Assignment（作业条目）。"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any
from zoneinfo import ZoneInfo

SCHEMA_VERSION = 1

STATUS_OPEN = "open"
STATUS_DONE = "done"
STATUS_PENDING = "pending_confirm"
STATUS_DROPPED = "dropped"

# 数值越大优先级越高：done 不会被任何后续状态覆盖
STATUS_RANK = {
    STATUS_DROPPED: 0,
    STATUS_PENDING: 1,
    STATUS_OPEN: 2,
    STATUS_DONE: 3,
}

def normalize(text: str) -> str:
    """归一化：全角转半角、去空白与标点、转小写。用于去重与匹配。"""
    if not text:
        return ""
    s = unicodedata.normalize("NFKC", text)
    kept: list[str] = []
    for ch in s:
        if ch.isspace():
            continue
        if unicodedata.category(ch)[0] in ("P", "S"):
            continue
        kept.append(ch.lower())
    return "".join(kept)


def make_id(course: str, title: str) -> str:
    """确定性 ID：只由课程与作业标题决定。

    刻意不含截止日期——第一次可能没解析出时间，后续补上时应当合并到同一条，
    而不是产生两条重复作业。
    """
    key = "|".join([normalize(course), normalize(title)])
    return hashlib.sha1(key.encode("utf-8")).hexdigest()[:16]


def now_local(tz_name: str = "Asia/Shanghai") -> datetime:
    return datetime.now(ZoneInfo(tz_name))


@dataclass
class Doc:
    """一份待处理的输入文档（转写后的课堂文本）。"""

    id: str
    recorded_at: datetime
    title: str
    text: str
    course_hint: str | None = None
    source: str = "unknown"

    @property
    def date(self) -> date:
        return self.recorded_at.date()

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "recorded_at": self.recorded_at.isoformat(),
            "title": self.title,
            "text": self.text,
            "course_hint": self.course_hint,
            "source": self.source,
        }


@dataclass
class Assignment:
    id: str
    course: str
    title: str
    detail: str = ""
    due: date | None = None
    due_time: str | None = None
    confidence: float = 0.5
    status: str = STATUS_OPEN
    source: dict[str, Any] = field(default_factory=dict)
    created_at: str = ""
    updated_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "course": self.course,
            "title": self.title,
            "detail": self.detail,
            "due": self.due.isoformat() if self.due else None,
            "due_time": self.due_time,
            "confidence": round(float(self.confidence), 3),
            "status": self.status,
            "source": self.source,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> "Assignment":
        due_raw = raw.get("due")
        due = date.fromisoformat(due_raw) if due_raw else None
        return cls(
            id=raw["id"],
            course=raw.get("course", ""),
            title=raw.get("title", ""),
            detail=raw.get("detail", ""),
            due=due,
            due_time=raw.get("due_time"),
            confidence=float(raw.get("confidence", 0.5)),
            status=raw.get("status", STATUS_OPEN),
            source=raw.get("source") or {},
            created_at=raw.get("created_at", ""),
            updated_at=raw.get("updated_at", ""),
        )

    def is_actionable(self, today: date) -> bool:
        """是否应该出现在提醒里：未完成、有截止日、且未逾期太久。"""
        if self.status not in (STATUS_OPEN,):
            return False
        if not self.due:
            return False
        return (self.due - today).days >= -1
