# 作业自动提醒链路

上完课 → 系统自己知道「哪门课、留了什么、什么时候交」→ 到点提醒你。

**手机上你只需要按一次录音键**，其余全在云端完成，不依赖电脑常开。

## 链路

```
① 手机自带录音机录音（唯一人工动作）
        ↓
② FolderSync 后台把录音目录自动同步到网盘（WebDAV）
        ↓
③ GitHub Actions 每 30 分钟拉取（云端，跟你的电脑无关）
        ↓
④ 转写：Whisper（免费）/ 自定义命令（可接更高精度的云端 ASR）
        ↓
⑤ 抽取：关键词预筛 → 规则引擎 + 可选 LLM → 中文相对时间用代码换算
        ↓
⑥ 产出与提醒
   ├─ 飞书机器人推送（主提醒，手机必响）
   ├─ homework.ics 日历（可视化副轨）
   └─ index.html 作业看板（手机浏览器打开，可加到桌面）
```

## 为什么这样设计

| 决策 | 原因 |
|---|---|
| 转写放云端而不放手机 | 手机后台保活不可靠；云端 CI 稳定且免费 |
| 日期用代码算，不让模型算 | LLM 算日期必错且错得自信；中文相对时间必须确定性换算 |
| 解析不出时间就标「待确认」 | 宁可漏提醒，不能编一个假日期去提醒 |
| 提醒用「时间窗口 + 当天去重」 | Actions cron 有 5–30 分钟抖动，追求准点必然失败 |
| 作业 ID 不含截止日期 | 日期是后补的，含日期会让同一作业分裂成两条 |
| 日历只做可视化 | 多数 Android 系统日历对「订阅日历」不触发闹钟，只显示不响 |

## 快速开始

```bash
# 1. 零配置自测（用内置样例，不需要任何账号）
python -m homework.cli selftest

# 2. 环境自检
python -m homework.cli doctor

# 3. 正式跑一次
python -m homework.cli run

# 4. 查看作业池
python -m homework.cli list

# 5. 标记某项完成
python -m homework.cli done <id>
```

## 清空演示数据

仓库里的 `data/homework.json` 是 demo 样例，用来展示看板效果。接上真实数据前清掉它：

```bash
# Windows PowerShell
Remove-Item data/homework.json, data/state.json -ErrorAction SilentlyContinue

# macOS / Linux
rm -f data/homework.json data/state.json
```

## 一次性配置

详见 [docs/setup-android.md](docs/setup-android.md)：手机端 3 步、云端 4 步，配完就不用再管。

## 环境变量

| 变量 | 作用 | 默认 |
|---|---|---|
| `SOURCE` | 数据源：`folder` / `webdav` / `demo` | `folder` |
| `SOURCE_DIR` | folder 模式的扫描目录 | `data/inbox` |
| `WEBDAV_URL` / `WEBDAV_USER` / `WEBDAV_PASSWORD` | 网盘连接信息 | — |
| `TRANSCRIBE_ENGINE` | `passthrough` / `whisper` / `custom` | `passthrough` |
| `WHISPER_MODEL` | `tiny` / `base` / `small` / `medium` | `small` |
| `TRANSCRIBE_CMD` | custom 模式的命令，支持 `{input}` `{output}` | — |
| `LLM_BASE_URL` / `LLM_API_KEY` / `LLM_MODEL` | 可选的抽取增强 | — |
| `FEISHU_WEBHOOK` | 飞书自定义机器人地址 | — |
| `REMIND_MORNING` | 早间提醒窗口 | `07:00-10:00` |
| `REMIND_EVENING` | 晚间提醒窗口 | `19:00-22:00` |

## 成本

- GitHub Actions：私有仓库 2000 分钟/月，每 30 分钟一次约 1400 分钟，够用；公开仓库完全免费
- Whisper：本地推理，零成本
- 飞书机器人：免费

## 失败排查

| 现象 | 先看这里 |
|---|---|
| 没有推送 | `python -m homework.cli doctor` 看推送通道是否配置 |
| 抽不出作业 | 看 `data/errors.log`，确认转写文本是否正常 |
| 日期不对 | 进 `homework/timeparse.py`，或检查 `source.time_phrase` |
| 日历不响 | 这是已知平台限制，靠推送而不是日历 |
