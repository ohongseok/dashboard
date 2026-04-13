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
    page_title="1P 상품등록 Ops Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)
 
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800&display=swap');
html, body, [class*="css"] {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, sans-serif !important;
}
.main { background-color: #f0f2f6; }
.kpi-card {
    background: white; border-radius: 16px; padding: 18px 22px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.07); border-left: 4px solid #4F8EF7;
    margin-bottom: 6px; min-height: 90px;
}
.kpi-label { font-size: 11px; color: #6B7280; font-weight: 600; letter-spacing: 0.5px; text-transform: uppercase; }
.kpi-value { font-size: 30px; font-weight: 800; color: #111827; line-height: 1.1; margin: 3px 0; }
.kpi-sub   { font-size: 11px; color: #9CA3AF; }
.section-header {
    background: linear-gradient(90deg, #4F8EF7 0%, #7C3AED 100%);
    color: white; padding: 10px 20px; border-radius: 10px;
    font-size: 15px; font-weight: 700; margin: 20px 0 12px 0;
}
.section-header-orange {
    background: linear-gradient(90deg, #F59E0B 0%, #EF4444 100%);
    color: white; padding: 10px 20px; border-radius: 10px;
    font-size: 15px; font-weight: 700; margin: 20px 0 12px 0;
}
.section-header-green {
    background: linear-gradient(90deg, #10B981 0%, #059669 100%);
    color: white; padding: 10px 20px; border-radius: 10px;
    font-size: 15px; font-weight: 700; margin: 20px 0 12px 0;
}
.sync-banner {
    background: #EEF2FF; border: 1px solid #C7D2FE;
    border-radius: 10px; padding: 10px 16px; margin-bottom: 12px;
    font-size: 13px; color: #4338CA;
}
[data-testid="stSidebar"] { background: #1E1E2E; }
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p { color: #C9D1D9 !important; }
.stTabs [data-baseweb="tab-list"] { gap: 8px; background: white; padding: 8px; border-radius: 12px; }
.stTabs [data-baseweb="tab"] { border-radius: 8px; font-weight: 600; font-size: 13px; height: 40px; }
</style>
""", unsafe_allow_html=True)
 
# ─────────────────────────────────────────────
# 1. CONSTANTS
# ─────────────────────────────────────────────
SPREADSHEET_ID  = "1e-uxQVNCCF3qS8e3a_S8sZbCx5qj343ycsEfkIF2POA"
SHEET_NAME      = "Summary"
FIXED_REVIEWERS = ["오홍석", "유지윤", "장근수", "백건우"]
TRUE_VALUES     = {"true", "1", "y", "yes", "완료", "o", "v", "✓", "check", "checked"}
 
STAGE_COLORS = {
    "5.등록 완료":      "#10B981",
    "4.구매 완료":      "#3B82F6",
    "3.구매 요청":      "#8B5CF6",
    "2.검토/등록 요청": "#F59E0B",
    "1.리스트업 완료":  "#6B7280",
    "0.미진행":         "#D1D5DB",
    "X.등록 불가":      "#EF4444",
}
 
DELAY_CATEGORY_MAP = {
    "해외배송/리드타임": ["해외배송", "해외 배송", "배송", "입고", "출고", "리드타임", "묶음"],
    "샘플/실물확인":    ["샘플", "실물", "확인후 등록", "실물 확인"],
    "가품검수/정가품":  ["가품", "정가품", "검수"],
    "데이터/품번이슈":  ["품번", "sku", "모델명"],
    "가격/운영판단":    ["가격", "원가", "마진", "보류", "불가"],
    "담당자/행정":      ["담당자", "부재", "행정"],
    "구매지연":         ["구매 지연", "구매지연"],
}
 
CHART_TPL = dict(
    template="plotly_white",
    font=dict(family="Pretendard, -apple-system, sans-serif", size=12),
    margin=dict(l=16, r=16, t=40, b=16),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)
 
# ─────────────────────────────────────────────
# 2. GOOGLE SHEETS LOADER
# ─────────────────────────────────────────────
def load_from_gsheet():
    """Returns (values_list, None) on success or (None, error_str) on failure"""
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
    # 헤더 행 탐색
    header_idx = 2
    for i, row in enumerate(values[:10]):
        if any("브랜드" in str(c) for c in row):
            header_idx = i
            break
 
    df_raw = pd.DataFrame(values[header_idx + 1:], columns=values[header_idx])
    df_raw.columns = [str(c).strip() for c in df_raw.columns]
 
    df = df_raw[
        df_raw["브랜드(영문)"].apply(lambda x: bool(str(x).strip()) and str(x).strip() not in ["", "nan"]) &
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
        if "등록 불가" in bigo or ("불가" in bigo and "확인" not in bigo): return "X.등록 불가"
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
    raw = pd.read_excel(io.BytesIO(raw_bytes), sheet_name="Summary", header=None)
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
        <div style='padding:16px 0 4px 0;'>
          <span style='color:#4F8EF7;font-size:19px;font-weight:800;'>📊 1P Ops Intel</span><br>
          <span style='color:#6B7280;font-size:11px;'>C-Level Strategy Dashboard</span>
        </div>
        """, unsafe_allow_html=True)
 
        st.markdown("---")
        st.markdown("<p style='color:#9CA3AF;font-size:11px;font-weight:700;letter-spacing:1px;'>DATA SOURCE</p>", unsafe_allow_html=True)
 
        # 구글 시트 동기화 버튼
        if st.button("🔄 구글 시트 최신 동기화", use_container_width=True, type="primary"):
            with st.spinner("구글 시트 연결 중..."):
                vals, err = load_from_gsheet()
            if err:
                st.error(f"❌ 연결 실패\n{err}")
            else:
                preprocess_gsheet.clear()
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.session_state["gsheet_values"]     = vals
                st.session_state["gsheet_fetched_at"] = ts
                st.session_state["data_source"]       = "gsheet"
                st.success("✅ 동기화 완료!")
                time.sleep(0.6)
                st.rerun()
 
        if "gsheet_fetched_at" in st.session_state:
            st.markdown(
                f"<div style='color:#6EE7B7;font-size:11px;text-align:center;margin-top:4px;'>"
                f"마지막 동기화: {st.session_state['gsheet_fetched_at']}</div>",
                unsafe_allow_html=True
            )
 
        # 엑셀 업로드 (보조 수단)
        st.markdown("<p style='color:#6B7280;font-size:11px;margin-top:14px;'>보조: 엑셀 파일 직접 업로드</p>",
                    unsafe_allow_html=True)
        uploaded = st.file_uploader("", type=["xlsx"], label_visibility="collapsed")
        if uploaded:
            preprocess_bytes.clear()
            st.session_state["xlsx_bytes"]  = uploaded.read()
            st.session_state["data_source"] = "xlsx"
            st.rerun()
 
        # 현재 소스 표시
        src = st.session_state.get("data_source", "none")
        label = {"gsheet": "🟢 Google Sheet 연결됨", "xlsx": "🟡 Excel 파일 사용 중"}.get(src, "🔴 데이터 없음")
        st.markdown(f"<div style='color:#9CA3AF;font-size:11px;text-align:center;margin-top:6px;'>{label}</div>",
                    unsafe_allow_html=True)
 
        # ── 필터 ──
        st.markdown("---")
        st.markdown("<p style='color:#9CA3AF;font-size:11px;font-weight:700;letter-spacing:1px;'>FILTERS</p>",
                    unsafe_allow_html=True)
 
        reviewers    = sorted(df["검토자_정제"].unique().tolist())
        f_rev        = st.multiselect("👤 검토자", options=reviewers,
                                       default=[r for r in FIXED_REVIEWERS if r in reviewers])
        country_opts = sorted(df["국내해외"].unique().tolist())
        f_country    = st.multiselect("🌍 국내/해외", options=country_opts, default=country_opts)
        year_opts    = sorted([y for y in df["년도"].dropna().unique().tolist()])
        f_year       = st.multiselect("📅 분석 연도", options=year_opts, default=year_opts)
        stage_opts   = sorted(df["현재단계"].unique().tolist())
        f_stage      = st.multiselect("🔖 진행 단계", options=stage_opts, default=stage_opts)
        f_delay      = st.multiselect("⏱ 지연 여부", options=["정상", "지연"], default=["정상", "지연"])
        keyword      = st.text_input("🔍 브랜드/비고 검색", placeholder="예: Jellycat")
 
        st.markdown("---")
        st.markdown(
            f"<div style='color:#4B5563;font-size:10px;'>Loaded: {len(df):,}행<br>"
            f"{datetime.now().strftime('%Y-%m-%d %H:%M')}</div>",
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
        <div style='text-align:center;padding:80px 0 24px 0;'>
          <div style='font-size:64px;'>📊</div>
          <h2 style='font-weight:800;color:#111827;font-size:28px;'>1P 상품등록 Ops Intelligence</h2>
          <p style='color:#6B7280;font-size:15px;line-height:1.7;'>
            C-Level 보고용 실시간 운영 분석 대시보드<br>
            사이드바에서 <b style='color:#4F8EF7;'>🔄 구글 시트 최신 동기화</b> 버튼을 클릭하세요.
          </p>
        </div>
        <div style='background:white;border-radius:16px;padding:24px;box-shadow:0 4px 20px rgba(0,0,0,0.08);'>
          <h4 style='color:#4F8EF7;margin:0 0 16px 0;'>🚀 시작 방법</h4>
          <ol style='color:#374151;line-height:2.2;font-size:14px;'>
            <li>왼쪽 사이드바 → <b>🔄 구글 시트 최신 동기화</b> 클릭</li>
            <li>자동으로 실시간 시트 데이터 로드 및 분석 시작</li>
            <li>필터(검토자 / 연도 / 단계 등)로 원하는 뷰 설정</li>
          </ol>
          <hr style='border:none;border-top:1px solid #F3F4F6;margin:12px 0;'>
          <p style='color:#9CA3AF;font-size:12px;margin:0;'>
            시트 URL: 1e-uxQVNCCF3qS8e3a_S8sZbCx5qj343ycsEfkIF2POA<br>
            구글 시트 연결 불가 시 엑셀 파일 업로드를 이용하세요.
          </p>
        </div>
        """, unsafe_allow_html=True)
 
# ─────────────────────────────────────────────
# 7. DASHBOARD
# ─────────────────────────────────────────────
def render_dashboard(df: pd.DataFrame, source: str):
    df_24 = df[df["등록완료일_dt"] >= "2024-01-01"].copy()
 
    # 소스 배너
    if source == "gsheet":
        ts = st.session_state.get("gsheet_fetched_at", "")
        st.markdown(
            f"<div class='sync-banner'>🟢 <b>Google Sheet 실시간 연결</b> · "
            f"동기화: {ts} · 총 <b>{len(df):,}건</b></div>",
            unsafe_allow_html=True
        )
    else:
        st.markdown(
            f"<div class='sync-banner' style='background:#FFFBEB;border-color:#FDE68A;color:#92400E;'>"
            f"🟡 <b>Excel 파일</b> 사용 중 · 총 <b>{len(df):,}건</b></div>",
            unsafe_allow_html=True
        )
 
    st.markdown("""
    <h1 style='font-size:24px;font-weight:800;color:#111827;margin:4px 0 2px 0;'>
      📊 1P 상품등록 Ops Intelligence
    </h1>
    <p style='color:#6B7280;font-size:13px;margin:0 0 8px 0;'>
      C-Level Strategy Dashboard · 실시간 운영 지표 분석
    </p>
    <hr style='border:none;border-top:1px solid #E5E7EB;margin:0 0 12px 0;'>
    """, unsafe_allow_html=True)
 
    # ══════════════ KPI 카드 ══════════════
    st.markdown("<div class='section-header'>📍 종합 핵심 운영 지표 (Total Cumulative KPIs)</div>",
                unsafe_allow_html=True)
 
    total      = len(df)
    reg_done   = int(df["bool_reg_done"].sum())
    wip        = total - reg_done
    lt_avg     = df["리드타임"].mean()
    lt_med     = df["리드타임"].median()
    delayed    = int((df["지연여부"] == "지연").sum())
 
    cols = st.columns(6)
    def kpi(col, label, val, sub="", color="#4F8EF7"):
        col.markdown(f"""
        <div class='kpi-card' style='border-left-color:{color};'>
          <div class='kpi-label'>{label}</div>
          <div class='kpi-value' style='color:{color};'>{val}</div>
          <div class='kpi-sub'>{sub}</div>
        </div>""", unsafe_allow_html=True)
 
    kpi(cols[0], "전체 분석 건수",  f"{total:,}건",
        "필터 적용 후", "#4F8EF7")
    kpi(cols[1], "최종 등록 완료",  f"{reg_done:,}건",
        f"등록률 {safe_rate(reg_done, total)}%", "#10B981")
    kpi(cols[2], "진행 중 WIP",     f"{wip:,}건",
        "미완료", "#F59E0B")
    kpi(cols[3], "평균 리드타임",
        f"{lt_avg:.1f}일" if pd.notna(lt_avg) else "N/A",
        f"중앙값 {lt_med:.0f}일" if pd.notna(lt_med) else "", "#8B5CF6")
    kpi(cols[4], "지연 발생 건수",  f"{delayed:,}건",
        f"지연률 {safe_rate(delayed, total)}%", "#EF4444")
    kpi(cols[5], "24년+ 분석 건수", f"{len(df_24):,}건",
        "심화 분석 대상", "#06B6D4")
 
    # ══════════════ 파이프라인 ══════════════
    st.markdown("<div class='section-header'>🔄 등록 파이프라인 현황 (전체 기간)</div>",
                unsafe_allow_html=True)
    c1, c2, c3 = st.columns(3)
 
    with c1:
        fig = go.Figure(go.Funnel(
            y=["리스트업 완료", "검토/등록 요청", "구매 완료", "최종 등록"],
            x=[int(df["bool_listed"].sum()), int(df["bool_request_done"].sum()),
               int(df["bool_purchase_done"].sum()), int(df["bool_reg_done"].sum())],
            textinfo="value+percent previous", textfont=dict(size=13),
            marker=dict(color=["#4F8EF7", "#8B5CF6", "#F59E0B", "#10B981"]),
            connector=dict(line=dict(color="#E5E7EB", width=2)),
        ))
        fig.update_layout(**CHART_TPL, title="📉 등록 전환 Funnel", height=310)
        st.plotly_chart(fig, use_container_width=True)
 
    with c2:
        sc = df["현재단계"].value_counts().reset_index()
        sc.columns = ["단계", "건수"]
        fig = go.Figure(go.Pie(
            labels=sc["단계"], values=sc["건수"], hole=0.55,
            marker=dict(colors=[STAGE_COLORS.get(s, "#9CA3AF") for s in sc["단계"]]),
            textinfo="percent+label", textfont=dict(size=11),
        ))
        fig.update_layout(**CHART_TPL, title="🎯 단계별 분포", height=310,
                          legend=dict(orientation="v", x=1.02, y=0.5))
        st.plotly_chart(fig, use_container_width=True)
 
    with c3:
        cross = (df[df["국내해외"].isin(["국내", "해외"])]
                 .groupby(["국내해외", "현재단계"]).size().reset_index(name="건수"))
        fig = px.bar(cross, x="국내해외", y="건수", color="현재단계",
                     color_discrete_map=STAGE_COLORS, barmode="stack",
                     title="🌍 국내/해외별 단계")
        fig.update_layout(**CHART_TPL, height=310,
                          legend=dict(orientation="v", x=1.02, y=0.5))
        st.plotly_chart(fig, use_container_width=True)
 
    # ══════════════ 24년+ 심화 ══════════════
    st.markdown("<div class='section-header-orange'>🚀 2024+ 운영 트렌드 심화 분석</div>",
                unsafe_allow_html=True)
 
    if df_24.empty:
        st.info("선택된 필터 내에 2024년 이후 데이터가 없습니다.")
    else:
        tab1, tab2, tab3, tab4 = st.tabs([
            "📈 시계열 트렌드", "⏱ 리드타임 Deep-Dive", "🚩 지연 분석", "👤 담당자 성과"
        ])
 
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
                                subplot_titles=("등록 완료 건수 vs 전체", "등록률 (%)"),
                                vertical_spacing=0.12, shared_xaxes=True)
            fig.add_trace(go.Bar(x=ts["기간"], y=ts["전체건수"],
                                  name="전체", marker_color="#E5E7EB"), row=1, col=1)
            fig.add_trace(go.Bar(x=ts["기간"], y=ts["등록완료"],
                                  name="등록완료", marker_color="#4F8EF7"), row=1, col=1)
            fig.add_trace(go.Scatter(x=ts["기간"], y=ts["등록률"],
                                      name="등록률%", mode="lines+markers",
                                      line=dict(color="#10B981", width=2),
                                      fill="tozeroy", fillcolor="rgba(16,185,129,0.1)"),
                          row=2, col=1)
            fig.update_layout(**CHART_TPL, height=460, barmode="overlay",
                               title_text=f"{view} 등록 현황 (2024+)")
            fig.update_yaxes(showgrid=True, gridcolor="#F3F4F6")
            st.plotly_chart(fig, use_container_width=True)
            with st.expander("📋 기간별 상세 수치"):
                st.dataframe(ts.style.format({
                    "등록완료": "{:,}", "전체건수": "{:,}",
                    "평균리드타임": "{:.1f}", "등록률": "{:.1f}%"
                }), use_container_width=True, hide_index=True)
 
        with tab2:
            lt = df_24[df_24["리드타임"].notna()].copy()
            r1, r2 = st.columns(2)
            with r1:
                fig = px.box(lt, x="국내해외", y="리드타임", color="국내해외",
                             title="국내/해외 리드타임 분포", points="outliers",
                             color_discrete_map={"국내": "#4F8EF7", "해외": "#F59E0B", "미입력": "#9CA3AF"})
                fig.update_layout(**CHART_TPL, height=340)
                st.plotly_chart(fig, use_container_width=True)
            with r2:
                fig = px.histogram(lt, x="리드타임", color="국내해외",
                                   nbins=30, barmode="overlay", opacity=0.75,
                                   title="리드타임 빈도 분포",
                                   color_discrete_map={"국내": "#4F8EF7", "해외": "#F59E0B", "미입력": "#9CA3AF"})
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
            fig = px.bar(bkt, x="리드타임구간", y="건수", color="국내해외", barmode="group",
                         title="리드타임 구간별 건수",
                         color_discrete_map={"국내": "#4F8EF7", "해외": "#F59E0B", "미입력": "#9CA3AF"})
            fig.update_layout(**CHART_TPL, height=300)
            st.plotly_chart(fig, use_container_width=True)
 
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
                             title="🚩 지연 사유 유형별 건수",
                             color="건수", color_continuous_scale="Reds")
                fig.update_layout(**CHART_TPL, height=320)
                st.plotly_chart(fig, use_container_width=True)
            with d2:
                dm = df_24.groupby(["년월", "지연여부"]).size().reset_index(name="건수")
                fig = px.bar(dm, x="년월", y="건수", color="지연여부",
                             barmode="stack", title="📅 월별 지연/정상 현황",
                             color_discrete_map={"정상": "#10B981", "지연": "#EF4444"})
                fig.update_layout(**CHART_TPL, height=320)
                st.plotly_chart(fig, use_container_width=True)
            if len(ddf) > 0:
                with st.expander(f"📋 지연 건 상세 목록 ({len(ddf)}건)"):
                    scols = ["브랜드(영문)", "요청자_정제", "검토자_정제", "국내해외",
                             "지연분류", "지연 사유", "리드타임", "현재단계"]
                    st.dataframe(ddf[scols].sort_values("리드타임", ascending=False),
                                 use_container_width=True, hide_index=True)
 
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
            for i, (col, color) in enumerate([
                ("담당건수", "#4F8EF7"), ("등록률", "#10B981"), ("평균리드타임", "#F59E0B")
            ]):
                fig.add_trace(go.Bar(
                    x=pr["검토자_정제"], y=pr[col].round(1), name=col,
                    marker_color=color, text=pr[col].round(1), textposition="auto",
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
                         color="등록률", color_continuous_scale="Blues",
                         title="요청자별 등록 요청 건수 TOP 15 (2024+)", text="요청건수")
            fig.update_layout(**CHART_TPL, height=320)
            st.plotly_chart(fig, use_container_width=True)
 
    # ══════════════ YoY ══════════════
    st.markdown("<div class='section-header-green'>📊 연도별 YoY 성과 비교 (2023 ~ 2026)</div>",
                unsafe_allow_html=True)
 
    yoy = df.groupby("년도").agg(
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
        fig.add_trace(go.Bar(x=yoy["년도"], y=yoy["전체건수"], name="전체",    marker_color="#E5E7EB"))
        fig.add_trace(go.Bar(x=yoy["년도"], y=yoy["등록완료"], name="등록완료", marker_color="#4F8EF7"))
        fig.update_layout(**CHART_TPL, title="연도별 전체 vs 등록완료",
                          barmode="overlay", height=300)
        st.plotly_chart(fig, use_container_width=True)
    with y2:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(go.Bar(x=yoy["년도"], y=yoy["평균리드타임"].round(1),
                              name="평균 리드타임(일)", marker_color="#8B5CF6"), secondary_y=False)
        fig.add_trace(go.Scatter(x=yoy["년도"], y=yoy["지연률"], name="지연률(%)",
                                  mode="lines+markers",
                                  line=dict(color="#EF4444", width=2)), secondary_y=True)
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
 
    # ══════════════ 마스터 트래킹 ══════════════
    st.markdown("<div class='section-header'>📑 마스터 업무 트래킹 시트 (전체 레코드)</div>",
                unsafe_allow_html=True)
 
    col_show = ["브랜드(영문)", "요청자_정제", "검토자_정제", "국내해외",
                "현재단계", "지연분류", "리드타임", "년월", "비고_text"]
    ddisp = df[col_show].copy().rename(columns={
        "브랜드(영문)": "브랜드", "요청자_정제": "요청자", "검토자_정제": "검토자",
        "비고_text": "비고", "년월": "등록년월"
    })
 
    sort_sel = st.selectbox("정렬 기준", ["리드타임(내림)", "등록년월(최신)", "현재단계"])
    if sort_sel == "리드타임(내림)":    ddisp = ddisp.sort_values("리드타임", ascending=False)
    elif sort_sel == "등록년월(최신)":   ddisp = ddisp.sort_values("등록년월", ascending=False)
    else:                                ddisp = ddisp.sort_values("현재단계")
 
    st.dataframe(ddisp, use_container_width=True, hide_index=True, height=420)
 
    csv = ddisp.to_csv(index=False).encode("utf-8-sig")
    st.download_button("📥 필터링 데이터 다운로드 (CSV)", data=csv,
                       file_name=f"1P_Ops_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                       mime="text/csv")
 
 
# ─────────────────────────────────────────────
# 8. MAIN
# ─────────────────────────────────────────────
def main():
    source = st.session_state.get("data_source", "none")
 
    # ── 데이터 로드 ──
    if source == "gsheet" and "gsheet_values" in st.session_state:
        cache_key = st.session_state.get("gsheet_fetched_at", "")
        df = preprocess_gsheet(cache_key, st.session_state["gsheet_values"])
 
    elif source == "xlsx" and "xlsx_bytes" in st.session_state:
        df = preprocess_bytes(st.session_state["xlsx_bytes"])
 
    else:
        # 시크릿 존재 시 앱 최초 실행에 자동 연결 시도
        has_secret = False
        try:
            _ = st.secrets["gcp_service_account"]
            has_secret = True
        except Exception:
            pass
 
        if has_secret and "auto_tried" not in st.session_state:
            st.session_state["auto_tried"] = True
            with st.spinner("🔄 구글 시트 자동 연결 중..."):
                vals, err = load_from_gsheet()
            if not err:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.session_state["gsheet_values"]     = vals
                st.session_state["gsheet_fetched_at"] = ts
                st.session_state["data_source"]       = "gsheet"
                st.rerun()
            else:
                st.warning(f"자동 연결 실패: {err}")
                render_landing()
                return
        else:
            render_landing()
            return
 
    # ── 필터 ──
    f_rev, f_country, f_year, f_stage, f_delay, keyword = render_sidebar(df)
 
    dff = df.copy()
    if f_rev:     dff = dff[dff["검토자_정제"].isin(f_rev)]
    if f_country: dff = dff[dff["국내해외"].isin(f_country)]
    if f_year:    dff = dff[dff["년도"].isin(f_year) | dff["년도"].isna()]
    if f_stage:   dff = dff[dff["현재단계"].isin(f_stage)]
    if f_delay:   dff = dff[dff["지연여부"].isin(f_delay)]
    if keyword:   dff = dff[dff.apply(lambda r: keyword.strip().lower() in str(r).lower(), axis=1)]
 
    render_dashboard(dff, source)
 
 
if __name__ == "__main__":
    main()
 
