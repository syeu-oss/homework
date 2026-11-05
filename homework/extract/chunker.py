"""文本切分：先按句切，再挑出疑似含作业的句子。

以「句子」而不是「大段」为单位，是因为一次课可能布置多项作业，
按段落合并会把它们压成一条，丢失信息。
"""

from __future__ import annotations

import re

from .keywords import score_sentence

_SENT_SPLIT = re.compile(r"(?<=[。！？；!?;])\s*|\n+")
MAX_CHUNK_CHARS = 1200


def split_sentences(text: str) -> list[str]:
    if not text:
        return []
    parts = [p.strip() for p in _SENT_SPLIT.split(text)]
    return [p for p in parts if p]


def split_long(text: str, limit: int = MAX_CHUNK_CHARS) -> list[str]:
    """把超长文本按标点切块，避免单次请求过大。"""
    if len(text) <= limit:
        return [text]
    pieces: list[str] = []
    buffer = ""
    for sentence in split_sentences(text):
        if len(buffer) + len(sentence) > limit and buffer:
            pieces.append(buffer)
            buffer = sentence
        else:
            buffer += sentence
    if buffer:
        pieces.append(buffer)
    return pieces


def candidate_sentences(text: str, min_score: int = 3) -> list[tuple[int, str, int]]:
    """返回 [(句子下标, 句子, 分数)]，只保留达到阈值的。"""
    sentences = split_sentences(text)
    picked: list[tuple[int, str, int]] = []
    for idx, sentence in enumerate(sentences):
        score = score_sentence(sentence)
        if score >= min_score and len(sentence) >= 8:
            picked.append((idx, sentence, score))
    return picked


def context_for(sentences: list[str], idx: int, radius: int = 1) -> str:
    """取该句前后若干句，用于补全截止时间等跨句信息。"""
    lo = max(0, idx - radius)
    hi = min(len(sentences), idx + radius + 1)
    return "".join(sentences[lo:hi])
