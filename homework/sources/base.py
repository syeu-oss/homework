"""数据源协议与统一输入结构。

所有输入差异（本地目录 / 网盘 / 内置样例）都收敛在这里，
上游只关心拿到一批 RawItem，不关心它从哪来。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Protocol
from zoneinfo import ZoneInfo

AUDIO_EXTS = {".m4a", ".mp3", ".wav", ".aac", ".amr", ".opus", ".ogg", ".flac", ".mp4", ".3gp"}
TEXT_EXTS = {".txt", ".md", ".json"}

# 文件名里可能包含的日期：20261103 / 2026-11-03 / 2026_11_03，可带时分
_DATE_PATTERNS = (
    re.compile(r"(20\d{2})[-_.]?(\d{2})[-_.]?(\d{2})[-_ T]?(\d{2})?[-_.:]?(\d{2})?"),
    re.compile(r"(20\d{2})(\d{2})(\d{2})"),
)


@dataclass
class RawItem:
    """一个待转写的输入单元。"""

    id: str
    filename: str
    path: Path | None
    recorded_at: datetime
    media_type: str  # "audio" | "text"
    text: str | None = None
    origin: str = "local"
    course_hint: str | None = None
    # 远端文件的版本标记（大小 + 修改时间）。用途只有一个：
    # 云端每 30 分钟就会重扫一次，靠它判断「这个文件处理过没有」，
    # 避免把同一段一小时的录音反复转写。空字符串表示无法判断。
    revision: str = ""

    @property
    def fingerprint_hint(self) -> str:
        if self.text:
            return str(len(self.text))
        if self.path and self.path.exists():
            return f"{self.path.stat().st_size}"
        return "0"


class Source(Protocol):
    name: str

    def fetch(self, since: date, should_skip=None) -> list[RawItem]:
        """取一批待处理输入。

        `should_skip(id, revision)` 可选：实现方可以在真正取文件之前询问，
        答 True 就别取（省流量、省时间）。
        """
        ...


def parse_recorded_at(filename: str, tz: str) -> datetime | None:
    """从文件名推断录音时间，失败返回 None。"""
    stem = Path(filename).stem
    for pattern in _DATE_PATTERNS:
        m = pattern.search(stem)
        if not m:
            continue
        groups = [g for g in m.groups() if g]
        if len(groups) < 3:
            continue
        try:
            year, month, day = int(groups[0]), int(groups[1]), int(groups[2])
            hour = int(groups[3]) if len(groups) > 3 else 8
            minute = int(groups[4]) if len(groups) > 4 else 0
            if not (1 <= month <= 12 and 1 <= day <= 31):
                continue
            if not (0 <= hour <= 23 and 0 <= minute <= 59):
                hour, minute = 8, 0
            return datetime(year, month, day, hour, minute, tzinfo=ZoneInfo(tz))
        except ValueError:
            continue
    return None


def get_source(name: str, settings) -> Source:
    """按名字构造数据源。"""
    key = (name or "folder").lower()
    if key == "demo":
        from .demo import DemoSource

        return DemoSource()
    if key == "webdav":
        from .webdav import WebDavSource

        return WebDavSource(settings)
    from .folder import FolderSource

    target = settings.source_dir or str(settings.inbox_dir)
    return FolderSource(Path(target), settings.timezone)
