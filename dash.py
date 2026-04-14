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
# KREAM-inspired CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@300;400;500;600;700;800;900&display=swap');
 
/* ── 전역 ── */
html, body, [class*="css"], .stMarkdown, .stText {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}
.main, .block-container {
    background: #fafafa !important;
    padding-top: 0 !important;
}
.block-container { max-width: 100% !important; padding: 0 32px 40px 32px !important; }
 
/* ── 사이드바 ── */
[data-testid="stSidebar"] {
    background: #111111 !important;
    border-right: 1px solid #222 !important;
}
[data-testid="stSidebar"] > div { padding-top: 0 !important; }
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMultiSelect label,
[data-testid="stSidebar"] .stTextInput label { color: #aaaaaa !important; font-size: 11px !important; }
[data-testid="stSidebar"] .stButton > button {
    background: #ffffff !important; color: #111 !important;
    border: none !important; border-radius: 6px !important;
    font-weight: 700 !important; font-size: 13px !important;
    height: 40px !important;
}
[data-testid="stSidebar"] .stButton > button:hover { background: #e5e5e5 !important; }
[data-testid="stSidebar"] [data-baseweb="tag"] {
    background: #333 !important; color: #fff !important;
}
 
/* ── 탑 헤더 바 ── */
.kream-header {
    background: #111111;
    color: white;
    padding: 0 32px;
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 0 -32px 28px -32px;
    position: sticky;
    top: 0;
    z-index: 100;
}
.kream-logo {
    font-size: 18px; font-weight: 900; letter-spacing: -0.5px; color: white;
}
.kream-logo span { color: #ccff00; }
.kream-header-right { display: flex; align-items: center; gap: 16px; }
.live-dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: #ccff00; display: inline-block; margin-right: 5px;
    animation: pulse 1.5s infinite;
}
@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.4} }
.live-badge {
    font-size: 11px; font-weight: 700; color: #ccff00;
    letter-spacing: 1px;
}
.header-ts { font-size: 11px; color: #666; }
 
/* ── 섹션 타이틀 ── */
.sec-title {
    font-size: 13px; font-weight: 700; color: #111;
    letter-spacing: 0.8px; text-transform: uppercase;
    border-left: 3px solid #111; padding-left: 10px;
    margin: 28px 0 14px 0;
}
.sec-title-gray {
    font-size: 13px; font-weight: 700; color: #555;
    letter-spacing: 0.8px; text-transform: uppercase;
    border-left: 3px solid #ccc; padding-left: 10px;
    margin: 28px 0 14px 0;
}
 
/* ── KPI 카드 ── */
.kpi-wrap {
    background: #ffffff;
    border: 1px solid #ebebeb;
    border-radius: 12px;
    padding: 20px 20px 16px 20px;
    transition: box-shadow .15s;
}
.kpi-wrap:hover { box-shadow: 0 4px 20px rgba(0,0,0,0.08); }
.kpi-tag {
    font-size: 10px; font-weight: 700; letter-spacing: 1px;
    text-transform: uppercase; color: #999; margin-bottom: 6px;
}
.kpi-num {
    font-size: 32px; font-weight: 900; color: #111;
    line-height: 1; letter-spacing: -1px;
}
.kpi-num-sm { font-size: 24px; }
.kpi-unit { font-size: 14px; font-weight: 600; color: #555; margin-left: 2px; }
.kpi-sub { font-size: 11px; color: #bbb; margin-top: 5px; }
.kpi-accent-green  { border-top: 3px solid #05c072; }
.kpi-accent-black  { border-top: 3px solid #111; }
.kpi-accent-yellow { border-top: 3px solid #f5a623; }
.kpi-accent-red    { border-top: 3px solid #f04452; }
.kpi-accent-purple { border-top: 3px solid #8b5cf6; }
.kpi-accent-lime   { border-top: 3px solid #ccff00; }
 
/* ── 배너 ── */
.banner-live {
    background: #111; color: #ccff00;
    border-radius: 8px; padding: 9px 16px;
    font-size: 12px; font-weight: 600;
    display: flex; align-items: center; gap: 10px;
    margin-bottom: 20px;
}
.banner-excel {
    background: #fffbe6; color: #7a5800;
    border: 1px solid #ffe58f;
    border-radius: 8px; padding: 9px 16px;
    font-size: 12px; font-weight: 600;
    margin-bottom: 20px;
}
 
/* ── 차트 카드 ── */
.chart-card {
    background: white; border: 1px solid #ebebeb;
    border-radius: 12px; padding: 20px;
    margin-bottom: 12px;
}
 
/* ── WIP 팝업 테이블 ── */
.wip-row {
    display: flex; justify-content: space-between; align-items: center;
    padding: 8px 0; border-bottom: 1px solid #f0f0f0;
    font-size: 13px;
}
.wip-brand { font-weight: 600; color: #111; }
.wip-stage-badge {
    font-size: 10px; font-weight: 700; letter-spacing: 0.5px;
    padding: 3px 8px; border-radius: 20px;
    background: #f5f5f5; color: #555;
}
 
/* ── 인터랙티브 테이블 필터 ── */
.filter-chip-row { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 8px; }
.filter-chip {
    font-size: 11px; font-weight: 600; padding: 4px 12px;
    border-radius: 20px; border: 1px solid #ddd;
    background: white; color: #555; cursor: pointer;
    transition: all .15s;
}
.filter-chip:hover { border-color: #111; color: #111; }
.filter-chip.active { background: #111; color: white; border-color: #111; }
 
/* ── 탭 ── */
.stTabs [data-baseweb="tab-list"] {
    gap: 0; background: transparent; padding: 0;
    border-bottom: 1px solid #ebebeb; margin-bottom: 20px;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 0; font-weight: 600; font-size: 13px;
    height: 44px; padding: 0 20px;
    border-bottom: 2px solid transparent;
    background: transparent !important;
    color: #aaa !important;
}
.stTabs [aria-selected="true"] {
    border-bottom: 2px solid #111 !important;
    color: #111 !important;
}
 
/* ── 데이터프레임 ── */
.stDataFrame { border-radius: 10px; overflow: hidden; border: 1px solid #ebebeb; }
[data-testid="stDataFrameResizable"] { border-radius: 10px; }
 
/* ── 메트릭 override ── */
[data-testid="stMetricValue"] { font-size: 26px !important; font-weight: 900 !important; color: #111 !important; }
[data-testid="stMetricLabel"] { font-size: 11px !important; color: #999 !important; font-weight: 600 !important; }
 
/* ── divider ── */
.k-divider { border: none; border-top: 1px solid #ebebeb; margin: 24px 0; }
 
/* ── raw data 테이블 헤더 ── */
.raw-section {
    background: white; border: 1px solid #ebebeb; border-radius: 12px;
    padding: 24px; margin-top: 8px;
}
</style>
""", unsafe_allow_html=True)
 
# ─────────────────────────────────────────────
# 1. CONSTANTS
# ─────────────────────────────────────────────
SPREADSHEET_ID  = "1e-uxQVNCCF3qS8e3a_S8sZbCx5qj343ycsEfkIF2POA"
SHEET_NAME      = "Summary"
# ★ 요청: 오홍석, 유지윤, 전현희, 장근수 만
FIXED_REVIEWERS = ["오홍석", "유지윤", "전현희", "장근수"]
 
TRUE_VALUES = {"true", "1", "y", "yes", "완료", "o", "v", "✓", "check", "checked"}
 
STAGE_COLORS = {
    "5.등록 완료":      "#05c072",
    "4.구매 완료":      "#3b82f6",
    "3.구매 요청":      "#8b5cf6",
    "2.검토/등록 요청": "#f5a623",
    "1.리스트업 완료":  "#aaaaaa",
    "0.미진행":         "#dddddd",
    "X.등록 불가":      "#f04452",
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
    margin=dict(l=16, r=16, t=40, b=16),
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
    if pd.isna(v) or v == "": return False
    if isinstance(v, bool):   return v
    if isinstance(v, (int, float)): return bool(v)
    return str(v).strip().lower() in TRUE_VALUES
 
def parse_korean_date(v):
    if pd.isna(v) or str(v).strip() in ["", "-", "#REF!", "nan"]: return pd.NaT
    s = str(v).strip()
    for fmt in ["%y.%m.%d", "%Y.%m.%d", "%Y-%m-%d", "%y-%m-%d"]:
        try:    return pd.to_datetime(s, format=fmt)
        except: pass
    return pd.to_datetime(s, errors="coerce")
 
def safe_rate(num, den) -> float:
    return round((num / den) * 100, 1) if den and den > 0 else 0.0
 
def classify_delay(reason: str) -> str:
    if not reason or reason.strip() in ["-", "", "nan"]: return "없음"
    r = reason.lower()
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
    header_idx = 2
    for i, row in enumerate(values[:10]):
        if any("브랜드" in str(c) for c in row):
            header_idx = i
            break
 
    df_raw = pd.DataFrame(values[header_idx + 1:], columns=values[header_idx])
    df_raw.columns = [str(c).strip() for c in df_raw.columns]
 
    df = df_raw[
        df_raw["브랜드(영문)"].apply(
            lambda x: bool(str(x).strip()) and str(x).strip() not in ["", "nan"]
        ) &
        (df_raw["등록 완료일"].astype(str).str.strip() != "#REF!")
    ].copy().reset_index(drop=True)
 
    df["등록완료일_dt"] = df["등록 완료일"].apply(parse_korean_date)
    df["등록요청일_dt"] = df["등록 요청일"].apply(parse_korean_date)
 
    iso = df["등록완료일_dt"].dt.isocalendar()
    df["년도"]   = df["등록완료일_dt"].dt.year.astype("Int64")
    df["월"]     = df["등록완료일_dt"].dt.month.astype("Int64")
    df["년월"]   = df["등록완료일_dt"].dt.strftime("%Y-%m")
    df["분기"]   = "Q" + df["등록완료일_dt"].dt.quarter.astype(str)
    df["년분기"]  = df["년도"].astype(str) + "-" + df["분기"]
    df["ISO년도"] = iso.year.astype("Int64")
    df["주차"]    = iso.week.astype("Int64")
    df["년주차"]  = df["ISO년도"].astype(str) + "-W" + df["주차"].astype(str).str.zfill(2)
 
    df["리드타임"] = (df["등록완료일_dt"] - df["등록요청일_dt"]).dt.days
    df["리드타임"] = df["리드타임"].where((df["리드타임"] >= 0) & (df["리드타임"] <= 180))
 
    for src, dst in [
        ("리스트업 완료",              "bool_listed"),
        ("검토 및 등록 요청 완료",      "bool_request_done"),
        ("상품 구매 요청",              "bool_purchase_req"),
        ("상품 구매 완료",              "bool_purchase_done"),
        ("등록 완료 (앱 노출 시 체크)", "bool_reg_done"),
    ]:
        df[dst] = df[src].apply(parse_bool) if src in df.columns else False
 
    def classify_country(v):
        s = str(v).strip() if pd.notna(v) else ""
        if "국내" in s: return "국내"
        if "해외" in s: return "해외"
        return "미입력"
 
    df["국내해외"]    = df["국내/해외"].apply(classify_country)
    df["요청자_정제"] = df["요청자"].apply(normalize_requester)
    df["검토자_정제"] = df["검토자"].apply(lambda x: str(x).strip() if pd.notna(x) else "미입력")
    df["비고_text"]   = df["비고"].apply(lambda x: str(x).strip() if pd.notna(x) else "")
    df["지연분류"]    = df["지연 사유"].apply(lambda x: classify_delay(str(x)) if pd.notna(x) else "없음")
 
    def get_stage(row):
        bigo = row["비고_text"]
        if "등록 불가" in bigo or ("불가" in bigo and "확인" not in bigo):
            return "X.등록 불가"
        if row["bool_reg_done"]:      return "5.등록 완료"
        if row["bool_purchase_done"]: return "4.구매 완료"
        if row["bool_purchase_req"]:  return "3.구매 요청"
        if row["bool_request_done"]:  return "2.검토/등록 요청"
        if row["bool_listed"]:        return "1.리스트업 완료"
        return "0.미진행"
 
    df["현재단계"] = df.apply(get_stage, axis=1)
    df["지연여부"] = df["지연분류"].apply(lambda x: "지연" if x != "없음" else "정상")
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
        # 로고
        st.markdown("""
        <div style='padding:20px 16px 12px 16px;border-bottom:1px solid #222;'>
          <div style='font-size:20px;font-weight:900;color:white;letter-spacing:-0.5px;'>
            OPS<span style='color:#ccff00;'>·</span>INTEL
          </div>
          <div style='font-size:10px;color:#555;margin-top:2px;letter-spacing:1px;'>
            1P PRODUCT REGISTRATION
          </div>
        </div>
        """, unsafe_allow_html=True)
 
        # 동기화
        st.markdown("<div style='padding:12px 0 6px 0;'>", unsafe_allow_html=True)
        if st.button("↻  구글 시트 동기화", use_container_width=True, type="primary"):
            with st.spinner("연결 중..."):
                vals, err = load_from_gsheet()
            if err:
                st.error(f"연결 실패\n{err}")
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
                f"<div style='font-size:10px;color:#555;text-align:center;padding:4px 0;'>"
                f"Last sync · {st.session_state['gsheet_fetched_at']}</div>",
                unsafe_allow_html=True
            )
 
        st.markdown("<p style='color:#444;font-size:10px;margin:10px 0 3px 0;'>보조 — XLSX 업로드</p>",
                    unsafe_allow_html=True)
        uploaded = st.file_uploader("", type=["xlsx"], label_visibility="collapsed")
        if uploaded:
            preprocess_bytes.clear()
            st.session_state["xlsx_bytes"]  = uploaded.read()
            st.session_state["data_source"] = "xlsx"
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
 
        src = st.session_state.get("data_source", "none")
        label = {
            "gsheet": "● Google Sheet",
            "xlsx":   "● Excel 파일",
        }.get(src, "● 연결 없음")
        color = {"gsheet": "#ccff00", "xlsx": "#f5a623"}.get(src, "#555")
        st.markdown(
            f"<div style='font-size:11px;color:{color};text-align:center;padding:4px 0 12px;'>{label}</div>",
            unsafe_allow_html=True
        )
 
        # ── 필터 ──
        st.markdown("<div style='border-top:1px solid #222;padding-top:14px;'>", unsafe_allow_html=True)
        st.markdown("<p style='color:#555;font-size:10px;letter-spacing:1px;font-weight:700;'>FILTERS</p>",
                    unsafe_allow_html=True)
 
        # ★ 검토자 — 4명만
        avail_rev   = [r for r in FIXED_REVIEWERS if r in df["검토자_정제"].unique()]
        f_rev       = st.multiselect("검토자", options=FIXED_REVIEWERS,
                                      default=avail_rev)
 
        country_opts = sorted(df["국내해외"].unique().tolist())
        f_country    = st.multiselect("국내 / 해외", options=country_opts, default=country_opts)
 
        # 연도: 전체 KPI는 24~26, 필터는 연도 선택 그대로
        year_opts    = sorted([y for y in df["년도"].dropna().unique().tolist()])
        f_year       = st.multiselect("분석 연도", options=year_opts, default=year_opts)
 
        stage_opts   = sorted(df["현재단계"].unique().tolist())
        f_stage      = st.multiselect("진행 단계", options=stage_opts, default=stage_opts)
 
        f_delay      = st.multiselect("지연 여부", options=["정상", "지연"], default=["정상", "지연"])
        keyword      = st.text_input("브랜드 / 비고 검색", placeholder="Jellycat…")
 
        st.markdown("</div>", unsafe_allow_html=True)
 
        st.markdown(
            f"<div style='border-top:1px solid #222;padding-top:12px;"
            f"font-size:10px;color:#444;text-align:center;'>"
            f"Rows loaded · {len(df):,}<br>{datetime.now().strftime('%Y-%m-%d')}</div>",
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
          <div style='font-size:48px;font-weight:900;letter-spacing:-2px;color:#111;'>
            OPS<span style='color:#ccff00;background:#111;padding:0 6px;border-radius:4px;'>·</span>INTEL
          </div>
          <p style='color:#888;font-size:14px;margin-top:8px;letter-spacing:0.5px;'>
            1P PRODUCT REGISTRATION · C-LEVEL DASHBOARD
          </p>
        </div>
        <div style='background:#111;border-radius:16px;padding:28px;'>
          <p style='color:#ccff00;font-size:11px;font-weight:700;letter-spacing:1.5px;margin:0 0 16px;'>
            QUICK START
          </p>
          <ol style='color:#ccc;line-height:2.4;font-size:14px;margin:0;padding-left:20px;'>
            <li>왼쪽 사이드바 → <b style='color:white;'>↻ 구글 시트 동기화</b> 클릭</li>
            <li>자동으로 실시간 데이터 로드 및 분석 시작</li>
            <li>필터로 검토자 / 연도 / 단계 조정</li>
          </ol>
          <div style='margin-top:16px;border-top:1px solid #222;padding-top:12px;
                      font-size:11px;color:#444;'>
            Sheet ID · 1e-uxQVNCCF3qS8e3a_S8sZbCx5qj343ycsEfkIF2POA
          </div>
        </div>
        """, unsafe_allow_html=True)
 
# ─────────────────────────────────────────────
# 7. DASHBOARD
# ─────────────────────────────────────────────
def render_dashboard(df_filtered: pd.DataFrame, df_full: pd.DataFrame, source: str):
    """
    df_filtered : 사이드바 필터 적용된 전체 데이터 (23~26)
    df_full     : 필터 전 원본 전체 (마스터 시트에서 사용)
    """
 
    # ★ KPI용: 24년 이후만
    df_kpi = df_filtered[df_filtered["년도"].isin([2024, 2025, 2026])].copy()
    # ★ 심화 분석용
    df_24  = df_filtered[df_filtered["등록완료일_dt"] >= "2024-01-01"].copy()
 
    # ── 헤더 바 ──
    ts_str = st.session_state.get("gsheet_fetched_at", datetime.now().strftime("%Y-%m-%d %H:%M"))
    src_txt = "Google Sheet · LIVE" if source == "gsheet" else "Excel Upload"
    st.markdown(f"""
    <div class='kream-header'>
      <div class='kream-logo'>OPS<span>·</span>INTEL</div>
      <div class='kream-header-right'>
        <span class='header-ts'>{src_txt} · {ts_str}</span>
        <span class='live-badge'><span class='live-dot'></span>LIVE</span>
      </div>
    </div>
    """, unsafe_allow_html=True)
 
    # ══════════════════════════════════════════════
    # SECTION 1 — KPI (24~26 기준)
    # ══════════════════════════════════════════════
    st.markdown("<div class='sec-title'>종합 핵심 운영 지표 · 2024–2026</div>", unsafe_allow_html=True)
 
    total_kpi    = len(df_kpi)
    reg_done_kpi = int(df_kpi["bool_reg_done"].sum())
    reg_rate_kpi = safe_rate(reg_done_kpi, total_kpi)
    lt_avg_kpi   = df_kpi["리드타임"].mean()
    lt_med_kpi   = df_kpi["리드타임"].median()
    delayed_kpi  = int((df_kpi["지연여부"] == "지연").sum())
 
    # ★ WIP: 등록완료도 아니고 등록불가도 아닌 것
    wip_df = df_kpi[
        (~df_kpi["bool_reg_done"]) &
        (df_kpi["현재단계"] != "X.등록 불가")
    ].copy()
    wip_cnt = len(wip_df)
 
    c1, c2, c3, c4, c5, c6 = st.columns(6)
 
    def kpi_card(col, tag, num, unit, sub, accent, num_sm=False):
        sm = "kpi-num-sm" if num_sm else ""
        col.markdown(f"""
        <div class='kpi-wrap {accent}'>
          <div class='kpi-tag'>{tag}</div>
          <div class='kpi-num {sm}'>{num}<span class='kpi-unit'>{unit}</span></div>
          <div class='kpi-sub'>{sub}</div>
        </div>
        """, unsafe_allow_html=True)
 
    kpi_card(c1, "전체 분석 건수", f"{total_kpi:,}", "건",
             "2024–2026 기준", "kpi-accent-black")
    kpi_card(c2, "최종 등록 완료", f"{reg_done_kpi:,}", "건",
             f"등록률 {reg_rate_kpi}%", "kpi-accent-green")
    kpi_card(c3, "평균 리드타임",
             f"{lt_avg_kpi:.1f}" if pd.notna(lt_avg_kpi) else "N/A", "일",
             f"중앙값 {lt_med_kpi:.0f}일" if pd.notna(lt_med_kpi) else "", "kpi-accent-purple")
    kpi_card(c4, "지연 발생 건수", f"{delayed_kpi:,}", "건",
             f"지연률 {safe_rate(delayed_kpi, total_kpi)}%", "kpi-accent-red")
 
    # ★ WIP 카드 — expander로 진행중 브랜드 목록 표시
    with c5:
        st.markdown(f"""
        <div class='kpi-wrap kpi-accent-yellow'>
          <div class='kpi-tag'>진행 중 WIP</div>
          <div class='kpi-num'>{wip_cnt:,}<span class='kpi-unit'>건</span></div>
          <div class='kpi-sub'>등록완료·불가 제외</div>
        </div>
        """, unsafe_allow_html=True)
 
    with c6:
        kpi_card(c6, "24년+ 분석 건수", f"{len(df_24):,}", "건",
                 "심화 분석 대상", "kpi-accent-lime")
 
    # ★ WIP 브랜드 상세 — 카드 아래 expander
    with st.expander(f"📋 진행 중 브랜드 상세 목록 ({wip_cnt}건) — 클릭해서 펼치기"):
        if wip_cnt == 0:
            st.write("진행 중인 브랜드가 없습니다.")
        else:
            wip_show = wip_df[["브랜드(영문)", "요청자_정제", "검토자_정제",
                                "국내해외", "현재단계", "리드타임", "비고_text"]].copy()
            wip_show = wip_show.rename(columns={
                "브랜드(영문)": "브랜드", "요청자_정제": "요청자",
                "검토자_정제": "검토자", "비고_text": "비고"
            }).sort_values("현재단계")
 
            # 단계별 색상 표시
            def color_stage(val):
                c = STAGE_COLORS.get(val, "#eee")
                return f"background-color: {c}22; color: {c}; font-weight:600;"
 
            st.dataframe(
                wip_show.style.map(color_stage, subset=["현재단계"]),
                use_container_width=True, hide_index=True, height=340
            )
 
    st.markdown("<hr class='k-divider'>", unsafe_allow_html=True)
 
    # ══════════════════════════════════════════════
    # SECTION 2 — 파이프라인 (24~26)
    # ══════════════════════════════════════════════
    st.markdown("<div class='sec-title'>등록 파이프라인 · 2024–2026</div>", unsafe_allow_html=True)
 
    p1, p2, p3 = st.columns(3)
 
    with p1:
        fig = go.Figure(go.Funnel(
            y=["리스트업 완료", "검토/등록 요청", "구매 완료", "최종 등록"],
            x=[int(df_kpi["bool_listed"].sum()),
               int(df_kpi["bool_request_done"].sum()),
               int(df_kpi["bool_purchase_done"].sum()),
               int(df_kpi["bool_reg_done"].sum())],
            textinfo="value+percent previous",
            textfont=dict(size=12, color="#333"),
            marker=dict(color=["#333", "#555", "#888", "#05c072"]),
            connector=dict(line=dict(color="#eee", width=2)),
        ))
        fig.update_layout(**CHART_TPL, title="등록 전환 Funnel", height=300)
        st.plotly_chart(fig, use_container_width=True)
 
    with p2:
        sc = df_kpi["현재단계"].value_counts().reset_index()
        sc.columns = ["단계", "건수"]
        fig = go.Figure(go.Pie(
            labels=sc["단계"], values=sc["건수"], hole=0.6,
            marker=dict(colors=[STAGE_COLORS.get(s, "#ccc") for s in sc["단계"]]),
            textinfo="percent", textfont=dict(size=11),
        ))
        fig.update_layout(**CHART_TPL, title="단계별 분포", height=300,
                          legend=dict(orientation="v", x=1.02, y=0.5, font=dict(size=10)))
        st.plotly_chart(fig, use_container_width=True)
 
    with p3:
        cross = (df_kpi[df_kpi["국내해외"].isin(["국내", "해외"])]
                 .groupby(["국내해외", "현재단계"]).size().reset_index(name="건수"))
        fig = px.bar(cross, x="국내해외", y="건수", color="현재단계",
                     color_discrete_map=STAGE_COLORS, barmode="stack",
                     title="국내 / 해외별 단계")
        fig.update_layout(**CHART_TPL, height=300,
                          legend=dict(orientation="v", x=1.02, y=0.5, font=dict(size=10)))
        st.plotly_chart(fig, use_container_width=True)
 
    st.markdown("<hr class='k-divider'>", unsafe_allow_html=True)
 
    # ══════════════════════════════════════════════
    # SECTION 3 — 24년+ 심화 분석
    # ══════════════════════════════════════════════
    st.markdown("<div class='sec-title'>2024+ 운영 트렌드 심화 분석</div>", unsafe_allow_html=True)
 
    if df_24.empty:
        st.info("선택 필터 내 2024년 이후 데이터가 없습니다.")
    else:
        tab1, tab2, tab3, tab4 = st.tabs([
            "시계열 트렌드", "리드타임 Deep-Dive", "지연 분석", "담당자 성과"
        ])
 
        # ── TAB1 ──
        with tab1:
            view  = st.radio("집계 단위", ["월별", "주차별", "분기별"], horizontal=True)
            g_col = {"월별": "년월", "주차별": "년주차", "분기별": "년분기"}[view]
            ts = df_24.dropna(subset=[g_col]).groupby(g_col).agg(
                등록완료=("bool_reg_done", "sum"),
                전체건수=("bool_reg_done", "count"),
                평균리드타임=("리드타임", "mean"),
            ).reset_index()
            ts.columns = ["기간", "등록완료", "전체건수", "평균리드타임"]
            ts["등록률"] = (ts["등록완료"] / ts["전체건수"] * 100).round(1)
 
            fig = make_subplots(rows=2, cols=1,
                                subplot_titles=("등록 완료 vs 전체 건수", "등록률 (%)"),
                                vertical_spacing=0.14, shared_xaxes=True)
            fig.add_trace(go.Bar(x=ts["기간"], y=ts["전체건수"],
                                  name="전체", marker_color="#ebebeb"), row=1, col=1)
            fig.add_trace(go.Bar(x=ts["기간"], y=ts["등록완료"],
                                  name="등록완료", marker_color="#111"), row=1, col=1)
            fig.add_trace(go.Scatter(x=ts["기간"], y=ts["등록률"],
                                      name="등록률%", mode="lines+markers",
                                      line=dict(color="#05c072", width=2.5),
                                      fill="tozeroy",
                                      fillcolor="rgba(5,192,114,0.08)"),
                          row=2, col=1)
            fig.update_layout(**CHART_TPL, height=440, barmode="overlay",
                               title_text=f"{view} 등록 현황 (2024+)")
            fig.update_yaxes(showgrid=True, gridcolor="#f5f5f5")
            st.plotly_chart(fig, use_container_width=True)
            with st.expander("상세 수치 테이블"):
                st.dataframe(ts.style.format({
                    "등록완료": "{:,}", "전체건수": "{:,}",
                    "평균리드타임": "{:.1f}", "등록률": "{:.1f}%"
                }), use_container_width=True, hide_index=True)
 
        # ── TAB2 ──
        with tab2:
            lt = df_24[df_24["리드타임"].notna()].copy()
            r1, r2 = st.columns(2)
            with r1:
                fig = px.box(lt, x="국내해외", y="리드타임", color="국내해외",
                             title="국내/해외 리드타임 분포", points="outliers",
                             color_discrete_map={"국내": "#111", "해외": "#888", "미입력": "#ccc"})
                fig.update_layout(**CHART_TPL, height=340, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            with r2:
                fig = px.histogram(lt, x="리드타임", color="국내해외",
                                   nbins=30, barmode="overlay", opacity=0.75,
                                   title="리드타임 빈도 분포",
                                   color_discrete_map={"국내": "#111", "해외": "#888", "미입력": "#ccc"})
                fig.update_layout(**CHART_TPL, height=340)
                st.plotly_chart(fig, use_container_width=True)
 
            stat = lt.groupby("국내해외")["리드타임"].agg(
                건수="count", 평균="mean", 중앙값="median", 최솟값="min", 최댓값="max"
            ).reset_index().round(1)
            st.dataframe(stat.style.format({
                "평균": "{:.1f}일", "중앙값": "{:.1f}일",
                "최솟값": "{:.0f}일", "최댓값": "{:.0f}일"
            }), use_container_width=True, hide_index=True)
 
            def lt_bucket(d):
                if pd.isna(d): return "데이터 없음"
                if d <= 7:    return "① 1주 이내"
                if d <= 14:   return "② 2주 이내"
                if d <= 30:   return "③ 1개월 이내"
                return "④ 1개월 초과"
            lt["리드타임구간"] = lt["리드타임"].apply(lt_bucket)
            bkt = lt.groupby(["국내해외", "리드타임구간"]).size().reset_index(name="건수")
            fig = px.bar(bkt, x="리드타임구간", y="건수", color="국내해외",
                         barmode="group", title="리드타임 구간별 건수",
                         color_discrete_map={"국내": "#111", "해외": "#888", "미입력": "#ccc"})
            fig.update_layout(**CHART_TPL, height=300)
            st.plotly_chart(fig, use_container_width=True)
 
        # ── TAB3 ──
        with tab3:
            ddf = df_24[df_24["지연여부"] == "지연"]
            ca, cb, cc = st.columns(3)
            ca.metric("지연 건수", f"{len(ddf):,}건")
            cb.metric("정상 건수", f"{len(df_24)-len(ddf):,}건")
            cc.metric("지연률",    f"{safe_rate(len(ddf), len(df_24))}%")
 
            d1, d2 = st.columns(2)
            with d1:
                dc = df_24["지연분류"].value_counts().reset_index()
                dc.columns = ["분류", "건수"]
                dc = dc[dc["분류"] != "없음"]
                fig = px.bar(dc, y="분류", x="건수", orientation="h",
                             title="지연 사유 유형별 건수",
                             color_discrete_sequence=["#111"])
                fig.update_layout(**CHART_TPL, height=320)
                st.plotly_chart(fig, use_container_width=True)
            with d2:
                dm = df_24.groupby(["년월", "지연여부"]).size().reset_index(name="건수")
                fig = px.bar(dm, x="년월", y="건수", color="지연여부",
                             barmode="stack", title="월별 지연 / 정상 현황",
                             color_discrete_map={"정상": "#05c072", "지연": "#f04452"})
                fig.update_layout(**CHART_TPL, height=320)
                st.plotly_chart(fig, use_container_width=True)
 
            if len(ddf) > 0:
                with st.expander(f"지연 건 상세 목록 ({len(ddf)}건)"):
                    scols = ["브랜드(영문)", "요청자_정제", "검토자_정제", "국내해외",
                             "지연분류", "지연 사유", "리드타임", "현재단계"]
                    st.dataframe(ddf[scols].sort_values("리드타임", ascending=False),
                                 use_container_width=True, hide_index=True)
 
        # ── TAB4 ──
        with tab4:
            pr = df_24.groupby("검토자_정제").agg(
                담당건수=("bool_reg_done", "count"),
                등록완료=("bool_reg_done", "sum"),
                평균리드타임=("리드타임", "mean"),
                지연건수=("지연여부", lambda x: (x == "지연").sum()),
            ).reset_index()
            pr["등록률"] = (pr["등록완료"] / pr["담당건수"] * 100).round(1)
            pr["지연률"] = (pr["지연건수"] / pr["담당건수"] * 100).round(1)
            pr = pr.sort_values("담당건수", ascending=False)
 
            fig = make_subplots(rows=1, cols=3,
                                subplot_titles=("담당 건수", "등록률 (%)", "평균 리드타임 (일)"))
            for i, (col_, color) in enumerate([
                ("담당건수", "#111"), ("등록률", "#05c072"), ("평균리드타임", "#f5a623")
            ]):
                fig.add_trace(go.Bar(
                    x=pr["검토자_정제"], y=pr[col_].round(1),
                    name=col_, marker_color=color,
                    text=pr[col_].round(1), textposition="auto",
                ), row=1, col=i+1)
            fig.update_layout(**CHART_TPL, height=320, showlegend=False,
                               title_text="검토자별 운영 성과 (2024+)")
            st.plotly_chart(fig, use_container_width=True)
 
            preq = df_24.groupby("요청자_정제").agg(
                요청건수=("bool_reg_done", "count"),
                등록완료=("bool_reg_done", "sum"),
            ).reset_index()
            preq["등록률"] = (preq["등록완료"] / preq["요청건수"] * 100).round(1)
            preq = preq.sort_values("요청건수", ascending=False).head(15)
            fig = px.bar(preq, x="요청자_정제", y="요청건수",
                         color="등록률", color_continuous_scale=["#eee", "#111"],
                         title="요청자별 등록 요청 건수 TOP 15 (2024+)", text="요청건수")
            fig.update_layout(**CHART_TPL, height=320)
            st.plotly_chart(fig, use_container_width=True)
 
    st.markdown("<hr class='k-divider'>", unsafe_allow_html=True)
 
    # ══════════════════════════════════════════════
    # SECTION 4 — YoY
    # ══════════════════════════════════════════════
    st.markdown("<div class='sec-title'>연도별 YoY 성과 비교 · 2023–2026</div>", unsafe_allow_html=True)
 
    yoy = df_filtered.groupby("년도").agg(
        전체건수=("bool_reg_done", "count"),
        등록완료=("bool_reg_done", "sum"),
        평균리드타임=("리드타임", "mean"),
        지연건수=("지연여부", lambda x: (x == "지연").sum()),
    ).reset_index().dropna(subset=["년도"])
    yoy["등록률"] = (yoy["등록완료"] / yoy["전체건수"] * 100).round(1)
    yoy["지연률"] = (yoy["지연건수"] / yoy["전체건수"] * 100).round(1)
    yoy["년도"]   = yoy["년도"].astype(int).astype(str)
 
    y1, y2 = st.columns(2)
    with y1:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=yoy["년도"], y=yoy["전체건수"],
                              name="전체", marker_color="#ebebeb"))
        fig.add_trace(go.Bar(x=yoy["년도"], y=yoy["등록완료"],
                              name="등록완료", marker_color="#111"))
        fig.update_layout(**CHART_TPL, title="연도별 전체 vs 등록완료",
                          barmode="overlay", height=300)
        st.plotly_chart(fig, use_container_width=True)
    with y2:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=yoy["년도"], y=yoy["평균리드타임"].round(1),
                              name="리드타임(일)", marker_color="#555"), secondary_y=False)
        fig.add_trace(go.Scatter(x=yoy["년도"], y=yoy["지연률"], name="지연률(%)",
                                  mode="lines+markers",
                                  line=dict(color="#f04452", width=2.5)), secondary_y=True)
        fig.update_layout(**CHART_TPL, title="연도별 리드타임 vs 지연률", height=300)
        fig.update_yaxes(title_text="리드타임(일)", secondary_y=False)
        fig.update_yaxes(title_text="지연률(%)",    secondary_y=True)
        st.plotly_chart(fig, use_container_width=True)
 
    st.dataframe(
        yoy.style
           .format({"전체건수": "{:,}", "등록완료": "{:,}", "지연건수": "{:,}",
                    "평균리드타임": "{:.1f}일", "등록률": "{:.1f}%", "지연률": "{:.1f}%"})
           .background_gradient(subset=["등록률"], cmap="Greens")
           .background_gradient(subset=["지연률"], cmap="Reds"),
        use_container_width=True, hide_index=True
    )
 
    st.markdown("<hr class='k-divider'>", unsafe_allow_html=True)
 
    # ══════════════════════════════════════════════
    # SECTION 5 — 마스터 트래킹 (23~26 전체, 클릭 필터)
    # ══════════════════════════════════════════════
    st.markdown("<div class='sec-title'>마스터 업무 트래킹 · 2023–2026 전체</div>", unsafe_allow_html=True)
    st.markdown("<div class='raw-section'>", unsafe_allow_html=True)
 
    # 트래킹 시트는 df_filtered (사이드바 필터 적용) 사용
    col_show = ["브랜드(영문)", "요청자_정제", "검토자_정제", "국내해외",
                "현재단계", "지연분류", "리드타임", "년월", "비고_text"]
    df_master = df_filtered[col_show].copy().rename(columns={
        "브랜드(영문)": "브랜드", "요청자_정제": "요청자", "검토자_정제": "검토자",
        "비고_text": "비고", "년월": "등록년월"
    })
 
    # ── ★ 인터랙티브 컬럼 필터 (Streamlit selectbox 방식) ──
    st.markdown("**컬럼별 필터**", unsafe_allow_html=False)
    fc1, fc2, fc3, fc4, fc5, fc6 = st.columns(6)
 
    def col_filter(container, label, series, key):
        opts = ["전체"] + sorted(series.dropna().unique().tolist())
        return container.selectbox(label, options=opts, key=key, index=0)
 
    sel_rev    = col_filter(fc1, "검토자",   df_master["검토자"],   "mf_rev")
    sel_req    = col_filter(fc2, "요청자",   df_master["요청자"],   "mf_req")
    sel_nat    = col_filter(fc3, "국내/해외", df_master["국내해외"], "mf_nat")
    sel_stage  = col_filter(fc4, "현재단계",  df_master["현재단계"], "mf_stage")
    sel_delay  = col_filter(fc5, "지연분류",  df_master["지연분류"], "mf_delay")
    sel_month  = col_filter(fc6, "등록년월",  df_master["등록년월"], "mf_month")
 
    df_view = df_master.copy()
    if sel_rev   != "전체": df_view = df_view[df_view["검토자"]   == sel_rev]
    if sel_req   != "전체": df_view = df_view[df_view["요청자"]   == sel_req]
    if sel_nat   != "전체": df_view = df_view[df_view["국내해외"] == sel_nat]
    if sel_stage != "전체": df_view = df_view[df_view["현재단계"]  == sel_stage]
    if sel_delay != "전체": df_view = df_view[df_view["지연분류"]  == sel_delay]
    if sel_month != "전체": df_view = df_view[df_view["등록년월"]  == sel_month]
 
    # 정렬
    sort_by = st.selectbox("정렬 기준",
                            ["등록년월 (최신순)", "리드타임 (내림차순)", "현재단계"],
                            key="master_sort")
    if sort_by == "등록년월 (최신순)":       df_view = df_view.sort_values("등록년월", ascending=False)
    elif sort_by == "리드타임 (내림차순)":   df_view = df_view.sort_values("리드타임", ascending=False)
    else:                                    df_view = df_view.sort_values("현재단계")
 
    st.caption(f"표시: {len(df_view):,}건 / 전체 {len(df_master):,}건")
 
    # 단계 컬러맵
    def stage_color(val):
        c = STAGE_COLORS.get(val, "#eee")
        return f"background-color: {c}22; color: {c}; font-weight: 600;"
 
    st.dataframe(
        df_view.style.map(stage_color, subset=["현재단계"]),
        use_container_width=True, hide_index=True, height=460
    )
 
    # 다운로드
    csv = df_view.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "↓ CSV 다운로드", data=csv,
        file_name=f"1P_Ops_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )
    st.markdown("</div>", unsafe_allow_html=True)
 
 
# ─────────────────────────────────────────────
# 8. MAIN
# ─────────────────────────────────────────────
def main():
    source = st.session_state.get("data_source", "none")
 
    # 데이터 로드
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
        except Exception:
            pass
 
        if has_secret and "auto_tried" not in st.session_state:
            st.session_state["auto_tried"] = True
            with st.spinner("구글 시트 자동 연결 중..."):
                vals, err = load_from_gsheet()
            if not err:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.session_state.update({
                    "gsheet_values": vals,
                    "gsheet_fetched_at": ts,
                    "data_source": "gsheet",
                })
                st.rerun()
            else:
                st.warning(f"자동 연결 실패: {err}")
                render_landing()
                return
        else:
            render_landing()
            return
 
    # 사이드바 필터
    f_rev, f_country, f_year, f_stage, f_delay, keyword = render_sidebar(df_full)
 
    # 필터 적용
    dff = df_full.copy()
    if f_rev:     dff = dff[dff["검토자_정제"].isin(f_rev)]
    if f_country: dff = dff[dff["국내해외"].isin(f_country)]
    if f_year:    dff = dff[dff["년도"].isin(f_year) | dff["년도"].isna()]
    if f_stage:   dff = dff[dff["현재단계"].isin(f_stage)]
    if f_delay:   dff = dff[dff["지연여부"].isin(f_delay)]
    if keyword:   dff = dff[dff.apply(lambda r: keyword.strip().lower() in str(r).lower(), axis=1)]
 
    render_dashboard(dff, df_full, source)
 
 
if __name__ == "__main__":
    main()
 
