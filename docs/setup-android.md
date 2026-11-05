# 一次性配置清单

配完之后，你只需要上课按录音键。以下每个步骤只做一次。

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
