#!/usr/bin/env python3
"""每日 OpenClaw 相关视频检索 - 按观看/点赞/评论综合排序，可选 Telegram 推送"""
import logging
import re
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

from config import (
    OUTPUT_DIR,
    SEARCH_QUERY,
    TELEGRAM_BOT_TOKEN,
    TELEGRAM_CHAT_ID,
    USE_WEB_SEARCH,
    CHINESE_ONLY,
    YOUTUBE_API_KEY,
    HOURS_SINCE,
)


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
        dt_utc = dt.replace(tzinfo=timezone.utc)
        delta = datetime.now(timezone.utc) - dt_utc
        return max(0.0, delta.total_seconds() / 86400)
    except Exception:
        return 999.0


# 中文筛选：标题必须含 CJK，且中文占比高于英文
_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
_LATIN_RE = re.compile(r"[a-zA-Z]")


def _filter_chinese_only(items: list) -> list:
    """仅保留标题以中文为主的视频：CJK≥英文字母，或 CJK≥3 且英文字母<15（容错 openclaw 等）"""
    out = []
    for v in items:
        title = v.get("title") or ""
        if not _CJK_RE.search(title):
            continue
        cjk = len(_CJK_RE.findall(title))
        latin = len(_LATIN_RE.findall(title))
        if cjk >= latin:
            out.append(v)
        elif cjk >= 3 and latin < 15:  # 如 "最全openclaw中文教程"
            out.append(v)
        # 否则排除（如 "0142 日常英語聽力營 | Someone said their OpenClaw bot..."）
    return out

# 日志
_LOG_DIR = Path(__file__).resolve().parent / "logs"
def _setup_logging():
    _LOG_DIR.mkdir(parents=True, exist_ok=True)
    fmt = "%(asctime)s %(levelname)s %(message)s"
    log = logging.getLogger("youtube_openclaw")
    log.setLevel(logging.INFO)
    if not log.handlers:
        sh = logging.StreamHandler()
        sh.setFormatter(logging.Formatter(fmt))
        log.addHandler(sh)
        try:
            fh = logging.FileHandler(_LOG_DIR / "run_once.log", encoding="utf-8")
            fh.setFormatter(logging.Formatter(fmt))
            log.addHandler(fh)
        except Exception:
            pass
    return log


def _fmt_video(v: dict) -> list:
    """单个视频的格式化行"""
    return [
        f"- [{v['title']}]",
        f"  - {v['url']}",
        f"  - 频道: {v['channel']} | "
        f"播放: {v['view_count']} | 点赞: {v['like_count']} | 评论: {v['comment_count']} | "
        f"{v['published_at'][:10] if v.get('published_at') else ''}",
        "",
    ]


