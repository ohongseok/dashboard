import io
import re
import time
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

# ─────────────────────────────────────────────────────────────
# 0. PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="1P Ops Intelligence",
    page_icon="⬛",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700;800;900&display=swap');

html, body, [class*="css"], [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

*, *::before, *::after {
    box-sizing: border-box;
}

html, body, .main, .stApp, [data-testid="stAppViewContainer"] {
    background: #f5f5f7 !important;
    color: #111111 !important;
}

.block-container {
    max-width: 100% !important;
    padding: 0 28px 48px 28px !important;
}

/* ━━━ 공통 텍스트 / 레이아웃 ━━━ */
h1, h2, h3, h4, h5, h6, p, span, label, div {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

[data-testid="stMarkdownContainer"] p,
[data-testid="stMarkdownContainer"] li,
[data-testid="stText"] {
    color: #111111 !important;
}

/* ━━━ 사이드바 ━━━ */
[data-testid="stSidebar"] {
    background: #111111 !important;
    border-right: 1px solid #222222 !important;
    min-width: 260px !important;
}
[data-testid="stSidebar"] > div {
    padding-top: 0 !important;
}
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] {
    color: #d6d6d6 !important;
}
[data-testid="stSidebar"] .stButton > button {
    background: #d4ff00 !important;
    color: #111111 !important;
    border: none !important;
    border-radius: 10px !important;
    font-weight: 800 !important;
    font-size: 13px !important;
    height: 44px !important;
    width: 100% !important;
    transition: all .15s ease !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #c3eb00 !important;
}
[data-testid="stSidebar"] [data-baseweb="tag"] {
    background: #2a2a2a !important;
    color: #ffffff !important;
    border: 1px solid #3a3a3a !important;
}

/* 입력창 / 멀티셀렉트 / 셀렉트 */
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] textarea,
[data-testid="stSidebar"] [data-baseweb="input"] > div,
[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] [data-baseweb="base-input"] {
    background: #1a1a1a !important;
    color: #ffffff !important;
    border: 1px solid #333333 !important;
}
[data-testid="stSidebar"] input::placeholder {
    color: #8d8d8d !important;
}
[data-testid="stSidebar"] svg {
    fill: #dddddd !important;
}

/* 드롭다운 펼쳤을 때 텍스트 안보이는 문제 대응 */
div[role="listbox"],
ul[role="listbox"] {
    background: #1a1a1a !important;
    border: 1px solid #333333 !important;
}
div[role="option"],
li[role="option"] {
    background: #1a1a1a !important;
    color: #ffffff !important;
}
div[role="option"]:hover,
li[role="option"]:hover {
    background: #262626 !important;
}
[data-baseweb="popover"] *,
[data-baseweb="select"] *,
[data-baseweb="menu"] * {
    color: inherit !important;
}

/* ━━━ 상단 바 ━━━ */
.topbar {
    background: #111111;
    margin: 0 -28px 28px -28px;
    padding: 0 28px;
    min-height: 64px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
}
.topbar-logo {
    font-size: 19px;
    font-weight: 900;
    color: #ffffff;
    letter-spacing: -0.4px;
}
.topbar-logo span {
    color: #d4ff00;
}
.topbar-right {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
}
.topbar-src {
    font-size: 11px;
    color: #a5a5a5;
    font-weight: 600;
}
.live-chip {
    background: #d4ff00;
    color: #111111;
    font-size: 10px;
    font-weight: 900;
    letter-spacing: 1.4px;
    padding: 5px 11px;
    border-radius: 999px;
}

/* ━━━ 섹션 타이틀 ━━━ */
.sec {
    font-size: 11px;
    font-weight: 900;
    letter-spacing: 1.8px;
    text-transform: uppercase;
    color: #111111;
    margin: 32px 0 16px 0;
    display: flex;
    align-items: center;
    gap: 10px;
}
.sec::after {
    content: '';
    flex: 1;
    height: 1px;
    background: #dddddd;
}

/* ━━━ KPI 카드 ━━━ */
.kcard {
    background: #ffffff;
    border-radius: 16px;
    border: 1px solid #e8e8e8;
    padding: 22px 20px 18px;
    position: relative;
    overflow: hidden;
    transition: box-shadow .2s ease, transform .2s ease;
    min-height: 136px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
}
.kcard:hover {
    box-shadow: 0 10px 24px rgba(0,0,0,0.06);
    transform: translateY(-1px);
}
.kcard-bar {
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 3px;
}
.kcard-label {
    font-size: 10px;
    font-weight: 900;
    letter-spacing: 1.4px;
    text-transform: uppercase;
    color: #8f8f8f;
}
.kcard-value {
    font-size: 36px;
    font-weight: 900;
    color: #111111;
    letter-spacing: -1.8px;
    line-height: 1;
}
.kcard-unit {
    font-size: 15px;
    font-weight: 700;
    color: #9a9a9a;
    margin-left: 2px;
}
.kcard-sub {
    font-size: 11px;
    font-weight: 600;
    color: #8a8a8a;
}
.kcard-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
    font-weight: 800;
    padding: 4px 10px;
    border-radius: 999px;
    margin-top: 4px;
}

/* ━━━ 액션 보드 ━━━ */
.action-box {
    background: #ffffff;
    border: 1px solid #e8e8e8;
    border-radius: 16px;
    padding: 18px 18px 14px;
    min-height: 220px;
}
.action-box-title {
    font-size: 11px;
    font-weight: 900;
    color: #7a7a7a;
    letter-spacing: 1.4px;
    text-transform: uppercase;
    margin-bottom: 10px;
}
.action-box-value {
    font-size: 32px;
    font-weight: 900;
    letter-spacing: -1.4px;
    line-height: 1;
    margin-bottom: 6px;
}
.action-box-sub {
    font-size: 12px;
    font-weight: 600;
    color: #8a8a8a;
    margin-bottom: 14px;
}

/* ━━━ WIP 패널 ━━━ */
.wip-kcard {
    background: #ffffff;
    border-radius: 16px;
    border: 1px solid #e8e8e8;
    padding: 22px 20px 18px;
    position: relative;
    overflow: hidden;
}
.wip-stat-row {
    display: flex;
    gap: 8px;
    margin-top: 14px;
}
.wip-stat {
    flex: 1;
    border-radius: 10px;
    padding: 10px 12px;
    display: flex;
    flex-direction: column;
    gap: 2px;
}
.wip-stat-label {
    font-size: 10px;
    font-weight: 900;
    letter-spacing: 1px;
}
.wip-stat-val {
    font-size: 25px;
    font-weight: 900;
    letter-spacing: -1px;
    line-height: 1;
}
.wip-rule {
    font-size: 11px;
    color: #7a7a7a;
    line-height: 1.6;
    margin-top: 12px;
}

