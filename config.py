"""配置：API Key 等，优先从环境变量读取"""
import os

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# API Key
YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "")

# 搜索配置
SEARCH_QUERY = os.environ.get("YOUTUBE_SEARCH_QUERY", "OpenClaw")
MAX_RESULTS = int(os.environ.get("YOUTUBE_MAX_RESULTS", "20"))
# 仅保留中文结果：标题或频道含中文
CHINESE_ONLY = os.environ.get("CHINESE_ONLY", "1").lower() in ("1", "true", "yes")
# 中文模式下搜索词追加「中文」以获取更多中文视频
EFFECTIVE_SEARCH_QUERY = (SEARCH_QUERY + " 中文") if CHINESE_ONLY else SEARCH_QUERY
# 中文模式下多拉取以便筛选后仍有足够数量
EFFECTIVE_MAX_RESULTS = int(MAX_RESULTS * 3) if CHINESE_ONLY else MAX_RESULTS
# 只搜最近多少小时内的新视频（24=当日）
HOURS_SINCE = int(os.environ.get("YOUTUBE_HOURS_SINCE", "24"))

# 关注频道（二选一）：
# 方式一：OAuth 登录后自动获取订阅，配置下面三项
YOUTUBE_CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID", "").strip()
YOUTUBE_CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET", "").strip()
YOUTUBE_REFRESH_TOKEN = os.environ.get("YOUTUBE_REFRESH_TOKEN", "").strip()
# 方式二：手动填写 channel ID，逗号分隔
CHANNEL_IDS = [
    c.strip() for c in os.environ.get("YOUTUBE_CHANNEL_IDS", "").split(",") if c.strip()
]

# 综合排序权重：views, likes, comments, recency（更新时间优先）
# 得分 = views*1 + likes*100 + comments*50 + 时间衰减加分
# 时间衰减：发布越新加分越高，100 天内线性衰减（0天=100分，100天=0分）
SORT_WEIGHT_VIEWS = float(os.environ.get("YOUTUBE_SORT_WEIGHT_VIEWS", "1"))
SORT_WEIGHT_LIKES = float(os.environ.get("YOUTUBE_SORT_WEIGHT_LIKES", "100"))
SORT_WEIGHT_COMMENTS = float(os.environ.get("YOUTUBE_SORT_WEIGHT_COMMENTS", "50"))
SORT_WEIGHT_RECENCY = float(os.environ.get("YOUTUBE_SORT_WEIGHT_RECENCY", "5000"))  # 新近度权重，0=关闭
SORT_RECENCY_DAYS = int(os.environ.get("YOUTUBE_SORT_RECENCY_DAYS", "100"))  # 多少天内衰减

# 搜索模式：USE_WEB_SEARCH=1 时使用 DuckDuckGo 网页搜索（无需 YouTube API，避免登录验证限制）
USE_WEB_SEARCH = os.environ.get("USE_WEB_SEARCH", "").lower() in ("1", "true", "yes")

# 输出
OUTPUT_DIR = os.environ.get("YOUTUBE_OUTPUT_DIR", "output")

# 可选：Telegram 推送
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
