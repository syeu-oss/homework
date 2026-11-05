"""本地目录数据源：扫描同步目录里的文本与音频。"""

from __future__ import annotations

import hashlib
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from .base import AUDIO_EXTS, TEXT_EXTS, RawItem, parse_recorded_at


class FolderSource:
    name = "folder"

    def __init__(self, directory: Path, timezone: str = "Asia/Shanghai") -> None:
        self.directory = Path(directory)
        self.timezone = timezone

    def fetch(self, since: date, should_skip=None) -> list[RawItem]:
        if not self.directory.exists():
            return []

        tz = ZoneInfo(self.timezone)
        cutoff = datetime.combine(since, datetime.min.time(), tzinfo=tz)
        items: list[RawItem] = []

        for path in sorted(self.directory.rglob("*")):
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            if suffix not in AUDIO_EXTS and suffix not in TEXT_EXTS:
                continue

            recorded_at = parse_recorded_at(path.name, self.timezone)
            if recorded_at is None:
                mtime = datetime.fromtimestamp(path.stat().st_mtime, tz=tz)
                recorded_at = mtime
            if recorded_at < cutoff - timedelta(days=1):
                continue

            item_id = hashlib.sha1(str(path).encode("utf-8")).hexdigest()[:16]
            stat = path.stat()
            revision = f"{stat.st_size}:{int(stat.st_mtime)}"
            if suffix in TEXT_EXTS:
                try:
                    text = path.read_text(encoding="utf-8", errors="ignore")
                except OSError:
                    continue
                if not text.strip():
                    continue
                items.append(
                    RawItem(
                        id=item_id,
                        filename=path.name,
                        path=path,
                        recorded_at=recorded_at,
                        media_type="text",
                        text=text,
                        origin="folder",
                        revision=revision,
                    )
                )
            else:
                items.append(
                    RawItem(
                        id=item_id,
                        filename=path.name,
                        path=path,
                        recorded_at=recorded_at,
                        media_type="audio",
                        origin="folder",
                        revision=revision,
                    )
                )

        items.sort(key=lambda i: i.recorded_at)
        return items
