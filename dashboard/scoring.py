"""핏 스코어 계산 — 브랜드 키워드/팔로워 구간을 기준으로 인플루언서를 점수화한다.

가중치: 인게이지먼트율 50% + 키워드 매칭 25% + 게시 활발도 15% + 팔로워구간 적합 10%.
숫자를 직접 만지지 말고, 여기 상수만 바꿔서 기준을 조정하면 된다.
"""
from __future__ import annotations

import math

TIERS: list[tuple[str, int, float]] = [
    ("나노", 1_000, 10_000),
    ("마이크로", 10_000, 100_000),
    ("매크로", 100_000, 1_000_000),
    ("메가", 1_000_000, math.inf),
]

TIER_ORDER = [t[0] for t in TIERS]

# 인게이지먼트율(%) 만점 기준. 인스타그램 업계 평균은 1~3%대라 8%를 만점으로 잡는다.
ENGAGEMENT_RATE_FOR_FULL_SCORE = 8.0


def follower_tier(followers: int) -> str:
    if followers < TIERS[0][1]:
        return "1천 미만"
    for name, low, high in TIERS:
        if low <= followers < high:
            return name
    return "메가"


def matched_keywords(bio: str, category: str, keywords: list[str]) -> list[str]:
    text = f"{bio or ''} {category or ''}".lower()
    return [kw for kw in keywords if kw.strip() and kw.strip().lower() in text]


def activity_label(avg_days_between_posts: float | None) -> str:
    if avg_days_between_posts is None or avg_days_between_posts == "":
        return "정보 없음"
    days = float(avg_days_between_posts)
    if days <= 3:
        return "매우 활발"
    if days <= 7:
        return "활발"
    if days <= 14:
        return "보통"
    return "저조"


def _clamp(value: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, value))


def fit_score(
    engagement_rate: float,
    matched_kw_count: int,
    avg_days_between_posts,
    tier_target: set[str] | None,
    tier: str,
) -> float:
    engagement_score = _clamp(engagement_rate / ENGAGEMENT_RATE_FOR_FULL_SCORE * 100)
    keyword_score = _clamp(matched_kw_count * 50)  # 키워드 2개 이상 매칭 시 만점

    if avg_days_between_posts is None or avg_days_between_posts == "":
        activity_score = 30.0
    else:
        activity_score = _clamp(100 - (float(avg_days_between_posts) - 3) * 8)

    if not tier_target:
        tier_score = 70.0
    else:
        tier_score = 100.0 if tier in tier_target else 30.0

    return round(
        engagement_score * 0.50
        + keyword_score * 0.25
        + activity_score * 0.15
        + tier_score * 0.10,
        1,
    )
