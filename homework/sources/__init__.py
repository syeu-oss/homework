"""数据源适配器：把不同来源的录音/文本统一成 RawItem。"""

from __future__ import annotations

from .base import RawItem, get_source

__all__ = ["RawItem", "get_source"]
