"""中文相对时间解析：把「下周三前」「月底」「11月10日」换算成具体日期。

设计原则：能确定才返回日期，含糊不清一律返回 None 交给上层标 pending_confirm。
"""

from __future__ import annotations

import calendar
import re
from datetime import date, timedelta

_CN_DIGITS = {
    "零": 0, "〇": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
}

_WEEKDAY_MAP = {
    "一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6,
    "1": 0, "2": 1, "3": 2, "4": 3, "5": 4, "6": 5, "7": 6,
}


def cn_to_int(s: str) -> int | None:
    s = s.strip()
    if not s:
        return None
    if s.isdigit():
        return int(s)
    if "十" in s:
        left, _, right = s.partition("十")
        tens = _CN_DIGITS.get(left, 1) if left else 1
        ones = _CN_DIGITS.get(right, 0) if right else 0
        return tens * 10 + ones
    if len(s) == 1:
        return _CN_DIGITS.get(s)
    return None


def _month_last_day(year: int, month: int) -> date:
    return date(year, month, calendar.monthrange(year, month)[1])


def _shift_month(d: date, months: int) -> tuple[int, int]:
    idx = d.year * 12 + (d.month - 1) + months
    return idx // 12, idx % 12 + 1


def _future_month_day(base: date, month: int, day: int) -> date | None:
    """给定月日，取未来最近的一次（跨年顺延）。"""
    if not (1 <= month <= 12 and 1 <= day <= 31):
        return None
    for year in (base.year, base.year + 1):
        try:
            candidate = date(year, month, day)
        except ValueError:
            continue
        if candidate >= base:
            return candidate
    return None


# 明确的月日：11月10日 / 11月10号 / 十一月十号
_RE_MONTH_DAY = re.compile(r"(\d{1,2}|[一二三四五六七八九十]{1,3})\s*月\s*(\d{1,2}|[一二三四五六七八九十]{1,3})\s*[日号]?")
# 简写：11/10
_RE_SLASH = re.compile(r"(?<!\d)(\d{1,2})\s*[/／]\s*(\d{1,2})(?!\d)")
# 周：下周三 / 本周五 / 周日 / 下个星期一
_RE_WEEK = re.compile(r"(下下|下个?|本|这|当)?\s*(?:个)?\s*(?:周|星期|礼拜)\s*([一二三四五六日天1-7])")
# 相对天数
_RE_DAY = re.compile(r"(大后天|后天|明天|明日|今天|今日)")
_RE_N_DAYS = re.compile(r"(\d{1,2}|[一二三四五六七八九十]{1,3})\s*(?:天|日)\s*(?:之内|以内|内|后|以后)")
# 月底 / 月初
_RE_MONTH_EDGE = re.compile(r"(下下|下|本|这|当)?\s*(?:个)?\s*月?\s*(底|末|初)")
# 单独的 X 号 / X 日
_RE_DAY_ONLY = re.compile(r"(?<![\d月])(\d{1,2}|[一二三四五六七八九十]{1,3})\s*[号日](?![\d])")

_TIME_HINTS = ("之前", "以前", "前", "截止", "之前交", "当天", "内")


def _resolve_week(base: date, prefix: str | None, weekday_char: str) -> date | None:
    target_wd = _WEEKDAY_MAP.get(weekday_char)
    if target_wd is None:
        return None
    monday = base - timedelta(days=base.weekday())

    if prefix == "下下":
        week_start = monday + timedelta(days=14)
        return week_start + timedelta(days=target_wd)
    if prefix in ("下", "下个"):
        week_start = monday + timedelta(days=7)
        return week_start + timedelta(days=target_wd)
    if prefix in ("本", "这", "当"):
        candidate = monday + timedelta(days=target_wd)
        if candidate < base:
            candidate += timedelta(days=7)
        return candidate
    # 无修饰：取未来最近的那个周X（含今天）
    offset = (target_wd - base.weekday()) % 7
    return base + timedelta(days=offset)


def parse_due(text: str, base: date) -> tuple[date | None, str | None]:
    """从一段文本中解析截止日期。

    返回 (日期 或 None, 命中的原文片段)。
    优先级：明确月日 > 简写日期 > 周 > 相对天 > 月边缘 > 单独日。
    """
    if not text:
        return None, None

    m = _RE_MONTH_DAY.search(text)
    if m:
        month = cn_to_int(m.group(1))
        day = cn_to_int(m.group(2))
        if month and day:
            got = _future_month_day(base, month, day)
            if got:
                return got, m.group(0)

    m = _RE_SLASH.search(text)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        got = _future_month_day(base, month, day)
        if got:
            return got, m.group(0)

    m = _RE_WEEK.search(text)
    if m:
        got = _resolve_week(base, m.group(1), m.group(2))
        if got:
            return got, m.group(0)

    m = _RE_DAY.search(text)
    if m:
        word = m.group(1)
        delta = {"大后天": 3, "后天": 2, "明天": 1, "明日": 1, "今天": 0, "今日": 0}[word]
        return base + timedelta(days=delta), m.group(0)

    m = _RE_N_DAYS.search(text)
    if m:
        n = cn_to_int(m.group(1))
        if n is not None and 0 <= n <= 60:
            return base + timedelta(days=n), m.group(0)

    m = _RE_MONTH_EDGE.search(text)
    if m:
        prefix = m.group(1)
        edge = m.group(2)
        months = 0
        if prefix in ("下", "下个"):
            months = 1
        elif prefix == "下下":
            months = 2
        year, month = _shift_month(base, months)
        if edge in ("底", "末"):
            got = _month_last_day(year, month)
        else:  # 初
            got = date(year, month, 1)
        if got < base:
            year, month = _shift_month(base, months + 1)
            got = _month_last_day(year, month) if edge in ("底", "末") else date(year, month, 1)
        return got, m.group(0)

    m = _RE_DAY_ONLY.search(text)
    if m:
        day = cn_to_int(m.group(1))
        if day and 1 <= day <= 31:
            got = _future_month_day(base, base.month, day)
            if not got:
                year, month = _shift_month(base, 1)
                got = _future_month_day(base, month, day)
            if got:
                return got, m.group(0)

    return None, None


def extract_deadline_hint(text: str) -> str | None:
    """抽取「什么时候交」的原始描述，供 pending_confirm 展示。"""
    for kw in ("之前", "以前", "截止", "前交", "交"):
        idx = text.find(kw)
        if idx > 0:
            start = max(0, idx - 12)
            return text[start: idx + len(kw) + 2].strip()
    return None
