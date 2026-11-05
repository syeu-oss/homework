"""推送提醒：飞书自定义机器人优先，也兼容任意接收 POST 的端点。

两个实现细节很关键：
1. 飞书若选了「自定义关键词」安全设置，消息里必须固定包含该关键词（这里用「作业」）。
2. 是否已发由 state.json 记录，不靠 cron 准点，cron 抖动也不会重复打扰。
"""

from __future__ import annotations

from datetime import date, timedelta

import requests

from ..models import Assignment

_KEYWORD = "作业"


def send(settings, text: str) -> bool:
    """发送一条推送。未配置任何通道时静默返回 False。"""
    body: dict
    url = ""

    if settings.feishu_webhook:
        url = settings.feishu_webhook
        body = {"msg_type": "text", "content": {"text": text}}
    elif settings.webhook_url:
        url = settings.webhook_url
        body = {"text": text}
    else:
        return False

    try:
        resp = requests.post(url, json=body, timeout=20)
        resp.raise_for_status()
        return True
    except requests.RequestException:
        return False


def _line(item: Assignment, today: date) -> str:
    delta = (item.due - today).days if item.due else 99
    if delta < 0:
        badge = f"已逾期 {abs(delta)} 天"
    elif delta == 0:
        badge = "今天截止"
    elif delta == 1:
        badge = "明天截止"
    else:
        badge = f"还有 {delta} 天"
    due_text = item.due.strftime("%m-%d") if item.due else "未定"
    return f"· [{item.course}] {item.title}\n  {due_text}｜{badge}"


def build_morning(items: list[Assignment], today: date) -> str:
    """早间汇总：今天与明天到期的作业。"""
    urgent = [i for i in items if i.due and 0 <= (i.due - today).days <= 1]
    if not urgent:
        return ""
    lines = [f"作业提醒｜今天 {today.strftime('%m-%d')}", ""]
    lines.extend(_line(i, today) for i in sorted(urgent, key=lambda x: x.due))
    lines.append("")
    lines.append("现在动手，别等晚上。")
    return "\n".join(lines)


def build_evening(items: list[Assignment], today: date, days_before: int = 3) -> str:
    """前夜汇总：未来几天到期 + 已逾期。"""
    horizon = today + timedelta(days=days_before)
    focus = [
        i
        for i in items
        if i.due and (i.due <= horizon)
    ]
    if not focus:
        return ""
    lines = [f"作业盘点｜{today.strftime('%m-%d')} 晚", ""]
    lines.extend(_line(i, today) for i in sorted(focus, key=lambda x: x.due))
    overdue = [i for i in focus if i.due and i.due < today]
    if overdue:
        lines.append("")
        lines.append(f"有 {len(overdue)} 项已经逾期，先处理这些。")
    return "\n".join(lines)


def window_of(now_hm: str, window: str) -> bool:
    """判断当前时刻是否落在 "07:00-10:00" 这样的窗口内。"""
    try:
        start_s, end_s = window.split("-")
        hh, mm = (int(x) for x in now_hm.split(":"))
        current = hh * 60 + mm
        sh, sm = (int(x) for x in start_s.split(":"))
        eh, em = (int(x) for x in end_s.split(":"))
        return sh * 60 + sm <= current <= eh * 60 + em
    except (ValueError, AttributeError):
        return False
