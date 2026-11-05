"""规则抽取引擎：零配置、零成本，保证没有 API key 也能跑通全链路。

职责边界：
- 找作业句、清洗成一句话标题、解析截止日期
- 不猜日期：解析不出来就置 pending_confirm，绝不编一个假时间
"""

from __future__ import annotations

import re

from ..models import STATUS_OPEN, STATUS_PENDING, Assignment, Doc, make_id
from ..timeparse import parse_due
from .chunker import candidate_sentences, context_for, split_sentences
from .keywords import LEADING_NOISE, has_negation, match_course

_MAX_TITLE = 60
_TRAILING_PUNCT = re.compile(r"[\s，,。.;；、]+$")


def clean_title(sentence: str) -> str:
    """把口语化的作业句压缩成一句能看懂的话。"""
    text = sentence.strip()
    text = _TRAILING_PUNCT.sub("", text)

    changed = True
    while changed:
        changed = False
        for noise in LEADING_NOISE:
            if text.startswith(noise):
                text = text[len(noise):].lstrip("，,、 ：:")
                changed = True

    text = re.sub(r"^(那么|然后|另外|还有|所以)", "", text).strip()
    if len(text) > _MAX_TITLE:
        text = text[:_MAX_TITLE].rstrip() + "…"
    return text or sentence[:_MAX_TITLE]


def _confidence(score: int, has_due: bool) -> float:
    if has_due and score >= 5:
        return 0.85
    if has_due:
        return 0.7
    return 0.45


# 任务派给别人的信号：这类句子不是布置给我的作业
_OTHER_TARGETS = ("班长", "课代表", "学习委员", "学委", "组长", "组员")


def _assigned_to_someone_else(sentence: str) -> bool:
    if not any(word in sentence for word in _OTHER_TARGETS):
        return False
    return not any(word in sentence for word in ("每位同学", "所有人", "大家", "你们"))


def extract_from_doc(doc: Doc, min_score: int = 3) -> list[Assignment]:
    """从一份转写文本中抽取作业条目。"""
    sentences = split_sentences(doc.text)
    if not sentences:
        return []

    base_date = doc.date
    results: list[Assignment] = []
    seen: set[str] = set()

    for idx, sentence, score in candidate_sentences(doc.text, min_score=min_score):
        if has_negation(sentence):
            continue

        window = context_for(sentences, idx, radius=1)

        due, phrase = parse_due(sentence, base_date)
        if due is None and idx + 1 < len(sentences):
            # 只允许向后借一句，且必须是短句，否则会误借到无关的时间表达
            follow = sentences[idx + 1]
            if len(follow) <= 24:
                due, phrase = parse_due(follow, base_date)

        if _assigned_to_someone_else(sentence):
            continue

        course = doc.course_hint or match_course(window) or match_course(doc.text) or "未指定课程"
        title = clean_title(sentence)
        if not title:
            continue

        assignment_id = make_id(course, title)
        if assignment_id in seen:
            continue
        seen.add(assignment_id)

        results.append(
            Assignment(
                id=assignment_id,
                course=course,
                title=title,
                detail=sentence.strip(),
                due=due,
                due_time=None,
                confidence=_confidence(score, due is not None),
                status=STATUS_OPEN if due else STATUS_PENDING,
                source={
                    "doc_id": doc.id,
                    "recorded_at": doc.recorded_at.isoformat(timespec="seconds"),
                    "snippet": window[:200],
                    "time_phrase": phrase,
                    "engine": "rules",
                },
            )
        )

    return results
