#!/usr/bin/env python3
"""通过 DuckDuckGo 网页搜索查找 OpenClaw 相关 YouTube 视频（无需 YouTube API，避免登录验证限制）"""
import re
import time
from typing import Optional

try:
    from duckduckgo_search import DDGS
except ImportError:
    raise ImportError("请安装: pip install duckduckgo-search")

from datetime import datetime, timezone
from config import (
    SEARCH_QUERY,
    EFFECTIVE_SEARCH_QUERY,
    EFFECTIVE_MAX_RESULTS,
    MAX_RESULTS,
    SORT_WEIGHT_VIEWS,
    SORT_WEIGHT_LIKES,
    SORT_WEIGHT_COMMENTS,
    SORT_WEIGHT_RECENCY,
    SORT_RECENCY_DAYS,
)


def _parse_int(s, default=0):
    try:
        return int(s) if s else default
    except (ValueError, TypeError):
        return default


def _extract_video_id(url: str) -> Optional[str]:
    """从 YouTube URL 提取 video_id"""
    if not url:
        return None
    # youtube.com/watch?v=XXX 或 youtu.be/XXX
    m = re.search(r"(?:v=|youtu\.be/)([a-zA-Z0-9_-]{11})", url)
    return m.group(1) if m else None


def _parse_statistics(stats_str: str) -> tuple[int, int, int]:
    """从 statistics 字符串解析 viewCount, likeCount 等"""
    views = likes = comments = 0
    if stats_str:
        try:
            import ast
            d = ast.literal_eval(stats_str)
            views = _parse_int(d.get("viewCount"))
            likes = _parse_int(d.get("likeCount"))
            comments = _parse_int(d.get("commentCount"))
        except Exception:
            pass
    return views, likes, comments


def _days_since_publish(published_at: str) -> float:
    """解析发布时间，返回距今天数；解析失败返回 999"""
    if not published_at:
        return 999.0
    try:
        s = str(published_at)[:19].replace("T", " ").replace("Z", "").strip()
        if len(s) >= 19:
            dt = datetime.strptime(s[:19], "%Y-%m-%d %H:%M:%S")
        elif len(s) >= 10:
            dt = datetime.strptime(s[:10], "%Y-%m-%d")
        else:
            return 999.0
        # 假设发布时间为 UTC
        dt_utc = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt_utc
        return max(0.0, delta.total_seconds() / 86400)
    except Exception:
        return 999.0


def _calc_score(v: dict) -> float:
    """综合得分：观看、点赞、评论加权 + 更新时间衰减加分"""
    base = (
        v.get("view_count", 0) * SORT_WEIGHT_VIEWS
        + v.get("like_count", 0) * SORT_WEIGHT_LIKES
        + v.get("comment_count", 0) * SORT_WEIGHT_COMMENTS
    )
    if SORT_WEIGHT_RECENCY <= 0:
        return base
    days = _days_since_publish(v.get("published_at", ""))
    # 0 天 = 100 分，SORT_RECENCY_DAYS 天 = 0 分
    recency_frac = max(0, 1 - days / SORT_RECENCY_DAYS)
    recency_bonus = SORT_WEIGHT_RECENCY * recency_frac
    return base + recency_bonus


def search_videos_web(query: str = None, max_results: int = None) -> list[dict]:
    """
    使用 DuckDuckGo 网页搜索查找 YouTube 视频，无需 YouTube API。
    返回与 search_youtube 兼容的格式（含 view_count、score 等）。
    """
    query = query or EFFECTIVE_SEARCH_QUERY
    max_results = max_results or EFFECTIVE_MAX_RESULTS

    items = []
    seen_ids = set()
    try:
        ddgs = DDGS()
        # 避免请求过快
        time.sleep(2)
        for r in ddgs.videos(keywords=query, max_results=max_results):
            if r is None:
                continue
            url = r.get("content") or r.get("embed_url", "").replace("/embed/", "/watch?v=").split("?")[0]
            vid = _extract_video_id(url)
            if not vid or vid in seen_ids:
                continue
            seen_ids.add(vid)
            title = r.get("title", "")
            uploader = r.get("uploader", "")
            published = r.get("published", "")[:19].replace("T", " ") if r.get("published") else ""
            views, likes, comments = _parse_statistics(str(r.get("statistics", "{}")))
            it = {
                "video_id": vid,
                "title": title,
                "channel": uploader,
                "channel_id": "",
                "published_at": published,
                "source": "web_search",
                "view_count": views,
                "like_count": likes,
                "comment_count": comments,
                "url": f"https://www.youtube.com/watch?v={vid}",
            }
            it["score"] = _calc_score(it)
            items.append(it)
            if len(items) >= max_results:
                break
    except Exception as e:
        print(f"⚠️ 网页搜索异常: {e}")
        return []

    # 按综合得分排序
    items.sort(key=lambda x: x["score"], reverse=True)
    return items


def run() -> tuple[list[dict], list[dict], list[dict]]:
    """
    执行网页搜索流程。
    返回 (search_videos, channel_videos, merged_sorted)。
    网页模式下 channel_videos 为空，merged 即 search 结果。
    """
    items = search_videos_web()
    return items, [], items


if __name__ == "__main__":
    print(f"网页搜索: {SEARCH_QUERY} | 最多 {MAX_RESULTS} 条\n")
    s, c, m = run()
    print(f"找到 {len(m)} 条\n")
    for v in m:
        print(f"- [{v['title']}]")
        print(f"  {v['url']} | {v['channel']} | 播放:{v['view_count']} 点赞:{v['like_count']} | {v['source']}")
