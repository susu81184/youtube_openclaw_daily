#!/usr/bin/env python3
"""快速检查项目配置与依赖"""
import os
import sys
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

def main():
    print("=== youtube_openclaw_daily 配置检查 ===\n")
    ok = True

    # .env
    if Path(".env").exists():
        print("✅ .env 存在")
    else:
        print("❌ .env 不存在，请 cp .env.example .env 并填入配置")
        ok = False

    # API Key
    key = os.environ.get("YOUTUBE_API_KEY", "")
    if key and key != "your_api_key_here":
        print("✅ YOUTUBE_API_KEY 已配置")
    else:
        print("⚠️ YOUTUBE_API_KEY 未配置（若用 USE_WEB_SEARCH=1 可忽略）")

    # Telegram
    tok = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    cid = os.environ.get("TELEGRAM_CHAT_ID", "")
    if tok and cid:
        print("✅ Telegram 已配置（会推送）")
    else:
        print("⚠️ Telegram 未配置（仅保存到文件，不推送）")

    # USE_WEB_SEARCH
    use_web = os.environ.get("USE_WEB_SEARCH", "").lower() in ("1", "true", "yes")
    print(f"   搜索模式: {'网页(DuckDuckGo)' if use_web else 'YouTube API'}")

    # 依赖
    try:
        if use_web:
            from duckduckgo_search import DDGS
            print("✅ duckduckgo-search 已安装")
        else:
            from googleapiclient.discovery import build
            print("✅ google-api-python-client 已安装")
    except ImportError as e:
        print(f"❌ 依赖缺失: {e}")
        ok = False

    print("\n运行测试: python3 run_once.py")
    print("定时任务: 见 README 或 crontab.example")
    return 0 if ok else 1

if __name__ == "__main__":
    sys.exit(main())
