"""로그인된 브라우저 세션으로 인스타그램 프로필 데이터 수집.

Instagram의 비로그인 공개 API(web_profile_info)가 사실상 항상 429로 막혀서,
본인 Chrome 로그인 세션으로 프로필 페이지를 "실제로 방문"하고, 그 페이지가
자체적으로 호출하는 동일한 API 응답을 네트워크 레벨에서 가로채는 방식으로 바꿨다.
직접 API를 조립해서 호출하지 않고, 실제 페이지 방문이 만드는 트래픽만 사용한다.
"""
from __future__ import annotations

from playwright.sync_api import BrowserContext

from scraper import human_like


class LoginWallError(Exception):
    """로그인/체크포인트 페이지로 리다이렉트됨 — 계정 보호를 위해 즉시 중단해야 함."""


class ProfileFetchFailed(Exception):
    pass


def fetch_profile_via_browser(context: BrowserContext, username: str, timeout_ms: int = 25000) -> dict:
    page = context.new_page()
    captured: dict = {"user": None}

    def handle_response(response) -> None:
        if captured["user"] is not None:
            return
        if "web_profile_info" not in response.url:
            return
        try:
            payload = response.json()
        except Exception:
            return
        user = (payload or {}).get("data", {}).get("user")
        if user and str(user.get("username", "")).lower() == username.lower():
            captured["user"] = user

    page.on("response", handle_response)
    try:
        page.goto(f"https://www.instagram.com/{username}/", wait_until="load", timeout=timeout_ms)
        human_like.page_load_pause()

        if "accounts/login" in page.url or "challenge" in page.url:
            raise LoginWallError(
                f"@{username} — 로그인/보안 확인 페이지로 리다이렉트됨. "
                "계정 보호를 위해 전체 수집을 즉시 중단합니다."
            )

        human_like.wiggle_mouse(page)
        human_like.smooth_scroll(page, target_pixels=400)
        page.wait_for_timeout(1200)
    finally:
        page.close()

    if captured["user"] is None:
        raise ProfileFetchFailed(
            f"@{username} — 프로필 데이터를 가져오지 못했습니다 "
            "(존재하지 않는 계정이거나, 비공개 계정이거나, 응답 캡처 실패)"
        )
    return captured["user"]
