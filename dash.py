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
# KREAM-inspired CSS — 원본 디자인 및 모든 스타일 100% 보존
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

/* ── 메트릭 override ── */
[data-testid="stMetricValue"] { font-size:28px !important; font-weight:900 !important; color:#111 !important; }
[data-testid="stMetricLabel"] { font-size:11px !important; color:#888 !important; font-weight:700 !important; }

/* ── 데이터프레임 ── */
[data-testid="stDataFrameResizable"] thead tr th {
    background: #f8f8f8 !important; font-weight: 800 !important;
    font-size: 12px !important; color: #333 !important;
    border-bottom: 2px solid #e8e8e8 !important;
}
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
    font=dict(family="Pretendard", size=12, color="#333"),
    margin=dict(l=16, r=16, t=44, b=16),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)

# ─────────────────────────────────────────────
# 2. LOADERS
# ─────────────────────────────────────────────
def load_from_gsheet():
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=scopes)
        client = gspread.authorize(creds)
        ws = client.open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        return ws.get_all_values(), None
    except Exception as e:
        return None, str(e)

# ─────────────────────────────────────────────
# 3. HELPERS
# ─────────────────────────────────────────────
def parse_bool(v) -> bool:
    if pd.isna(v) or str(v).strip() == "": return False
    if isinstance(v, bool): return v
    return str(v).strip().lower() in TRUE_VALUES