/* ━━━ 탭 ━━━ */
.stTabs [data-baseweb="tab-list"] {
    gap: 0 !important;
    background: transparent !important;
    padding: 0 !important;
    border-bottom: 2px solid #e5e5e5 !important;
    margin-bottom: 18px !important;
    flex-wrap: wrap !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 0 !important;
    font-weight: 800 !important;
    font-size: 13px !important;
    height: 46px !important;
    padding: 0 18px !important;
    border-bottom: 2px solid transparent !important;
    background: transparent !important;
    color: #a8a8a8 !important;
    margin-bottom: -2px !important;
}
.stTabs [aria-selected="true"] {
    border-bottom: 2px solid #111111 !important;
    color: #111111 !important;
}

/* ━━━ Metric ━━━ */
[data-testid="metric-container"] {
    background: #ffffff !important;
    border: 1px solid #e8e8e8 !important;
    border-radius: 14px !important;
    padding: 18px !important;
}
[data-testid="stMetricLabel"] {
    font-size: 10px !important;
    font-weight: 900 !important;
    color: #8f8f8f !important;
    letter-spacing: 1.2px !important;
    text-transform: uppercase !important;
}
[data-testid="stMetricValue"] {
    font-size: 28px !important;
    font-weight: 900 !important;
    color: #111111 !important;
    letter-spacing: -1px !important;
}

/* ━━━ 데이터프레임 ━━━ */
[data-testid="stDataFrame"] {
    border-radius: 14px !important;
    overflow: hidden !important;
    border: 1px solid #e8e8e8 !important;
    background: #ffffff !important;
}
[data-testid="stDataFrameResizable"] {
    border-radius: 14px !important;
    overflow: hidden !important;
    border: 1px solid #e8e8e8 !important;
    background: #ffffff !important;
}
[data-testid="stDataFrameResizable"] *,
[data-testid="stDataFrame"] * {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif !important;
}
[data-testid="stDataFrameResizable"] thead th,
[data-testid="stDataFrame"] thead th {
    background: #fafafa !important;
    color: #444444 !important;
    font-size: 12px !important;
    font-weight: 800 !important;
    border-bottom: 1px solid #e8e8e8 !important;
}
[data-testid="stDataFrameResizable"] tbody td,
[data-testid="stDataFrame"] tbody td,
[data-testid="stDataFrameResizable"] canvas,
[data-testid="stDataFrame"] canvas {
    color: #222222 !important;
}

/* ━━━ 셀렉트/라디오 본문 가시성 ━━━ */
.stRadio label,
.stSelectbox label,
.stMultiSelect label,
.stTextInput label,
.stFileUploader label {
    color: #4b4b4b !important;
    font-weight: 700 !important;
}

/* ━━━ 플롯 영역 ━━━ */
.js-plotly-plot, .plotly, .main-svg {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif !important;
}

/* ━━━ 구분선 ━━━ */
.kdiv {
    border: none;
    border-top: 1px solid #e5e5e5;
    margin: 30px 0;
}

/* ━━━ 마스터 테이블 래퍼 ━━━ */
.master-box {
    background: #ffffff;
    border: 1px solid #e8e8e8;
    border-radius: 16px;
    padding: 24px;
}
.filter-row-label {
    font-size: 10px;
    font-weight: 900;
    letter-spacing: 1.4px;
    color: #9b9b9b;
    text-transform: uppercase;
    margin-bottom: 10px;
}

/* ━━━ 상태 배지 ━━━ */
.note-chip {
    display: inline-flex;
    align-items: center;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 800;
    background: #f0f0f0;
    color: #444444;
    margin-right: 6px;
}

/* ━━━ 추가 폰트/글자 깨짐 방지 패치 ━━━ */
[data-baseweb="popover"] *,
[data-baseweb="menu"] *,
div[role="listbox"] *,
li[role="option"] *,
div[role="option"] * {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif !important;
    color: #ffffff !important;
}

[data-testid="stDataFrameResizable"] *,
[data-testid="stDataFrame"] *,
.glideDataEditor *,
.stDataFrame *,
.stTable * {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif !important;
    -webkit-font-smoothing: antialiased !important;
    text-rendering: geometricPrecision !important;
}

[data-testid="stMetricValue"],
[data-testid="stMetricLabel"],
[data-testid="stMetricDelta"] {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif !important;
    -webkit-font-smoothing: antialiased !important;
}

.js-plotly-plot .plotly text,
.js-plotly-plot .plotly .gtitle,
.js-plotly-plot .plotly .xtick text,
.js-plotly-plot .plotly .ytick text,
.js-plotly-plot .plotly .legendtext {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif !important;
    shape-rendering: geometricPrecision !important;
}

section[data-testid="stSidebar"] [data-baseweb="select"] > div,
section[data-testid="stSidebar"] [data-baseweb="tag"] {
    min-height: 40px !important;
}

