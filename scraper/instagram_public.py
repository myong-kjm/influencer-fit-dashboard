"""인스타그램 공개 프로필 정보 수집 — 로그인 없이 공개 웹 API만 사용.

주의: 자동 수집은 Instagram 이용약관상 회색 지대입니다. 로그인하지 않고,
공개된 프로필 정보만, 요청 사이 충분한 지연을 두고 소량으로만 조회하세요.
429(요청 제한) 응답을 받으면 즉시 멈추고 같은 IP로 바로 재시도하지 마세요.
"""
from __future__ import annotations

import random
import time
from datetime import datetime, timezone

import requests

WEB_PROFILE_URL = "https://www.instagram.com/api/v1/users/web_profile_info/"
APP_ID = "936619743392459"  # 인스타그램 웹 클라이언트가 쓰는 공개 앱 ID (로그인 불필요)
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


class RateLimited(Exception):
    pass


class ProfileNotFound(Exception):
    pass


def _headers() -> dict:
    return {
        "x-ig-app-id": APP_ID,
        "User-Agent": USER_AGENT,
        "Accept": "*/*",
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
    }


def fetch_profile_raw(username: str, session: requests.Session) -> dict:
    resp = session.get(
        WEB_PROFILE_URL,
        params={"username": username},
        headers=_headers(),
        timeout=15,
    )
    if resp.status_code == 429:
        raise RateLimited(f"@{username} — 요청 제한(429)에 걸렸습니다. 잠시 후 다시 시도하세요.")
    if resp.status_code == 404:
        raise ProfileNotFound(f"@{username} — 존재하지 않는 계정입니다.")
    resp.raise_for_status()
    payload = resp.json()
    user = payload.get("data", {}).get("user")
    if not user:
        raise ProfileNotFound(f"@{username} — 프로필 정보를 찾을 수 없습니다.")
    return user


def parse_profile(username: str, user: dict) -> dict:
    followers = user.get("edge_followed_by", {}).get("count") or 0
    posts_count = user.get("edge_owner_to_timeline_media", {}).get("count") or 0
    is_private = bool(user.get("is_private"))

    edges = user.get("edge_owner_to_timeline_media", {}).get("edges", [])
    recent = [e["node"] for e in edges if "node" in e][:12]

    likes = [n.get("edge_liked_by", {}).get("count") or 0 for n in recent]
    comments = [n.get("edge_media_to_comment", {}).get("count") or 0 for n in recent]
    timestamps = sorted(
        (n.get("taken_at_timestamp") for n in recent if n.get("taken_at_timestamp")),
        reverse=True,
    )

    avg_likes = round(sum(likes) / len(likes), 1) if likes else 0
    avg_comments = round(sum(comments) / len(comments), 1) if comments else 0
    engagement_rate = (
        round((avg_likes + avg_comments) / followers * 100, 2) if followers else 0.0
    )

    last_post_days_ago = ""
    avg_days_between_posts = ""
    if timestamps:
        now = datetime.now(timezone.utc).timestamp()
        last_post_days_ago = round((now - timestamps[0]) / 86400, 1)
        if len(timestamps) >= 2:
            gaps = [
                (timestamps[i] - timestamps[i + 1]) / 86400
                for i in range(len(timestamps) - 1)
            ]
            avg_days_between_posts = round(sum(gaps) / len(gaps), 1)

    return {
        "username": username,
        "full_name": user.get("full_name") or "",
        "biography": (user.get("biography") or "").replace("\n", " ").replace("\r", ""),
        "category_name": user.get("category_name") or "",
        "is_verified": bool(user.get("is_verified")),
        "is_business_account": bool(user.get("is_business_account")),
        "is_private": is_private,
        "followers": followers,
        "posts_count": posts_count,
        "sample_posts": len(recent),
        "avg_likes": avg_likes,
        "avg_comments": avg_comments,
        "engagement_rate": engagement_rate,
        "last_post_days_ago": last_post_days_ago,
        "avg_days_between_posts": avg_days_between_posts,
        "external_url": user.get("external_url") or "",
        "collected_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "error": "",
    }


def sleep_between(min_s: float, max_s: float) -> None:
    time.sleep(random.uniform(min_s, max_s))
