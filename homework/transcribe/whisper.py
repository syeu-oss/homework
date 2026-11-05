"""本地 Whisper 转写：免费、隐私、在云端 CI 里跑。

依赖 faster-whisper（见 requirements-whisper.txt）。
模型加载用进程内缓存，CI 里再用 actions/cache 缓存模型文件，避免每次重下。
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from ..sources.base import RawItem
from .base import TranscribeError


@lru_cache(maxsize=2)
def _load_model(model_name: str, device: str, compute_type: str):
    try:
        from faster_whisper import WhisperModel
    except ImportError as exc:  # pragma: no cover - 依赖缺失时给出明确指引
        raise TranscribeError(
            "缺少 faster-whisper。请执行 pip install -r requirements-whisper.txt"
        ) from exc

    download_root = os.getenv("WHISPER_CACHE_DIR") or None
    return WhisperModel(
        model_name,
        device=device,
        compute_type=compute_type,
        download_root=download_root,
    )


class WhisperTranscriber:
    name = "whisper"

    def __init__(self, settings) -> None:
        self.model_name = settings.whisper_model
        self.device = settings.whisper_device
        self.compute_type = settings.whisper_compute
        self.language = settings.whisper_language
        self.max_minutes = settings.max_audio_minutes

    def transcribe(self, item: RawItem) -> str:
        if item.media_type == "text" and item.text:
            return item.text

        path = item.path
        if not path or not Path(path).exists():
            raise TranscribeError(f"音频文件不存在：{item.filename}")

        model = _load_model(self.model_name, self.device, self.compute_type)
        segments, info = model.transcribe(
            str(path),
            language=self.language,
            vad_filter=True,
            beam_size=5,
            condition_on_previous_text=False,
        )

        duration_min = (getattr(info, "duration", 0) or 0) / 60
        if duration_min > self.max_minutes:
            raise TranscribeError(
                f"音频时长 {duration_min:.1f} 分钟超过上限 {self.max_minutes} 分钟，已跳过以免烧预算"
            )

        parts: list[str] = []
        for seg in segments:
            text = (seg.text or "").strip()
            if text:
                parts.append(text)

        merged = "".join(parts)
        if not merged:
            raise TranscribeError(f"转写结果为空：{item.filename}")
        return merged
