# 一次性配置清单

配完之后，你只需要上课按录音键。以下每个步骤只做一次。

---

## 现在到哪一步了

| 环节 | 状态 | 判断依据 |
|---|---|---|
| 云端定时任务 | ✅ 已通 | Actions 每 30 分钟跑一次，Pages 看板每天自动刷新日期 |
| 看板 / 日历 / Markdown 产出 | ✅ 已通 | 线上 `https://syeu-oss.github.io/homework/` 可打开 |
| 网盘（WebDAV）读取 | ❌ 未配 | 云端没有 `WEBDAV_*` 密钥，取数直接失败 |
| 手机录音自动上传 | ❌ 未配 | FolderSync 还没建同步任务 |
| 飞书推送 | ❌ 未配 | 没有 `FEISHU_WEBHOOK`，不会发消息 |

也就是说：**电脑侧和云端全部就绪，缺的正是手机上这一段。**
演示数据已清空，看板现在是空状态，等真实录音进来。

### 5 个动作，顺序不要乱

0. **先选网盘**（决定后面填什么地址）：

| 备选 | 免费额度 | WebDAV 地址 |
|---|---|---|
| 坚果云 | 上传 1GB/月、下载 3GB/月 | `https://dav.jianguoyun.com/dav/` |
| InfiniCLOUD | 20GB，不限流量（注册有时排队） | `https://用户名.teracloud.jp/dav/` |
| Koofr | 10GB，不限流量 | `https://app.koofr.net/dav/Koofr` |

   代码只认 WebDAV 标准，换服务商不用改任何代码，只换环境变量。
   每月 20 节课 ≈ 0.3–1.2GB，坚果云免费版勉强够，嫌紧就选后两个。

1. **网盘建目录**：根目录建 `hw`。坚果云另需在「安全选项 → 添加应用」生成**应用密码**（不是登录密码）；InfiniCLOUD / Koofr 用账号密码或各自的应用密码即可。
2. **GitHub 填密钥**：仓库 Settings → Secrets and variables → Actions，加 `WEBDAV_URL` / `WEBDAV_USER` / `WEBDAV_PASSWORD`，Variables 里 `SOURCE=webdav`、`TRANSCRIBE_ENGINE=whisper`。
3. **手机装 FolderSync**，建「仅上传」任务把录音目录传到 `/hw`，并做保活设置（见下文第一节）。顺手把录音机的录音质量调成「标准」，一小时文件能从 40MB 降到 15MB 左右。
4. **飞书建机器人**，把 webhook 填进 `FEISHU_WEBHOOK`。
5. **验证**：手机录一段带作业的话，等 15 分钟后按下面方法逐环确认。

### 每一环怎么单独验证

```bash
# 本机跑（先把环境变量设成和 GitHub Secrets 一样的值）
$env:SOURCE="webdav"; $env:WEBDAV_URL="https://dav.jianguoyun.com/dav/"; $env:WEBDAV_USER="你的账号"; $env:WEBDAV_PASSWORD="应用密码"
python -m homework.cli check --notify
```

`check` 会真连一次网盘、报出目录里有几个可处理文件、并（加 `--notify` 时）发一条飞书测试消息，哪一环断了一眼能看到：

```
[OK  ] 网盘目录：连接正常，3 个可处理文件，最新：录音_20261105_100212.m4a
[OK  ] 已入池：处理过 3 个文件，作业池 5 条
[OK  ] 推送测试：已发送，看手机
```

- 网盘 FAIL 且提示 401 → 密码用错了，坚果云必须用应用密码
- 网盘 FAIL 且提示 404 → 网盘里没有 `hw` 目录
- 网盘 OK 但文件数是 0 → FolderSync 没传上去，回到手机端查保活
- 网盘 OK 有文件、作业池却没变 → 云端还没跑，去 Actions 里手动 Run workflow

---

## 一、手机端（3 步）

### 1. 确认录音机开着 AI 转写（可选但建议）

ColorOS / realme UI：录音机 → 右上角设置 → 打开「AI 录音助手」
OriginOS：录音机 → 设置 → 打开「录音转文字」

这一步不影响自动化，只是让你在手机上也能直接看文字。**真正送进链路的是音频文件。**

> 注意：系统录音机的转写文本存在 App 内部数据库，普通同步工具读不到。
> 所以链路传的是**音频文件**，转写在云端做。这也是为什么必须开 Whisper。

### 2. 安装 FolderSync（免费版即可）

