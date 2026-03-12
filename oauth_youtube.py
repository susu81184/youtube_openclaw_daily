#!/usr/bin/env python3
"""
YouTube OAuth 2.0：获取用户订阅的频道
需配置 YOUTUBE_CLIENT_ID、YOUTUBE_CLIENT_SECRET，首次运行 auth_youtube.py 完成授权
"""
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config import YOUTUBE_CLIENT_ID, YOUTUBE_CLIENT_SECRET, YOUTUBE_REFRESH_TOKEN

# OAuth 所需 scope
SCOPES = ["https://www.googleapis.com/auth/youtube.readonly"]


def get_credentials():
    """用 refresh_token 构造并刷新 credentials"""
    if not YOUTUBE_REFRESH_TOKEN or not YOUTUBE_CLIENT_ID or not YOUTUBE_CLIENT_SECRET:
        return None
    creds = Credentials(
        token=None,
        refresh_token=YOUTUBE_REFRESH_TOKEN,
        token_uri="https://oauth2.googleapis.com/token",
        client_id=YOUTUBE_CLIENT_ID,
        client_secret=YOUTUBE_CLIENT_SECRET,
        scopes=SCOPES,
    )
    creds.refresh(Request())
    return creds


def get_subscribed_channel_ids(creds, max_results: int = 50) -> list[str]:
    """
    获取当前登录用户订阅的频道 ID 列表
    subscriptions.list 消耗 1 单位/请求，分页时每页 1 单位
    """
    youtube = build("youtube", "v3", credentials=creds)
    channel_ids = []
    page_token = None
    while len(channel_ids) < max_results:
        try:
            resp = youtube.subscriptions().list(
                part="snippet",
                mine=True,
                maxResults=min(50, max_results - len(channel_ids)),
                pageToken=page_token or "",
            ).execute()
        except HttpError as e:
            if e.resp.status == 403:
                raise
            return channel_ids
        for item in resp.get("items", []):
            cid = item.get("snippet", {}).get("resourceId", {}).get("channelId")
            if cid:
                channel_ids.append(cid)
        page_token = resp.get("nextPageToken")
        if not page_token:
            break
    return channel_ids
