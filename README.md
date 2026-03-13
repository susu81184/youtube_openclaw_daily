# YouTube OpenClaw 每日视频检索

按日检索 YouTube 上关于 OpenClaw 的新视频，按**观看·点赞·评论**综合排序；支持**关注频道**有新视频时一并推送；可选 Telegram 通知。

## 功能

- 只搜最近 24 小时内新发布的视频（可配置）
- 综合排序：观看量×1 + 点赞×100 + 评论×50 + 时间衰减加分（可配置权重）
- 关注频道：配置 channel ID，订阅博主有新视频时一并推送
- 输出：终端 + Markdown 文件 + 可选 Telegram 推送

## 搜索模式

- **首选 YouTube API**（`USE_WEB_SEARCH=0` 或不设置）：使用 YouTube Data API 搜索，结果更稳定、可按发布时间筛选；需配置 `YOUTUBE_API_KEY`
- **API 失败时自动 fallback 到 DuckDuckGo**：配额用尽、网络错误等情况下，自动切换到 DuckDuckGo 网页搜索
- **强制网页搜索**：设置 `USE_WEB_SEARCH=1` 时仅用 DuckDuckGo，不调用 YouTube API
- **报告中标明搜索来源**：每次推送会显示本次搜索使用的是「YouTube API」还是「DuckDuckGo」

## 前置（仅 API 模式需要）

1. 在 [Google Cloud Console](https://console.cloud.google.com/) 创建项目并启用 **YouTube Data API v3**
2. 创建 **API 密钥**（搜索用）
3. 若要用 OAuth 自动获取订阅：创建 **OAuth 2.0 客户端 ID**（应用类型选「桌面应用」）
4. **⚠️ 安全**：不要把 API Key / Client Secret / Refresh Token 暴露在聊天或代码库中

## 安装

```bash
cd youtube_openclaw_daily
pip install -r requirements.txt
```

## 配置

```bash
cp .env.example .env
# 编辑 .env 填入配置
```

| 变量 | 说明 |
|------|------|
| `YOUTUBE_API_KEY` | YouTube API 密钥（使用 API 模式时必填） |
| `USE_WEB_SEARCH` | 设为 `1` 时用 DuckDuckGo 网页搜索，**无需 API**，避免登录验证/配额限制 |
| `YOUTUBE_SEARCH_QUERY` | 搜索词，默认 OpenClaw |
| `YOUTUBE_MAX_RESULTS` | 搜索最多条数，默认 20 |
| `YOUTUBE_HOURS_SINCE` | 只搜最近多少小时，默认 24 |
| `YOUTUBE_SORT_WEIGHT_RECENCY` | 时间衰减权重，默认 5000，0=关闭 |
| `YOUTUBE_SORT_RECENCY_DAYS` | 衰减周期（天），默认 100 |
| `TELEGRAM_BOT_TOKEN` | 可选，Telegram Bot Token |
| `TELEGRAM_CHAT_ID` | 可选，Telegram Chat ID |

### 关注频道（二选一）

**方式一：OAuth 自动获取订阅（推荐）**

1. 在 [Google Cloud 凭据](https://console.cloud.google.com/apis/credentials) 创建 OAuth 2.0 客户端 ID，类型选「桌面应用」
2. 在 OAuth 同意屏幕添加你的 Google 账号为测试用户
3. 在 `.env` 中填入 `YOUTUBE_CLIENT_ID`、`YOUTUBE_CLIENT_SECRET`
4. 运行 `python auth_youtube.py`，在浏览器中登录并授权
5. 将输出的 `YOUTUBE_REFRESH_TOKEN` 复制到 `.env`

**方式二：手动填写 channel ID**

在 `.env` 中设置 `YOUTUBE_CHANNEL_IDS=UCxxx,UCyyy`。频道 ID 可从频道页 URL 中 `/channel/UC...` 获取。

## 运行

```bash
python run_once.py
```

或供 OpenClaw/Telegram 机器人调用（仅输出报告）：
```bash
python search_for_agent.py           # 搜索 OpenClaw
python search_for_agent.py "关键词"  # 自定义搜索词
```

结果会：
- 打印到终端
- 保存到 `output/openclaw_videos_YYYY-MM-DD.md`
- 若配置了 Telegram，会推送到指定会话

## GitHub Actions（推荐，本机关机也能跑）

1. 将项目推送到 **公开** GitHub 仓库（公开仓库 Actions 免费）
2. 在仓库 **Settings → Secrets and variables → Actions** 添加 Secrets：
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
   - `YOUTUBE_API_KEY`（可选：`USE_WEB_SEARCH=1` 时可不填；若需在网页搜索模式下推送订阅频道更新，必须填写）
   - `YOUTUBE_CLIENT_ID` / `YOUTUBE_CLIENT_SECRET` / `YOUTUBE_REFRESH_TOKEN`（可选：用于 OAuth 获取订阅频道；或改用 `YOUTUBE_CHANNEL_IDS` 环境变量）
3. 推送后自动生效，每天 9:00 北京时间执行；也可在 Actions 页 **Run workflow** 手动触发

## N8N 工作流（定时自动化）

导入 `n8n_youtube_openclaw_daily.json` 到 N8N 即可使用：

1. 打开 N8N → 工作流 → 导入 → 选择 `n8n_youtube_openclaw_daily.json`
2. 打开「执行视频检索并推送」节点，**修改项目路径**为你的实际路径（默认 `/Users/susu/学习/youtube_openclaw_daily`）
3. 保存并**发布**工作流

**注意：**
- 仅支持**自托管 N8N**（n8n Cloud 无 Execute Command 节点）
- N8N 需与项目在同一台机器，或 Docker 挂载项目目录
- 若 Execute Command 不可用，需设置环境变量 `NODES_EXCLUDE="[]"` 启用

## 定时执行（crontab）

crontab 每天 9 点执行：

```bash
# 首次添加（会保留现有 crontab）
(crontab -l 2>/dev/null; echo "0 9 * * * cd /Users/susu/学习/youtube_openclaw_daily && python3 run_once.py >> /tmp/youtube_openclaw_daily.log 2>&1") | crontab -
```

或参考 `crontab.example`。

## 配置检查

```bash
python3 check_setup.py
```

## 日志

运行日志写入 `logs/run_once.log`，便于 crontab 排查。同日期多次运行会备份上一次结果为 `*.md.prev`。
