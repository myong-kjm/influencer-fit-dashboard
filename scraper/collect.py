"""로컬에서 실행: 본인 Chrome 로그인 세션으로 인스타그램 계정을 방문해
공개 프로필 정보를 수집하고 data/influencers.csv 로 저장한다.

⚠️ 본인 인스타그램 계정으로 로그인한 세션을 재사용합니다. 자동화 탐지 시
계정이 일시 제한될 수 있습니다 — 하루 수십 계정 이내로, 계정 사이 충분한
지연을 두고 소량으로만 사용하세요. 로그인/보안 확인 페이지로 리다이렉트되면
즉시 전체 수집을 중단합니다.

실행:
    python scraper/collect.py                 # config.json의 influencers 전체 수집
    python scraper/collect.py --add 계정아이디   # 계정 1개만 추가 수집
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scraper import browser as browser_mod
from scraper.instagram_browser import LoginWallError, ProfileFetchFailed, fetch_profile_via_browser
from scraper.instagram_public import parse_profile
from scraper.human_like import between_accounts_pause

CONFIG_PATH = ROOT / "config.json"
OUT_PATH = ROOT / "data" / "influencers.csv"

FIELDNAMES = [
    "username", "full_name", "biography", "category_name",
    "is_verified", "is_business_account", "is_private",
    "followers", "posts_count", "sample_posts",
    "avg_likes", "avg_comments", "engagement_rate",
    "avg_views", "video_sample_posts",
    "last_post_days_ago", "avg_days_between_posts",
    "external_url", "collected_at", "error",
]


def load_config() -> dict:
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def load_existing() -> dict[str, dict]:
    if not OUT_PATH.exists():
        return {}
    with OUT_PATH.open(encoding="utf-8-sig", newline="") as f:
        return {row["username"]: row for row in csv.DictReader(f)}


def save_all(rows: dict[str, dict]) -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with OUT_PATH.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        for username in sorted(rows):
            writer.writerow({k: rows[username].get(k, "") for k in FIELDNAMES})


def collect(usernames: list[str], config: dict) -> None:
    existing = load_existing()
    delay_min, delay_max = config.get("request_delay_seconds", [10, 25])

    with sync_playwright() as playwright:
        context = browser_mod.launch_context(playwright, config)
        try:
            for i, raw_username in enumerate(usernames):
                username = raw_username.strip().lstrip("@")
                if not username:
                    continue
                print(f"[{i + 1}/{len(usernames)}] @{username} 방문 중...")
                try:
                    user = fetch_profile_via_browser(context, username)
                    row = parse_profile(username, user)
                    existing[username] = row
                    print(f"  -> 팔로워 {row['followers']:,} / 인게이지먼트율 {row['engagement_rate']}%")
                except LoginWallError as e:
                    print(f"  [중단] {e}")
                    save_all(existing)
                    return
                except ProfileFetchFailed as e:
                    print(f"  [실패] {e}")
                    existing[username] = {"username": username, "error": str(e), "collected_at": ""}
                except Exception as e:
                    print(f"  [실패] 예상치 못한 오류: {e}")
                    existing[username] = {"username": username, "error": str(e), "collected_at": ""}

                save_all(existing)

                if i < len(usernames) - 1:
                    between_accounts_pause(delay_min, delay_max)
        finally:
            context.close()

    print(f"\n완료 — data/influencers.csv 에 총 {len(existing)}개 계정 저장됨")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--add", help="config.json 목록과 별개로 계정 1개만 수집 (아이디만, @ 제외)")
    args = parser.parse_args()

    config = load_config()
    if args.add:
        usernames = [args.add]
    else:
        usernames = list(config.get("influencers", []))

    collect(usernames, config)


if __name__ == "__main__":
    main()
