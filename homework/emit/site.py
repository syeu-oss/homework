"""把作业池注入单文件模板，产出可离线打开的手机看板。"""

from __future__ import annotations

import json
import shutil
from datetime import date, timedelta
from pathlib import Path

from ..models import STATUS_DONE, STATUS_OPEN, STATUS_PENDING, Assignment

_TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "template.html"
_PLACEHOLDER = "/*__DATA__*/null"

_WEEKDAYS = ("周一", "周二", "周三", "周四", "周五", "周六", "周日")


def _payload(items: list[Assignment], today: date, repo: str = "") -> dict:
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    # 展示全部未完成作业，而不是只看本周——远期作业恰恰最容易被忘掉
    week_items = [i for i in items if i.status in (STATUS_OPEN, STATUS_PENDING)]
    total = len(week_items)
    done = len([i for i in items if i.status == STATUS_DONE and i.due and week_start <= i.due <= week_end])

    rows = []
    for item in week_items:
        if item.status == STATUS_PENDING or item.due is None:
            group = "pending"
            due_text = "待确认"
            delta_text = "日期未定"
            delta_days = None
        else:
            delta_days = (item.due - today).days
            due_text = item.due.strftime("%m月%d日")
            if delta_days < 0:
                group = "overdue"
                delta_text = f"逾期{abs(delta_days)}天"
            elif delta_days == 0:
                group = "today"
                delta_text = "今天截止"
            elif delta_days <= 1:
                group = "today"
                delta_text = "明天截止"
            elif item.due <= week_end:
                group = "week"
                delta_text = f"还有{delta_days}天"
            else:
                group = "later"
                delta_text = f"还有{delta_days}天"
            due_text = f"{due_text} {_WEEKDAYS[item.due.weekday()]}"

        rows.append(
            {
                "id": item.id,
                "course": item.course,
                "title": item.title,
                "detail": item.detail or item.title,
                "due": item.due.isoformat() if item.due else None,
                "dueText": due_text,
                "delta": delta_text,
                "deltaDays": delta_days,
                "group": group,
                "status": item.status,
                "confidence": item.confidence,
                "snippet": (item.source or {}).get("snippet", ""),
                "timePhrase": (item.source or {}).get("time_phrase") or "",
            }
        )

    rows.sort(key=lambda r: (r["due"] or "9999", r["course"]))

    overdue = len([r for r in rows if r["group"] == "overdue"])
    nearest = next((r for r in rows if r["group"] != "pending"), None)

    return {
        "repo": repo,
        "weekLabel": f"{week_start.strftime('%m.%d')} - {week_end.strftime('%m.%d')}",
        "today": today.isoformat(),
        "todayLabel": today.strftime("%Y年%m月%d日") + " " + _WEEKDAYS[today.weekday()],
        "updatedAt": "",
        "stats": {
            "open": total,
            "done": done,
            "overdue": overdue,
            "nearest": nearest["dueText"] if nearest else "—",
        },
        "items": rows,
    }


def _copy_assets(target_dir: Path) -> None:
    """把 manifest 与图标放到页面同级目录，PWA 才能被安装。"""
    for name in ("manifest.json", "icon.svg"):
        src = _TEMPLATE.parent / name
        if not src.exists():
            continue
        dst = target_dir / name
        try:
            if not dst.exists() or dst.read_bytes() != src.read_bytes():
                shutil.copyfile(src, dst)
        except OSError:
            pass


def build(
    items: list[Assignment],
    today: date,
    output: Path,
    updated_at: str = "",
    repo: str = "",
) -> bool:
    if not _TEMPLATE.exists():
        return False

    data = _payload(items, today, repo)
    data["updatedAt"] = updated_at
    payload = json.dumps(data, ensure_ascii=False)

    template = _TEMPLATE.read_text(encoding="utf-8")
    html = template.replace(_PLACEHOLDER, payload)

    old = output.read_text(encoding="utf-8") if output.exists() else ""
    if old == html:
        return False
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(html, encoding="utf-8")
    _copy_assets(output.parent)
    return True
