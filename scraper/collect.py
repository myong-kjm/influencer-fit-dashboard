"""로컬에서 실행: config.json의 인스타그램 계정 목록을 수집해 data/influencers.csv 로 저장.

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

import requests

if sys.platform == "win32":
    # 콘솔 기본 인코딩(cp949)에서 한글/특수문자 출력 시 죽지 않도록 강제 UTF-8.
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scraper.instagram_public import (
    ProfileNotFound,
    RateLimited,
    fetch_profile_raw,
    parse_profile,
    sleep_between,
)

CONFIG_PATH = ROOT / "config.json"
OUT_PATH = ROOT / "data" / "influencers.csv"

FIELDNAMES = [
    "username", "full_name", "biography", "category_name",
    "is_verified", "is_business_account", "is_private",
    "followers", "posts_count", "sample_posts",
    "avg_likes", "avg_comments", "engagement_rate",
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


def collect(usernames: list[str], delay_min: float, delay_max: float) -> None:
    existing = load_existing()
    session = requests.Session()

    for i, raw_username in enumerate(usernames):
        username = raw_username.strip().lstrip("@")
        if not username:
            continue
        print(f"[{i + 1}/{len(usernames)}] @{username} 수집 중...")
        try:
            raw = fetch_profile_raw(username, session)
            row = parse_profile(username, raw)
            existing[username] = row
            print(f"  -> 팔로워 {row['followers']:,} / 인게이지먼트율 {row['engagement_rate']}%")
        except RateLimited as e:
            print(f"  [경고] {e}")
            print("  요청이 차단된 것 같습니다. 여기서 멈추고 잠시 후(가능하면 몇 시간 뒤) 다시 실행하세요.")
            break
        except ProfileNotFound as e:
            print(f"  [실패] {e}")
            existing[username] = {"username": username, "error": str(e), "collected_at": ""}
        except requests.RequestException as e:
            print(f"  [실패] 네트워크 오류: {e}")
            existing[username] = {"username": username, "error": str(e), "collected_at": ""}

        save_all(existing)  # 매 계정마다 저장 — 중간에 멈춰도 데이터 유실 없음

        if i < len(usernames) - 1:
            sleep_between(delay_min, delay_max)

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

    delay = config.get("request_delay_seconds", [8, 20])
    collect(usernames, delay[0], delay[1])


if __name__ == "__main__":
    main()
