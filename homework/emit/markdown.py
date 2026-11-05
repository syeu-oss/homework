"""生成 HOMEWORK.md 周视图，方便在仓库里或手机上快速扫一眼。"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

from ..models import STATUS_DONE, STATUS_OPEN, STATUS_PENDING, Assignment

_WEEKDAYS = ("一", "二", "三", "四", "五", "六", "日")


def _badge(item: Assignment, today: date) -> str:
    if item.status == STATUS_PENDING:
        return "待确认"
    if item.due is None:
        return "未定"
    delta = (item.due - today).days
    if delta < 0:
        return f"逾期{abs(delta)}天"
    if delta == 0:
        return "今天"
    if delta == 1:
        return "明天"
    return f"{delta}天"


def render(items: list[Assignment], today: date, updated_at: str = "") -> str:
    lines = ["# 作业清单", ""]
    if updated_at:
        lines.append(f"> 更新于 {updated_at}")
        lines.append("")

    active = [i for i in items if i.status in (STATUS_OPEN, STATUS_PENDING)]
    if not active:
        lines.append("这周很干净，没有待办作业。")
        lines.append("")
        return "\n".join(lines)

    groups: dict[str, list[Assignment]] = {
        "逾期": [],
        "今天": [],
        "本周内": [],
        "稍后": [],
        "日期待确认": [],
    }
    week_end = today + timedelta(days=(6 - today.weekday()))

    for item in active:
        if item.status == STATUS_PENDING or item.due is None:
            groups["日期待确认"].append(item)
        elif item.due < today:
            groups["逾期"].append(item)
        elif item.due == today:
            groups["今天"].append(item)
        elif item.due <= week_end:
            groups["本周内"].append(item)
        else:
            groups["稍后"].append(item)

    for name, bucket in groups.items():
        if not bucket:
            continue
        lines.append(f"## {name}（{len(bucket)}）")
        lines.append("")
        bucket.sort(key=lambda a: a.due or date.max)
        for item in bucket:
            due_text = item.due.strftime("%m-%d") if item.due else "未定"
            weekday = f" 周{_WEEKDAYS[item.due.weekday()]}" if item.due else ""
            lines.append(
                f"- [ ] **{item.course}**｜{item.title} "
                f"<sub>{due_text}{weekday} · {_badge(item, today)}</sub>"
            )
        lines.append("")

    done = [i for i in items if i.status == STATUS_DONE]
    if done:
        lines.append(f"## 已完成（{len(done)}）")
        lines.append("")
        for item in done[-10:]:
            lines.append(f"- [x] {item.course}｜{item.title}")
        lines.append("")

    return "\n".join(lines)


def write(path: Path, items: list[Assignment], today: date, updated_at: str = "") -> bool:
    content = render(items, today, updated_at)
    old = path.read_text(encoding="utf-8") if path.exists() else ""
    if old == content:
        return False
    path.write_text(content, encoding="utf-8")
    return True
