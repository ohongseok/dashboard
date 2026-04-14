import io
import re
import time
from typing import List, Optional
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from datetime import datetime

# ─────────────────────────────────────────────
# 0. PAGE CONFIG
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="1P Ops Intelligence · KREAM",
    page_icon="⬛",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ─────────────────────────────────────────────
# KREAM-inspired CSS — 원본 dashboard (1).py의 모든 스타일 유지
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700;800;900&display=swap');

html, body, [class*="css"], .stMarkdown, .stText {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}
.main, .block-container {
    background: #f5f5f5 !important;
    padding-top: 0 !important;
}
.block-container { max-width:100% !important; padding: 0 32px 40px 32px !important; }

/* ── 사이드바 ── */
[data-testid="stSidebar"] { background: #0f0f0f !important; border-right: 1px solid #2a2a2a !important; }
[data-testid="stSidebar"] > div { padding-top: 0 !important; }
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] label { color: #999 !important; font-size: 11px !important; font-weight:600 !important; }
[data-testid="stSidebar"] .stButton > button {
    background: #d4ff00 !important; color: #111 !important;
    border: none !important; border-radius: 8px !important;
    font-weight: 800 !important; font-size: 13px !important; height: 42px !important;
}
[data-testid="stSidebar"] .stButton > button:hover { background: #c3ec00 !important; }
[data-testid="stSidebar"] [data-baseweb="tag"] { background: #2a2a2a !important; color: #eee !important; }
[data-testid="stSidebar"] input { background: #1e1e1e !important; color: #eee !important; border-color:#333 !important; }

/* ── 헤더 바 ── */
.kream-header {
    background: #111; color: white;
    padding: 0 32px; height: 60px;
    display: flex; align-items: center; justify-content: space-between;
    margin: 0 -32px 28px -32px;
}
.kream-logo { font-size:20px; font-weight:900; letter-spacing:-1px; color:white; }
.kream-logo em { font-style:normal; color:#d4ff00; }
.header-meta { font-size:12px; color:#666; display:flex; align-items:center; gap:16px; }
.live-pill {
    background:#d4ff00; color:#111; font-size:10px; font-weight:900;
    letter-spacing:1.5px; padding:3px 10px; border-radius:20px;
}

/* ── 섹션 타이틀 ── */
.sec-title {
    font-size:14px; font-weight:800; color:#111;
    letter-spacing:0.5px; text-transform:uppercase;
    padding:6px 0 6px 14px; border-left:4px solid #111;
    margin:28px 0 16px 0; background:transparent;
}
.sec-title-accent {
    font-size:14px; font-weight:800; color:#111;
    letter-spacing:0.5px; text-transform:uppercase;
    padding:6px 0 6px 14px; border-left:4px solid #d4ff00;
    background: linear-gradient(90deg,rgba(212,255,0,0.08) 0%,transparent 60%);
    margin:28px 0 16px 0;
}
.sec-title-muted {
    font-size:13px; font-weight:700; color:#555;
    letter-spacing:0.5px; text-transform:uppercase;
    padding:6px 0 6px 12px; border-left:3px solid #ccc;
    margin:28px 0 16px 0;
}

/* ── KPI 카드 ── */
.kpi-card {
    background:#fff; border:1.5px solid #e8e8e8;
    border-radius:14px; padding:22px 20px 18px;
    transition: box-shadow .2s, border-color .2s;
    position: relative; overflow: hidden;
}
.kpi-card:hover { box-shadow:0 8px 30px rgba(0,0,0,0.10); border-color:#ccc; }
.kpi-card::before {
    content:''; position:absolute; top:0; left:0; right:0; height:4px;
    background: var(--accent, #111);
}
.kpi-tag { font-size:10px; font-weight:800; letter-spacing:1.2px; text-transform:uppercase; color:#999; margin-bottom:10px; }
.kpi-num { font-size:36px; font-weight:900; color:#111; line-height:1; letter-spacing:-2px; }
.kpi-num-unit { font-size:16px; font-weight:700; color:#777; margin-left:2px; }
.kpi-sub { font-size:11px; color:#aaa; margin-top:8px; font-weight:500; }
.kpi-badge {
    display:inline-block; font-size:10px; font-weight:800;
    padding:2px 8px; border-radius:20px; margin-top:6px;
    letter-spacing:0.5px;
}

/* ── WIP 구분 카드 ── */
.wip-type-header {
    font-size:11px; font-weight:800; letter-spacing:1px; text-transform:uppercase;
    color:#fff; padding:5px 12px; border-radius:6px; display:inline-block;
    margin-bottom:10px;
}
.wip-row {
    display:flex; align-items:center; justify-content:space-between;
    padding:10px 14px; border-bottom:1px solid #f0f0f0;
    border-radius:8px; margin-bottom:4px; background:#fafafa;
    transition: background .15s;
}
.wip-row:hover { background:#f0f0f0; }
.wip-brand { font-size:13px; font-weight:700; color:#111; }
.wip-meta  { font-size:11px; color:#999; margin-top:2px; }
.wip-stage-pill {
    font-size:10px; font-weight:800; padding:3px 10px;
    border-radius:20px; letter-spacing:0.5px; white-space:nowrap;
}

/* ── 탭 ── */
.stTabs [data-baseweb="tab-list"] {
    gap:0; background:transparent; padding:0;
    border-bottom:2px solid #e8e8e8; margin-bottom:20px;
}
.stTabs [data-baseweb="tab"] {
    border-radius:0; font-weight:700; font-size:13px;
    height:46px; padding:0 22px;
    border-bottom:2px solid transparent !important;
    background:transparent !important; color:#aaa !important;
    margin-bottom:-2px;
}
.stTabs [aria-selected="true"] {
    border-bottom:2px solid #111 !important; color:#111 !important;
}

/* ── 차트 래퍼 ── */
.chart-wrap {
    background:white; border:1.5px solid #e8e8e8;
    border-radius:14px; padding:20px;
}

/* ── 마스터 테이블 래퍼 ── */
.master-wrap {
    background:white; border:1.5px solid #e8e8e8;
    border-radius:14px; padding:24px;
}

/* ── 필터 칩 라벨 ── */
.filter-label {
    font-size:10px; font-weight:800; letter-spacing:1px;
    text-transform:uppercase; color:#555; margin-bottom:4px;
}

/* ── 구분선 ── */
.k-div { border:none; border-top:1px solid #e8e8e8; margin:28px 0; }

/* ── 메트릭 override ── */
[data-testid="stMetricValue"] { font-size:28px !important; font-weight:900 !important; color:#111 !important; }
[data-testid="stMetricLabel"] { font-size:11px !important; color:#888 !important; font-weight:700 !important; }
[data-testid="metric-container"] {
    background:white !important; border:1.5px solid #e8e8e8 !important;
    border-radius:12px !important; padding:16px !important;
}

/* ── 데이터프레임 ── */
[data-testid="stDataFrameResizable"] thead tr th {
    background: #f8f8f8 !important;
    font-weight: 800 !important;
    font-size: 12px !important;
    color: #333 !important;
    border-bottom: 2px solid #e8e8e8 !important;
}

/* ── 스크롤바 ── */
::-webkit-scrollbar { width:6px; height:6px; }
::-webkit-scrollbar-track { background:#f5f5f5; }
::-webkit-scrollbar-thumb { background:#ccc; border-radius:3px; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 1. CONSTANTS
# ─────────────────────────────────────────────
SPREADSHEET_ID  = "1e-uxQVNCCF3qS8e3a_S8sZbCx5qj343ycsEfkIF2POA"
SHEET_NAME      = "Summary"
FIXED_REVIEWERS = ["오홍석", "유지윤", "전현희", "장근수"]

TRUE_VALUES = {"true", "1", "y", "yes", "완료", "o", "v", "✓", "check", "checked"}

STAGE_COLORS = {
    "5.등록 완료":      "#05c072",
    "4.구매 완료":      "#3b82f6",
    "3.구매 요청":      "#8b5cf6",
    "2.검토/등록 요청": "#f5a623",
    "1.리스트업 완료":  "#888888",
    "0.미진행":         "#cccccc",
    "X.등록 불가":      "#f04452",
}

STAGE_BG = {
    "5.등록 완료":      "rgba(5,192,114,0.12)",
    "4.구매 완료":      "rgba(59,130,246,0.12)",
    "3.구매 요청":      "rgba(139,92,246,0.12)",
    "2.검토/등록 요청": "rgba(245,166,35,0.12)",
    "1.리스트업 완료":  "rgba(136,136,136,0.10)",
    "0.미진행":         "rgba(200,200,200,0.10)",
    "X.등록 불가":      "rgba(240,68,82,0.12)",
}

DELAY_CATEGORY_MAP = {
    "해외배송/리드타임": ["해외배송", "해외 배송", "배송", "입고", "출고", "리드타임", "묶음"],
    "샘플/실물확인":    ["샘플", "실물", "확인후 등록"],
    "가품검수/정가품":  ["가품", "정가품", "검수"],
    "데이터/품번이슈":  ["품번", "sku", "모델명"],
    "가격/운영판단":    ["가격", "원가", "마진", "보류", "불가"],
    "담당자/행정":      ["담당자", "부재", "행정"],
    "구매지연":         ["구매 지연", "구매지연"],
}

CHART_TPL = dict(
    template="plotly_white",
    font=dict(family="Pretendard, -apple-system, sans-serif", size=12, color="#333"),
    margin=dict(l=16, r=16, t=44, b=16),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)

# ─────────────────────────────────────────────
# 2. GOOGLE SHEETS LOADER
# ─────────────────────────────────────────────
def load_from_gsheet():
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds  = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=scopes
        )
        client = gspread.authorize(creds)
        ws     = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        return ws.get_all_values(), None
    except Exception as e:
        return None, str(e)

# ─────────────────────────────────────────────
# 3. DATA HELPERS
# ─────────────────────────────────────────────
def parse_bool(v) -> bool:
    if pd.isna(v) or str(v).strip() == "": return False
    if isinstance(v, bool):   return v
    if isinstance(v, (int, float)): return bool(v)
    return str(v).strip().lower() in TRUE_VALUES

def parse_korean_date(v):
    s = str(v).strip()
    if s in ["", "-", "#REF!", "nan", "None", "NaT"]: return pd.NaT
    for fmt in ["%y.%m.%d", "%Y.%m.%d", "%Y-%m-%d", "%y-%m-%d"]:
        try:    return pd.to_datetime(s, format=fmt)
        except: pass
    return pd.to_datetime(s, errors="coerce")

def has_date_value(v) -> bool:
    s = str(v).strip() if pd.notna(v) else ""
    return s not in ["", "nan", "NaT", "#REF!", "-", "None"]

def safe_rate(num, den) -> float:
    try:
        n, d = float(num), float(den)
        return round((n / d) * 100, 1) if d > 0 else 0.0
    except: return 0.0

def classify_delay(reason: str) -> str:
    if not reason or str(reason).strip() in ["-", "", "nan"]: return "없음"
    r = str(reason).lower()
    for cat, kws in DELAY_CATEGORY_MAP.items():
        if any(k.lower() in r for k in kws): return cat
    return "기타"

def normalize_requester(v) -> str:
    if pd.isna(v) or str(v).strip() == "": return "미입력"
    return re.split(r"[,/|·\n\s]+", str(v).strip())[0].strip()

# ─────────────────────────────────────────────
# 4. PREPROCESSING ENGINE
# ─────────────────────────────────────────────
def _build_df(values: list) -> pd.DataFrame:
    # 헤더 행 고정 (3행 = Index 2)
    header_idx = 2
    header = [str(c).strip() for c in values[header_idx]]
    df_raw = pd.DataFrame(values[header_idx + 1:], columns=header)

    # 유효 데이터 필터링 (브랜드명이 있는 경우만)
    df = df_raw[df_raw["브랜드(영문)"].apply(lambda x: bool(str(x).strip()) and str(x).strip() not in ["", "nan"])].copy()

    # 날짜 처리
    df["등록완료일_dt"] = df["등록 완료일"].apply(parse_korean_date)
    df["등록요청일_dt"] = df["등록 요청일"].apply(parse_korean_date)

    # TypeError 방지: 년도와 월을 float64로 저장
    df["년도"]   = df["등록완료일_dt"].dt.year.astype("float64")
    df["월"]     = df["등록완료일_dt"].dt.month.astype("float64")
    df["년월"]   = df["등록완료일_dt"].dt.strftime("%Y-%m")
    
    iso = df["등록완료일_dt"].dt.isocalendar()
    df["ISO년도"] = iso.year.astype("float64")
    df["주차"]    = iso.week.astype("float64")
    df["년주차"]  = iso.year.astype(str) + "-W" + iso.week.astype(str).str.zfill(2)
    df["분기"]    = "Q" + df["등록완료일_dt"].dt.quarter.astype(str)
    df["년분기"]  = df["년도"].astype(str) + "-" + df["분기"]

    # 리드타임
    df["리드타임"] = (df["등록완료일_dt"] - df["등록요청일_dt"]).dt.days
    df["리드타임"] = df["리드타임"].where((df["리드타임"] >= 0) & (df["리드타임"] <= 180))

    # 불리언 상태 매핑
    BOOL_MAP = [
        ("리스트업 완료",              "bool_listed"),
        ("검토 및 등록 요청 완료",      "bool_request_done"),
        ("상품 구매 요청",              "bool_purchase_req"),
        ("상품 구매 완료",              "bool_purchase_done"),
        ("등록 완료 (앱 노출 시 체크)", "bool_reg_done"),
    ]
    for src, dst in BOOL_MAP:
        df[dst] = df[src].apply(parse_bool) if src in df.columns else False

    # ★ WIP 로직 정확도 보정 (홍석님 요청 사항 반영)
    df["bool_h_filled"] = df["등록 요청일"].apply(has_date_value)
    
    # 등록 진행중: E열(검토요청) 완료 & H열(등록요청일) 기입 & I열(등록완료) 미체크
    df["is_reg_wip"] = (df["bool_request_done"] & df["bool_h_filled"] & (~df["bool_reg_done"]))
    
    # 검토 진행중: D열(리스트업) 완료 & E열(검토요청) 미체크
    df["is_rev_wip"] = (df["bool_listed"] & (~df["bool_request_done"]))

    # 텍스트 및 카테고리 정제
    df["국내해외"]    = df["국내/해외"].apply(lambda x: "국내" if "국내" in str(x) else ("해외" if "해외" in str(x) else "미입력"))
    df["요청자_정제"] = df["요청자"].apply(normalize_requester)
    df["검토자_정제"] = df["검토자"].apply(lambda x: str(x).strip() if pd.notna(x) and str(x).strip() != "" else "미입력")
    df["비고_text"]   = df["비고"].apply(lambda x: str(x).strip() if pd.notna(x) else "")
    df["지연분류"]    = df["지연 사유"].apply(classify_delay)
    df["지연여부"]    = df["지연분류"].apply(lambda x: "지연" if x != "없음" else "정상")

    def get_stage(row):
        bigo = row["비고_text"]
        if "등록 불가" in bigo or ("불가" in bigo and "확인" not in bigo): return "X.등록 불가"
        if row["bool_reg_done"]:      return "5.등록 완료"
        if row["bool_purchase_done"]: return "4.구매 완료"
        if row["bool_purchase_req"]:  return "3.구매 요청"
        if row["bool_request_done"]:  return "2.검토/등록 요청"
        if row["bool_listed"]:        return "1.리스트업 완료"
        return "0.미진행"

    df["현재단계"] = df.apply(get_stage, axis=1)
    return df

@st.cache_data(ttl=300, show_spinner=False)
def preprocess_bytes(raw_bytes: bytes) -> pd.DataFrame:
    raw  = pd.read_excel(io.BytesIO(raw_bytes), sheet_name="Summary", header=None)
    vals = raw.fillna("").astype(str).values.tolist()
    return _build_df(vals)

@st.cache_data(ttl=300, show_spinner=False)
def preprocess_gsheet(_cache_key: str, values: list) -> pd.DataFrame:
    return _build_df(values)

# ─────────────────────────────────────────────
# 5. SIDEBAR
# ─────────────────────────────────────────────
def render_sidebar(df: pd.DataFrame):
    with st.sidebar:
        st.markdown("""
        <div style='padding:20px 16px 14px;border-bottom:1px solid #1e1e1e;'>
          <div style='font-size:22px;font-weight:900;color:white;letter-spacing:-1px;line-height:1;'>
            OPS<em style='font-style:normal;color:#d4ff00;'>·</em>INTEL
          </div>
          <div style='font-size:9px;color:#444;margin-top:4px;letter-spacing:2px;font-weight:700;'>
            1P PRODUCT REGISTRATION
          </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='padding:14px 0 6px;'>", unsafe_allow_html=True)
        if st.button("↻  구글 시트 동기화", use_container_width=True, type="primary"):
            with st.spinner("연결 중..."):
                vals, err = load_from_gsheet()
            if err:
                st.error(f"연결 실패: {err}")
            else:
                preprocess_gsheet.clear()
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.session_state.update({
                    "gsheet_values": vals,
                    "gsheet_fetched_at": ts,
                    "data_source": "gsheet",
                })
                st.success("동기화 완료")
                time.sleep(0.5)
                st.rerun()

        if "gsheet_fetched_at" in st.session_state:
            st.markdown(
                f"<div style='font-size:10px;color:#444;text-align:center;padding:5px 0;'>"
                f"Last sync · {st.session_state['gsheet_fetched_at']}</div>",
                unsafe_allow_html=True
            )

        st.markdown(
            "<p style='color:#3a3a3a;font-size:10px;margin:12px 0 3px;font-weight:700;letter-spacing:0.5px;'>"
            "보조 — XLSX 업로드</p>",
            unsafe_allow_html=True
        )
        uploaded = st.file_uploader("", type=["xlsx"], label_visibility="collapsed")
        if uploaded:
            preprocess_bytes.clear()
            st.session_state["xlsx_bytes"]  = uploaded.read()
            st.session_state["data_source"] = "xlsx"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

        src   = st.session_state.get("data_source", "none")
        label = {"gsheet": "● Google Sheet", "xlsx": "● Excel 파일"}.get(src, "● 연결 없음")
        color = {"gsheet": "#d4ff00", "xlsx": "#f5a623"}.get(src, "#444")
        st.markdown(
            f"<div style='font-size:11px;color:{color};text-align:center;padding:4px 0 12px;font-weight:700;'>"
            f"{label}</div>",
            unsafe_allow_html=True
        )

        st.markdown(
            "<div style='border-top:1px solid #1e1e1e;padding:14px 0 0;'>"
            "<p style='color:#3a3a3a;font-size:9px;letter-spacing:2px;font-weight:800;margin-bottom:12px;'>"
            "FILTERS</p>",
            unsafe_allow_html=True
        )

        avail_rev = [r for r in FIXED_REVIEWERS if r in df["검토자_정제"].unique()]
        f_rev     = st.multiselect("검토자", options=FIXED_REVIEWERS, default=avail_rev)

        country_opts = sorted(df["국내해외"].unique().tolist())
        f_country    = st.multiselect("국내 / 해외", options=country_opts, default=country_opts)

        year_opts = sorted([float(y) for y in df["년도"].dropna().unique().tolist()])
        f_year    = st.multiselect("분석 연도", options=year_opts, default=[2024.0, 2025.0, 2026.0])

        stage_opts = sorted(df["현재단계"].unique().tolist())
        f_stage    = st.multiselect("진행 단계", options=stage_opts, default=stage_opts)

        f_delay = st.multiselect("지연 여부", options=["정상", "지연"], default=["정상", "지연"])
        keyword = st.text_input("브랜드 / 비고 검색", placeholder="Jellycat…")

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='border-top:1px solid #1e1e1e;padding:10px 0 0;"
            f"font-size:10px;color:#333;text-align:center;'>"
            f"Rows · {len(df):,} &nbsp;|&nbsp; {datetime.now().strftime('%Y-%m-%d')}</div>",
            unsafe_allow_html=True
        )

    return f_rev, f_country, f_year, f_stage, f_delay, keyword

# ─────────────────────────────────────────────
# 6. LANDING PAGE
# ─────────────────────────────────────────────
def render_landing():
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("""
        <div style='text-align:center;padding:100px 0 32px 0;'>
          <div style='font-size:52px;font-weight:900;letter-spacing:-2px;color:#111;line-height:1;'>
            OPS<em style='font-style:normal;background:#111;color:#d4ff00;
            padding:2px 8px;border-radius:6px;'>·</em>INTEL
          </div>
          <p style='color:#999;font-size:13px;margin-top:12px;letter-spacing:1px;font-weight:600;'>
            1P PRODUCT REGISTRATION · C-LEVEL DASHBOARD
          </p>
        </div>
        <div style='background:#111;border-radius:16px;padding:30px;'>
          <p style='color:#d4ff00;font-size:10px;font-weight:800;letter-spacing:2px;margin:0 0 16px;'>
            QUICK START
          </p>
          <ol style='color:#aaa;line-height:2.4;font-size:14px;margin:0;padding-left:20px;'>
            <li>왼쪽 사이드바 → <b style='color:white;'>↻ 구글 시트 동기화</b> 클릭</li>
            <li>자동으로 실시간 데이터 로드 및 분석 시작</li>
            <li>필터로 검토자 / 연도 / 단계 조정</li>
          </ol>
          <div style='margin-top:20px;border-top:1px solid #222;padding-top:14px;
                      font-size:11px;color:#444;'>
            Sheet ID · 1e-uxQVNCCF3qS8e3a_S8sZbCx5qj343ycsEfkIF2POA
          </div>
        </div>
        """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 7. WIP 상세 패널 렌더
# ─────────────────────────────────────────────
def render_wip_panel(df_kpi: pd.DataFrame):
    reg_wip = df_kpi[df_kpi["is_reg_wip"]].copy()
    rev_wip = df_kpi[df_kpi["is_rev_wip"]].copy()

    total_wip = len(reg_wip) + len(rev_wip)

    col_kpi, col_detail = st.columns([2, 8])

    with col_kpi:
        st.markdown(f"""
        <div class='kpi-card' style='--accent:#f5a623; height:100%;'>
          <div class='kpi-tag'>진행 중 WIP</div>
          <div class='kpi-num'>{total_wip:,}<span class='kpi-num-unit'>건</span></div>
          <div style='margin-top:12px;'>
            <div style='display:flex;justify-content:space-between;align-items:center;
                        background:#fff9f0;border-radius:8px;padding:8px 12px;margin-bottom:6px;'>
              <span style='font-size:11px;font-weight:700;color:#f5a623;'>등록 진행중</span>
              <span style='font-size:20px;font-weight:900;color:#f5a623;'>{len(reg_wip)}</span>
            </div>
            <div style='display:flex;justify-content:space-between;align-items:center;
                        background:#f0f7ff;border-radius:8px;padding:8px 12px;'>
              <span style='font-size:11px;font-weight:700;color:#3b82f6;'>검토 진행중</span>
              <span style='font-size:20px;font-weight:900;color:#3b82f6;'>{len(rev_wip)}</span>
            </div>
          </div>
          <div class='kpi-sub' style='margin-top:10px;'>등록완료·불가 제외</div>
        </div>
        """, unsafe_allow_html=True)

    with col_detail:
        tab_r, tab_v = st.tabs([
            f"🟠 등록 진행중 ({len(reg_wip)}건) — E열 ✓ · H열 기입 · I열 미체크",
            f"🔵 검토 진행중 ({len(rev_wip)}건) — D열 ✓ · E열 미체크"
        ])

        SHOW_COLS = ["브랜드(영문)", "요청자_정제", "검토자_정제",
                     "국내해외", "현재단계", "등록 요청일", "리드타임", "비고_text"]
        COL_RENAME = {
            "브랜드(영문)": "브랜드", "요청자_정제": "요청자",
            "검토자_정제": "검토자", "비고_text": "비고",
        }

        def stage_color_map(val):
            c  = STAGE_COLORS.get(val, "#888")
            bg = STAGE_BG.get(val, "rgba(200,200,200,0.1)")
            return f"background-color:{bg};color:{c};font-weight:800;"

        with tab_r:
            if reg_wip.empty:
                st.success("등록 진행중 브랜드가 없습니다.")
            else:
                show = reg_wip[SHOW_COLS].rename(columns=COL_RENAME).sort_values("리드타임", ascending=False)
                st.dataframe(
                    show.style.map(stage_color_map, subset=["현재단계"]),
                    use_container_width=True, hide_index=True, height=260
                )

        with tab_v:
            if rev_wip.empty:
                st.success("검토 진행중 브랜드가 없습니다.")
            else:
                show = rev_wip[SHOW_COLS].rename(columns=COL_RENAME)
                st.dataframe(
                    show.style.map(stage_color_map, subset=["현재단계"]),
                    use_container_width=True, hide_index=True, height=260
                )

# ─────────────────────────────────────────────
# 8. DASHBOARD
# ─────────────────────────────────────────────
def render_dashboard(df_filtered: pd.DataFrame, source: str):

    # KPI 기준: 24~26년
    df_kpi = df_filtered[df_filtered["년도"].isin([2024.0, 2025.0, 2026.0])].copy()
    # 심화 분석 기준: 24년 이후
    df_24  = df_filtered[df_filtered["등록완료일_dt"] >= "2024-01-01"].copy()

    # ── 헤더 ──
    ts  = st.session_state.get("gsheet_fetched_at", datetime.now().strftime("%Y-%m-%d %H:%M"))
    src = "Google Sheet · LIVE" if source == "gsheet" else "Excel Upload"
    st.markdown(f"""
    <div class='kream-header'>
      <div class='kream-logo'>OPS<em>·</em>INTEL</div>
      <div class='header-meta'>
        <span>{src} · {ts}</span>
        <span class='live-pill'>LIVE</span>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # ══════════════════════════════════════════
    # SECTION 1 — KPI (2024–2026)
    # ══════════════════════════════════════════
    st.markdown("<div class='sec-title'>종합 핵심 운영 지표 · 2024–2026</div>", unsafe_allow_html=True)

    total_k    = len(df_kpi)
    reg_done_k = int(df_kpi["bool_reg_done"].sum())
    lt_avg_k   = df_kpi["리드타임"].mean()
    lt_med_k   = df_kpi["리드타임"].median()
    delayed_k  = int((df_kpi["지연여부"] == "지연").sum())
    reg_rate_k = safe_rate(reg_done_k, total_k)
    delay_rate_k = safe_rate(delayed_k, total_k)

    k1, k2, k3, k4, k5 = st.columns(5)

    def kcard(col, tag, num, unit, sub, accent, badge_txt="", badge_color="#111"):
        badge_html = f"<div class='kpi-badge' style='background:{badge_color}22;color:{badge_color};'>{badge_txt}</div>" if badge_txt else ""
        col.markdown(f"""
        <div class='kpi-card' style='--accent:{accent};'>
          <div class='kpi-tag'>{tag}</div>
          <div class='kpi-num'>{num}<span class='kpi-num-unit'>{unit}</span></div>
          {badge_html}
          <div class='kpi-sub'>{sub}</div>
        </div>
        """, unsafe_allow_html=True)

    kcard(k1, "전체 분석 건수",  f"{total_k:,}",    "건",
          "2024–2026 기준", "#111")
    kcard(k2, "최종 등록 완료",  f"{reg_done_k:,}", "건",
          "누적 등록 성공",  "#05c072",
          f"등록률 {reg_rate_k}%", "#05c072")
    kcard(k3, "평균 리드타임",
          f"{lt_avg_k:.1f}" if pd.notna(lt_avg_k) else "N/A", "일",
          f"중앙값 {lt_med_k:.0f}일" if pd.notna(lt_med_k) else "", "#8b5cf6")
    kcard(k4, "지연 발생 건수",  f"{delayed_k:,}",  "건",
          "지연 사유 기입 건",  "#f04452",
          f"지연률 {delay_rate_k}%", "#f04452")
    kcard(k5, "24년+ 분석 건수", f"{len(df_24):,}", "건",
          "심화 분석 대상", "#d4ff00")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── WIP 상세 패널 ──
    st.markdown("<div class='sec-title-accent'>진행 중 브랜드 현황 (WIP)</div>", unsafe_allow_html=True)
    render_wip_panel(df_kpi)

    st.markdown("<hr class='k-div'>", unsafe_allow_html=True)

    # ══════════════════════════════════════════
    # SECTION 2 — 파이프라인 (2024–2026)
    # ══════════════════════════════════════════
    st.markdown("<div class='sec-title'>등록 파이프라인 · 2024–2026</div>", unsafe_allow_html=True)

    p1, p2, p3 = st.columns(3)

    with p1:
        fig = go.Figure(go.Funnel(
            y=["리스트업 완료", "검토/등록 요청", "구매 완료", "최종 등록"],
            x=[int(df_kpi["bool_listed"].sum()), int(df_kpi["bool_request_done"].sum()),
               int(df_kpi["bool_purchase_done"].sum()), int(df_kpi["bool_reg_done"].sum())],
            textinfo="value+percent previous",
            textfont=dict(size=13, color="#fff"),
            marker=dict(color=["#555", "#777", "#999", "#05c072"]),
            connector=dict(line=dict(color="#eee", width=2)),
        ))
        fig.update_layout(**CHART_TPL, title="<b>등록 전환 Funnel</b>", height=320)
        st.plotly_chart(fig, use_container_width=True)

    with p2:
        sc = df_kpi["현재단계"].value_counts().reset_index()
        sc.columns = ["단계", "건수"]
        fig = go.Figure(go.Pie(
            labels=sc["단계"], values=sc["건수"], hole=0.62,
            marker=dict(colors=[STAGE_COLORS.get(s, "#ccc") for s in sc["단계"]],
                        line=dict(color="#fff", width=2)),
            textinfo="percent", textfont=dict(size=12, color="#333"),
        ))
        fig.update_layout(**CHART_TPL, title="<b>단계별 분포</b>", height=320,
                          legend=dict(orientation="v", x=1.02, y=0.5, font=dict(size=11)))
        st.plotly_chart(fig, use_container_width=True)

    with p3:
        cross = (df_kpi[df_kpi["국내해외"].isin(["국내", "해외"])]
                 .groupby(["국내해외", "현재단계"]).size().reset_index(name="건수"))
        fig = px.bar(cross, x="국내해외", y="건수", color="현재단계",
                     color_discrete_map=STAGE_COLORS, barmode="stack",
                     title="<b>국내 / 해외별 단계</b>")
        fig.update_layout(**CHART_TPL, height=320,
                          legend=dict(orientation="v", x=1.02, y=0.5, font=dict(size=11)))
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("<hr class='k-div'>", unsafe_allow_html=True)

    # ══════════════════════════════════════════
    # SECTION 3 — 24년+ 심화 분석
    # ══════════════════════════════════════════
    st.markdown("<div class='sec-title'>2024+ 운영 트렌드 심화 분석</div>", unsafe_allow_html=True)

    if df_24.empty:
        st.info("선택 필터 내 2024년 이후 데이터가 없습니다.")
    else:
        tab1, tab2, tab3, tab4 = st.tabs([
            "시계열 트렌드", "리드타임 Deep-Dive", "지연 분석", "담당자 성과"
        ])

        with tab1:
            view  = st.radio("집계 단위", ["월별", "주차별", "분기별"], horizontal=True)
            g_col = {"월별": "년월", "주차별": "년주차", "분기별": "년분기"}[view]
            ts_df = df_24.dropna(subset=[g_col]).groupby(g_col).agg(
                등록완료=("bool_reg_done", "sum"),
                전체건수=("bool_reg_done", "count"),
                평균리드타임=("리드타임", "mean"),
            ).reset_index()
            ts_df.columns = ["기간", "등록완료", "전체건수", "평균리드타임"]
            
            # TypeError 해결: float64 변환 후 나눗셈
            ts_df["등록률"] = (ts_df["등록완료"].astype(float) / ts_df["전체건수"].astype(float) * 100).round(1)

            fig = make_subplots(rows=2, cols=1,
                                subplot_titles=("등록 완료 vs 전체 건수", "등록률 (%)"),
                                vertical_spacing=0.14, shared_xaxes=True)
            fig.add_trace(go.Bar(x=ts_df["기간"], y=ts_df["전체건수"],
                                  name="전체", marker_color="#ebebeb"), row=1, col=1)
            fig.add_trace(go.Bar(x=ts_df["기간"], y=ts_df["등록완료"],
                                  name="등록완료", marker_color="#111"), row=1, col=1)
            fig.add_trace(go.Scatter(x=ts_df["기간"], y=ts_df["등록률"],
                                      name="등록률", mode="lines+markers",
                                      line=dict(color="#05c072", width=2.5),
                                      marker=dict(size=6),
                                      fill="tozeroy",
                                      fillcolor="rgba(5,192,114,0.08)"),
                          row=2, col=1)
            fig.update_layout(**CHART_TPL, height=460, barmode="overlay",
                               title_text=f"<b>{view} 등록 현황 (2024+)</b>")
            fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
            st.plotly_chart(fig, use_container_width=True)
            with st.expander("상세 수치 테이블"):
                st.dataframe(ts_df.style.format({
                    "등록완료": "{:,}", "전체건수": "{:,}",
                    "평균리드타임": "{:.1f}", "등록률": "{:.1f}%"
                }), use_container_width=True, hide_index=True)

        with tab2:
            lt = df_24[df_24["리드타임"].notna()].copy()
            r1, r2 = st.columns(2)
            with r1:
                fig = px.box(lt, x="국내해외", y="리드타임", color="국내해외",
                             title="<b>국내/해외 리드타임 분포</b>", points="outliers",
                             color_discrete_map={"국내": "#111", "해외": "#888", "미입력": "#ccc"})
                fig.update_layout(**CHART_TPL, height=340, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            with r2:
                fig = px.histogram(lt, x="리드타임", color="국내해외",
                                   nbins=30, barmode="overlay", opacity=0.75,
                                   title="<b>리드타임 빈도 분포</b>",
                                   color_discrete_map={"국내": "#111", "해외": "#888", "미입력": "#ccc"})
                fig.update_layout(**CHART_TPL, height=340)
                st.plotly_chart(fig, use_container_width=True)

            stat = lt.groupby("국내해외")["리드타임"].agg(
                건수="count", 평균="mean", 중앙값="median", 최솟값="min", 최댓값="max"
            ).reset_index().round(1)
            st.dataframe(stat.style.format({
                "평균": "{:.1f}일", "중앙값": "{:.1f}일",
                "최솟값": "{:.0f}일", "최댓값": "{:.0f}일"
            }).set_properties(**{"font-weight": "600"}),
            use_container_width=True, hide_index=True)

        with tab3:
            ddf = df_24[df_24["지연여부"] == "지연"]
            ca, cb, cc = st.columns(3)
            ca.metric("지연 건수", f"{len(ddf):,}건",  delta=None)
            cb.metric("정상 건수", f"{len(df_24)-len(ddf):,}건")
            cc.metric("지연률",    f"{safe_rate(len(ddf), len(df_24))}%")

            d1, d2 = st.columns(2)
            with d1:
                dc = df_24["지연분류"].value_counts().reset_index()
                dc.columns = ["분류", "건수"]
                dc = dc[dc["분류"] != "없음"]
                fig = px.bar(dc, y="분류", x="건수", orientation="h",
                             title="<b>지연 사유 유형별 건수</b>",
                             color="건수",
                             color_continuous_scale=["#f0f0f0", "#f04452"])
                fig.update_layout(**CHART_TPL, height=340)
                st.plotly_chart(fig, use_container_width=True)
            with d2:
                dm = df_24.groupby(["년월", "지연여부"]).size().reset_index(name="건수")
                fig = px.bar(dm, x="년월", y="건수", color="지연여부",
                             barmode="stack", title="<b>월별 지연 / 정상 현황</b>",
                             color_discrete_map={"정상": "#05c072", "지연": "#f04452"})
                fig.update_layout(**CHART_TPL, height=340)
                st.plotly_chart(fig, use_container_width=True)

        with tab4:
            pr = df_24.groupby("검토자_정제").agg(
                담당건수=("bool_reg_done", "count"),
                등록완료=("bool_reg_done", "sum"),
                평균리드타임=("리드타임", "mean"),
                지연건수=("지연여부", lambda x: (x == "지연").sum()),
            ).reset_index()
            pr["등록률"] = (pr["등록완료"].astype(float) / pr["담당건수"].astype(float) * 100).round(1)
            pr["지연률"] = (pr["지연건수"].astype(float) / pr["담당건수"].astype(float) * 100).round(1)
            pr = pr.sort_values("담당건수", ascending=False)

            fig = make_subplots(rows=1, cols=3,
                                subplot_titles=("담당 건수", "등록률 (%)", "평균 리드타임 (일)"))
            for i, (col_, color) in enumerate([
                ("담당건수", "#111"), ("등록률", "#05c072"), ("평균리드타임", "#f5a623")
            ]):
                fig.add_trace(go.Bar(
                    x=pr["검토자_정제"], y=pr[col_].round(1), name=col_,
                    marker_color=color,
                    text=pr[col_].round(1), textposition="outside",
                    textfont=dict(size=12, color="#333"),
                ), row=1, col=i+1)
            fig.update_layout(**CHART_TPL, height=340, showlegend=False,
                               title_text="<b>검토자별 운영 성과 (2024+)</b>")
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("<hr class='k-div'>", unsafe_allow_html=True)

    # ══════════════════════════════════════════
    # SECTION 4 — YoY
    # ══════════════════════════════════════════
    st.markdown("<div class='sec-title-muted'>연도별 YoY 성과 비교 · 2023–2026</div>", unsafe_allow_html=True)

    yoy = df_filtered.groupby("년도").agg(
        전체건수=("bool_reg_done", "count"),
        등록완료=("bool_reg_done", "sum"),
        평균리드타임=("리드타임", "mean"),
        지연건수=("지연여부", lambda x: (x == "지연").sum()),
    ).reset_index().dropna(subset=["년도"])
    
    # TypeError 해결: float64 변환
    yoy["등록률"] = (yoy["등록완료"].astype(float) / yoy["전체건수"].astype(float) * 100).round(1)
    yoy["지연률"] = (yoy["지연건수"].astype(float) / yoy["전체건수"].astype(float) * 100).round(1)
    yoy["년도"]   = yoy["년도"].astype(int).astype(str)

    y1, y2 = st.columns(2)
    with y1:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=yoy["년도"], y=yoy["전체건수"],
                              name="전체", marker_color="#e8e8e8",
                              text=yoy["전체건수"], textposition="outside"))
        fig.add_trace(go.Bar(x=yoy["년도"], y=yoy["등록완료"],
                              name="등록완료", marker_color="#111",
                              text=yoy["등록완료"], textposition="outside"))
        fig.update_layout(**CHART_TPL, title="<b>연도별 전체 vs 등록완료</b>",
                          barmode="overlay", height=320)
        st.plotly_chart(fig, use_container_width=True)
    with y2:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=yoy["년도"], y=yoy["평균리드타임"].round(1),
                              name="리드타임(일)", marker_color="#555",
                              text=yoy["평균리드타임"].round(1),
                              textposition="outside"), secondary_y=False)
        fig.add_trace(go.Scatter(x=yoy["년도"], y=yoy["지연률"], name="지연률(%)",
                                  mode="lines+markers+text",
                                  text=yoy["지연률"].astype(str) + "%",
                                  textposition="top center",
                                  textfont=dict(color="#f04452", size=12),
                                  line=dict(color="#f04452", width=2.5),
                                  marker=dict(size=8, color="#f04452")),
                      secondary_y=True)
        fig.update_layout(**CHART_TPL, title="<b>연도별 리드타임 vs 지연률</b>", height=320)
        fig.update_yaxes(title_text="리드타임(일)", secondary_y=False, showgrid=True, gridcolor="#f0f0f0")
        fig.update_yaxes(title_text="지연률(%)",    secondary_y=True,  showgrid=False)
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        yoy.style
           .format({"전체건수": "{:,}", "등록완료": "{:,}", "지연건수": "{:,}",
                    "평균리드타임": "{:.1f}일", "등록률": "{:.1f}%", "지연률": "{:.1f}%"})
           .background_gradient(subset=["등록률"], cmap="Greens")
           .background_gradient(subset=["지연률"], cmap="Reds")
           .set_properties(**{"font-weight": "600", "font-size": "13px"}),
        use_container_width=True, hide_index=True
    )

    st.markdown("<hr class='k-div'>", unsafe_allow_html=True)

    # ══════════════════════════════════════════
    # SECTION 5 — 마스터 트래킹
    # ══════════════════════════════════════════
    st.markdown("<div class='sec-title-muted'>마스터 업무 트래킹 · 2023–2026 전체 Raw</div>",
                unsafe_allow_html=True)

    col_show = ["브랜드(영문)", "요청자_정제", "검토자_정제", "국내해외",
                "현재단계", "지연분류", "리드타임", "년월", "비고_text"]
    df_master = df_filtered[col_show].copy().rename(columns={
        "브랜드(영문)": "브랜드", "요청자_정제": "요청자", "검토자_정제": "검토자",
        "비고_text": "비고", "년월": "등록년월"
    })

    st.markdown("<div class='master-wrap'>", unsafe_allow_html=True)
    fc1, fc2, fc3, fc4, fc5, fc6 = st.columns(6)

    def col_sel(container, label, series, key):
        opts = ["전체"] + sorted([x for x in series.dropna().unique() if str(x).strip() not in ["", "nan"]])
        return container.selectbox(label, options=opts, key=key, index=0)

    sel_rev   = col_sel(fc1, "검토자",   df_master["검토자"],   "mf_rev")
    sel_req   = col_sel(fc2, "요청자",   df_master["요청자"],   "mf_req")
    sel_nat   = col_sel(fc3, "국내/해외", df_master["국내해외"], "mf_nat")
    sel_stage = col_sel(fc4, "현재단계",  df_master["현재단계"], "mf_stage")
    sel_delay = col_sel(fc5, "지연분류",  df_master["지연분류"], "mf_delay")
    sel_month = col_sel(fc6, "등록년월",  df_master["등록년월"], "mf_month")

    df_view = df_master.copy()
    if sel_rev   != "전체": df_view = df_view[df_view["검토자"]   == sel_rev]
    if sel_req   != "전체": df_view = df_view[df_view["요청자"]   == sel_req]
    if sel_nat   != "전체": df_view = df_view[df_view["국내해외"] == sel_nat]
    if sel_stage != "전체": df_view = df_view[df_view["현재단계"]  == sel_stage]
    if sel_delay != "전체": df_view = df_view[df_view["지연분류"]  == sel_delay]
    if sel_month != "전체": df_view = df_view[df_view["등록년월"]  == sel_month]

    sc1, _ = st.columns([2, 8])
    sort_by = sc1.selectbox("정렬 기준", ["등록년월 (최신순)", "리드타임 (내림차순)", "현재단계"], key="master_sort")
    if sort_by == "등록년월 (최신순)":     df_view = df_view.sort_values("등록년월", ascending=False)
    elif sort_by == "리드타임 (내림차순)": df_view = df_view.sort_values("리드타임", ascending=False)
    else:                                  df_view = df_view.sort_values("현재단계")

    def stage_color_f(val):
        c, bg = STAGE_COLORS.get(val, "#888"), STAGE_BG.get(val, "rgba(200,200,200,0.1)")
        return f"background-color:{bg};color:{c};font-weight:800;"

    st.dataframe(
        df_view.style.map(stage_color_f, subset=["현재단계"]),
        use_container_width=True, hide_index=True, height=480
    )
    st.markdown("</div>", unsafe_allow_html=True)


# ─────────────────────────────────────────────
# 9. MAIN
# ─────────────────────────────────────────────
def main():
    source = st.session_state.get("data_source", "none")

    if source == "gsheet" and "gsheet_values" in st.session_state:
        cache_key = st.session_state.get("gsheet_fetched_at", "")
        df_full   = preprocess_gsheet(cache_key, st.session_state["gsheet_values"])
    elif source == "xlsx" and "xlsx_bytes" in st.session_state:
        df_full   = preprocess_bytes(st.session_state["xlsx_bytes"])
    else:
        has_secret = False
        try:
            _ = st.secrets["gcp_service_account"]
            has_secret = True
        except Exception: pass

        if has_secret and "auto_tried" not in st.session_state:
            st.session_state["auto_tried"] = True
            with st.spinner("구글 시트 자동 연결 중..."):
                vals, err = load_from_gsheet()
            if not err:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.session_state.update({"gsheet_values": vals, "gsheet_fetched_at": ts, "data_source": "gsheet"})
                st.rerun()
            else: render_landing(); return
        else: render_landing(); return

    f_rev, f_country, f_year, f_stage, f_delay, keyword = render_sidebar(df_full)

    dff = df_full.copy()
    if f_rev:     dff = dff[dff["검토자_정제"].isin(f_rev)]
    if f_country: dff = dff[dff["국내해외"].isin(f_country)]
    if f_year:    dff = dff[dff["년도"].isin(f_year)]
    if f_stage:   dff = dff[dff["현재단계"].isin(f_stage)]
    if f_delay:   dff = dff[dff["지연여부"].isin(f_delay)]
    if keyword:   dff = dff[dff.apply(lambda r: keyword.strip().lower() in str(r).lower(), axis=1)]

    render_dashboard(dff, source)

if __name__ == "__main__":
    main()
