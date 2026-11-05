# 部署到云端（一次性）

配完之后，电脑彻底退出。手机录音 → 云端处理 → 手机收到提醒。

全程约 10 分钟，需要一台能运行命令的电脑做最后一次推送。

---

## 第 1 步：建仓库

打开 https://github.com/new

- Repository name：随便起，比如 `homework`
- 可见性：**选 Public**

> 为什么必须公开？GitHub Pages 对私有仓库需要付费账号。公开仓库的 Pages 和 Actions 都完全免费。
> 代价是仓库内容公开可见，包括 `data/homework.json` 里的作业文本。如果不接受，跳到最后一节「不想公开怎么办」。

- **不要**勾选 "Add a README file"
- **不要**勾选 .gitignore 和 license

创建后拿到地址：`https://github.com/你的用户名/homework.git`

---

## 第 2 步：生成 Token

打开 https://github.com/settings/tokens → **Tokens (classic)** → Generate new token (classic)

- Note：`homework-deploy`
- Expiration：90 days 即可
- 勾选权限：
  - ✅ **repo**（整个大类）
  - ✅ **workflow**

> `workflow` 必须勾。仓库里有 `.github/workflows/hw.yml`，没这个权限推送会被直接拒绝。

生成后复制那串 `ghp_` 开头的字符。**只显示一次。**

---

## 第 3 步：推送

在这台电脑上，项目根目录执行：

```powershell
powershell -ExecutionPolicy Bypass -File tools\push-to-github.ps1
```

按提示粘贴仓库地址和 Token。成功后脚本会自动把带 Token 的地址清掉。

---

## 第 4 步：配置 Secrets

仓库 → **Settings** → **Secrets and variables** → **Actions**

### Secrets 标签，逐个 New repository secret

| 名称 | 填什么 |
|---|---|
| `WEBDAV_URL` | 网盘 WebDAV 地址（坚果云：`https://dav.jianguoyun.com/dav/`） |
| `WEBDAV_USER` | 网盘账号 |
| `WEBDAV_PASSWORD` | 网盘应用密码（**不是**登录密码） |
| `FEISHU_WEBHOOK` | 飞书机器人地址，见第 6 步 |

可选（想要更准的抽取再填）：

| 名称 | 填什么 |
|---|---|
| `LLM_BASE_URL` | OpenAI 兼容接口地址 |
| `LLM_API_KEY` | 对应的 key |

### Variables 标签，New repository variable

| 名称 | 值 |
|---|---|
| `SOURCE` | `webdav` |
| `TRANSCRIBE_ENGINE` | `whisper` |
| `WHISPER_MODEL` | `small` |
| `WEBDAV_DIR` | `/hw` |

---

## 第 5 步：开启 Pages

仓库 → **Settings** → **Pages** → Source 选 **GitHub Actions**

不用选分支，选 Actions 那一项。

---

## 第 6 步：建飞书机器人

1. 飞书里建一个只有自己的群
2. 群设置 → 群机器人 → 添加机器人 → **自定义机器人**
3. 安全设置选 **自定义关键词**，填：`作业`
4. 复制 webhook 地址，填回第 4 步的 `FEISHU_WEBHOOK`

> 关键词必须是「作业」，代码里每条消息都带这个词。选 IP 白名单会失败，因为 GitHub 的出口 IP 不固定。

---

## 第 7 步：跑第一次

仓库 → **Actions** → 左侧选 `homework-reminder` → 右侧 **Run workflow** → 勾选 force → Run

等 1–3 分钟。绿色对勾表示成功。

如果失败，点进去看日志，最常见的原因是：

| 报错 | 原因 |
|---|---|
| `WebDAV 未配置` | Secrets 名字拼错，或没保存 |
| `401 / 403` 推送失败 | Token 缺 workflow 权限 |
| Whisper 下载超时 | 重跑一次，模型会命中缓存 |

---

## 第 8 步：手机安装

看板地址：

```
https://你的用户名.github.io/homework/
```

手机 Chrome 打开 → 右上角菜单 → **安装应用 / 添加到主屏幕**

点开就是全屏，无地址栏，有图标。电脑关机也照常打开。

---

## 日常是怎么跑的

| 时间 | 发生什么 |
|---|---|
| 你上课按录音 | 手机本地存音频 |
| 每 15 分钟 | FolderSync 静默上传到网盘 |
| 每 30 分钟 | GitHub Actions 拉取、转写、抽取、更新数据 |
| 07:00–10:00 | 当天首次运行，推送早间提醒 |
| 19:00–22:00 | 当天首次运行，推送晚间盘点 |

**全过程电脑不参与。**

---

## 不想公开怎么办

作业内容会随仓库公开。如果介意：

**方案一：私有仓库 + 放弃 Pages**
仓库设为 Private，Actions 照常跑（每月 2000 分钟免费额度够用），提醒照常推送到飞书。
代价是看板用不了，只能在飞书里看清单。对「防忘记作业」这件事，其实没有损失。

**方案二：私有仓库 + Cloudflare Pages**
Cloudflare Pages 可以连私有仓库并免费部署，但要多配一层。需要的话再说。

---

## 清空样例数据

仓库里的 `data/homework.json` 目前是演示数据，用来展示看板效果。

接真实数据前，在本地执行：

```powershell
Remove-Item data/homework.json, data/state.json -ErrorAction SilentlyContinue
git add -A
git -c user.name="me" -c user.email="me@local" commit -m "chore: 清空演示数据"
git push
```

之后 Actions 会从网盘拉真实录音重新建池。
