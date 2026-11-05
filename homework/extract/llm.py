"""LLM 增强抽取（可选）。

有 key 才启用，无 key 时整条链路仍由规则引擎独立跑通。
日期一律由 timeparse 换算，模型只负责摘录原文时间描述，绝不让它算日期。
"""

from __future__ import annotations

import json
import re

import requests

from ..models import STATUS_OPEN, STATUS_PENDING, Assignment, Doc, make_id
from ..timeparse import parse_due

_SYSTEM_PROMPT = """你是课程助教，负责从课堂录音的转写文本中提取老师布置的作业。
只输出 JSON 数组，不要任何解释文字。数组每个元素包含四个字段：
- "course": 课程名，没提到就填空字符串
- "title": 一句话说清要做什么，不超过40字，用陈述句
- "due_text": 原文里关于截止时间的原话，原样摘录；原文没提就填空字符串
- "confidence": 0 到 1 之间的浮点数，表示你有多确定这是一项作业

提取规则：
1. 只提取老师布置给学生的任务。课堂上的一般性通知、点名、考试安排不算，除非明确指出是要交的东西。
2. 严禁臆造时间。due_text 必须能在原文中找到依据。
3. 同一项作业被反复提到，只输出一条。
4. 没有作业就输出空数组 []。"""

_JSON_BLOCK = re.compile(r"\[.*\]", re.S)


def _parse_json_array(content: str) -> list[dict]:
    content = content.strip()
    content = re.sub(r"^```(?:json)?\s*|\s*```$", "", content)
    match = _JSON_BLOCK.search(content)
    if not match:
        return []
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return []
    return [item for item in data if isinstance(item, dict)]


def extract_with_llm(doc: Doc, settings, min_chars: int = 30) -> list[Assignment]:
    """调用 LLM 抽取。任何失败都返回空列表，由规则结果兜底。"""
    if not settings.llm_api_key or not settings.llm_base_url:
        return []
    if len(doc.text) < min_chars:
        return []

    text = doc.text[: settings.llm_max_chars]
    endpoint = settings.llm_base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": settings.llm_model,
        "temperature": 0.1,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"录音日期：{doc.recorded_at.date().isoformat()}\n"
                    f"课程提示：{doc.course_hint or '未知'}\n\n"
                    f"转写文本：\n{text}"
                ),
            },
        ],
    }

    try:
        resp = requests.post(
            endpoint,
            json=payload,
            headers={
                "Authorization": f"Bearer {settings.llm_api_key}",
                "Content-Type": "application/json",
            },
            timeout=settings.llm_timeout,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"]
    except (requests.RequestException, KeyError, IndexError, ValueError):
        return []

    results: list[Assignment] = []
    for item in _parse_json_array(content):
        title = str(item.get("title") or "").strip()
        if not title:
            continue
        course = str(item.get("course") or "").strip() or doc.course_hint or "未指定课程"
        due_text = str(item.get("due_text") or "").strip()

        due = None
        if due_text:
            due, _ = parse_due(due_text, doc.date)

        try:
            confidence = float(item.get("confidence", 0.6))
        except (TypeError, ValueError):
            confidence = 0.6
        confidence = max(0.0, min(1.0, confidence))
        if due is None:
            confidence = min(confidence, 0.5)

        results.append(
            Assignment(
                id=make_id(course, title),
                course=course,
                title=title[:60],
                detail=due_text,
                due=due,
                confidence=confidence,
                status=STATUS_OPEN if due else STATUS_PENDING,
                source={
                    "doc_id": doc.id,
                    "recorded_at": doc.recorded_at.isoformat(timespec="seconds"),
                    "time_phrase": due_text,
                    "engine": "llm",
                },
            )
        )

    return results