</style>
""",
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────────
# 1. CONSTANTS
# ─────────────────────────────────────────────────────────────
SPREADSHEET_ID = "1e-uxQVNCCF3qS8e3a_S8sZbCx5qj343ycsEfkIF2POA"
SHEET_NAME = "Summary"
FIXED_REVIEWERS = ["오홍석", "유지윤", "전현희", "장근수"]
TRUE_VALUES = {"true", "false", "1", "0", "y", "yes", "완료", "o", "v", "✓", "check", "checked", "t", "f"}

STAGE_COLORS = {
    "5.등록 완료": "#05c072",
    "4.구매 완료": "#3b82f6",
    "3.구매 요청": "#8b5cf6",
    "2.검토/등록 요청": "#f5a623",
    "1.리스트업 완료": "#888888",
    "0.미진행": "#c7c7c7",
    "X.등록 불가": "#f04452",
}
STAGE_BG = {k: v + "18" for k, v in STAGE_COLORS.items()}

DELAY_MAP = {
    "해외배송/리드타임": ["해외배송", "해외 배송", "배송", "입고", "출고", "리드타임", "묶음"],
    "샘플/실물확인": ["샘플", "실물", "확인후 등록"],
    "가품검수/정가품": ["가품", "정가품", "검수"],
    "데이터/품번이슈": ["품번", "sku", "모델명"],
    "가격/운영판단": ["가격", "원가", "마진", "보류"],
    "담당자/행정": ["담당자", "부재", "행정"],
    "구매지연": ["구매 지연", "구매지연"],
}

CHART_TPL = dict(
    template="plotly_white",
    font=dict(family="Pretendard, sans-serif", size=12, color="#333333"),
    margin=dict(l=16, r=16, t=44, b=16),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)

# ─────────────────────────────────────────────────────────────
# 2. GOOGLE SHEETS
# ─────────────────────────────────────────────────────────────
def load_from_gsheet():
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=scopes
        )
        ws = gspread.authorize(creds).open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        return ws.get_all_values(), None
    except Exception as e:
        return None, str(e)

# ─────────────────────────────────────────────────────────────
# 3. HELPERS
# ─────────────────────────────────────────────────────────────
def pb(v) -> bool:
    if pd.isna(v) or v == "":
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    return str(v).strip().lower() in TRUE_VALUES


def parse_date(v):
    if pd.isna(v):
        return pd.NaT
    if isinstance(v, pd.Timestamp):
        return v if not pd.isna(v) else pd.NaT
    s = str(v).strip()
    if s in ["", "-", "#REF!", "nan", "NaT", "None"]:
        return pd.NaT
    for fmt in ["%y.%m.%d", "%Y.%m.%d", "%Y-%m-%d", "%y-%m-%d"]:
        try:
            return pd.to_datetime(s, format=fmt)
        except Exception:
            pass
    return pd.to_datetime(s, errors="coerce")


def h_filled(v) -> bool:
    if pd.isna(v):
        return False
    s = str(v).strip()
    return s not in ["", "nan", "NaT", "-", "#REF!", "None", "NaN"]


def is_filled_text(v) -> bool:
    if pd.isna(v):
        return False
    s = str(v).strip()
    return s not in ["", "nan", "NaT", "-", "#REF!", "None", "NaN"]


def safe_rate(n, d) -> float:
    return round(n / d * 100, 1) if d and d > 0 else 0.0


def classify_delay(v) -> str:
    if pd.isna(v):
        return "없음"
    s = str(v).strip()
    if s in ["", "-"]:
        return "없음"
    sl = s.lower()
    for cat, kws in DELAY_MAP.items():
        if any(k.lower() in sl for k in kws):
            return cat
    return "기타"


def norm_req(v) -> str:
    if pd.isna(v) or str(v).strip() == "":
        return "미입력"
    return re.split(r"[,/|·\n\s]+", str(v).strip())[0].strip()


def first_valid_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None


def column_by_position(df: pd.DataFrame, pos: int, fallback: str | None = None) -> str:
    if fallback and fallback in df.columns:
        return fallback
    if 0 <= pos < len(df.columns):
        return df.columns[pos]
    raise ValueError(f"열 위치 {pos}를 찾지 못했습니다.")

# ─────────────────────────────────────────────────────────────
# 4. PREPROCESSING
# ─────────────────────────────────────────────────────────────
def _build(values: list) -> pd.DataFrame:
    hi = 2
    for i, row in enumerate(values[:10]):
        if any("브랜드" in str(c) for c in row):
            hi = i
            break

    raw = pd.DataFrame(values[hi + 1 :], columns=values[hi])
    raw.columns = [str(c).strip().replace("\n", " ").replace("\r", " ") for c in raw.columns]

    brand_col = column_by_position(raw, 0, first_valid_column(raw, ["브랜드(영문)"]))
    requester_col = column_by_position(raw, 1, first_valid_column(raw, ["요청자"]))
    reviewer_col = column_by_position(raw, 2, first_valid_column(raw, ["검토자"]))
    listed_col = column_by_position(raw, 3, first_valid_column(raw, ["리스트업 완료"]))
    req_done_col = column_by_position(raw, 4, first_valid_column(raw, ["검토 및 등록 요청 완료"]))
    purchase_req_col = column_by_position(raw, 5, first_valid_column(raw, ["상품 구매 요청"]))
    purchase_done_col = column_by_position(raw, 6, first_valid_column(raw, ["상품 구매 완료"]))
    req_date_col = column_by_position(raw, 7, first_valid_column(raw, ["등록 요청일"]))
    reg_done_col = column_by_position(raw, 8, first_valid_column(raw, ["등록 완료 (앱 노출 시 체크)"]))
    reg_date_col = column_by_position(raw, 9, first_valid_column(raw, ["등록 완료일"]))

    df = raw[
        raw[brand_col].apply(lambda x: bool(str(x).strip()) and str(x).strip() not in ["", "nan"])
        & (raw[reg_date_col].astype(str).str.strip() != "#REF!")
    ].copy().reset_index(drop=True)

    df["등록완료일_dt"] = df[reg_date_col].apply(parse_date)
    df["등록요청일_dt"] = df[req_date_col].apply(parse_date)

    iso = df["등록완료일_dt"].dt.isocalendar()
    df["년도"] = df["등록완료일_dt"].dt.year.astype("Int64")
    df["년월"] = df["등록완료일_dt"].dt.strftime("%Y-%m")
    df["분기"] = "Q" + df["등록완료일_dt"].dt.quarter.astype("Int64").astype(str)
    df["년분기"] = df["년도"].astype(str) + "-" + df["분기"]
    df["주차"] = iso.week.astype("Int64")
    df["년주차"] = iso.year.astype(str) + "-W" + df["주차"].astype(str).str.zfill(2)

    df["리드타임"] = (df["등록완료일_dt"] - df["등록요청일_dt"]).dt.days
    df["리드타임"] = df["리드타임"].where((df["리드타임"] >= 0) & (df["리드타임"] <= 180))

    df["D_listed"] = df[listed_col].apply(pb)
    df["E_req_done"] = df[req_done_col].apply(pb)
    df["F_purchase_req"] = df[purchase_req_col].apply(pb)
    df["G_purchase_done"] = df[purchase_done_col].apply(pb)
    df["I_reg_done"] = df[reg_done_col].apply(pb)
    df["H_filled"] = df[req_date_col].apply(h_filled)

    def country(v):
        s = str(v).strip() if pd.notna(v) else ""
        if "국내" in s:
            return "국내"
        if "해외" in s:
            return "해외"
        return "미입력"

    df["국내해외"] = df["국내/해외"].apply(country)
    df["요청자_정제"] = df[requester_col].apply(norm_req)
    df["검토자_정제"] = df[reviewer_col].apply(lambda x: str(x).strip() if pd.notna(x) and str(x).strip() else "미입력")

    df["비고_txt"] = df["비고"].apply(lambda x: str(x).strip() if pd.notna(x) else "")
    df["브랜드별검토사항_txt"] = df["브랜드별 검토사항"].apply(lambda x: str(x).strip() if pd.notna(x) else "") if "브랜드별 검토사항" in df.columns else ""
    df["지연분류"] = df["지연 사유"].apply(classify_delay)
    df["is_불가"] = df["비고_txt"].str.contains(r"등록\s*불가", na=False)

    def stage(r):
        if r["is_불가"]:
            return "X.등록 불가"
        if r["I_reg_done"]:
            return "5.등록 완료"
        if r["G_purchase_done"]:
            return "4.구매 완료"
        if r["F_purchase_req"]:
            return "3.구매 요청"
        if r["E_req_done"]:
            return "2.검토/등록 요청"
        if r["D_listed"]:
            return "1.리스트업 완료"
        return "0.미진행"

    df["현재단계"] = df.apply(stage, axis=1)
    df["지연여부"] = df["지연분류"].apply(lambda x: "지연" if x != "없음" else "정상")

    # ★ 사용자 정의 기준 WIP
    # 검토 진행중: B열(요청자) 값 있음 + E=False + 등록불가 제외
    # 등록 진행중: B열(요청자) 값 있음 + E=True + I=False + 등록불가 제외
    df["B_exists"] = df[requester_col].apply(is_filled_text)
    df["wip_검토"] = df["B_exists"] & (~df["E_req_done"]) & (~df["is_불가"])
    df["wip_등록"] = df["B_exists"] & df["E_req_done"] & (~df["I_reg_done"]) & (~df["is_불가"])

    df["wip_종류"] = ""
    df.loc[df["wip_검토"], "wip_종류"] = "검토 진행중"
    df.loc[df["wip_등록"], "wip_종류"] = "등록 진행중"

    return df


@st.cache_data(ttl=300, show_spinner=False)
def from_bytes(b: bytes) -> pd.DataFrame:
    raw = pd.read_excel(io.BytesIO(b), sheet_name="Summary", header=None)
    vals = raw.fillna("").astype(str).values.tolist()
    return _build(vals)


@st.cache_data(ttl=300, show_spinner=False)
def from_gsheet(_key: str, vals: list) -> pd.DataFrame:
    return _build(vals)

# ─────────────────────────────────────────────────────────────
# 5. SIDEBAR
# ─────────────────────────────────────────────────────────────
def sidebar(df: pd.DataFrame):
    with st.sidebar:
        st.markdown(
            """
        <div style='padding:20px 16px 14px;border-bottom:1px solid #1f1f1f;'>
          <div style='font-size:20px;font-weight:900;color:#fff;letter-spacing:-0.5px;line-height:1.1;'>
            OPS<span style='color:#d4ff00;'>·</span>INTEL
          </div>
          <div style='font-size:9px;color:#747474;margin-top:5px;letter-spacing:2.5px;font-weight:800;'>
            KREAM · 1P PRODUCT REGISTRATION
          </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

        if st.button("↻  구글 시트 동기화", use_container_width=True, type="primary"):
            with st.spinner("연결 중..."):
                vals, err = load_from_gsheet()
            if err:
                st.error(f"연결 실패: {err}")
            else:
                from_gsheet.clear()
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.session_state.update(
                    {
                        "gsheet_values": vals,
                        "gsheet_ts": ts,
                        "source": "gsheet",
                    }
                )
                st.success("동기화 완료")
                time.sleep(0.4)
                st.rerun()

        if st.session_state.get("gsheet_ts"):
            st.markdown(
                f"<div style='font-size:10px;color:#8a8a8a;text-align:center;padding:5px 0 2px;'>"
                f"Last sync · {st.session_state['gsheet_ts']}</div>",
                unsafe_allow_html=True,
            )

        st.markdown(
            "<p style='color:#d6d6d6;font-size:10px;margin:14px 0 3px;font-weight:700;letter-spacing:0.5px;'>"
            "XLSX 보조 업로드</p>",
            unsafe_allow_html=True,
        )
        uploaded = st.file_uploader("", type=["xlsx"], label_visibility="collapsed")
        if uploaded:
            from_bytes.clear()
            st.session_state["xlsx_bytes"] = uploaded.read()
            st.session_state["source"] = "xlsx"
            st.rerun()

        src = st.session_state.get("source", "none")
        label = {"gsheet": "● Google Sheet", "xlsx": "● Excel 파일"}.get(src, "● 연결 없음")
        color = {"gsheet": "#d4ff00", "xlsx": "#f5a623"}.get(src, "#6f6f6f")
        st.markdown(
            f"<div style='font-size:11px;color:{color};text-align:center;padding:6px 0 14px;font-weight:800;'>{label}</div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            "<div style='border-top:1px solid #1f1f1f;padding-top:14px;'>"
            "<p style='color:#9a9a9a;font-size:9px;letter-spacing:2px;font-weight:900;margin-bottom:12px;'>FILTERS</p>",
            unsafe_allow_html=True,
        )

        avail = [r for r in FIXED_REVIEWERS if r in df["검토자_정제"].unique()]
        f_rev = st.multiselect("검토자", FIXED_REVIEWERS, default=avail)

        c_opts = sorted(df["국내해외"].dropna().unique().tolist())
        f_country = st.multiselect("국내 / 해외", c_opts, default=c_opts)

        y_opts = sorted([y for y in df["년도"].dropna().unique().tolist()])
        f_year = st.multiselect("분석 연도", y_opts, default=y_opts)

        s_opts = sorted(df["현재단계"].dropna().unique().tolist())
        f_stage = st.multiselect("진행 단계", s_opts, default=s_opts)

        f_delay = st.multiselect("지연 여부", ["정상", "지연"], default=["정상", "지연"])
        keyword = st.text_input("브랜드 검색", placeholder="예: Jellycat")

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='border-top:1px solid #1f1f1f;padding-top:10px;font-size:10px;color:#8a8a8a;text-align:center;'>"
            f"Total {len(df):,}행 · {datetime.now().strftime('%Y-%m-%d')}</div>",
            unsafe_allow_html=True,
        )

    return f_rev, f_country, f_year, f_stage, f_delay, keyword

