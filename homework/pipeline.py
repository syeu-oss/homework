"""主流程：一次运行 = 取数 → 转写 → 抽取 → 合并 → 产出 → 提醒。"""

from __future__ import annotations

import hashlib
import traceback
from datetime import timedelta
from pathlib import Path

from .config import Settings, SETTINGS
from .emit import ics, markdown, notify, site
from .extract.llm import extract_with_llm
from .extract.rules import extract_from_doc
from .models import STATUS_OPEN, STATUS_PENDING, Doc, now_local
from .sources import get_source
from .store import (
    already_notified,
    already_processed,
    already_seen,
    load_pool,
    load_state,
    mark_notified,
    mark_processed,
    mark_seen,
    merge_pool,
    prune_state,
    save_pool,
    save_state,
)
from .transcribe import get_transcriber


def _log_error(settings: Settings, message: str) -> None:
    try:
        settings.data_dir.mkdir(parents=True, exist_ok=True)
        with settings.errors_log.open("a", encoding="utf-8") as fh:
            fh.write(message.rstrip() + "\n")
    except OSError:
        pass


def run_once(settings: Settings = SETTINGS, force: bool = False, do_notify: bool = True) -> dict:
    settings.ensure_dirs()
    now = now_local(settings.timezone)
    today = now.date()
    since = today - timedelta(days=settings.scan_since_days)

    stats = {
        "source": settings.source,
        "engine": settings.transcribe_engine,
        "fetched": 0,
        "transcribed": 0,
        "skipped": 0,
        "extracted": 0,
        "added": 0,
        "open": 0,
        "pending": 0,
        "notified": [],
        "errors": [],
    }

    pool = load_pool(settings.pool_path)
    state = load_state(settings.state_path)

    source = get_source(settings.source, settings)
    transcriber = get_transcriber(settings.transcribe_engine, settings)

    try:
        raw_items = source.fetch(since)
    except Exception as exc:  # 取数失败不该让历史作业丢失
        stats["errors"].append(f"取数失败: {exc}")
        _log_error(settings, f"[fetch] {exc}\n{traceback.format_exc()}")
        raw_items = []

    stats["fetched"] = len(raw_items)
    extracted_all = []

    for item in raw_items:
        # 先按文件版本判断，能把「同一段录音被反复转写」挡在转写之前
        if not force and already_seen(state, item.id, item.revision):
            stats["skipped"] += 1
            continue

        try:
            text = transcriber.transcribe(item)
        except Exception as exc:
            stats["errors"].append(f"转写失败 {item.filename}: {exc}")
            _log_error(settings, f"[transcribe] {item.filename}: {exc}")
            continue

        stats["transcribed"] += 1
        fingerprint = hashlib.sha1(text.encode("utf-8")).hexdigest()[:16]
        if not force and already_processed(state, item.id, fingerprint):
            stats["skipped"] += 1
            continue

        doc = Doc(
            id=item.id,
            recorded_at=item.recorded_at,
            title=item.filename,
            text=text,
            course_hint=item.course_hint,
            source=item.origin,
        )

        found = extract_from_doc(doc)
        if settings.llm_api_key:
            try:
                found = found + extract_with_llm(doc, settings)
            except Exception as exc:
                _log_error(settings, f"[llm] {item.filename}: {exc}")

        # 过滤极低置信度的噪声
        found = [a for a in found if a.confidence >= settings.min_confidence]
        extracted_all.extend(found)
        mark_processed(state, item.id, fingerprint)
        mark_seen(state, item.id, item.revision)

    stats["extracted"] = len(extracted_all)
    merged, added = merge_pool(pool, extracted_all)
    stats["added"] = added

    stamp = now.strftime("%Y-%m-%d %H:%M")
    changed = save_pool(settings.pool_path, merged)

    # 产出
    ics.write(settings.data_dir / "homework.ics", merged)
    markdown.write(settings.root / "HOMEWORK.md", merged, today, stamp)
    site.build(merged, today, settings.root / "index.html", stamp)

    active = [a for a in merged if a.status in (STATUS_OPEN, STATUS_PENDING)]
    stats["open"] = len([a for a in active if a.status == STATUS_OPEN and a.due])
    stats["pending"] = len([a for a in active if a.status == STATUS_PENDING])

    # 提醒：窗口内首次运行才发，state 保证当天不重复
    if do_notify:
        hm = now.strftime("%H:%M")
        if notify.window_of(hm, settings.remind_morning) and not already_notified(state, today, "morning"):
            text = notify.build_morning(active, today)
            if text and notify.send(settings, text):
                mark_notified(state, today, "morning")
                stats["notified"].append("morning")
        elif notify.window_of(hm, settings.remind_evening) and not already_notified(state, today, "evening"):
            text = notify.build_evening(active, today, settings.remind_days_before)
            if text and notify.send(settings, text):
                mark_notified(state, today, "evening")
                stats["notified"].append("evening")

    prune_state(state)
    save_state(settings.state_path, state)

    if stats["errors"]:
        _log_error(settings, f"[run {stamp}] {len(stats['errors'])} 个错误")

    return {"stats": stats, "changed": changed, "total": len(merged)}