def parse_korean_date(v):
    s = str(v).strip()
    if s in ["", "-", "#REF!", "nan", "None", "NaT"]: return pd.NaT
    for fmt in ["%y.%m.%d", "%Y.%m.%d", "%Y-%m-%d", "%y-%m-%d"]:
        try: return pd.to_datetime(s, format=fmt)
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
# 4. PREPROCESSING ENGINE (정밀 보정)
# ─────────────────────────────────────────────
def _build_df(values: list) -> pd.DataFrame:
    # ★ 사본 데이터 기준: 3행(Index 2)이 진짜 헤더
    header_idx = 2
    header = [str(c).strip() for c in values[header_idx]]
    df_raw = pd.DataFrame(values[header_idx + 1:], columns=header)

    # 유효 데이터 필터링 (브랜드명이 있는 경우만)
    df = df_raw[df_raw["브랜드(영문)"].apply(lambda x: bool(str(x).strip()) and str(x).strip() not in ["", "nan"])].copy()

    # 날짜 처리 및 타입 변환 (TypeError 차단)
    df["등록완료일_dt"] = df["등록 완료일"].apply(parse_korean_date)
    df["등록요청일_dt"] = df["등록 요청일"].apply(parse_korean_date)
    df["년도"] = df["등록완료일_dt"].dt.year.astype("float64")
    df["월"]   = df["등록완료일_dt"].dt.month.astype("float64")
    df["년월"] = df["등록완료일_dt"].dt.strftime("%Y-%m")
    
    iso = df["등록완료일_dt"].dt.isocalendar()
    df["ISO년도"] = iso.year.astype("float64")
    df["주차"]    = iso.week.astype("float64")
    df["년주차"]  = iso.year.astype(str) + "-W" + iso.week.astype(str).str.zfill(2)
    df["분기"]    = "Q" + df["등록완료일_dt"].dt.quarter.astype(str)
    df["년분기"]  = df["년도"].astype(str) + "-" + df["분기"]

    # 리드타임
    df["리드타임"] = (df["등록완료일_dt"] - df["등록요청일_dt"]).dt.days
    df["리드타임"] = df["리드타임"].where((df["리드타임"] >= 0) & (df["리드타임"] <= 180))

    # 불리언 상태 매핑 (D, E, F, G, I열)
    BOOL_MAP = [
        ("리스트업 완료",              "bool_listed"),         # D열
        ("검토 및 등록 요청 완료",      "bool_request_done"),   # E열
        ("상품 구매 요청",              "bool_purchase_req"),   # F열
        ("상품 구매 완료",              "bool_purchase_done"),  # G열
        ("등록 완료 (앱 노출 시 체크)", "bool_reg_done"),       # I열
    ]
    for src, dst in BOOL_MAP:
        df[dst] = df[src].apply(parse_bool) if src in df.columns else False

    # ★ WIP 로직 정밀 보정 (CSV 샘플 기준)
    df["bool_h_filled"] = df["등록 요청일"].apply(has_date_value) # H열 기입 여부
    
    # 1. 등록 진행중 (Registration WIP): 
    #   E열(검토완료)=TRUE AND I열(등록완료)=FALSE
    df["is_reg_wip"] = (df["bool_request_done"] == True) & (df["bool_reg_done"] == False)
    
    # 2. 검토 진행중 (Review WIP): 
    #   D열(리스트업)=TRUE AND E열(검토완료)=FALSE
    df["is_rev_wip"] = (df["bool_listed"] == True) & (df["bool_request_done"] == False)

    # 텍스트 및 기타 정제
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
        </div>
        """, unsafe_allow_html=True)

# ─────────────────────────────────────────────
# 7. WIP 상세 패널 (가시성 핵심)
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
            f"🟠 등록 진행중 ({len(reg_wip)}건) — E열 ✓ · I열 미체크",
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
    # SECTION 1 — KPI
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

    kcard(k1, "전체 분석 건수",  f"{total_k:,}",    "건", "2024–2026 기준", "#111")
    kcard(k2, "최종 등록 완료",  f"{reg_done_k:,}", "건", "누적 등록 성공",  "#05c072", f"등록률 {reg_rate_k}%", "#05c072")
    kcard(k3, "평균 리드타임",  f"{lt_avg_k:.1f}" if pd.notna(lt_avg_k) else "N/A", "일", f"중앙값 {lt_med_k:.0f}일" if pd.notna(lt_med_k) else "", "#8b5cf6")
    kcard(k4, "지연 발생 건수",  f"{delayed_k:,}",  "건", "지연 사유 기입 건",  "#f04452", f"지연률 {delay_rate_k}%", "#f04452")
    kcard(k5, "24년+ 분석 건수", f"{len(df_24):,}", "건", "심화 분석 대상", "#d4ff00")

    st.markdown("<br>", unsafe_allow_html=True)

    # ── WIP 상세 패널 ──
    st.markdown("<div class='sec-title-accent'>진행 중 브랜드 현황 (WIP)</div>", unsafe_allow_html=True)
    render_wip_panel(df_kpi)

    st.markdown("<hr class='k-div'>", unsafe_allow_html=True)

    # ══════════════════════════════════════════
    # SECTION 2 — 파이프라인
    # ══════════════════════════════════════════
    st.markdown("<div class='sec-title'>등록 파이프라인 · 2024–2026</div>", unsafe_allow_html=True)

    p1, p2, p3 = st.columns(3)

    with p1:
        fig = go.Figure(go.Funnel(
            y=["리스트업 완료", "검토/등록 요청", "구매 완료", "최종 등록"],
            x=[int(df_kpi["bool_listed"].sum()), int(df_kpi["bool_request_done"].sum()),
               int(df_kpi["bool_purchase_done"].sum()), int(df_kpi["bool_reg_done"].sum())],
            textinfo="value+percent previous",
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
            textinfo="percent",
        ))
        fig.update_layout(**CHART_TPL, title="<b>단계별 분포</b>", height=320)
        st.plotly_chart(fig, use_container_width=True)

    with p3:
        cross = (df_kpi[df_kpi["국내해외"].isin(["국내", "해외"])]
                 .groupby(["국내해외", "현재단계"]).size().reset_index(name="건수"))
        fig = px.bar(cross, x="국내해외", y="건수", color="현재단계",
                     color_discrete_map=STAGE_COLORS, barmode="stack",
                     title="<b>국내 / 해외별 단계</b>")
        fig.update_layout(**CHART_TPL, height=320)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("<hr class='k-div'>", unsafe_allow_html=True)

    # ══════════════════════════════════════════
    # SECTION 3 — 24년+ 심화 분석
    # ══════════════════════════════════════════
    st.markdown("<div class='sec-title'>2024+ 운영 트렌드 심화 분석</div>", unsafe_allow_html=True)

    if df_24.empty:
        st.info("선택 필터 내 2024년 이후 데이터가 없습니다.")
    else:
        tab1, tab2, tab3, tab4 = st.tabs(["시계열 트렌드", "리드타임 Deep-Dive", "지연 분석", "담당자 성과"])

        with tab1:
            view  = st.radio("집계 단위", ["월별", "주차별", "분기별"], horizontal=True)
            g_col = {"월별": "년월", "주차별": "년주차", "분기별": "년분기"}[view]
            ts_df = df_24.dropna(subset=[g_col]).groupby(g_col).agg(
                등록완료=("bool_reg_done", "sum"), 전체건수=("bool_reg_done", "count")
            ).reset_index()
            # TypeError 해결: float64 변환
            ts_df["등록률"] = (ts_df["등록완료"].astype(float) / ts_df["전체건수"].astype(float) * 100).round(1)

            fig = make_subplots(rows=2, cols=1, subplot_titles=("등록 완료 vs 전체 건수", "등록률 (%)"), vertical_spacing=0.14, shared_xaxes=True)
            fig.add_trace(go.Bar(x=ts_df[g_col], y=ts_df["전체건수"], name="전체", marker_color="#ebebeb"), row=1, col=1)
            fig.add_trace(go.Bar(x=ts_df[g_col], y=ts_df["등록완료"], name="등록완료", marker_color="#111"), row=1, col=1)
            fig.add_trace(go.Scatter(x=ts_df[g_col], y=ts_df["등록률"], name="등록률", mode="lines+markers", line=dict(color="#05c072", width=2.5)), row=2, col=1)
            fig.update_layout(**CHART_TPL, height=460, barmode="overlay", title_text=f"<b>{view} 등록 현황 (2024+)</b>")
            st.plotly_chart(fig, use_container_width=True)

        with tab2:
            lt = df_24[df_24["리드타임"].notna()].copy()
            r1, r2 = st.columns(2)
            with r1:
                fig = px.box(lt, x="국내해외", y="리드타임", color="국내해외", title="<b>국내/해외 리드타임 분포</b>", color_discrete_map={"국내": "#111", "해외": "#888"})
                fig.update_layout(**CHART_TPL, height=340, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            with r2:
                fig = px.histogram(lt, x="리드타임", color="국내해외", barmode="overlay", title="<b>리드타임 빈도 분포</b>", color_discrete_map={"국내": "#111", "해외": "#888"})
                fig.update_layout(**CHART_TPL, height=340)
                st.plotly_chart(fig, use_container_width=True)

        with tab3:
            ddf = df_24[df_24["지연여부"] == "지연"]
            ca, cb, cc = st.columns(3)
            ca.metric("지연 건수", f"{len(ddf):,}건")
            cb.metric("정상 건수", f"{len(df_24)-len(ddf):,}건")
            cc.metric("지연률",    f"{safe_rate(len(ddf), len(df_24))}%")

            dc = df_24["지연분류"].value_counts().reset_index()
            dc.columns = ["분류", "건수"]
            dc = dc[dc["분류"] != "없음"]
            fig = px.bar(dc, y="분류", x="건수", orientation="h", title="<b>지연 사유 유형별 건수</b>", color_discrete_sequence=["#f04452"])
            fig.update_layout(**CHART_TPL, height=340)
            st.plotly_chart(fig, use_container_width=True)

        with tab4:
            pr = df_24.groupby("검토자_정제").agg(담당건수=("bool_reg_done", "count"), 등록완료=("bool_reg_done", "sum")).reset_index()
            # TypeError 해결: float64 변환
            pr["등록률"] = (pr["등록완료"].astype(float) / pr["담당건수"].astype(float) * 100).round(1)
            fig = px.bar(pr, x="검토자_정제", y="담당건수", color="등록률", title="<b>검토자별 담당 건수 및 등록률</b>", color_continuous_scale="Greens")
            fig.update_layout(**CHART_TPL, height=340)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("<hr class='k-div'>", unsafe_allow_html=True)

    # ══════════════════════════════════════════
    # SECTION 4 — YoY
    # ══════════════════════════════════════════
    st.markdown("<div class='sec-title-muted'>연도별 YoY 성과 비교 · 2023–2026</div>", unsafe_allow_html=True)

    yoy = df_filtered.groupby("년도").agg(전체건수=("bool_reg_done", "count"), 등록완료=("bool_reg_done", "sum"), 지연건수=("지연여부", lambda x: (x == "지연").sum())).reset_index().dropna(subset=["년도"])
    # TypeError 해결
    yoy["등록률"] = (yoy["등록완료"].astype(float) / yoy["전체건수"].astype(float) * 100).round(1)
    yoy["지연률"] = (yoy["지연건수"].astype(float) / yoy["전체건수"].astype(float) * 100).round(1)
    yoy["년도"]   = yoy["년도"].astype(int).astype(str)

    y1, y2 = st.columns(2)
    with y1:
        fig = px.bar(yoy, x="년도", y=["전체건수", "등록완료"], barmode="group", title="<b>연도별 전체 vs 등록완료</b>", color_discrete_sequence=["#e8e8e8", "#111"])
        fig.update_layout(**CHART_TPL, height=320)
        st.plotly_chart(fig, use_container_width=True)
    with y2:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=yoy["년도"], y=yoy["등록률"], name="등록률(%)", marker_color="#05c072"), secondary_y=False)
        fig.add_trace(go.Scatter(x=yoy["년도"], y=yoy["지연률"], name="지연률(%)", line=dict(color="#f04452", width=3)), secondary_y=True)
        fig.update_layout(**CHART_TPL, title="<b>연도별 등록률 vs 지연률</b>", height=320)
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("<hr class='k-div'>", unsafe_allow_html=True)

    # ══════════════════════════════════════════
    # SECTION 5 — 마스터 트래킹
    # ══════════════════════════════════════════
    st.markdown("<div class='sec-title-muted'>마스터 업무 트래킹 · 2023–2026 전체 Raw</div>", unsafe_allow_html=True)

    df_view = df_filtered[["브랜드(영문)", "요청자_정제", "검토자_정제", "국내해외", "현재단계", "지연분류", "리드타임", "년월", "비고_text"]].copy()
    
    st.markdown("<div class='master-wrap'>", unsafe_allow_html=True)
    def stage_color_f(val):
        c, bg = STAGE_COLORS.get(val, "#888"), STAGE_BG.get(val, "rgba(200,200,200,0.1)")
        return f"background-color:{bg};color:{c};font-weight:800;"

    st.dataframe(df_view.style.map(stage_color_f, subset=["현재단계"]), use_container_width=True, hide_index=True, height=480)
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
