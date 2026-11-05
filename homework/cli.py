"""命令行入口。

常用：
    python -m homework.cli selftest      # 零配置自测全链路
    python -m homework.cli doctor        # 环境自检
    python -m homework.cli run           # 正式跑一次
    python -m homework.cli list          # 看当前作业池
    python -m homework.cli done <id>     # 标记完成
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
from dataclasses import replace
from pathlib import Path

from .config import SETTINGS
from .models import now_local
from .pipeline import (
    OPTIONAL_CHECKS,
    doctor,
    mark_done,
    processed_docs,
    probe_webdav,
    run_once,
)
from .store import load_pool


def _cmd_run(args: argparse.Namespace) -> int:
    result = run_once(SETTINGS, force=args.force, do_notify=not args.no_notify)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if not result["stats"]["errors"] else 1


def _cmd_doctor(_: argparse.Namespace) -> int:
    print("环境自检\n" + "=" * 46)
    failed = 0
    for name, ok, detail in doctor(SETTINGS):
        if ok:
            mark = "OK  "
        elif name in OPTIONAL_CHECKS:
            mark = "WARN"
        else:
            mark = "FAIL"
            failed += 1
        print(f"[{mark}] {name}: {detail}")
    print("=" * 46)
    print("全部通过。" if not failed else f"有 {failed} 项需要注意。")
    return 0


def _cmd_list(_: argparse.Namespace) -> int:
    pool = load_pool(SETTINGS.pool_path)
    if not pool:
        print("作业池是空的。先跑一次 run 或 selftest。")
        return 0
    today = now_local(SETTINGS.timezone).date()
    for item in sorted(pool, key=lambda a: (a.due or today, a.course)):
        due = item.due.isoformat() if item.due else "待确认"
        delta = (item.due - today).days if item.due else ""
        print(f"{item.id}  {due:<10} {str(delta):>4}  [{item.course}] {item.title}")
    return 0


def _cmd_done(args: argparse.Namespace) -> int:
    ok = mark_done(SETTINGS, args.id)
    print("已标记完成。" if ok else f"没有找到 ID：{args.id}")
    return 0 if ok else 1


def _cmd_selftest(_: argparse.Namespace) -> int:
    tmp = Path(tempfile.mkdtemp(prefix="hw-selftest-"))
    try:
        settings = replace(
            SETTINGS,
            root=tmp,
            data_dir=tmp / "data",
            source="demo",
            transcribe_engine="passthrough",
            feishu_webhook="",
            webhook_url="",
        )
        result = run_once(settings, force=True, do_notify=False)

        pool = load_pool(settings.pool_path)
        print("自测结果\n" + "=" * 52)
        print(json.dumps(result["stats"], ensure_ascii=False, indent=2))
        print("-" * 52)
        for item in sorted(pool, key=lambda a: (a.due or now_local().date(), a.course)):
            due = item.due.isoformat() if item.due else "待确认"
            print(f"  {due:<12} [{item.course}] {item.title}  (conf={item.confidence:.2f})")
        print("-" * 52)
        print(f"作业池：{len(pool)} 条")
        print(f"日历：  {settings.data_dir / 'homework.ics'}")
        print(f"看板：  {tmp / 'index.html'}")

        expected_min = 3
        if len(pool) < expected_min:
            print(f"\n警告：样例应至少抽出 {expected_min} 条作业，实际 {len(pool)} 条。")
            return 1
        print("\n自测通过。")
        return 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _cmd_check(args: argparse.Namespace) -> int:
    """逐个外链做真实探测：手机同步 → 网盘 → 推送，哪一环断了一目了然。"""
    print("手机链路自检\n" + "=" * 52)
    failed = 0

    ok, detail = probe_webdav(SETTINGS)
    print(f"[{'OK  ' if ok else 'FAIL'}] 网盘目录：{detail}")
    failed += 0 if ok else 1

    docs = processed_docs(SETTINGS)
    pool = load_pool(SETTINGS.pool_path)
    print(f"[OK  ] 已入池：处理过 {docs} 个文件，作业池 {len(pool)} 条")

    from .emit import notify

    has_channel = bool(SETTINGS.feishu_webhook or SETTINGS.webhook_url)
    if args.notify:
        sent = notify.send(SETTINGS, "作业链路自检：这条能收到，推送就通了。")
        print(f"[{'OK  ' if sent else 'FAIL'}] 推送测试：{'已发送，看手机' if sent else '未配置 webhook 或发送失败'}")
        failed += 0 if sent else 1
    else:
        print(f"[{'OK  ' if has_channel else 'WARN'}] 推送配置：{'已配置（加 --notify 可发一条测试）' if has_channel else '未配置，只生成页面不推送'}")

    print("=" * 52)
    print("全部打通。" if not failed else "上面标 FAIL 的按提示修，其余环节是好的。")
    return 0 if not failed else 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="homework", description="作业自动提醒链路")
    sub = parser.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="跑一次完整流程")
    p_run.add_argument("--force", action="store_true", help="忽略已处理记录，强制重跑")
    p_run.add_argument("--no-notify", action="store_true", help="只生成产物，不发推送")
    p_run.set_defaults(func=_cmd_run)

    p_doctor = sub.add_parser("doctor", help="环境自检")
    p_doctor.set_defaults(func=_cmd_doctor)

    p_list = sub.add_parser("list", help="查看作业池")
    p_list.set_defaults(func=_cmd_list)

    p_done = sub.add_parser("done", help="标记某项完成")
    p_done.add_argument("id", help="作业 ID")
    p_done.set_defaults(func=_cmd_done)

    p_test = sub.add_parser("selftest", help="用内置样例自测")
    p_test.set_defaults(func=_cmd_selftest)

    p_check = sub.add_parser("check", help="探测手机链路：网盘、作业池、推送")
    p_check.add_argument("--notify", action="store_true", help="真发一条测试消息到手机")
    p_check.set_defaults(func=_cmd_check)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())
