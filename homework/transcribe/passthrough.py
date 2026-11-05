"""直通引擎：输入已经是文本时直接使用，不产生任何成本。"""

from __future__ import annotations

from ..sources.base import RawItem
from .base import TranscribeError


class PassthroughTranscriber:
    name = "passthrough"

    def transcribe(self, item: RawItem) -> str:
        if item.media_type == "text" and item.text:
            return item.text
        raise TranscribeError(
            f"passthrough 引擎不支持音频输入（{item.filename}）。"
            "请把 TRANSCRIBE_ENGINE 设为 whisper，或改用 custom 接入外部转写服务。"
        )
