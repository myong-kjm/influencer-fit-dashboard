"""인플루언서 인게이지먼트 핏 분석 대시보드 — Streamlit.

실행: streamlit run dashboard/app.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from dashboard import scoring

DATA_PATH = ROOT / "data" / "influencers.csv"
CONFIG_PATH = ROOT / "config.json"

CONTACT_OPTIONS = ["컨택예정", "컨택완료", "미진행"]

# 클라우드(Streamlit Community Cloud)에서는 계정 추가/수집을 막고 조회만 허용한다.
# 이유: Instagram이 클라우드 공용 IP 대역을 훨씬 빨리 차단하고, 여러 사람이
# 동시에 실행하면 순식간에 요청 제한에 걸리기 때문 — 수집은 항상 로컬에서.
IS_CLOUD = Path("/mount/src").exists()

# dataviz 스킬 검증 팔레트의 첫 4개 카테고리컬 슬롯 (라이트 모드 기준)
TIER_COLORS = {
    "나노": "#2a78d6",
    "마이크로": "#008300",
    "매크로": "#e87ba4",
    "메가": "#eda100",
    "1천 미만": "#898781",
}

st.set_page_config(
    page_title="인플루언서 핏 분석",
    page_icon="🎯",
    layout="wide",
)

st.markdown(
    """
    <style>
    @import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.css');

    /* ============================================================
       디자인 토큰 — 8px 그리드 기준 간격, 반경, 색상
       ============================================================ */
    :root {
        --sp-1: 8px;  --sp-2: 16px; --sp-3: 24px; --sp-4: 32px; --sp-5: 40px; --sp-6: 48px;
        --radius-card: 20px;
        --radius-control: 10px;
        --border-color: #EFE6D8;
        --ink-primary: #1a1a1a;
        --ink-secondary: #6b6459;
        --ink-muted: #8f8879;
        --surface-card: #ffffff;
        --surface-page: #F7F1E8;
        --accent: #E85D8E;
        --accent-tint: #FCE9F0;
        --accent-tint-border: #F3C2D6;
        --shadow-card: 0 2px 10px rgba(120, 90, 60, 0.08);
    }

    html, body { font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif !important; }

    /* ============================================================
       레이아웃 기본 골격 — 페이지/사이드바 여백을 8px 그리드로 통일
       ============================================================ */
    .block-container {
        padding: var(--sp-5) var(--sp-6) var(--sp-6) !important;
        max-width: 1280px;
    }
    [data-testid="stSidebar"] { min-width: 336px; }
    [data-testid="stSidebarUserContent"] {
        padding: var(--sp-4) var(--sp-3) var(--sp-4) !important;
    }
    [data-testid="stSidebarUserContent"] [data-testid="stVerticalBlock"] {
        gap: var(--sp-3) !important;
    }
    [data-testid="stMain"] [data-testid="stVerticalBlock"] { gap: var(--sp-2) !important; }

    [data-testid="stMain"], section.main,
    [data-testid="stAppViewContainer"] > .main,
    [data-testid="stHeader"] { background: var(--surface-page) !important; }
    [data-testid="stSidebar"] { background: var(--surface-card) !important; border-right: 1px solid var(--border-color); }

    [data-testid="stMain"] h1, [data-testid="stMain"] h2, [data-testid="stMain"] h3,
    [data-testid="stMain"] h4,
    [data-testid="stMain"] [data-testid="stMarkdownContainer"] p,
    [data-testid="stMain"] [data-testid="stMetricLabel"],
    [data-testid="stMain"] [data-testid="stMetricValue"],
    [data-testid="stMain"] [data-baseweb="tab"] > div { color: var(--ink-primary) !important; }
    [data-testid="stMain"] [data-testid="stCaptionContainer"],
    [data-testid="stSidebar"] [data-testid="stCaptionContainer"] { color: var(--ink-secondary) !important; }

    /* ============================================================
       타이포그래피 계층 — 페이지 타이틀 / 섹션 타이틀 / 패널 라벨
       ============================================================ */
    [data-testid="stMain"] h1, [data-testid="stSidebar"] h1 {
        font-family: 'Pretendard', -apple-system, sans-serif !important;
        font-weight: 800 !important; letter-spacing: -0.5px;
    }
    [data-testid="stMain"] h1 { margin-bottom: 4px !important; }
    .page-subtitle { color: var(--ink-secondary); font-size: 0.92rem; margin: 0 0 var(--sp-4) 0; }
    .section-title {
        font-weight: 700; font-size: 1.05rem; color: var(--ink-primary);
        margin: 0 0 var(--sp-2) 0; letter-spacing: -0.2px;
    }
    .panel-label {
        font-weight: 700; font-size: 0.78rem; letter-spacing: 0.3px;
        color: var(--ink-muted); text-transform: uppercase;
        margin: 0 0 var(--sp-1) 0;
    }
    .panel-label-accent { color: var(--accent); }

    /* 사이드바 헤더 — 메인 타이틀(대시보드)과 동일한 폰트 크기 */
    .sidebar-brand { display: flex; align-items: flex-start; gap: 8px; margin-bottom: 2px; }
    .sidebar-brand-emoji { font-size: 1.3rem; line-height: 1.2; padding-top: 4px; }
    [data-testid="stSidebar"] .sidebar-title {
        margin: 0; font-family: 'Pretendard', -apple-system, sans-serif;
        font-weight: 800; font-size: 44px; line-height: 1.15;
        letter-spacing: -1px; color: var(--ink-primary);
        word-break: keep-all; overflow-wrap: normal;
    }
    .sidebar-subtitle {
        color: var(--ink-secondary); font-size: 0.86rem; line-height: 1.5;
        margin: var(--sp-1) 0 0 0;
    }

    /* ============================================================
       버튼 — 크기/반경/두께 통일 (탭 버튼은 제외)
       ============================================================ */
    [data-testid="stMain"] button:not([role="tab"]),
    [data-testid="stSidebar"] button {
        border-radius: var(--radius-control) !important;
        font-weight: 600 !important;
        min-height: 40px;
    }
    [data-testid="stMain"] button:not([role="tab"]),
    [data-testid="stMain"] button:not([role="tab"]) * { color: #fafafa !important; }
    [data-testid="stMain"] [data-testid="stExpander"] [data-testid="stButton"] button,
    [data-testid="stMain"] [data-testid="stExpander"] [data-testid="stButton"] button * { color: #212121 !important; }
    [data-testid="stHeader"] a, [data-testid="stHeader"] span, [data-testid="stHeader"] button {
        color: var(--ink-primary) !important;
    }

    /* ============================================================
       입력 요소 — text_input / selectbox / multiselect / slider 반경 통일
       ============================================================ */
    [data-testid="stTextInput"] input,
    [data-testid="stSelectbox"] div[data-baseweb="select"] > div,
    [data-testid="stMultiSelect"] div[data-baseweb="select"] > div {
        border-radius: var(--radius-control) !important;
        min-height: 40px !important;
    }

    /* ============================================================
       카드형 컨테이너 (st.container(border=True, key=...)) — 그룹 구분을 명확하게
       Streamlit이 border/key 스타일을 stVerticalBlock 자체에 적용하므로 그걸 직접 타겟팅
       ============================================================ */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"][class*="st-key-"] {
        border-radius: var(--radius-card) !important;
        border: none !important;
        background: var(--surface-page) !important;
        box-shadow: var(--shadow-card);
        padding: var(--sp-3) !important;
        gap: var(--sp-2) !important;
    }
    [data-testid="stSidebar"] [data-testid="stExpander"] { border-radius: var(--radius-card) !important; }

    /* 메인 영역의 카드형 컨테이너 (상세 프로필 등) — 흰 배경으로 페이지와 구분 */
    [data-testid="stMain"] [data-testid="stVerticalBlock"][class*="st-key-"] {
        border-radius: var(--radius-card) !important;
        border: none !important;
        background: var(--surface-card) !important;
        box-shadow: var(--shadow-card);
        padding: var(--sp-4) !important;
        gap: var(--sp-2) !important;
    }

    /* "계정 추가" 패널 강조 — 이 앱에서 유일한 데이터 입력 지점 */
    [data-testid="stSidebar"] [data-testid="stVerticalBlock"].st-key-add-account-panel {
        background: var(--accent-tint) !important;
        box-shadow: none !important;
        border: 1.5px solid var(--accent-tint-border) !important;
    }

    /* ============================================================
       지표 카드 (st.metric) — 패딩/반경 통일, 그림자 기반 카드
       ============================================================ */
    [data-testid="stMain"] [data-testid="stMetric"] {
        background: var(--surface-card); border: none;
        border-radius: var(--radius-card);
        padding: var(--sp-4); box-shadow: var(--shadow-card);
    }
    div[data-testid="stMetricValue"] { font-size: 1.6rem; }
    [data-testid="stMain"] [data-testid="stVerticalBlock"][class*="st-key-"] div[data-testid="stMetricValue"] {
        font-size: 1.35rem;
    }
    [data-testid="stMain"] [data-testid="stMetric"] [data-testid="stMetricLabel"] {
        color: var(--ink-secondary) !important; font-size: 0.84rem; font-weight: 600;
    }
    [data-testid="stMain"] [data-testid="stMetric"] [data-testid="stMetricValue"] {
        color: #111 !important; font-weight: 800;
    }

    /* ============================================================
       탭 — 세그먼트 필(pill) 컨트롤 스타일
       ============================================================ */
    [data-testid="stMain"] [data-baseweb="tab-list"] {
        background: #EFE6D8 !important; border-bottom: none !important;
        border-radius: var(--radius-control) !important;
        padding: 4px !important; gap: 4px !important; display: inline-flex !important;
    }
    [data-testid="stMain"] button[role="tab"], [data-testid="stMain"] button[role="tab"] *,
    [data-testid="stMain"] [data-baseweb="tab-list"] button,
    [data-testid="stMain"] [data-baseweb="tab-list"] button * {
        color: var(--ink-muted) !important; font-size: 0.92rem !important; font-weight: 700 !important;
    }
    [data-testid="stMain"] [data-baseweb="tab-list"] button {
        border-radius: 7px !important; height: 38px !important;
    }
    [data-testid="stMain"] button[role="tab"][aria-selected="true"] {
        background: var(--surface-card) !important; box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
    }
    [data-testid="stMain"] button[role="tab"][aria-selected="true"],
    [data-testid="stMain"] button[role="tab"][aria-selected="true"] * { color: var(--ink-primary) !important; }
    [data-testid="stMain"] [data-baseweb="tab-highlight"] { display: none !important; }
    [data-testid="stMain"] [data-baseweb="tab-border"] { display: none !important; }
    [data-testid="stMain"] [data-baseweb="tab-panel"] { padding-top: var(--sp-3) !important; }

    /* ============================================================
       데이터 테이블/카드 컨테이너 — 그림자 기반, 테두리 없이
       ============================================================ */
    [data-testid="stDataFrame"], [data-testid="stDataEditor"] {
        border-radius: var(--radius-card) !important; overflow: hidden;
        border: none !important; box-shadow: var(--shadow-card);
    }
    [data-testid="stExpander"] {
        border-radius: var(--radius-card) !important; border: none !important;
        box-shadow: var(--shadow-card);
    }

    /* ============================================================
       매칭 키워드 — 알약(pill) 배지 스타일
       ============================================================ */
    .kw-pill {
        display: inline-block; background: var(--accent-tint); color: #A83E6C;
        border-radius: 999px; padding: 4px 12px; font-size: 0.8rem; font-weight: 700;
        margin: 0 6px 6px 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return {"brand_keywords": [], "influencers": [], "request_delay_seconds": [8, 20]}
    return json.loads(CONFIG_PATH.read_text(encoding="utf-8"))


def save_config(config: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")


def load_data() -> pd.DataFrame:
    if not DATA_PATH.exists():
        return pd.DataFrame()
    df = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
    if df.empty:
        return df
    for col in ["followers", "posts_count", "avg_likes", "avg_comments", "engagement_rate"]:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    for col in ["last_post_days_ago", "avg_days_between_posts", "avg_views", "video_sample_posts"]:
        if col not in df.columns:
            df[col] = pd.NA
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df["biography"] = df.get("biography", "").fillna("")
    df["category_name"] = df.get("category_name", "").fillna("")
    df["error"] = df.get("error", "").fillna("")

    if "contact_status" not in df.columns:
        df["contact_status"] = ""
    df["contact_status"] = df["contact_status"].fillna("")
    df.loc[~df["contact_status"].isin(CONTACT_OPTIONS), "contact_status"] = "미진행"
    return df


def save_contact_status(username: str, status: str) -> None:
    if not DATA_PATH.exists():
        return
    raw = pd.read_csv(DATA_PATH, encoding="utf-8-sig")
    if "contact_status" not in raw.columns:
        raw["contact_status"] = ""
    raw.loc[raw["username"] == username, "contact_status"] = status
    raw.to_csv(DATA_PATH, index=False, encoding="utf-8-sig")


def enrich(df: pd.DataFrame, keywords: list[str]) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["tier"] = df["followers"].apply(scoring.follower_tier)
    df["matched_keywords"] = df.apply(
        lambda r: scoring.matched_keywords(r["biography"], r["category_name"], keywords), axis=1
    )
    df["matched_keywords_str"] = df["matched_keywords"].apply(lambda ks: ", ".join(ks) if ks else "-")
    df["activity"] = df["avg_days_between_posts"].apply(
        lambda v: scoring.activity_label(None if pd.isna(v) else v)
    )
    return df


def apply_score(df: pd.DataFrame, tier_target: set[str]) -> pd.DataFrame:
    if df.empty:
        return df
    df = df.copy()
    df["fit_score"] = df.apply(
        lambda r: scoring.fit_score(
            engagement_rate=r["engagement_rate"],
            matched_kw_count=len(r["matched_keywords"]),
            avg_days_between_posts=None if pd.isna(r["avg_days_between_posts"]) else r["avg_days_between_posts"],
            tier_target=tier_target,
            tier=r["tier"],
        ),
        axis=1,
    )
    return df


@st.dialog("계정 수집 중")
def run_collect_dialog(cmd: list[str]) -> None:
    st.markdown("### ⏳ 로그인 세션으로 프로필을 방문하고 있어요")
    st.caption("Chrome 창이 따로 뜨고, 계정 사이 10~25초씩 쉽니다. 창을 닫지 말고 기다려주세요.")
    log_box = st.empty()
    lines: list[str] = []
    rc = -1
    try:
        proc = subprocess.Popen(
            cmd, cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, encoding="utf-8", errors="replace", bufsize=1,
        )
        for line in proc.stdout:  # type: ignore[union-attr]
            lines.append(line.rstrip())
            log_box.code("\n".join(lines[-20:]))
        rc = proc.wait()
    except Exception as e:
        st.error(f"실행 실패: {e}")

    joined = "\n".join(lines)
    if rc == 0 and "완료" in joined:
        st.success("수집 완료 — 목록이 갱신됐어요")
    else:
        st.warning("수집이 중간에 멈췄을 수 있어요. 로그를 확인하세요. (요청 제한이면 몇 시간 후 재시도)")

    if st.button("닫고 새로고침", type="primary", width="stretch"):
        st.session_state._collect_cmd = None
        st.rerun(scope="app")


config = load_config()

if "_collect_cmd" not in st.session_state:
    st.session_state._collect_cmd = None

with st.sidebar:
    st.markdown(
        '<div class="sidebar-brand">'
        '<span class="sidebar-brand-emoji">💛</span>'
        '<span class="sidebar-title">IG 계정 분석기</span>'
        '</div>',
        unsafe_allow_html=True,
    )

    with st.container(border=True, key="kw-panel"):
        st.markdown('<p class="panel-label">브랜드 키워드</p>', unsafe_allow_html=True)
        kw_input = st.text_input(
            "쉼표로 구분해서 입력",
            value=", ".join(config.get("brand_keywords", [])),
            label_visibility="collapsed",
            help="계정 소개글(bio)·카테고리에 이 단어가 있으면 핏 스코어가 올라가요",
        )
        keywords = [k.strip() for k in kw_input.split(",") if k.strip()]
        if keywords != config.get("brand_keywords", []):
            config["brand_keywords"] = keywords
            save_config(config)

    with st.container(border=True, key="filter-panel"):
        st.markdown('<p class="panel-label">필터 &amp; 정렬</p>', unsafe_allow_html=True)
        tier_target = set(
            st.multiselect(
                "팔로워 구간 (타겟)",
                options=scoring.TIER_ORDER,
                default=[],
                help="비워두면 전체 구간을 동일하게 취급해요. 선택하면 그 구간에 가산점을 줘요.",
            )
        )
        min_engagement = st.slider("최소 인게이지먼트율 (%)", 0.0, 15.0, 0.0, 0.1)
        sort_by = st.selectbox("정렬 기준", ["핏 스코어", "인게이지먼트율", "팔로워 수"])

    with st.container(border=True, key="add-account-panel"):
        st.markdown('<p class="panel-label panel-label-accent">➕ 새 계정 추가</p>', unsafe_allow_html=True)
        if IS_CLOUD:
            st.info("☁️ 클라우드에서는 조회만 가능해요. 계정 추가·수집은 로컬 PC에서 실행한 뒤 PUSH-Update.bat으로 반영하세요.")
        else:
            new_handle = st.text_input(
                "인스타그램 아이디", key="new_handle_input",
                placeholder="예: nike (@ 제외)", label_visibility="collapsed",
            )
            if st.button("➕ 추가 + 지금 수집", type="primary", width="stretch"):
                handle = new_handle.strip().lstrip("@")
                if not handle:
                    st.error("아이디를 입력해주세요.")
                else:
                    if handle not in config.get("influencers", []):
                        config.setdefault("influencers", []).append(handle)
                        save_config(config)
                    cmd = [sys.executable, str(ROOT / "scraper" / "collect.py"), "--add", handle]
                    st.session_state._collect_cmd = cmd
                    st.rerun()
            st.caption("⚠️ 본인 인스타그램 로그인 세션으로 프로필을 방문해 수집합니다. 너무 자주/많이 돌리면 계정이 일시 제한될 수 있어요 — 소량으로만 사용하세요.")

if st.session_state._collect_cmd is not None:
    run_collect_dialog(st.session_state._collect_cmd)

raw_df = load_data()

st.title("대시보드")
st.markdown('<p class="page-subtitle">수집된 인스타그램 계정을 브랜드 핏 기준으로 분석합니다.</p>', unsafe_allow_html=True)

if raw_df.empty:
    st.info(
        "아직 수집된 데이터가 없어요. "
        + ("로컬에서 `python scraper/collect.py` 를 실행하거나 " if not IS_CLOUD else "")
        + "왼쪽에서 계정을 추가해 수집을 시작하세요."
    )
    st.stop()

df = enrich(raw_df, keywords)
df = apply_score(df, tier_target)

valid_df = df[df["error"] == ""].copy()
filtered = valid_df[valid_df["engagement_rate"] >= min_engagement]
if tier_target:
    pass  # 팔로워 구간은 필터가 아니라 가산점으로만 반영 (완전히 배제하지 않음)

sort_col = {"핏 스코어": "fit_score", "인게이지먼트율": "engagement_rate", "팔로워 수": "followers"}[sort_by]
filtered = filtered.sort_values(sort_col, ascending=False)

st.markdown('<p class="section-title">요약</p>', unsafe_allow_html=True)
c1, c2, c3, c4 = st.columns(4)
c1.metric("분석 계정", f"{len(valid_df)}개")
c2.metric("평균 인게이지먼트율", f"{valid_df['engagement_rate'].mean():.2f}%" if len(valid_df) else "0%")
c3.metric("키워드 매칭 계정", f"{(valid_df['matched_keywords'].apply(len) > 0).sum()}개")
c4.metric("활발 게시 계정", f"{valid_df['activity'].isin(['매우 활발', '활발']).sum()}개")

if "dismissed_errors" not in st.session_state:
    st.session_state.dismissed_errors = set()

failed = df[(df["error"] != "") & (~df["username"].isin(st.session_state.dismissed_errors))]
if not failed.empty:
    with st.expander(f"⚠️ 수집 실패 {len(failed)}건"):
        for _, row in failed.iterrows():
            col_user, col_err, col_btn = st.columns([1.2, 4.5, 0.5])
            with col_user:
                st.write(f"**{row['username']}**")
            with col_err:
                st.caption(row["error"])
            with col_btn:
                if st.button("확인", key=f"dismiss_{row['username']}", width="content"):
                    st.session_state.dismissed_errors.add(row["username"])
                    st.rerun()

st.divider()

st.markdown('<p class="section-title">분석 결과</p>', unsafe_allow_html=True)
tab_rank, tab_chart, tab_detail = st.tabs(["🏆 순위", "📊 인게이지먼트 분포", "👤 상세 프로필"])

with tab_rank:
    if filtered.empty:
        st.info("조건에 맞는 계정이 없어요. 필터를 완화해보세요.")
    else:
        table = filtered[[
            "username", "followers", "tier", "engagement_rate", "avg_views",
            "matched_keywords_str", "activity", "fit_score", "contact_status",
        ]].copy()
        table["프로필"] = "https://instagram.com/" + filtered["username"]
        table = table.rename(columns={
            "username": "계정", "followers": "팔로워", "tier": "구간",
            "engagement_rate": "인게이지먼트율(%)", "avg_views": "평균 조회수",
            "matched_keywords_str": "매칭 키워드",
            "activity": "게시 활발도", "fit_score": "핏 스코어",
            "contact_status": "컨택여부",
        })
        edited_table = st.data_editor(
            table, width="stretch", height=460, hide_index=True,
            disabled=[c for c in table.columns if c != "컨택여부"],
            column_config={
                "핏 스코어": st.column_config.ProgressColumn("핏 스코어", min_value=0, max_value=100, format="%.1f"),
                "팔로워": st.column_config.NumberColumn("팔로워", format="%d"),
                "평균 조회수": st.column_config.NumberColumn("평균 조회수", format="%d", help="최근 영상(릴스) 게시물 기준 · 참고용, 인게이지먼트율 계산에는 미포함"),
                "프로필": st.column_config.LinkColumn("프로필", display_text="🔗 인스타 열기"),
                "컨택여부": st.column_config.SelectboxColumn("컨택여부", options=CONTACT_OPTIONS, required=True),
            },
            key="rank_table_editor",
        )
        changed = edited_table[edited_table["컨택여부"] != table["컨택여부"]]
        if not changed.empty:
            for _, r in changed.iterrows():
                save_contact_status(r["계정"], r["컨택여부"])
            st.rerun()

        st.download_button(
            "⬇️ 현재 목록 CSV로 내려받기 (컨택 후보 리스트)",
            data=edited_table.to_csv(index=False).encode("utf-8-sig"),
            file_name="influencer_shortlist.csv",
            mime="text/csv",
            type="primary",
        )

with tab_chart:
    if filtered.empty:
        st.info("표시할 데이터가 없어요.")
    else:
        with st.container(border=True, key="scatter-card"):
            scatter = px.scatter(
                valid_df, x="followers", y="engagement_rate", color="tier",
                size="fit_score" if "fit_score" in valid_df.columns else None,
                hover_data={"username": True, "biography": True, "followers": ":,", "engagement_rate": ":.2f"},
                color_discrete_map=TIER_COLORS,
                log_x=True,
                labels={"followers": "팔로워 수 (로그 스케일)", "engagement_rate": "인게이지먼트율 (%)", "tier": "구간"},
            )
            scatter.update_layout(
                plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
                font=dict(family="Pretendard, sans-serif", color="#1a1a1a"),
                legend=dict(orientation="h", yanchor="bottom", y=1.02),
                margin=dict(t=20, r=20),
            )
            scatter.update_xaxes(gridcolor="#EFE6D8")
            scatter.update_yaxes(gridcolor="#EFE6D8")
            st.plotly_chart(scatter, width="stretch")

        with st.container(border=True, key="hist-card"):
            hist = px.histogram(
                valid_df, x="engagement_rate", nbins=20,
                labels={"engagement_rate": "인게이지먼트율 (%)"},
                color_discrete_sequence=["#E85D8E"],
            )
            hist.update_layout(
                plot_bgcolor="#ffffff", paper_bgcolor="#ffffff",
                font=dict(family="Pretendard, sans-serif", color="#1a1a1a"),
                margin=dict(t=20, r=20),
            )
            hist.update_xaxes(gridcolor="#EFE6D8")
            hist.update_yaxes(gridcolor="#EFE6D8", title="계정 수")
            st.plotly_chart(hist, width="stretch")

with tab_detail:
    if valid_df.empty:
        st.info("표시할 데이터가 없어요.")
    else:
        pick = st.selectbox("계정 선택", options=valid_df["username"].tolist())
        row = valid_df[valid_df["username"] == pick].iloc[0]

        col_a, col_b = st.columns([1, 1.3], gap="medium")
        with col_a:
            with st.container(border=True, key="profile-card"):
                st.markdown(f"### @{row['username']}")
                if row.get("full_name"):
                    st.caption(row["full_name"])
                if row.get("is_verified"):
                    st.markdown("✅ 인증 계정")
                st.link_button("📷 인스타그램에서 열기", f"https://instagram.com/{row['username']}", width="stretch")

                m1, m2 = st.columns(2)
                m1.metric("팔로워", f"{int(row['followers']):,}")
                m2.metric("구간", row["tier"])
                m3, m4 = st.columns(2)
                m3.metric("인게이지먼트율", f"{row['engagement_rate']:.2f}%")
                m4.metric("핏 스코어", f"{row['fit_score']:.1f}")

        with col_b:
            with st.container(border=True, key="detail-card"):
                st.markdown('<p class="panel-label">소개(BIO)</p>', unsafe_allow_html=True)
                st.write(row["biography"] or "_(비어 있음)_")
                if row.get("category_name"):
                    st.caption(f"카테고리: {row['category_name']}")

                kws = row["matched_keywords"]
                if kws:
                    st.markdown('<p class="panel-label">매칭된 브랜드 키워드</p>', unsafe_allow_html=True)
                    st.markdown(" ".join(f'<span class="kw-pill">{k}</span>' for k in kws), unsafe_allow_html=True)

                st.markdown('<p class="panel-label">최근 게시물 기준 평균</p>', unsafe_allow_html=True)
                st.write(f"좋아요 {row['avg_likes']:,.0f}회 · 댓글 {row['avg_comments']:,.0f}개  ({int(row['sample_posts'])}개 게시물 기준)")
                avg_views = row["avg_views"]
                video_n = row["video_sample_posts"]
                if pd.isna(avg_views):
                    st.caption("평균 조회수: 정보 없음 (최근 게시물 중 영상이 없음)")
                else:
                    st.caption(f"평균 조회수 {avg_views:,.0f}회  (영상 게시물 {int(video_n)}개 기준 · 참고용, 인게이지먼트율 계산에는 미포함)")

                st.markdown('<p class="panel-label">게시 활발도</p>', unsafe_allow_html=True)
                st.write(row["activity"])
                last_post = row["last_post_days_ago"]
                avg_gap = row["avg_days_between_posts"]
                act1, act2 = st.columns(2)
                act1.metric("최근 업로드", "정보 없음" if pd.isna(last_post) else f"{last_post:.1f}일 전")
                act2.metric("평균 업로드 주기", "정보 없음" if pd.isna(avg_gap) else f"{avg_gap:.1f}일마다")
