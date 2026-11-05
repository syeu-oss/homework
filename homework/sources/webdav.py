"""WebDAV 数据源：直接从网盘拉取云端定时任务的输入，不依赖任何电脑。"""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.parse import unquote, urljoin
from zoneinfo import ZoneInfo

import requests

from .base import AUDIO_EXTS, TEXT_EXTS, RawItem, parse_recorded_at

_NS = {"d": "DAV:"}
_PROPFIND_BODY = (
    '<?xml version="1.0" encoding="utf-8"?>'
    '<d:propfind xmlns:d="DAV:"><d:prop>'
    "<d:getcontentlength/><d:getlastmodified/><d:resourcetype/>"
    "</d:prop></d:propfind>"
)


class WebDavSource:
    name = "webdav"

    def __init__(self, settings) -> None:
        self.base_url = settings.webdav_url.rstrip("/") + "/"
        self.user = settings.webdav_user
        self.password = settings.webdav_password
        self.remote_dir = (settings.webdav_dir or "/hw").strip("/")
        self.inbox = settings.inbox_dir
        self.timezone = settings.timezone

    def _auth(self) -> tuple[str, str]:
        return (self.user, self.password)

    def list_remote(self) -> list[tuple[str, str, int, str]]:
        """列出远程目录里的文件，返回 [(绝对 URL, 文件名, 字节数, 修改时间)]。

        也供 `cli check` 做连通性探测使用，因此不以下划线开头。
        """
        url = urljoin(self.base_url, self.remote_dir + "/")
        resp = requests.request(
            "PROPFIND",
            url,
            data=_PROPFIND_BODY.encode("utf-8"),
            headers={"Depth": "1", "Content-Type": "application/xml; charset=utf-8"},
            auth=self._auth(),
            timeout=30,
        )
        resp.raise_for_status()

        root = ET.fromstring(resp.content)
        entries: list[tuple[str, str, int, str]] = []
        for node in root.findall("d:response", _NS):
            href = node.findtext("d:href", default="", namespaces=_NS)
            if not href:
                continue
            is_dir = node.find(".//d:resourcetype/d:collection", _NS) is not None
            if is_dir:
                continue
            name = unquote(href.rstrip("/").rsplit("/", 1)[-1])
            if not name:
                continue
            size_text = node.findtext(".//d:getcontentlength", default="0", namespaces=_NS) or "0"
            try:
                size = int(size_text)
            except ValueError:
                size = 0
            lastmod = node.findtext(".//d:getlastmodified", default="", namespaces=_NS) or ""
            entries.append((urljoin(self.base_url, href.lstrip("/")), name, size, lastmod.strip()))
        return entries

    def fetch(self, since: date, should_skip=None) -> list[RawItem]:
        """拉取远端新文件。

        `should_skip(item_id, revision)` 会在**下载之前**被询问一次：
        已经处理过的文件连字节都不下载。网盘的下载流量按月计量，
        所以这一步直接决定会不会把额度烧光。
        """
        if not self.base_url or not self.user:
            raise RuntimeError("WebDAV 未配置：需要 WEBDAV_URL / WEBDAV_USER / WEBDAV_PASSWORD")

        self.inbox.mkdir(parents=True, exist_ok=True)
        tz = ZoneInfo(self.timezone)
        cutoff = datetime.combine(since, datetime.min.time(), tzinfo=tz) - timedelta(days=1)
        items: list[RawItem] = []

        for url, name, size, lastmod in self.list_remote():
            suffix = Path(name).suffix.lower()
            if suffix not in AUDIO_EXTS and suffix not in TEXT_EXTS:
                continue

            item_id = hashlib.sha1(name.encode("utf-8")).hexdigest()[:16]
            revision = f"{size}:{lastmod}" if (size and lastmod) else ""
            recorded_at = parse_recorded_at(name, self.timezone)

            # 文件名能看出日期 → 先判断该不该处理，再决定要不要下载
            if recorded_at is not None:
                if recorded_at < cutoff:
                    continue
                if should_skip and should_skip(item_id, revision):
                    continue

            local = self.inbox / name
            if not local.exists():
                resp = requests.get(url, auth=self._auth(), timeout=120)
                resp.raise_for_status()
                local.write_bytes(resp.content)

            if recorded_at is None:
                recorded_at = datetime.fromtimestamp(local.stat().st_mtime, tz=tz)
                if recorded_at < cutoff:
                    continue

            if not revision:
                revision = f"{local.stat().st_size}:{int(local.stat().st_mtime)}"

            if suffix in TEXT_EXTS:
                text = local.read_text(encoding="utf-8", errors="ignore")
                if not text.strip():
                    continue
                items.append(
                    RawItem(
                        id=item_id,
                        filename=name,
                        path=local,
                        recorded_at=recorded_at,
                        media_type="text",
                        text=text,
                        origin="webdav",
                        revision=revision,
                    )
                )
            else:
                items.append(
                    RawItem(
                        id=item_id,
                        filename=name,
                        path=local,
                        recorded_at=recorded_at,
                        media_type="audio",
                        origin="webdav",
                        revision=revision,
                    )
                )

        items.sort(key=lambda i: i.recorded_at)
        return items