def mark_done(settings: Settings, assignment_id: str) -> bool:
    from .store import set_status
    from .models import STATUS_DONE

    pool = load_pool(settings.pool_path)
    if not set_status(pool, assignment_id, STATUS_DONE):
        return False
    save_pool(settings.pool_path, pool)
    today = now_local(settings.timezone).date()
    ics.write(settings.data_dir / "homework.ics", pool)
    markdown.write(settings.root / "HOMEWORK.md", pool, today, now_local(settings.timezone).strftime("%Y-%m-%d %H:%M"))
    site.build(pool, today, settings.root / "index.html")
    return True


def doctor(settings: Settings = SETTINGS) -> list[tuple[str, bool, str]]:
    """环境自检：每一项返回 (检查名, 是否通过, 说明)。"""
    checks: list[tuple[str, bool, str]] = []

    checks.append(("数据目录", settings.data_dir.exists() or True, str(settings.data_dir)))
    checks.append(("时区", True, settings.timezone))

    if settings.source == "webdav":
        ok = bool(settings.webdav_url and settings.webdav_user and settings.webdav_password)
        checks.append(("WebDAV 配置", ok, settings.webdav_url or "未配置"))
    elif settings.source == "folder":
        path = Path(settings.source_dir or settings.inbox_dir)
        checks.append(("同步目录", path.exists(), str(path)))
    else:
        checks.append(("数据源", True, settings.source))

    engine = settings.transcribe_engine
    if engine == "whisper":
        try:
            import faster_whisper  # noqa: F401

            checks.append(("faster-whisper", True, f"model={settings.whisper_model}"))
        except ImportError:
            checks.append(("faster-whisper", False, "未安装，执行 pip install -r requirements-whisper.txt"))
    elif engine == "custom":
        checks.append(("自定义转写命令", bool(settings.transcribe_cmd), settings.transcribe_cmd or "未配置"))
    else:
        checks.append(("转写引擎", True, "passthrough（仅处理文本输入）"))

    checks.append(
        (
            "LLM 增强",
            bool(settings.llm_api_key and settings.llm_base_url),
            "已启用" if settings.llm_api_key else "未配置（规则引擎独立可用）",
        )
    )
    checks.append(
        (
            "推送通道",
            bool(settings.feishu_webhook or settings.webhook_url),
            "已配置" if (settings.feishu_webhook or settings.webhook_url) else "未配置，只会生成页面不发推送",
        )
    )

    return checks


# 常见失败码对应的排查方向。网盘类问题 90% 出在这几种。
_WEBDAV_HINTS = {
    400: "地址格式不对，坚果云 WebDAV 根地址是 https://dav.jianguoyun.com/dav/",
    401: "账号或密码不对。坚果云要用「安全选项」里生成的应用密码，不是登录密码",
    403: "账号没有该目录权限，或应用密码已失效",
    404: "远程目录不存在。先在网盘根目录建一个 hw 文件夹（对应 WEBDAV_DIR=/hw）",
    405: "服务端不接受 PROPFIND，确认填的是 WebDAV 地址而不是网页地址",
}


def probe_webdav(settings: Settings) -> tuple[bool, str]:
    """真连一次 WebDAV，列出目录。返回 (是否通过, 人话说明)。"""
    import requests

    from .sources.base import AUDIO_EXTS, TEXT_EXTS
    from .sources.webdav import WebDavSource

    if not (settings.webdav_url and settings.webdav_user and settings.webdav_password):
        return False, "缺少 WEBDAV_URL / WEBDAV_USER / WEBDAV_PASSWORD"

    try:
        entries = WebDavSource(settings).list_remote()
    except requests.HTTPError as exc:
        code = getattr(exc.response, "status_code", 0) or 0
        return False, f"列目录失败 HTTP {code}：{_WEBDAV_HINTS.get(code, '检查地址与账号')}"
    except requests.RequestException as exc:
        return False, f"连不上网盘：{exc}"

    usable = [e for e in entries if Path(e[1]).suffix.lower() in AUDIO_EXTS | TEXT_EXTS]
    if not usable:
        return True, f"连接正常，{settings.webdav_dir} 里还没有录音文件（手机同步任务没生效？）"

    newest = max(usable, key=lambda e: e[1])
    return True, f"连接正常，{len(usable)} 个可处理文件，最新：{newest[1]}"


def processed_docs(settings: Settings) -> int:
    """已处理过的音频/文本文件数，用来判断录音有没有真的进过链路。"""
    state = load_state(settings.state_path)
    docs = state.get("docs", {}) if isinstance(state, dict) else {}
    return len(docs)
