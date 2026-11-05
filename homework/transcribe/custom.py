"""自定义转写引擎：把转写交给任意外部命令行。

用途：如果你以后决定用更高精度的云端转写（例如通义听悟 API），
只需提供一个命令，无需改动本项目任何代码：

    TRANSCRIBE_ENGINE=custom
    TRANSCRIBE_CMD=python my_tingwu.py "{input}" "{output}"

命令约定：把转写结果写到 {output} 指定的文本文件里。
"""

from __future__ import annotations

import shlex
import subprocess
import tempfile
from pathlib import Path

from ..sources.base import RawItem
from .base import TranscribeError


class CustomTranscriber:
    name = "custom"

    def __init__(self, settings) -> None:
        self.template = settings.transcribe_cmd if hasattr(settings, "transcribe_cmd") else ""
        self.template = self.template or ""

    def transcribe(self, item: RawItem) -> str:
        if item.media_type == "text" and item.text:
            return item.text

        template = self.template.strip()
        if not template:
            raise TranscribeError(
                "custom 引擎需要配置 TRANSCRIBE_CMD，例如：my-asr \"{input}\" \"{output}\""
            )

        if not item.path or not Path(item.path).exists():
            raise TranscribeError(f"音频文件不存在：{item.filename}")

        with tempfile.TemporaryDirectory() as tmp:
            out_path = Path(tmp) / "transcript.txt"
            command = template.format(input=str(item.path), output=str(out_path))
            try:
                proc = subprocess.run(
                    shlex.split(command, posix=False),
                    capture_output=True,
                    text=True,
                    timeout=1800,
                )
            except subprocess.TimeoutExpired as exc:
                raise TranscribeError("外部转写命令超时") from exc

            if proc.returncode != 0:
                raise TranscribeError(
                    f"外部转写命令失败（code={proc.returncode}）：{proc.stderr[-500:]}"
                )

            if not out_path.exists():
                raise TranscribeError("外部转写命令未生成输出文件")

            text = out_path.read_text(encoding="utf-8", errors="ignore").strip()
            if not text:
                raise TranscribeError("外部转写结果为空")
            return text
