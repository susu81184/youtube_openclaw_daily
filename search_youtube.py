#!/usr/bin/env python3
"""调用 YouTube Data API v3：搜索每日新视频、关注频道更新、综合排序"""
from datetime import datetime, timezone, timedelta

try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
except ImportError:
    raise ImportError("请安装: pip install google-api-python-client")

from config import (
    YOUTUBE_API_KEY,
    SEARCH_QUERY,
    EFFECTIVE_SEARCH_QUERY,
    EFFECTIVE_MAX_RESULTS,
    MAX_RESULTS,
    HOURS_SINCE,
    CHANNEL_IDS,
    YOUTUBE_REFRESH_TOKEN,
    YOUTUBE_CLIENT_ID,
    YOUTUBE_CLIENT_SECRET,
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


def _days_since_publish(published_at: str) -> float:
    """解析发布时间，返回距今天数"""
    if not published_at:
        return 999.0
    try:
        pub = str(published_at).replace("Z", "+00:00")[:25]
        dt = datetime.fromisoformat(pub)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt
        return max(0.0, delta.total_seconds() / 86400)
    except Exception:
        return 999.0


def _calc_score(v: dict) -> float:
    """综合得分：观看、点赞、评论加权 + 时间衰减"""
    views = _parse_int(v.get("view_count", 0))
    likes = _parse_int(v.get("like_count", 0))
    comments = _parse_int(v.get("comment_count", 0))
    base = views * SORT_WEIGHT_VIEWS + likes * SORT_WEIGHT_LIKES + comments * SORT_WEIGHT_COMMENTS
    if SORT_WEIGHT_RECENCY <= 0:
        return base
    days = _days_since_publish(v.get("published_at", ""))
    recency_frac = max(0, 1 - days / SORT_RECENCY_DAYS)
    return base + SORT_WEIGHT_RECENCY * recency_frac


def _fetch_video_stats(youtube, video_ids: list[str]) -> dict:
    """获取视频统计（消耗 1 单位）"""
    if not video_ids:
        return {}
    resp = youtube.videos().list(part="statistics", id=",".join(video_ids[:50])).execute()
    return {v["id"]: v.get("statistics", {}) for v in resp.get("items", [])}


def search_daily_videos(api_key: str, query: str, max_results: int, hours_since: int) -> list[dict]:
    """
    搜索指定时间范围内新发布的视频
    返回带 view_count, like_count, comment_count 的列表
    """
    youtube = build("youtube", "v3", developerKey=api_key)
    published_after = (datetime.now(timezone.utc) - timedelta(hours=hours_since)).strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    search_resp = youtube.search().list(
        q=query,
        part="id,snippet",
        type="video",
        order="date",
        maxResults=max_results,
        publishedAfter=published_after,
    ).execute()

    video_ids = []
    items = []
    for item in search_resp.get("items", []):
        vid = item["id"].get("videoId")
        if vid:
            video_ids.append(vid)
            items.append({
                "video_id": vid,
                "title": item["snippet"].get("title", ""),
                "channel": item["snippet"].get("channelTitle", ""),
                "channel_id": item["snippet"].get("channelId", ""),
                "published_at": item["snippet"].get("publishedAt", ""),
                "source": "search",
            })

    stats_map = _fetch_video_stats(youtube, video_ids)
    for it in items:
        s = stats_map.get(it["video_id"], {})
        it["view_count"] = _parse_int(s.get("viewCount", 0))
        it["like_count"] = _parse_int(s.get("likeCount", 0))
        it["comment_count"] = _parse_int(s.get("commentCount", 0))
        it["url"] = f"https://www.youtube.com/watch?v={it['video_id']}"
        it["score"] = _calc_score(it)

    return items


def fetch_channel_latest(api_key: str, channel_ids: list[str], hours_since: int) -> list[dict]:
    """
    获取指定频道在时间范围内的最新视频
    每个频道取最近几条，再按时间过滤
    """
    if not channel_ids:
        return []

    youtube = build("youtube", "v3", developerKey=api_key)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours_since)
    all_items = []

    for cid in channel_ids[:20]:  # 最多 20 个频道，控制配额
        try:
            ch = youtube.channels().list(part="contentDetails,snippet", id=cid).execute()
            if not ch.get("items"):
                continue
            uploads_id = ch["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
            channel_title = ch["items"][0]["snippet"].get("title", "")

            pl = youtube.playlistItems().list(
                part="snippet",
                playlistId=uploads_id,
                maxResults=5,
            ).execute()

            for item in pl.get("items", []):
                sn = item.get("snippet", {})
                vid = sn.get("resourceId", {}).get("videoId")
                if not vid:
                    continue
                pub = sn.get("publishedAt", "")
                try:
                    pub_dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
                except Exception:
                    continue
                if pub_dt < cutoff:
                    continue
                all_items.append({
                    "video_id": vid,
                    "title": sn.get("title", ""),
                    "channel": channel_title,
                    "channel_id": cid,
                    "published_at": pub,
                    "source": "channel",
                })
        except HttpError:
            continue

    if not all_items:
        return []

    vid_ids = [x["video_id"] for x in all_items]
    stats_map = _fetch_video_stats(youtube, vid_ids)
    for it in all_items:
        s = stats_map.get(it["video_id"], {})
        it["view_count"] = _parse_int(s.get("viewCount", 0))
        it["like_count"] = _parse_int(s.get("likeCount", 0))
        it["comment_count"] = _parse_int(s.get("commentCount", 0))
        it["url"] = f"https://www.youtube.com/watch?v={it['video_id']}"
        it["score"] = _calc_score(it)

    return all_items


def merge_and_sort(search_items: list[dict], channel_items: list[dict]) -> list[dict]:
    """合并去重，按综合得分排序"""
    seen = set()
    merged = []
    for it in search_items + channel_items:
        vid = it["video_id"]
        if vid in seen:
            continue
        seen.add(vid)
        merged.append(it)
    merged.sort(key=lambda x: x["score"], reverse=True)
    return merged


def _get_channel_ids() -> list[str]:
    """优先用 OAuth 订阅，否则用手动配置的 CHANNEL_IDS"""
    if YOUTUBE_REFRESH_TOKEN and YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET:
        try:
            from oauth_youtube import get_credentials, get_subscribed_channel_ids
            creds = get_credentials()
            if creds:
                return get_subscribed_channel_ids(creds, max_results=50)
        except Exception:
            pass
    return CHANNEL_IDS


def run() -> tuple[list[dict], list[dict], list[dict]]:
    """
    执行完整流程，返回 (search_videos, channel_videos, merged_sorted)
    """
    if not YOUTUBE_API_KEY:
        print("❌ 请设置 YOUTUBE_API_KEY 环境变量，或复制 .env.example 为 .env 并填入 key")
        return [], [], []

    try:
        search_items = search_daily_videos(
            YOUTUBE_API_KEY, EFFECTIVE_SEARCH_QUERY, EFFECTIVE_MAX_RESULTS, HOURS_SINCE
        )
        channel_ids = _get_channel_ids()
        channel_items = fetch_channel_latest(YOUTUBE_API_KEY, channel_ids, HOURS_SINCE)
        merged = merge_and_sort(search_items, channel_items)
        return search_items, channel_items, merged
    except HttpError as e:
        if e.resp.status == 403:
            content = e.content.decode() if e.content else ""
            if "quotaExceeded" in content:
                print("❌ 今日配额已用尽，请明天再试")
            else:
                print(f"❌ API 403 错误: {content[:200]}")
        else:
            print(f"❌ API 错误: {e}")
        return [], [], []


if __name__ == "__main__":
    ch_ids = _get_channel_ids()
    src = "OAuth订阅" if (YOUTUBE_REFRESH_TOKEN and YOUTUBE_CLIENT_ID and YOUTUBE_CLIENT_SECRET) else "手动"
    print(f"搜索: {SEARCH_QUERY} (最近 {HOURS_SINCE}h) | 关注频道: {src} {len(ch_ids)} 个")
    s, c, m = run()
    print(f"\n搜索 {len(s)} 条 | 频道更新 {len(c)} 条 | 合并去重后 {len(m)} 条\n")
    for v in m:
        print(f"- [{v['title']}]")
        print(f"  {v['url']} | {v['channel']} | 播放:{v['view_count']} 点赞:{v['like_count']} 评论:{v['comment_count']} | {v['source']}")