只用一个工具，用来把录音目录自动传到网盘。

1. 装好后新建账户 → 选 **WebDAV**
2. 服务器地址填网盘提供的 WebDAV 地址（坚果云为 `https://dav.jianguoyun.com/dav/`）
3. 填入账号与应用密码（坚果云需在「安全选项」里单独生成应用密码，不是登录密码）

### 3. 建一个同步任务

1. 新建「文件夹对」→ 远程目标指向 `/hw`
2. 本地目录选你的录音目录，常见路径：
   - ColorOS：`/内部存储/Recordings` 或 `/内部存储/Music/Recordings`
   - OriginOS：`/内部存储/Record` 或 `/内部存储/录音`
   - 用文件管理器确认实际路径，不同机型有差异
3. 同步类型选「仅上传」，方向「本地 → 远程」
4. 调度选「每 15 分钟」或「检测到文件变化时」
5. 保存

**必做的保活设置**，否则后台会被杀：

- 设置 → 电池 → 应用耗电管理 → FolderSync → 允许后台运行 / 无限制
- 设置 → 应用管理 → FolderSync → 自启动 打开
- 最近任务里给 FolderSync 加锁（下拉卡片点锁图标）

---

## 二、云端（4 步）

### 1. 建仓库

新建一个 GitHub 仓库（私有即可），把本项目推上去。

### 2. 填 Secrets

仓库 → Settings → Secrets and variables → Actions → **Secrets**：

| 名称 | 值 |
|---|---|
| `WEBDAV_URL` | 你的 WebDAV 地址 |
| `WEBDAV_USER` | 网盘账号 |
| `WEBDAV_PASSWORD` | 网盘应用密码 |
| `FEISHU_WEBHOOK` | 飞书机器人 webhook（见第 3 步） |
| `LLM_BASE_URL` | 可选，OpenAI 兼容接口地址 |
| `LLM_API_KEY` | 可选，抽取增强用 |

**Variables**（同一页面的 Variables 标签）：

| 名称 | 值 |
|---|---|
| `SOURCE` | `webdav` |
| `TRANSCRIBE_ENGINE` | `whisper` |
| `WHISPER_MODEL` | `small` |

### 3. 建飞书机器人

1. 飞书里建一个只有自己的群
2. 群设置 → 群机器人 → 添加机器人 → **自定义机器人**
3. 安全设置选 **自定义关键词**，填 `作业`（代码里每条消息都带这个词）
4. 复制 webhook 地址，填进上面的 `FEISHU_WEBHOOK`

### 4. 开启 Pages

仓库 → Settings → Pages → Source 选 **GitHub Actions**。

之后看板地址是 `https://<用户名>.github.io/<仓库名>/`，手机浏览器打开后「添加到主屏幕」，图标和 App 一样。

---

## 三、验证

### 云端是否跑通

仓库 → Actions → 选 `homework-reminder` → Run workflow（勾选 force）。

跑完后检查：

- 绿色对勾 = 成功
- 点进去看「执行一次完整流程」日志
- 仓库里 `data/homework.json` 有没有新内容

### 手机是否同步成功

录一段音，等 15 分钟，去网盘 `/hw` 目录看音频有没有到。

**音频到不了** → 问题在手机端保活，按第 3 步的保活设置逐条检查。

### 提醒是否送达

本地先测：

```bash
# Windows PowerShell
$env:FEISHU_WEBHOOK="你的地址"
python -c "from homework.config import SETTINGS; from homework.emit import notify; print(notify.send(SETTINGS, '作业提醒测试'))"
```

手机飞书收到消息 = 通道通了。

---

## 常见问题

**Q：为什么不直接同步手机录音机转好的文字？**
A：系统录音机的转写结果存在 App 私有数据库里，FolderSync 这类工具只能看到文件，看不到数据库。所以传音频、云端转写。

**Q：一天跑 48 次会不会超 Actions 免费额度？**
A：私有仓库 2000 分钟/月，空跑一次约 30 秒，一天 48 次 ≈ 24 分钟/月，加上转写时间仍然很宽裕。仓库设为公开则完全免费。

**Q：录音文件太大传不动？**
A：一小时录音约 30–60MB。如果网盘空间紧张，可在 FolderSync 里设「仅同步最近 7 天」或在手机端把录音格式改为压缩率更高的 m4a。

**Q：电脑需要开机吗？**
A：完全不需要。整条链路在手机上触发、云端执行。
