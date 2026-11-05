"""作业信号词表与打分。

目的不是精确理解，而是用极低成本把 95% 的课堂闲聊过滤掉，
只把真正可能含作业的片段送去抽取。
"""

from __future__ import annotations

STRONG_SIGNALS: dict[str, int] = {
    "作业": 3,
    "习题": 3,
    "实验报告": 3,
    "大作业": 4,
    "课程设计": 3,
    "课程论文": 3,
    "提交": 3,
    "上交": 3,
    "交到": 3,
    "截止": 2,
    "答辩": 2,
    "随堂测验": 3,
    "小测": 2,
    "补交": 3,
    "迟交": 2,
}

MEDIUM_SIGNALS: dict[str, int] = {
    "报告": 2,
    "论文": 2,
    "实验": 2,
    "练习": 2,
    "预习": 2,
    "复习": 1,
    "背诵": 2,
    "小组": 2,
    "分组": 2,
    "ppt": 2,
    "演示": 1,
    "展示": 1,
    "阅读": 1,
    "题": 1,
    "字数": 2,
    "格式": 1,
    "参考文献": 2,
}

NEGATIONS: tuple[str, ...] = (
    "不用交",
    "不需要交",
    "不必交",
    "不交",
    "别交",
    "取消",
    "没有作业",
    "不用做",
    "不必做",
    "免了",
    "不要求",
)

# 常见课程名，用于在没有显式课程提示时回退识别
COURSE_NAMES: tuple[str, ...] = (
    "数据结构",
    "操作系统",
    "计算机网络",
    "计算机组成原理",
    "数据库",
    "编译原理",
    "软件工程",
    "人工智能",
    "机器学习",
    "深度学习",
    "算法设计与分析",
    "高等数学",
    "线性代数",
    "概率论",
    "离散数学",
    "大学物理",
    "大学英语",
    "马克思主义基本原理",
    "毛泽东思想",
    "思想道德与法治",
    "中国近现代史纲要",
    "形势与政策",
    "体育",
    "数字电路",
    "模拟电路",
    "信号与系统",
    "通信原理",
    "嵌入式",
    "单片机",
    "Python",
    "Java",
    "C语言",
    "Web开发",
    "网络安全",
)

# 用于清洗作业标题的引导语
LEADING_NOISE: tuple[str, ...] = (
    "那么",
    "然后",
    "另外",
    "还有",
    "所以",
    "那个",
    "就是",
    "大家",
    "同学们",
    "注意一下",
    "提醒一下",
    "我强调一下",
    "回去",
    "课后",
    "课下",
    "作业是这样",
    "作业是",
    "作业呢",
    "任务是这样",
    "要求是",
    "要求",
)


def score_sentence(sentence: str) -> int:
    """给一句话的「作业可能性」打分。"""
    lowered = sentence.lower()
    score = 0
    for word, weight in STRONG_SIGNALS.items():
        if word in lowered:
            score += weight
    for word, weight in MEDIUM_SIGNALS.items():
        if word in lowered:
            score += weight
    return score


def has_negation(sentence: str) -> bool:
    return any(word in sentence for word in NEGATIONS)


def match_course(text: str) -> str | None:
    for name in COURSE_NAMES:
        if name in text:
            return name
    return None