def _build_report(search_videos: list, channel_videos: list, merged: list, search_source: str = "") -> str:
    lines = []
    lines.append(f"# OpenClaw 相关视频 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    if search_source:
        lines.append(f"\n🔍 搜索来源: **{search_source}**")

    # 若视频同时出现在搜索和关注频道，归入关注频道更新
    channel_video_ids = {v["video_id"] for v in channel_videos}
    channel_items = [v for v in merged if v["video_id"] in channel_video_ids]
    search_items = [v for v in merged if v["video_id"] not in channel_video_ids]

    # 一、关注频道更新（单独列出）
    if channel_items:
        lines.append(f"\n## 关注频道更新（{len(channel_items)} 条）\n")
        for v in channel_items:
            lines.extend(_fmt_video(v))

    # 二、搜索视频
    if search_items:
        lines.append(f"\n## 搜索视频（{len(search_items)} 条）\n")
        for v in search_items:
            lines.extend(_fmt_video(v))

    lines.append(f"\n共 {len(merged)} 条")
    return "\n".join(lines).rstrip()


def _send_telegram(text: str, bot_token: str, chat_id: str, log) -> bool:
    if not bot_token or not chat_id:
        return False
    # Telegram 单条上限 4096，分条发送
    chunk_size = 4000
    chunks = [text[i : i + chunk_size] for i in range(0, len(text), chunk_size)]
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    ok_count = 0
    for i, chunk in enumerate(chunks):
        data = urllib.parse.urlencode({"chat_id": chat_id, "text": chunk})
        data = data.encode("utf-8")
        try:
            req = urllib.request.Request(url, data=data, method="POST")
            req.add_header("Content-Type", "application/x-www-form-urlencoded; charset=utf-8")
            with urllib.request.urlopen(req, timeout=15) as r:
                if r.status == 200:
                    ok_count += 1
        except Exception as e:
            log.warning("Telegram 推送失败: %s", e)
            return False
    return ok_count == len(chunks)


def main():
    log = _setup_logging()
    log.info("[%s] 开始检索: %s%s", datetime.now().strftime("%Y-%m-%d %H:%M"), SEARCH_QUERY, " (仅中文)" if CHINESE_ONLY else "")

    search_source = ""
    search_videos, channel_videos, merged = [], [], []

    # 1. 首选 YouTube API 搜索（需 YOUTUBE_API_KEY）
    if YOUTUBE_API_KEY and not USE_WEB_SEARCH:
        try:
            from search_youtube import run as api_run
            search_videos, channel_videos, merged = api_run()
            if merged:
                search_source = "YouTube API"
                log.info("使用 YouTube API 搜索")
        except Exception as e:
            log.warning("YouTube API 搜索失败: %s，将使用 DuckDuckGo 备用", e)

    # 2. 若 API 未用或失败/无结果，使用 DuckDuckGo 备用
    if not merged:
        from search_web import run as web_run
        search_videos, channel_videos, merged = web_run()
        search_source = "DuckDuckGo"
        log.info("使用 DuckDuckGo 网页搜索")
        # 若配置了 API，仍拉取订阅频道更新并合并
        if YOUTUBE_API_KEY:
            try:
                from search_youtube import fetch_channel_latest, merge_and_sort, _get_channel_ids
                channel_ids = _get_channel_ids()
                if channel_ids:
                    channel_items = fetch_channel_latest(YOUTUBE_API_KEY, channel_ids, HOURS_SINCE)
                    if channel_items:
                        merged = merge_and_sort(search_videos, channel_items)
                        channel_videos = channel_items
                        log.info("订阅频道更新 %d 条（已合并）", len(channel_items))
            except Exception as e:
                log.warning("拉取订阅频道失败: %s", e)
    elif not search_source:
        search_source = "YouTube API"

    if not merged:
        log.warning("未获取到结果")
        return

    if CHINESE_ONLY:
        merged = _filter_chinese_only(merged)
        merged = merged[: 20]  # 筛选后最多保留 20 条
        if not merged:
            log.warning("未找到中文视频")
            return

    # 按发布时间排序：越新越靠前，同天按综合得分
    merged.sort(key=lambda v: (_days_since_publish(v.get("published_at", "")), -(v.get("score", 0))))

    report = _build_report(search_videos, channel_videos, merged, search_source)
    log.info("共 %d 条", len(merged))
    print("\n" + report)

    # 保存到文件（同日期多次运行：备份旧文件后覆盖）
    Path(OUTPUT_DIR).mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    out_file = Path(OUTPUT_DIR) / f"openclaw_videos_{today}.md"
    if out_file.exists():
        prev = out_file.with_suffix(".md.prev")
        prev.write_text(out_file.read_text(encoding="utf-8"), encoding="utf-8")
    out_file.write_text(report, encoding="utf-8")
    log.info("已保存: %s", out_file)

    # Telegram 推送（自动分条，超过 4000 字符会发多条）
    if TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID:
        ok = _send_telegram(report, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, log)
        log.info("Telegram: %s", "已推送" if ok else "推送失败")
    else:
        log.info("未配置 Telegram，跳过推送")


if __name__ == "__main__":
    main()
