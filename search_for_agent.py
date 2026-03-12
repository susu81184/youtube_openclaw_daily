#!/usr/bin/env python3
"""供 OpenClaw/Telegram 机器人调用的视频搜索 - 仅输出 Markdown 报告到 stdout"""
import re
import sys
from datetime import datetime

from config import EFFECTIVE_SEARCH_QUERY, USE_WEB_SEARCH, CHINESE_ONLY

_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
_LATIN_RE = re.compile(r"[a-zA-Z]")


def _filter_chinese_only(items: list) -> list:
    """仅保留标题以中文为主的视频：CJK≥英文字母，或 CJK≥3 且英文字母<15"""
    out = []
    for v in items:
        title = v.get("title") or ""
        if not _CJK_RE.search(title):
            continue
        cjk = len(_CJK_RE.findall(title))
        latin = len(_LATIN_RE.findall(title))
        if cjk >= latin or (cjk >= 3 and latin < 15):
            out.append(v)
    return out


def _build_report(merged: list) -> str:
    lines = []
    lines.append(f"# OpenClaw 相关视频 - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    lines.append(f"\n按 观看·点赞·评论·更新时间 综合排序，共 {len(merged)} 条\n")
    for v in merged:
        src_tag = " [关注]" if v.get("source") == "channel" else ""
        lines.append(f"- [{v['title']}]{src_tag}")
        lines.append(f"  - {v['url']}")
        pub = (v.get("published_at") or "")[:10]
        lines.append(
            f"  - 频道: {v['channel']} | "
            f"播放: {v['view_count']} | 点赞: {v['like_count']} | 评论: {v['comment_count']} | {pub}"
        )
        lines.append("")
    return "\n".join(lines).rstrip()


def main():
    query = sys.argv[1] if len(sys.argv) > 1 else EFFECTIVE_SEARCH_QUERY
    merged = []
    if USE_WEB_SEARCH:
        from search_web import search_videos_web
        merged = search_videos_web(query=query)
    else:
        try:
            from search_youtube import run as search_run
            _, _, merged = search_run()
        except Exception:
            pass
        if not merged:
            from search_web import search_videos_web
            merged = search_videos_web(query=query)
    if not merged:
        print("未找到相关视频。")
        sys.exit(1)
    if CHINESE_ONLY:
        merged = _filter_chinese_only(merged)
    if not merged:
        print("未找到中文视频。")
        sys.exit(1)
    print(_build_report(merged))


if __name__ == "__main__":
    main()
