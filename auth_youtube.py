#!/usr/bin/env python3
"""
一次性授权：在浏览器中登录 Google 账号，获取 refresh_token
运行后请将输出的 YOUTUBE_REFRESH_TOKEN 添加到 .env
"""
import os
import sys

try:
    from google_auth_oauthlib.flow import InstalledAppFlow
except ImportError:
    print("请安装: pip install google-auth-oauthlib")
    sys.exit(1)

# 加载 .env
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

CLIENT_ID = os.environ.get("YOUTUBE_CLIENT_ID", "").strip()
CLIENT_SECRET = os.environ.get("YOUTUBE_CLIENT_SECRET", "").strip()
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]

if not CLIENT_ID or not CLIENT_SECRET:
    print("请先在 .env 中配置：")
    print("  YOUTUBE_CLIENT_ID=你的客户端ID")
    print("  YOUTUBE_CLIENT_SECRET=你的客户端密钥")
    print()
    print("获取方式：")
    print("  1. 打开 https://console.cloud.google.com/apis/credentials")
    print("  2. 创建 OAuth 2.0 客户端 ID")
    print("  3. 应用类型选「桌面应用」")
    print("  4. 创建后复制客户端 ID 和客户端密钥")
    print("  5. 在 OAuth 同意屏幕添加测试用户（你的 Google 账号）")
    sys.exit(1)

client_config = {
    "installed": {
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "redirect_uris": ["http://localhost:8080/", "http://localhost"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
    }
}

flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)
print("正在打开浏览器，请使用你的 YouTube 账号登录并授权...")
creds = flow.run_local_server(
    port=8080,
    open_browser=True,
    access_type="offline",
    prompt="consent",
)

if creds and creds.refresh_token:
    print()
    print("=" * 60)
    print("授权成功！请将下面这一行添加到 .env 文件中：")
    print()
    print(f"YOUTUBE_REFRESH_TOKEN={creds.refresh_token}")
    print()
    print("=" * 60)
else:
    print("未获取到 refresh_token，请重试并确保勾选授权所有请求的权限")
