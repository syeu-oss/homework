"""内置样例数据源：零凭证跑通全链路，用于自测与演示。"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .base import RawItem

_SAMPLES = [
    {
        "title": "数据结构 第8周",
        "course": "数据结构",
        "days_ago": 2,
        "text": (
            "好，我们继续。上节课讲了二叉树的遍历，今天讲平衡二叉树。"
            "大家回去把教材第六章的习题 6.1 到 6.8 做完，下周三之前交到学习通。"
            "另外提醒一下，实验报告第二份还没交的同学，本周五前一定要补上，"
            "迟交会扣分。还有，下节课我们会做随堂测验，范围是第五章到第六章。"
        ),
    },
    {
        "title": "操作系统 第8周",
        "course": "操作系统",
        "days_ago": 1,
        "text": (
            "这节课讲进程调度。作业是这样，写一个小的模拟程序，"
            "实现先来先服务和短作业优先两种调度算法，"
            "月底之前提交，代码和实验报告打包成压缩包。"
            "小组作业的分组名单，班长这周内统计好发给我。"
        ),
    },
]


class DemoSource:
    name = "demo"

    def fetch(self, since: date, should_skip=None) -> list[RawItem]:
        tz = ZoneInfo("Asia/Shanghai")
        today = datetime.now(tz).date()
        items: list[RawItem] = []

        for idx, sample in enumerate(_SAMPLES):
            recorded = datetime.combine(
                today - timedelta(days=sample["days_ago"]),
                datetime.min.time().replace(hour=10, minute=0),
                tzinfo=tz,
            )
            item_id = hashlib.sha1(sample["title"].encode("utf-8")).hexdigest()[:16]
            items.append(
                RawItem(
                    id=item_id,
                    filename=f"demo_{idx}.txt",
                    path=Path(f"demo://{item_id}"),
                    recorded_at=recorded,
                    media_type="text",
                    text=sample["text"],
                    origin="demo",
                    course_hint=sample["course"],
                )
            )

        return items