# ─────────────────────────────────────────────────────────────
# 6. LANDING
# ─────────────────────────────────────────────────────────────
def landing():
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown(
            """
        <div style='text-align:center;padding:90px 0 28px;'>
          <div style='font-size:48px;font-weight:900;letter-spacing:-2px;color:#111;line-height:1;'>
            OPS<span style='background:#111;color:#d4ff00;padding:0 8px;border-radius:6px;'>·</span>INTEL
          </div>
          <p style='color:#8a8a8a;font-size:12px;margin-top:10px;letter-spacing:2px;font-weight:800;text-transform:uppercase;'>
            KREAM · 1P Product Registration · Executive Dashboard
          </p>
        </div>
        <div style='background:#111;border-radius:16px;padding:28px;'>
          <p style='color:#d4ff00;font-size:9px;font-weight:900;letter-spacing:2.5px;margin:0 0 14px;text-transform:uppercase;'>Quick Start</p>
          <ol style='color:#c6c6c6;line-height:2.3;font-size:14px;margin:0;padding-left:18px;'>
            <li>왼쪽 사이드바 → <b style='color:#fff;'>↻ 구글 시트 동기화</b> 클릭</li>
            <li>실시간 Summary 시트 자동 로드</li>
            <li>검토자 / 국가 / 연도 / 단계 필터 조정</li>
          </ol>
        </div>
        """,
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────────────────────
# 7. DASHBOARD
# ─────────────────────────────────────────────────────────────
def dashboard(df: pd.DataFrame, src: str):
    df_kpi = df[df["년도"].isin([2024, 2025, 2026])].copy()
    df_24 = df[df["등록완료일_dt"] >= "2024-01-01"].copy()

    ts = st.session_state.get("gsheet_ts", datetime.now().strftime("%Y-%m-%d %H:%M"))
    tag = "Google Sheet · LIVE" if src == "gsheet" else "Excel Upload"
    st.markdown(
        f"""
    <div class='topbar'>
      <div class='topbar-logo'>OPS<span>·</span>INTEL</div>
      <div class='topbar-right'>
        <span class='topbar-src'>{tag} · {ts}</span>
        <span class='live-chip'>LIVE</span>
      </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # ══════════════════════════════════════════════
    # SECTION 1 — KPI (2024–2026)
    # ══════════════════════════════════════════════
    st.markdown("<div class='sec'>종합 핵심 운영 지표 · 2024–2026</div>", unsafe_allow_html=True)

    total = len(df_kpi)
    done = int(df_kpi["I_reg_done"].sum())
    lt_avg = df_kpi["리드타임"].mean()
    lt_med = df_kpi["리드타임"].median()
    delayed = int((df_kpi["지연여부"] == "지연").sum())

    # WIP는 등록완료일 기준 연도 필터(df_kpi)가 아니라 현재 필터된 전체 데이터(df) 기준으로 집계
    # 진행중 건은 등록완료일이 비어있는 경우가 많아 df_kpi로 자르면 누락될 수 있다.
    wip_scope = df.copy()
    wip_reg = wip_scope[wip_scope["wip_등록"]].copy()
    wip_rev = wip_scope[wip_scope["wip_검토"]].copy()
    wip_tot = len(wip_reg) + len(wip_rev)

    c1, c2, c3, c4, c5 = st.columns(5)

    def kcard(col, label, num, unit, sub, bar_color, badge="", badge_bg="", badge_fg=""):
        b = (
            f"<div class='kcard-badge' style='background:{badge_bg};color:{badge_fg};'>{badge}</div>"
            if badge
            else ""
        )
        col.markdown(
            f"""
        <div class='kcard'>
          <div class='kcard-bar' style='background:{bar_color};'></div>
          <div class='kcard-label'>{label}</div>
          <div>
            <span class='kcard-value'>{num}</span>
            <span class='kcard-unit'>{unit}</span>
          </div>
          {b}
          <div class='kcard-sub'>{sub}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    kcard(c1, "전체 분석 건수", f"{total:,}", "건", "2024–2026 기준", "#111111")
    kcard(
        c2,
        "최종 등록 완료",
        f"{done:,}",
        "건",
        "누적 등록 성공",
        "#05c072",
        f"등록률 {safe_rate(done, total)}%",
        "#05c07220",
        "#05c072",
    )
    kcard(
        c3,
        "평균 리드타임",
        f"{lt_avg:.1f}" if pd.notna(lt_avg) else "N/A",
        "일",
        f"중앙값 {lt_med:.0f}일" if pd.notna(lt_med) else "-",
        "#8b5cf6",
    )
    kcard(
        c4,
        "지연 발생 건수",
        f"{delayed:,}",
        "건",
        "지연 사유 기입 건",
        "#f04452",
        f"지연률 {safe_rate(delayed, total)}%",
        "#f0445220",
        "#f04452",
    )
    kcard(c5, "진행 중 WIP", f"{wip_tot:,}", "건", "현재 필터 기준 진행중 합계", "#d4ff00")

    # ══════════════════════════════════════════════
    # SECTION 1-2 — ACTION BOARD
    # ══════════════════════════════════════════════
    st.markdown("<div class='sec'>즉시 액션 필요 현황</div>", unsafe_allow_html=True)

    stale_reg = wip_reg[wip_reg["리드타임"].fillna(0) > 14].copy()
    stale_reg = stale_reg.sort_values("리드타임", ascending=False)
    stale_review = wip_rev.copy()

    a1, a2 = st.columns(2)
    with a1:
        st.markdown(
            f"""
            <div class='action-box'>
              <div class='action-box-title'>등록 병목</div>
              <div class='action-box-value' style='color:#f5a623;'>{len(stale_reg):,}건</div>
              <div class='action-box-sub'>리드타임 14일 초과 등록 진행중 브랜드</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if stale_reg.empty:
            st.success("14일 초과 등록 병목 브랜드 없음")
        else:
            reg_show = stale_reg[
                ["브랜드(영문)", "요청자_정제", "검토자_정제", "리드타임", "비고_txt"]
            ].rename(
                columns={
                    "브랜드(영문)": "브랜드",
                    "요청자_정제": "요청자",
                    "검토자_정제": "검토자",
                    "비고_txt": "비고",
                }
            )
            st.dataframe(reg_show, use_container_width=True, hide_index=True, height=240)

    with a2:
        st.markdown(
            f"""
            <div class='action-box'>
              <div class='action-box-title'>검토 대기</div>
              <div class='action-box-value' style='color:#3b82f6;'>{len(stale_review):,}건</div>
              <div class='action-box-sub'>요청자 값 존재 + 검토/등록 요청 미완료 브랜드</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        if stale_review.empty:
            st.success("검토 진행중 브랜드 없음")
        else:
            rev_show = stale_review[
                ["브랜드(영문)", "요청자_정제", "검토자_정제", "비고_txt"]
            ].rename(
                columns={
                    "브랜드(영문)": "브랜드",
                    "요청자_정제": "요청자",
                    "검토자_정제": "검토자",
                    "비고_txt": "비고",
                }
            )
            st.dataframe(rev_show, use_container_width=True, hide_index=True, height=240)

    # ══════════════════════════════════════════════
    # SECTION 1-3 — WIP PANEL
    # ══════════════════════════════════════════════
    st.markdown("<div class='sec'>진행 중 브랜드 현황 (WIP)</div>", unsafe_allow_html=True)

    wl, wr = st.columns([3, 7])

    with wl:
        st.markdown(
            f"""
        <div class='wip-kcard'>
          <div class='kcard-bar' style='background:#f5a623;'></div>
          <div class='kcard-label'>WIP Snapshot</div>
          <div>
            <span class='kcard-value'>{wip_tot:,}</span>
            <span class='kcard-unit'>건</span>
          </div>
          <div class='wip-stat-row'>
            <div class='wip-stat' style='background:#fff8ec;'>
              <div class='wip-stat-label' style='color:#f5a623;'>등록 진행중</div>
              <div class='wip-stat-val' style='color:#f5a623;'>{len(wip_reg):,}</div>
            </div>
            <div class='wip-stat' style='background:#eff6ff;'>
              <div class='wip-stat-label' style='color:#3b82f6;'>검토 진행중</div>
              <div class='wip-stat-val' style='color:#3b82f6;'>{len(wip_rev):,}</div>
            </div>
          </div>
          <div class='wip-rule'>
            • 검토 진행중 = B열(요청자) 값 있음 + E열 FALSE<br>
            • 등록 진행중 = B열(요청자) 값 있음 + E열 TRUE + I열 FALSE<br>
            • 등록 불가 건 제외
          </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    with wr:
        SHOW = [
            "브랜드(영문)",
            "요청자_정제",
            "검토자_정제",
            "국내해외",
            "현재단계",
            "등록 요청일",
            "리드타임",
            "지연분류",
            "비고_txt",
        ]
        REN = {
            "브랜드(영문)": "브랜드",
            "요청자_정제": "요청자",
            "검토자_정제": "검토자",
            "비고_txt": "비고",
        }

        def scolor(val):
            c = STAGE_COLORS.get(val, "#888888")
            bg = STAGE_BG.get(val, "#eeeeee")
            return f"background-color:{bg};color:{c};font-weight:800;"

        t_reg, t_rev = st.tabs(
            [
                f"🟠 등록 진행중 ({len(wip_reg)}건)",
                f"🔵 검토 진행중 ({len(wip_rev)}건)",
            ]
        )
        with t_reg:
            if wip_reg.empty:
                st.success("현재 등록 진행중 브랜드 없음")
            else:
                show = wip_reg[SHOW].rename(columns=REN).sort_values(
                    ["리드타임", "브랜드"], ascending=[False, True]
                )
                st.dataframe(
                    show.style.map(scolor, subset=["현재단계"]),
                    use_container_width=True,
                    hide_index=True,
                    height=290,
                )
        with t_rev:
            if wip_rev.empty:
                st.success("현재 검토 진행중 브랜드 없음")
            else:
                show = wip_rev[SHOW].rename(columns=REN).sort_values(["브랜드"], ascending=[True])
                st.dataframe(
                    show.style.map(scolor, subset=["현재단계"]),
                    use_container_width=True,
                    hide_index=True,
                    height=290,
                )

    st.markdown("<hr class='kdiv'>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════
    # SECTION 2 — 파이프라인 (2024–2026)
    # ══════════════════════════════════════════════
    st.markdown("<div class='sec'>등록 파이프라인 · 2024–2026</div>", unsafe_allow_html=True)

    p1, p2, p3 = st.columns(3)

    with p1:
        fig = go.Figure(
            go.Funnel(
                y=["리스트업 완료", "검토/등록 요청", "구매 완료", "최종 등록"],
                x=[
                    int(df_kpi["D_listed"].sum()),
                    int(df_kpi["E_req_done"].sum()),
                    int(df_kpi["G_purchase_done"].sum()),
                    int(df_kpi["I_reg_done"].sum()),
                ],
                textinfo="value+percent previous",
                textfont=dict(size=13, color="#ffffff"),
                marker=dict(color=["#444444", "#666666", "#888888", "#05c072"]),
                connector=dict(line=dict(color="#eeeeee", width=1.5)),
            )
        )
        fig.update_layout(**CHART_TPL, title="<b>등록 전환 Funnel</b>", height=320)
        st.plotly_chart(fig, use_container_width=True)

    with p2:
        sc = df_kpi["현재단계"].value_counts().reset_index()
        sc.columns = ["단계", "건수"]
        fig = go.Figure(
            go.Pie(
                labels=sc["단계"],
                values=sc["건수"],
                hole=0.62,
                marker=dict(
                    colors=[STAGE_COLORS.get(s, "#cccccc") for s in sc["단계"]],
                    line=dict(color="#ffffff", width=2),
                ),
                textinfo="percent",
                textfont=dict(size=12),
            )
        )
        fig.update_layout(
            **CHART_TPL,
            title="<b>단계별 분포</b>",
            height=320,
            legend=dict(font=dict(size=11), x=1.02, y=0.5),
        )
        st.plotly_chart(fig, use_container_width=True)

    with p3:
        cross = (
            df_kpi[df_kpi["국내해외"].isin(["국내", "해외"])]
            .groupby(["국내해외", "현재단계"])
            .size()
            .reset_index(name="건수")
        )
        fig = px.bar(
            cross,
            x="국내해외",
            y="건수",
            color="현재단계",
            color_discrete_map=STAGE_COLORS,
            barmode="stack",
            title="<b>국내 / 해외별 단계</b>",
        )
        fig.update_layout(
            **CHART_TPL,
            height=320,
            legend=dict(font=dict(size=11), x=1.02, y=0.5),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("<hr class='kdiv'>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════
    # SECTION 3 — 2024+ 심화 분석
    # ══════════════════════════════════════════════
    st.markdown("<div class='sec'>2024+ 운영 트렌드 심화 분석</div>", unsafe_allow_html=True)

    if df_24.empty:
        st.info("선택 필터 내 2024년 이후 데이터가 없습니다.")
    else:
        tab1, tab2, tab3, tab4 = st.tabs(["시계열 트렌드", "리드타임 분석", "지연 분석", "담당자 성과"])

        with tab1:
            view = st.radio("집계 단위", ["월별", "주차별", "분기별"], horizontal=True)
            gc = {"월별": "년월", "주차별": "년주차", "분기별": "년분기"}[view]
            ts_df = (
                df_24.dropna(subset=[gc])
                .groupby(gc)
                .agg(
                    등록완료=("I_reg_done", "sum"),
                    전체건수=("I_reg_done", "count"),
                    평균리드타임=("리드타임", "mean"),
                )
                .reset_index()
            )
            ts_df.columns = ["기간", "등록완료", "전체건수", "평균리드타임"]
            ts_df["등록률"] = (ts_df["등록완료"] / ts_df["전체건수"] * 100).round(1)

            fig = make_subplots(
                rows=2,
                cols=1,
                subplot_titles=("등록 완료 vs 전체", "등록률 (%)"),
                vertical_spacing=0.14,
                shared_xaxes=True,
            )
            fig.add_trace(
                go.Bar(x=ts_df["기간"], y=ts_df["전체건수"], name="전체", marker_color="#ebebeb"),
                row=1,
                col=1,
            )
            fig.add_trace(
                go.Bar(x=ts_df["기간"], y=ts_df["등록완료"], name="등록완료", marker_color="#111111"),
                row=1,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=ts_df["기간"],
                    y=ts_df["등록률"],
                    name="등록률",
                    mode="lines+markers",
                    line=dict(color="#05c072", width=2.5),
                    marker=dict(size=5),
                    fill="tozeroy",
                    fillcolor="rgba(5,192,114,0.07)",
                ),
                row=2,
                col=1,
            )
            fig.update_layout(**CHART_TPL, height=460, barmode="overlay")
            fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
            st.plotly_chart(fig, use_container_width=True)
            with st.expander("상세 수치"):
                st.dataframe(
                    ts_df.style.format(
                        {
                            "등록완료": "{:,}",
                            "전체건수": "{:,}",
                            "평균리드타임": "{:.1f}",
                            "등록률": "{:.1f}%",
                        }
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

        with tab2:
            lt = df_24[df_24["리드타임"].notna()].copy()
            r1, r2 = st.columns(2)
            cm = {"국내": "#111111", "해외": "#888888", "미입력": "#cccccc"}
            with r1:
                fig = px.box(
                    lt,
                    x="국내해외",
                    y="리드타임",
                    color="국내해외",
                    title="<b>리드타임 분포</b>",
                    points="outliers",
                    color_discrete_map=cm,
                )
                fig.update_layout(**CHART_TPL, height=350, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            with r2:
                fig = px.histogram(
                    lt,
                    x="리드타임",
                    color="국내해외",
                    nbins=30,
                    barmode="overlay",
                    opacity=0.75,
                    title="<b>리드타임 빈도 분포</b>",
                    color_discrete_map=cm,
                )
                fig.update_layout(**CHART_TPL, height=350)
                st.plotly_chart(fig, use_container_width=True)

            stat = (
                lt.groupby("국내해외")["리드타임"]
                .agg(건수="count", 평균="mean", 중앙값="median", 최솟값="min", 최댓값="max")
                .reset_index()
                .round(1)
            )
            st.dataframe(
                stat.style.format(
                    {
                        "평균": "{:.1f}일",
                        "중앙값": "{:.1f}일",
                        "최솟값": "{:.0f}일",
                        "최댓값": "{:.0f}일",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

        with tab3:
            ddf = df_24[df_24["지연여부"] == "지연"]
            ca, cb, cc = st.columns(3)
            ca.metric("지연 건수", f"{len(ddf):,}건")
            cb.metric("정상 건수", f"{len(df_24) - len(ddf):,}건")
            cc.metric("지연률", f"{safe_rate(len(ddf), len(df_24))}%")
            d1, d2 = st.columns(2)
            with d1:
                dc = df_24["지연분류"].value_counts().reset_index()
                dc.columns = ["분류", "건수"]
                dc = dc[dc["분류"] != "없음"]
                fig = px.bar(
                    dc,
                    y="분류",
                    x="건수",
                    orientation="h",
                    title="<b>지연 사유 유형별 건수</b>",
                    color="건수",
                    color_continuous_scale=["#f5f5f5", "#f04452"],
                )
                fig.update_layout(**CHART_TPL, height=330)
                st.plotly_chart(fig, use_container_width=True)
            with d2:
                dm = df_24.groupby(["년월", "지연여부"]).size().reset_index(name="건수")
                fig = px.bar(
                    dm,
                    x="년월",
                    y="건수",
                    color="지연여부",
                    barmode="stack",
                    title="<b>월별 지연 / 정상 현황</b>",
                    color_discrete_map={"정상": "#05c072", "지연": "#f04452"},
                )
                fig.update_layout(**CHART_TPL, height=330)
                st.plotly_chart(fig, use_container_width=True)
            if len(ddf) > 0:
                with st.expander(f"지연 건 상세 ({len(ddf)}건)"):
                    sc = [
                        "브랜드(영문)",
                        "요청자_정제",
                        "검토자_정제",
                        "국내해외",
                        "지연분류",
                        "지연 사유",
                        "리드타임",
                        "현재단계",
                    ]
                    st.dataframe(
                        ddf[sc].sort_values("리드타임", ascending=False),
                        use_container_width=True,
                        hide_index=True,
                    )

        with tab4:
            pr = (
                df_24.groupby("검토자_정제")
                .agg(
                    담당건수=("I_reg_done", "count"),
                    등록완료=("I_reg_done", "sum"),
                    평균리드타임=("리드타임", "mean"),
                    지연건수=("지연여부", lambda x: (x == "지연").sum()),
                )
                .reset_index()
            )
            pr["등록률"] = (pr["등록완료"] / pr["담당건수"] * 100).round(1)
            pr["지연률"] = (pr["지연건수"] / pr["담당건수"] * 100).round(1)
            pr = pr.sort_values("담당건수", ascending=False)

            fig = make_subplots(rows=1, cols=3, subplot_titles=("담당 건수", "등록률 (%)", "평균 리드타임 (일)"))
            for i, (c_, col_) in enumerate(
                [("담당건수", "#111111"), ("등록률", "#05c072"), ("평균리드타임", "#f5a623")]
            ):
                fig.add_trace(
                    go.Bar(
                        x=pr["검토자_정제"],
                        y=pr[c_].round(1),
                        name=c_,
                        marker_color=col_,
                        text=pr[c_].round(1),
                        textposition="outside",
                        textfont=dict(size=12, color="#333333"),
                    ),
                    row=1,
                    col=i + 1,
                )
            fig.update_layout(**CHART_TPL, height=360, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

            preq = (
                df_24.groupby("요청자_정제")
                .agg(요청건수=("I_reg_done", "count"), 등록완료=("I_reg_done", "sum"))
                .reset_index()
            )
            preq["등록률"] = (preq["등록완료"] / preq["요청건수"] * 100).round(1)
            preq = preq.sort_values("요청건수", ascending=False).head(15)
            fig = px.bar(
                preq,
                x="요청자_정제",
                y="요청건수",
                color="등록률",
                color_continuous_scale=["#e8e8e8", "#111111"],
                title="<b>요청자별 등록 요청 건수 TOP 15</b>",
                text="요청건수",
            )
            fig.update_layout(**CHART_TPL, height=330)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("<hr class='kdiv'>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════
    # SECTION 4 — YoY (2023–2026)
    # ══════════════════════════════════════════════
    st.markdown("<div class='sec'>연도별 YoY 성과 비교 · 2023–2026</div>", unsafe_allow_html=True)

    yoy = (
        df.groupby("년도")
        .agg(
            전체건수=("I_reg_done", "count"),
            등록완료=("I_reg_done", "sum"),
            평균리드타임=("리드타임", "mean"),
            지연건수=("지연여부", lambda x: (x == "지연").sum()),
        )
        .reset_index()
        .dropna(subset=["년도"])
    )
    yoy["등록률"] = (yoy["등록완료"] / yoy["전체건수"] * 100).round(1)
    yoy["지연률"] = (yoy["지연건수"] / yoy["전체건수"] * 100).round(1)
    yoy["년도"] = yoy["년도"].astype(int).astype(str)

    y1, y2 = st.columns(2)
    with y1:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=yoy["년도"],
                y=yoy["전체건수"],
                name="전체",
                marker_color="#e8e8e8",
                text=yoy["전체건수"],
                textposition="outside",
            )
        )
        fig.add_trace(
            go.Bar(
                x=yoy["년도"],
                y=yoy["등록완료"],
                name="등록완료",
                marker_color="#111111",
                text=yoy["등록완료"],
                textposition="outside",
            )
        )
        fig.update_layout(**CHART_TPL, title="<b>연도별 전체 vs 등록완료</b>", barmode="overlay", height=330)
        st.plotly_chart(fig, use_container_width=True)
    with y2:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Bar(
                x=yoy["년도"],
                y=yoy["평균리드타임"].round(1),
                name="리드타임(일)",
                marker_color="#888888",
                text=yoy["평균리드타임"].round(1),
                textposition="outside",
            ),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=yoy["년도"],
                y=yoy["지연률"],
                name="지연률(%)",
                mode="lines+markers+text",
                text=[f"{v}%" for v in yoy["지연률"]],
                textposition="top center",
                textfont=dict(color="#f04452", size=12),
                line=dict(color="#f04452", width=2.5),
                marker=dict(size=8, color="#f04452"),
            ),
            secondary_y=True,
        )
        fig.update_layout(**CHART_TPL, title="<b>연도별 리드타임 vs 지연률</b>", height=330)
        fig.update_yaxes(title_text="리드타임(일)", secondary_y=False, showgrid=True, gridcolor="#f0f0f0")
        fig.update_yaxes(title_text="지연률(%)", secondary_y=True, showgrid=False)
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        yoy.style.format(
            {
                "전체건수": "{:,}",
                "등록완료": "{:,}",
                "지연건수": "{:,}",
                "평균리드타임": "{:.1f}일",
                "등록률": "{:.1f}%",
                "지연률": "{:.1f}%",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("<hr class='kdiv'>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════
    # SECTION 5 — 마스터 트래킹 (2023–2026)
    # ══════════════════════════════════════════════
    st.markdown("<div class='sec'>마스터 업무 트래킹 · 2023–2026 전체</div>", unsafe_allow_html=True)

    MCOLS = [
        "브랜드(영문)",
        "요청자_정제",
        "검토자_정제",
        "국내해외",
        "현재단계",
        "wip_종류",
        "지연분류",
        "리드타임",
        "년월",
        "비고_txt",
    ]
    MREN = {
        "브랜드(영문)": "브랜드",
        "요청자_정제": "요청자",
        "검토자_정제": "검토자",
        "비고_txt": "비고",
        "년월": "등록년월",
        "wip_종류": "WIP구분",
    }

    master = df[MCOLS].rename(columns=MREN).copy()

    st.markdown("<div class='master-box'>", unsafe_allow_html=True)
    st.markdown("<div class='filter-row-label'>Column Filters</div>", unsafe_allow_html=True)

    fc = st.columns(7)

    def csel(container, label, series, key):
        opts = ["전체"] + sorted([x for x in series.dropna().unique() if str(x).strip() not in ["", "nan"]])
        return container.selectbox(label, opts, key=key)

    s_rev = csel(fc[0], "검토자", master["검토자"], "m_rev")
    s_req = csel(fc[1], "요청자", master["요청자"], "m_req")
    s_nat = csel(fc[2], "국내/해외", master["국내해외"], "m_nat")
    s_stage = csel(fc[3], "현재단계", master["현재단계"], "m_stage")
    s_wip = csel(fc[4], "WIP구분", master["WIP구분"], "m_wip")
    s_delay = csel(fc[5], "지연분류", master["지연분류"], "m_delay")
    s_month = csel(fc[6], "등록년월", master["등록년월"], "m_month")

    view = master.copy()
    if s_rev != "전체":
        view = view[view["검토자"] == s_rev]
    if s_req != "전체":
        view = view[view["요청자"] == s_req]
    if s_nat != "전체":
        view = view[view["국내해외"] == s_nat]
    if s_stage != "전체":
        view = view[view["현재단계"] == s_stage]
    if s_wip != "전체":
        view = view[view["WIP구분"] == s_wip]
    if s_delay != "전체":
        view = view[view["지연분류"] == s_delay]
    if s_month != "전체":
        view = view[view["등록년월"] == s_month]

    sc1, _, _ = st.columns([2, 2, 6])
    sort_by = sc1.selectbox("정렬", ["등록년월 최신순", "리드타임 내림차순", "현재단계"], key="msort")
    if sort_by == "등록년월 최신순":
        view = view.sort_values("등록년월", ascending=False)
    elif sort_by == "리드타임 내림차순":
        view = view.sort_values("리드타임", ascending=False)
    else:
        view = view.sort_values("현재단계")

    st.caption(f"표시 {len(view):,}건 / 전체 {len(master):,}건")

    def sc_stage(v):
        c = STAGE_COLORS.get(v, "#888888")
        bg = STAGE_BG.get(v, "#eeeeee")
        return f"background-color:{bg};color:{c};font-weight:800;"

    def sc_delay(v):
        return "color:#f04452;font-weight:700;" if v != "없음" else "color:#c0c0c0;"

    def sc_lt(v):
        try:
            n = float(v)
            if n > 30:
                return "color:#f04452;font-weight:700;"
            if n > 14:
                return "color:#f5a623;font-weight:700;"
            return "color:#05c072;font-weight:700;"
        except Exception:
            return ""

    def sc_wip(v):
        if v == "검토 진행중":
            return "background-color:#eff6ff;color:#3b82f6;font-weight:800;"
        if v == "등록 진행중":
            return "background-color:#fff8ec;color:#f5a623;font-weight:800;"
        return ""

    st.dataframe(
        view.style.map(sc_stage, subset=["현재단계"]).map(sc_wip, subset=["WIP구분"]).map(sc_delay, subset=["지연분류"]).map(sc_lt, subset=["리드타임"]).format(
            {"리드타임": lambda x: f"{int(x)}일" if pd.notna(x) else "-"}
        ),
        use_container_width=True,
        hide_index=True,
        height=520,
    )

    csv = view.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "↓ CSV 다운로드",
        data=csv,
        file_name=f"1P_Ops_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
    )
    st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# 8. MAIN
# ─────────────────────────────────────────────────────────────
def main():
    src = st.session_state.get("source", "none")

    if src == "gsheet" and "gsheet_values" in st.session_state:
        df = from_gsheet(st.session_state.get("gsheet_ts", ""), st.session_state["gsheet_values"])
    elif src == "xlsx" and "xlsx_bytes" in st.session_state:
        df = from_bytes(st.session_state["xlsx_bytes"])
    else:
        has_secret = False
        try:
            _ = st.secrets["gcp_service_account"]
            has_secret = True
        except Exception:
            pass

        if has_secret and "auto_tried" not in st.session_state:
            st.session_state["auto_tried"] = True
            with st.spinner("구글 시트 자동 연결 중..."):
                vals, err = load_from_gsheet()
            if not err:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.session_state.update({"gsheet_values": vals, "gsheet_ts": ts, "source": "gsheet"})
                st.rerun()
            else:
                st.warning(f"자동 연결 실패: {err}")
                landing()
                return
        else:
            landing()
            return

    f_rev, f_country, f_year, f_stage, f_delay, keyword = sidebar(df)

    dff = df.copy()
    if f_rev:
        dff = dff[dff["검토자_정제"].isin(f_rev)]
    if f_country:
        dff = dff[dff["국내해외"].isin(f_country)]
    if f_year:
        dff = dff[dff["년도"].isin(f_year) | dff["년도"].isna()]
    if f_stage:
        dff = dff[dff["현재단계"].isin(f_stage)]
    if f_delay:
        dff = dff[dff["지연여부"].isin(f_delay)]
    if keyword:
        kw = keyword.strip().lower()
        dff = dff[
            dff.apply(
                lambda r: kw in " ".join([str(v).lower() for v in r.values if pd.notna(v)]),
                axis=1,
            )
        ]

    dashboard(dff, src)


if __name__ == "__main__":
    main()
