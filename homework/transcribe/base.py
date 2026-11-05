"""转写协议：把 RawItem 变成纯文本。

引擎可切换，业务层不感知差异：
- passthrough：输入本身就是文本（手机已转写好），零成本
- whisper：云端本地跑 faster-whisper，免费
- custom：调用任意外部命令，接任意 ASR（例如更高精度的云端接口）
"""

from __future__ import annotations

from typing import Protocol

from ..sources.base import RawItem


class TranscribeError(RuntimeError):
    pass


class Transcriber(Protocol):
    name: str

    def transcribe(self, item: RawItem) -> str:
        ...


def get_transcriber(name: str, settings) -> Transcriber:
    key = (name or "passthrough").lower()
    if key == "whisper":
        from .whisper import WhisperTranscriber

        return WhisperTranscriber(settings)
    if key == "custom":
        from .custom import CustomTranscriber

        return CustomTranscriber(settings)
    from .passthrough import PassthroughTranscriber

    return PassthroughTranscriber()
