"""生成 .ics 日历文件。

注意一个已知事实：多数 Android 系统日历对「订阅日历」不执行 VALARM 闹钟，
只显示不响。所以日历在本方案里是可视化副轨，真正叫醒你的是推送。
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from ..models import STATUS_OPEN, Assignment

_HEADER = [
    "BEGIN:VCALENDAR",
    "VERSION:2.0",
    "PRODID:-//homework-reminder//CN",
    "CALSCALE:GREGORIAN",
    "METHOD:PUBLISH",
    "X-WR-CALNAME:作业截止",
    "X-WR-TIMEZONE:Asia/Shanghai",
    "BEGIN:VTIMEZONE",
    "TZID:Asia/Shanghai",
    "BEGIN:STANDARD",
    "DTSTART:19700101T000000",
    "TZOFFSETFROM:+0800",
    "TZOFFSETTO:+0800",
    "TZNAME:CST",
    "END:STANDARD",
    "END:VTIMEZONE",
]


def _escape(text: str) -> str:
    return (
        (text or "")
        .replace("\\", "\\\\")
        .replace(";", "\\;")
        .replace(",", "\\,")
        .replace("\n", "\\n")
    )


def _fold(line: str, limit: int = 75) -> list[str]:
    """按 RFC 5545 折行，避免中文长行被解析器丢弃。"""
    if len(line.encode("utf-8")) <= limit:
        return [line]
    chunks: list[str] = []
    current = ""
    for char in line:
        if len((current + char).encode("utf-8")) > limit:
            chunks.append(current)
            current = char
        else:
            current += char
    if current:
        chunks.append(current)
    return [chunks[0]] + [" " + c for c in chunks[1:]]


def _event(assignment: Assignment) -> list[str]:
    due: date = assignment.due  # 调用方已过滤 None
    next_day = due + timedelta(days=1)
    summary = f"[{assignment.course}] {assignment.title}"
    description = assignment.detail or assignment.title

    lines = [
        "BEGIN:VEVENT",
        f"UID:{assignment.id}@homework-reminder",
        f"DTSTAMP:{due.strftime('%Y%m%d')}T000000Z",
        f"DTSTART;VALUE=DATE:{due.strftime('%Y%m%d')}",
        f"DTEND;VALUE=DATE:{next_day.strftime('%Y%m%d')}",
        f"SUMMARY:{_escape(summary)}",
        f"DESCRIPTION:{_escape(description)}",
        "TRANSP:TRANSPARENT",
        "BEGIN:VALARM",
        "TRIGGER:-P1D",
        "ACTION:DISPLAY",
        f"DESCRIPTION:{_escape('明天截止：' + summary)}",
        "END:VALARM",
        "BEGIN:VALARM",
        "TRIGGER:-PT2H",
        "ACTION:DISPLAY",
        f"DESCRIPTION:{_escape('2 小时后截止：' + summary)}",
        "END:VALARM",
        "END:VEVENT",
    ]
    folded: list[str] = []
    for line in lines:
        folded.extend(_fold(line))
    return folded


def render(assignments: list[Assignment]) -> str:
    lines = list(_HEADER)
    for item in sorted(assignments, key=lambda a: (a.due or date.max, a.course)):
        if item.status != STATUS_OPEN or not item.due:
            continue
        lines.extend(_event(item))
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


def write(path: Path, assignments: list[Assignment]) -> bool:
    content = render(assignments)
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    if old == content:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8", newline="")
    return True
