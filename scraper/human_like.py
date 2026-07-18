"""봇 회피 — 사람형 행동 시뮬레이션 유틸.

핵심 원칙:
- 절대 0초로 즉시 행동 X
- 스크롤은 부드럽게, 가끔 위로
- 마우스는 페이지 진입 후 한 번 움직여줌
"""
from __future__ import annotations

import random
import time
from playwright.sync_api import Page


def sleep(min_s: float, max_s: float) -> None:
    time.sleep(random.uniform(min_s, max_s))


def wiggle_mouse(page: Page) -> None:
    try:
        viewport = page.viewport_size or {"width": 1280, "height": 800}
        x = random.randint(100, viewport["width"] - 100)
        y = random.randint(100, viewport["height"] - 100)
        page.mouse.move(x, y, steps=random.randint(10, 25))
    except Exception:
        pass


def smooth_scroll(page: Page, target_pixels: int = 500) -> None:
    chunks = random.randint(3, 6)
    chunk_size = target_pixels // chunks
    for _ in range(chunks):
        delta = chunk_size + random.randint(-30, 30)
        try:
            page.evaluate(f"window.scrollBy(0, {delta})")
        except Exception:
            page.mouse.wheel(0, delta)
        time.sleep(random.uniform(0.2, 0.4))


def page_load_pause() -> None:
    sleep(2.5, 5.5)


def between_accounts_pause(min_s: int, max_s: int) -> None:
    delay = random.uniform(min_s, max_s)
    print(f"  -> 다음 계정까지 {delay:.0f}초 휴식 (봇 감지 회피)")
    time.sleep(delay)
