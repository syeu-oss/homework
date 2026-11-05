"""集中配置：全部来自环境变量，缺省值保证零配置也能跑通 demo。"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_int(name: str, default: int) -> int:
    raw = _env(name)
    try:
        return int(raw)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    raw = _env(name)
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass
class Settings:
    # 路径
    root: Path = ROOT
    data_dir: Path = field(default_factory=lambda: Path(_env("DATA_DIR") or ROOT / "data"))
    timezone: str = field(default_factory=lambda: _env("TZ") or "Asia/Shanghai")

    # 数据源：folder | webdav | demo
    source: str = field(default_factory=lambda: _env("SOURCE") or "folder")
    source_dir: str = field(default_factory=lambda: _env("SOURCE_DIR"))
    scan_since_days: int = field(default_factory=lambda: _env_int("SCAN_SINCE_DAYS", 14))

    webdav_url: str = field(default_factory=lambda: _env("WEBDAV_URL"))
    webdav_user: str = field(default_factory=lambda: _env("WEBDAV_USER"))
    webdav_password: str = field(default_factory=lambda: _env("WEBDAV_PASSWORD"))
    webdav_dir: str = field(default_factory=lambda: _env("WEBDAV_DIR") or "/hw")

    # 转写：passthrough | whisper | tingwu
    transcribe_engine: str = field(default_factory=lambda: _env("TRANSCRIBE_ENGINE") or "passthrough")
    whisper_model: str = field(default_factory=lambda: _env("WHISPER_MODEL") or "small")
    whisper_device: str = field(default_factory=lambda: _env("WHISPER_DEVICE") or "cpu")
    whisper_compute: str = field(default_factory=lambda: _env("WHISPER_COMPUTE") or "int8")
    whisper_language: str = field(default_factory=lambda: _env("WHISPER_LANGUAGE") or "zh")

    transcribe_cmd: str = field(default_factory=lambda: _env("TRANSCRIBE_CMD"))

    tingwu_app_key: str = field(default_factory=lambda: _env("TINGWU_APP_KEY"))
    tingwu_access_key_id: str = field(default_factory=lambda: _env("TINGWU_ACCESS_KEY_ID"))
    tingwu_access_key_secret: str = field(default_factory=lambda: _env("TINGWU_ACCESS_KEY_SECRET"))
    tingwu_region: str = field(default_factory=lambda: _env("TINGWU_REGION") or "cn-beijing")

    # 抽取增强（可选）
    llm_base_url: str = field(default_factory=lambda: _env("LLM_BASE_URL"))
    llm_api_key: str = field(default_factory=lambda: _env("LLM_API_KEY"))
    llm_model: str = field(default_factory=lambda: _env("LLM_MODEL") or "gpt-4o-mini")
    llm_timeout: int = field(default_factory=lambda: _env_int("LLM_TIMEOUT", 60))
    llm_max_chars: int = field(default_factory=lambda: _env_int("LLM_MAX_CHARS", 60000))

    # 提醒
    feishu_webhook: str = field(default_factory=lambda: _env("FEISHU_WEBHOOK"))
    webhook_url: str = field(default_factory=lambda: _env("WEBHOOK_URL"))
    remind_morning: str = field(default_factory=lambda: _env("REMIND_MORNING") or "07:00-10:00")
    remind_evening: str = field(default_factory=lambda: _env("REMIND_EVENING") or "19:00-22:00")
    remind_days_before: int = field(default_factory=lambda: _env_int("REMIND_DAYS_BEFORE", 3))

    # 站点
    site_base_url: str = field(default_factory=lambda: _env("SITE_BASE_URL"))

    # 预算保护
    max_audio_minutes: int = field(default_factory=lambda: _env_int("MAX_AUDIO_MINUTES", 180))
    min_confidence: float = field(default_factory=lambda: _env_float("MIN_CONFIDENCE", 0.45))

    @property
    def pool_path(self) -> Path:
        return self.data_dir / "homework.json"

    @property
    def state_path(self) -> Path:
        return self.data_dir / "state.json"

    @property
    def inbox_dir(self) -> Path:
        return self.data_dir / "inbox"

    @property
    def errors_log(self) -> Path:
        return self.data_dir / "errors.log"

    def ensure_dirs(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.inbox_dir.mkdir(parents=True, exist_ok=True)


SETTINGS = Settings()
