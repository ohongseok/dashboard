import io
import re
from typing import List, Dict, Optional
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
from datetime import datetime, date
 
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
 
/* KPI 카드 */
.kpi-card {
    background: white;
    border-radius: 16px;
    padding: 20px 24px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
    border-left: 4px solid #4F8EF7;
    margin-bottom: 8px;
}
.kpi-label { font-size: 12px; color: #6B7280; font-weight: 600; letter-spacing: 0.5px; text-transform: uppercase; }
.kpi-value { font-size: 32px; font-weight: 800; color: #111827; line-height: 1.1; margin: 4px 0; }
.kpi-sub { font-size: 12px; color: #9CA3AF; }
.kpi-delta-pos { color: #10B981; font-size: 13px; font-weight: 600; }
.kpi-delta-neg { color: #EF4444; font-size: 13px; font-weight: 600; }
 
/* 섹션 헤더 */
.section-header {
    background: linear-gradient(90deg, #4F8EF7 0%, #7C3AED 100%);
    color: white;
    padding: 10px 20px;
    border-radius: 10px;
    font-size: 15px;
    font-weight: 700;
    margin: 20px 0 12px 0;
    letter-spacing: 0.3px;
}
.section-header-orange {
    background: linear-gradient(90deg, #F59E0B 0%, #EF4444 100%);
    color: white;
    padding: 10px 20px;
    border-radius: 10px;
    font-size: 15px;
    font-weight: 700;
    margin: 20px 0 12px 0;
}
.section-header-green {
    background: linear-gradient(90deg, #10B981 0%, #059669 100%);
    color: white;
    padding: 10px 20px;
    border-radius: 10px;
    font-size: 15px;
    font-weight: 700;
    margin: 20px 0 12px 0;
}
 
/* 상태 배지 */
.badge-done { background:#D1FAE5; color:#065F46; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:600; }
.badge-wip  { background:#FEF3C7; color:#92400E; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:600; }
.badge-fail { background:#FEE2E2; color:#991B1B; padding:2px 10px; border-radius:20px; font-size:12px; font-weight:600; }
 
/* 사이드바 */
[data-testid="stSidebar"] { background: #1E1E2E; }
[data-testid="stSidebar"] .stMarkdown, [data-testid="stSidebar"] label { color: #C9D1D9 !important; }
 
/* 탭 */
.stTabs [data-baseweb="tab-list"] { gap: 8px; background: white; padding: 8px; border-radius: 12px; }
.stTabs [data-baseweb="tab"] { border-radius: 8px; font-weight: 600; font-size: 13px; height: 40px; }
 
/* 데이터테이블 */
.stDataFrame { border-radius: 12px; overflow: hidden; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
 
div[data-testid="stMetricValue"] > div { font-size: 28px !important; font-weight: 800 !important; }
</style>
""", unsafe_allow_html=True)
 
# ─────────────────────────────────────────────
# 1. CONSTANTS
# ─────────────────────────────────────────────
FIXED_REVIEWERS = ["오홍석", "유지윤", "장근수", "백건우"]
TRUE_VALUES = {"true", "1", "y", "yes", "완료", "o", "v", "✓", "check", "checked"}
 
STAGE_COLORS = {
    "5.등록 완료":      "#10B981",
    "4.구매 완료":      "#3B82F6",
    "3.구매 요청":      "#8B5CF6",
    "2.검토/등록 요청":  "#F59E0B",
    "1.리스트업 완료":   "#6B7280",
    "0.미진행":         "#D1D5DB",
    "X.등록 불가":      "#EF4444",
}
 
DELAY_CATEGORY_MAP = {
    "해외배송/리드타임": ["해외배송", "해외 배송", "배송", "입고", "출고", "리드타임", "arrival", "ship", "묶음"],
    "샘플/실물확인":    ["샘플", "실물", "확인후 등록", "실물 확인"],
    "가품검수/정가품":  ["가품", "정가품", "검수", "authentic"],
    "데이터/품번이슈":  ["품번", "sku", "데이터", "정보", "리스트업", "모델명"],
    "가격/운영판단":    ["가격", "원가", "마진", "보류", "불가"],
    "담당자/행정":      ["담당자", "부재", "행정"],
    "구매지연":         ["구매 지연", "구매지연"],
}
 
# ─────────────────────────────────────────────
# 2. DATA HELPERS
# ─────────────────────────────────────────────
def parse_bool(v) -> bool:
    if pd.isna(v) or v == "": return False
    if isinstance(v, bool): return v
    if isinstance(v, (int, float)): return bool(v)
    return str(v).strip().lower() in TRUE_VALUES
 
def parse_korean_date(v):
    if pd.isna(v) or str(v).strip() in ["", "-", "#REF!", "nan"]: return pd.NaT
    s = str(v).strip()
    for fmt in ["%y.%m.%d", "%Y.%m.%d", "%Y-%m-%d", "%y-%m-%d"]:
        try:
            return pd.to_datetime(s, format=fmt)
        except: pass
    return pd.to_datetime(s, errors="coerce")
 
def safe_rate(num, den) -> float:
    return round((num / den) * 100, 1) if den and den > 0 else 0.0
 
def classify_delay(reason: str) -> str:
    if not reason or reason.strip() in ["-", "", "nan"]: return "없음"
    r = reason.lower()
    for cat, keywords in DELAY_CATEGORY_MAP.items():
        if any(k.lower() in r for k in keywords): return cat
    return "기타"
 
def normalize_requester(v) -> str:
    if pd.isna(v) or str(v).strip() == "": return "미입력"
    return re.split(r"[,/|·\n\s]+", str(v).strip())[0].strip()
 
# ─────────────────────────────────────────────
# 3. PREPROCESSING ENGINE
# ─────────────────────────────────────────────
@st.cache_data(ttl=600, show_spinner=False)
def preprocess(raw_bytes: bytes) -> pd.DataFrame:
    df_raw = pd.read_excel(io.BytesIO(raw_bytes), sheet_name="Summary", header=2)
    df_raw.columns = [str(c).strip() for c in df_raw.columns]
 
    # 유효 행만 (브랜드명 있고, #REF! 행 제외)
    df = df_raw[
        df_raw["브랜드(영문)"].notna() &
        (df_raw["브랜드(영문)"].astype(str).str.strip() != "") &
        (df_raw["등록 완료일"].astype(str).str.strip() != "#REF!")
    ].copy().reset_index(drop=True)
 
    # 날짜 파싱
    df["등록완료일_dt"]  = df["등록 완료일"].apply(parse_korean_date)
    df["등록요청일_dt"]  = df["등록 요청일"].apply(parse_korean_date)
 
    # 시간 컬럼
    df["년도"]   = df["등록완료일_dt"].dt.year.astype("Int64")
    df["월"]     = df["등록완료일_dt"].dt.month.astype("Int64")
    df["년월"]   = df["등록완료일_dt"].dt.strftime("%Y-%m")
    iso = df["등록완료일_dt"].dt.isocalendar()
    df["ISO년도"] = iso.year.astype("Int64")
    df["주차"]   = iso.week.astype("Int64")
    df["년주차"] = df["ISO년도"].astype(str) + "-W" + df["주차"].astype(str).str.zfill(2)
    df["분기"]   = "Q" + df["등록완료일_dt"].dt.quarter.astype(str)
    df["년분기"] = df["년도"].astype(str) + "-" + df["분기"]
 
    # 리드타임 (요청 → 완료)
    df["리드타임"] = (df["등록완료일_dt"] - df["등록요청일_dt"]).dt.days
    df["리드타임"] = df["리드타임"].where((df["리드타임"] >= 0) & (df["리드타임"] <= 180))
 
    # 불리언 상태
    for src, dst in [
        ("리스트업 완료",          "bool_listed"),
        ("검토 및 등록 요청 완료",  "bool_request_done"),
        ("상품 구매 요청",          "bool_purchase_req"),
        ("상품 구매 완료",          "bool_purchase_done"),
        ("등록 완료 (앱 노출 시 체크)", "bool_reg_done"),
    ]:
        df[dst] = df[src].apply(parse_bool)
 
    # 국내/해외
    def classify_country(v):
        s = str(v).strip() if pd.notna(v) else ""
        if "국내" in s: return "국내"
        if "해외" in s: return "해외"
        return "미입력"
    df["국내해외"] = df["국내/해외"].apply(classify_country)
 
    # 요청자 정제
    df["요청자_정제"] = df["요청자"].apply(normalize_requester)
 
    # 검토자 정제
    df["검토자_정제"] = df["검토자"].apply(lambda x: str(x).strip() if pd.notna(x) else "미입력")
 
    # 비고 텍스트
    df["비고_text"] = df["비고"].apply(lambda x: str(x).strip() if pd.notna(x) else "")
 
    # 지연 분류
    df["지연분류"] = df["지연 사유"].apply(lambda x: classify_delay(str(x)) if pd.notna(x) else "없음")
 
    # 현재 단계 (WF funnel)
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
 
    # 지연 여부 플래그
    df["지연여부"] = df["지연분류"].apply(lambda x: "지연" if x != "없음" else "정상")
 
    return df
 
 
# ─────────────────────────────────────────────
# 4. CHART HELPERS
# ─────────────────────────────────────────────
CHART_TEMPLATE = dict(
    template="plotly_white",
    font=dict(family="Pretendard, -apple-system, sans-serif", size=12),
    margin=dict(l=16, r=16, t=36, b=16),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
)
 
def apply_template(fig):
    fig.update_layout(**CHART_TEMPLATE)
    fig.update_xaxes(showgrid=True, gridcolor="#F3F4F6", zeroline=False)
    fig.update_yaxes(showgrid=True, gridcolor="#F3F4F6", zeroline=False)
    return fig
 
 
# ─────────────────────────────────────────────
# 5. SIDEBAR
# ─────────────────────────────────────────────
def render_sidebar(df: pd.DataFrame):
    with st.sidebar:
        st.markdown("""
        <div style='padding:16px 0 8px 0;'>
        <span style='color:#4F8EF7;font-size:20px;font-weight:800;'>📊 1P Ops Intel</span><br>
        <span style='color:#6B7280;font-size:11px;'>C-Level Strategy Dashboard</span>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("---")
 
        # 검토자
        reviewers = sorted(df["검토자_정제"].unique().tolist())
        f_rev = st.multiselect("👤 검토자", options=reviewers, default=[r for r in FIXED_REVIEWERS if r in reviewers])
 
        # 국내/해외
        country_opts = sorted(df["국내해외"].unique().tolist())
        f_country = st.multiselect("🌍 국내/해외", options=country_opts, default=country_opts)
 
        # 연도
        year_opts = sorted([y for y in df["년도"].dropna().unique().tolist()])
        f_year = st.multiselect("📅 분석 연도", options=year_opts, default=year_opts)
 
        # 단계
        stage_opts = sorted(df["현재단계"].unique().tolist())
        f_stage = st.multiselect("🔖 진행 단계", options=stage_opts, default=stage_opts)
 
        # 지연 여부
        f_delay = st.multiselect("⏱ 지연 여부", options=["정상", "지연"], default=["정상", "지연"])
 
        # 키워드
        keyword = st.text_input("🔍 브랜드/비고 검색", placeholder="예: Jellycat, 샘플확인...")
 
        st.markdown("---")
        st.markdown(f"<div style='color:#6B7280;font-size:11px;'>마지막 업데이트<br>{datetime.now().strftime('%Y-%m-%d %H:%M')}</div>", unsafe_allow_html=True)
 
    return f_rev, f_country, f_year, f_stage, f_delay, keyword
 
 
# ─────────────────────────────────────────────
# 6. MAIN
# ─────────────────────────────────────────────
def main():
    # ── 파일 업로드 ──────────────────────────────
    if "raw_bytes" not in st.session_state:
        col_c = st.columns([1, 2, 1])
        with col_c[1]:
            st.markdown("""
            <div style='text-align:center;padding:60px 0 20px 0;'>
            <div style='font-size:56px;'>📊</div>
            <h2 style='font-weight:800;color:#111827;'>1P 상품등록 Ops Intelligence</h2>
            <p style='color:#6B7280;'>구글 시트에서 다운로드한 .xlsx 파일을 업로드하면<br>C-Level 보고용 대시보드가 자동으로 생성됩니다.</p>
            </div>
            """, unsafe_allow_html=True)
            uploaded = st.file_uploader("📂 엑셀 파일 업로드 (Summary 시트 포함)", type=["xlsx"])
            if uploaded:
                st.session_state["raw_bytes"] = uploaded.read()
                st.rerun()
        return
 
    # ── 데이터 로드 ──────────────────────────────
    df_base = preprocess(st.session_state["raw_bytes"])
 
    # ── 사이드바 필터 ─────────────────────────────
    f_rev, f_country, f_year, f_stage, f_delay, keyword = render_sidebar(df_base)
 
    # ── 필터 적용 ─────────────────────────────────
    df = df_base.copy()
    if f_rev:     df = df[df["검토자_정제"].isin(f_rev)]
    if f_country: df = df[df["국내해외"].isin(f_country)]
    if f_year:    df = df[df["년도"].isin(f_year) | df["년도"].isna()]
    if f_stage:   df = df[df["현재단계"].isin(f_stage)]
    if f_delay:   df = df[df["지연여부"].isin(f_delay)]
    if keyword:   df = df[df.apply(lambda r: keyword.strip().lower() in str(r).lower(), axis=1)]
 
    df_24 = df[df["등록완료일_dt"] >= "2024-01-01"].copy()
 
    # ─────────────────────────────────────────
    # HEADER
    # ─────────────────────────────────────────
    st.markdown("""
    <div style='display:flex;align-items:center;justify-content:space-between;padding:8px 0 4px 0;'>
        <div>
            <h1 style='font-size:26px;font-weight:800;color:#111827;margin:0;'>
                📊 1P 상품등록 Ops Intelligence
            </h1>
            <p style='color:#6B7280;font-size:13px;margin:2px 0 0 0;'>
                C-Level Strategy Dashboard · 실시간 운영 지표 분석
            </p>
        </div>
        <div style='text-align:right;'>
            <span style='background:#EEF2FF;color:#4F8EF7;padding:6px 14px;border-radius:20px;font-size:12px;font-weight:700;'>
                LIVE
            </span>
        </div>
    </div>
    <hr style='border:none;border-top:1px solid #E5E7EB;margin:8px 0 16px 0;'>
    """, unsafe_allow_html=True)
 
    # ─────────────────────────────────────────
    # SECTION 1: KPI 카드
    # ─────────────────────────────────────────
    st.markdown("<div class='section-header'>📍 종합 핵심 운영 지표 (Total Cumulative KPIs)</div>", unsafe_allow_html=True)
 
    total       = len(df)
    reg_done    = int(df["bool_reg_done"].sum())
    reg_rate    = safe_rate(reg_done, total)
    wip         = total - reg_done
    lt_avg      = df["리드타임"].mean()
    lt_med      = df["리드타임"].median()
    delayed     = int((df["지연여부"] == "지연").sum())
    delay_rate  = safe_rate(delayed, total)
 
    # KPI 카드 (커스텀 HTML)
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    def kpi(col, label, value, sub="", color="#4F8EF7"):
        col.markdown(f"""
        <div class='kpi-card' style='border-left-color:{color};'>
            <div class='kpi-label'>{label}</div>
            <div class='kpi-value' style='color:{color};'>{value}</div>
            <div class='kpi-sub'>{sub}</div>
        </div>
        """, unsafe_allow_html=True)
 
    kpi(c1, "전체 분석 건수",  f"{total:,}건",      f"필터 적용 후",      "#4F8EF7")
    kpi(c2, "최종 등록 완료",  f"{reg_done:,}건",   f"등록률 {reg_rate}%", "#10B981")
    kpi(c3, "진행 중 (WIP)",   f"{wip:,}건",        f"미완료 건수",        "#F59E0B")
    kpi(c4, "평균 리드타임",
        f"{lt_avg:.1f}일" if pd.notna(lt_avg) else "N/A",
        f"중앙값 {lt_med:.0f}일" if pd.notna(lt_med) else "",
        "#8B5CF6")
    kpi(c5, "지연 발생 건수",  f"{delayed:,}건",    f"지연률 {delay_rate}%","#EF4444")
    kpi(c6, "24년+ 분석 건수", f"{len(df_24):,}건", "상세 분석 대상",      "#06B6D4")
 
    st.markdown("<br>", unsafe_allow_html=True)
 
    # ─────────────────────────────────────────
    # SECTION 2: 파이프라인 & 전환율
    # ─────────────────────────────────────────
    st.markdown("<div class='section-header'>🔄 등록 파이프라인 현황 (전체 기간)</div>", unsafe_allow_html=True)
 
    col_f, col_p, col_s = st.columns([4, 4, 4])
 
    with col_f:
        # Funnel
        funnel_stages = ["리스트업 완료", "검토/등록 요청", "구매 완료", "최종 등록 완료"]
        funnel_vals = [
            int(df["bool_listed"].sum()),
            int(df["bool_request_done"].sum()),
            int(df["bool_purchase_done"].sum()),
            int(df["bool_reg_done"].sum()),
        ]
        fig_funnel = go.Figure(go.Funnel(
            y=funnel_stages, x=funnel_vals,
            textinfo="value+percent previous",
            textfont=dict(size=13, family="Pretendard"),
            marker=dict(color=["#4F8EF7", "#8B5CF6", "#F59E0B", "#10B981"]),
            connector=dict(line=dict(color="#E5E7EB", width=2)),
        ))
        fig_funnel.update_layout(**CHART_TEMPLATE, title="📉 등록 전환 Funnel", height=300)
        st.plotly_chart(fig_funnel, use_container_width=True)
 
    with col_p:
        # 현재 단계 분포 (도넛)
        stage_cnt = df["현재단계"].value_counts().reset_index()
        stage_cnt.columns = ["단계", "건수"]
        stage_cnt = stage_cnt.sort_values("단계")
        colors = [STAGE_COLORS.get(s, "#9CA3AF") for s in stage_cnt["단계"]]
        fig_donut = go.Figure(go.Pie(
            labels=stage_cnt["단계"],
            values=stage_cnt["건수"],
            hole=0.55,
            marker=dict(colors=colors),
            textinfo="percent+label",
            textfont=dict(size=11),
            hovertemplate="%{label}: %{value}건 (%{percent})<extra></extra>",
        ))
        fig_donut.update_layout(**CHART_TEMPLATE, title="🎯 현재 단계 분포", height=300,
                                 legend=dict(orientation="v", x=1.02, y=0.5))
        st.plotly_chart(fig_donut, use_container_width=True)
 
    with col_s:
        # 국내 vs 해외 단계 비교
        cross = df.groupby(["국내해외", "현재단계"]).size().reset_index(name="건수")
        cross = cross[cross["국내해외"].isin(["국내", "해외"])]
        fig_cross = px.bar(
            cross, x="국내해외", y="건수", color="현재단계",
            color_discrete_map=STAGE_COLORS,
            title="🌍 국내/해외별 단계 현황",
            barmode="stack",
        )
        fig_cross.update_layout(**CHART_TEMPLATE, height=300, showlegend=True,
                                  legend=dict(orientation="v", x=1.02, y=0.5))
        st.plotly_chart(fig_cross, use_container_width=True)
 
    # ─────────────────────────────────────────
    # SECTION 3: 24년+ 심화 분석
    # ─────────────────────────────────────────
    st.markdown("<div class='section-header-orange'>🚀 2024+ 운영 트렌드 심화 분석</div>", unsafe_allow_html=True)
 
    if df_24.empty:
        st.info("선택된 필터 조건 내에 2024년 이후 데이터가 없습니다.")
    else:
        tab1, tab2, tab3, tab4 = st.tabs([
            "📈 시계열 트렌드",
            "⏱ 리드타임 Deep-Dive",
            "🚩 지연 분석",
            "👤 담당자 성과"
        ])
 
        # ── TAB1: 시계열 트렌드 ──────────────────
        with tab1:
            view = st.radio("집계 단위", ["월별", "주차별", "분기별"], horizontal=True, key="ts_view")
 
            if view == "월별":
                g = df_24.dropna(subset=["년월"]).groupby("년월")
            elif view == "주차별":
                g = df_24.dropna(subset=["년주차"]).groupby("년주차")
            else:
                g = df_24.dropna(subset=["년분기"]).groupby("년분기")
 
            ts = g.agg(
                등록완료=("bool_reg_done", "sum"),
                전체건수=("bool_reg_done", "count"),
                평균리드타임=("리드타임", "mean"),
            ).reset_index()
            ts.columns = ["기간", "등록완료", "전체건수", "평균리드타임"]
            ts["등록률"] = (ts["등록완료"] / ts["전체건수"] * 100).round(1)
 
            fig_ts = make_subplots(
                rows=2, cols=1,
                subplot_titles=("📦 기간별 등록 완료 건수", "📊 기간별 등록률 (%)"),
                vertical_spacing=0.12,
                shared_xaxes=True,
            )
            fig_ts.add_trace(
                go.Bar(x=ts["기간"], y=ts["등록완료"],
                       name="등록완료", marker_color="#4F8EF7",
                       hovertemplate="%{x}<br>등록완료: %{y}건<extra></extra>"),
                row=1, col=1
            )
            fig_ts.add_trace(
                go.Scatter(x=ts["기간"], y=ts["전체건수"],
                           name="전체", mode="lines+markers",
                           line=dict(color="#9CA3AF", dash="dot"),
                           hovertemplate="%{x}<br>전체: %{y}건<extra></extra>"),
                row=1, col=1
            )
            fig_ts.add_trace(
                go.Scatter(x=ts["기간"], y=ts["등록률"],
                           name="등록률%", mode="lines+markers",
                           line=dict(color="#10B981", width=2),
                           fill="tozeroy", fillcolor="rgba(16,185,129,0.1)",
                           hovertemplate="%{x}<br>등록률: %{y}%<extra></extra>"),
                row=2, col=1
            )
            fig_ts.update_layout(**CHART_TEMPLATE, height=440, showlegend=True,
                                  title_text="기간별 등록 완료 현황")
            fig_ts.update_yaxes(showgrid=True, gridcolor="#F3F4F6")
            st.plotly_chart(fig_ts, use_container_width=True)
 
            # 수치 테이블
            with st.expander("📋 기간별 상세 수치"):
                st.dataframe(
                    ts.style.format({"등록완료": "{:,}", "전체건수": "{:,}", "평균리드타임": "{:.1f}", "등록률": "{:.1f}%"}),
                    use_container_width=True, hide_index=True
                )
 
        # ── TAB2: 리드타임 Deep-Dive ─────────────
        with tab2:
            lt_data = df_24[df_24["리드타임"].notna()].copy()
 
            c1t, c2t = st.columns([5, 5])
            with c1t:
                # 국내/해외 리드타임 박스플롯
                fig_box = px.box(
                    lt_data, x="국내해외", y="리드타임",
                    color="국내해외",
                    title="📦 국내/해외 리드타임 분포",
                    color_discrete_map={"국내": "#4F8EF7", "해외": "#F59E0B", "미입력": "#9CA3AF"},
                    points="outliers",
                )
                fig_box.update_layout(**CHART_TEMPLATE, height=340)
                st.plotly_chart(fig_box, use_container_width=True)
 
            with c2t:
                # 히스토그램
                fig_hist = px.histogram(
                    lt_data, x="리드타임", color="국내해외",
                    nbins=30, barmode="overlay", opacity=0.75,
                    title="⏱ 리드타임 빈도 분포",
                    color_discrete_map={"국내": "#4F8EF7", "해외": "#F59E0B", "미입력": "#9CA3AF"},
                )
                fig_hist.update_layout(**CHART_TEMPLATE, height=340)
                st.plotly_chart(fig_hist, use_container_width=True)
 
            # 리드타임 통계 테이블
            lt_stat = lt_data.groupby("국내해외")["리드타임"].agg(
                건수="count", 평균="mean", 중앙값="median", 최솟값="min", 최댓값="max",
            ).reset_index().round(1)
            st.markdown("**리드타임 통계 요약**")
            st.dataframe(lt_stat.style.format({
                "평균": "{:.1f}일", "중앙값": "{:.1f}일", "최솟값": "{:.0f}일", "최댓값": "{:.0f}일"
            }), use_container_width=True, hide_index=True)
 
            # 리드타임 구간별 분류
            def lt_bucket(d):
                if pd.isna(d): return "데이터 없음"
                if d <= 7:  return "①  1주 이내"
                if d <= 14: return "②  2주 이내"
                if d <= 30: return "③  1개월 이내"
                return "④  1개월 초과"
 
            lt_data["리드타임구간"] = lt_data["리드타임"].apply(lt_bucket)
            lt_bucket_cnt = lt_data.groupby(["국내해외", "리드타임구간"]).size().reset_index(name="건수")
            fig_lt_bkt = px.bar(
                lt_bucket_cnt, x="리드타임구간", y="건수", color="국내해외",
                barmode="group", title="리드타임 구간별 건수",
                color_discrete_map={"국내": "#4F8EF7", "해외": "#F59E0B", "미입력": "#9CA3AF"},
            )
            fig_lt_bkt.update_layout(**CHART_TEMPLATE, height=300)
            st.plotly_chart(fig_lt_bkt, use_container_width=True)
 
        # ── TAB3: 지연 분석 ──────────────────────
        with tab3:
            delay_df = df_24[df_24["지연여부"] == "지연"].copy()
            no_delay = len(df_24) - len(delay_df)
 
            ca, cb, cc = st.columns(3)
            ca.metric("24년+ 지연 건수",  f"{len(delay_df):,}건")
            cb.metric("24년+ 정상 건수",  f"{no_delay:,}건")
            cc.metric("24년+ 지연률",     f"{safe_rate(len(delay_df), len(df_24))}%")
 
            d1, d2 = st.columns([5, 5])
            with d1:
                dc = df_24["지연분류"].value_counts().reset_index()
                dc.columns = ["분류", "건수"]
                dc = dc[dc["분류"] != "없음"]
                fig_d = px.bar(dc, y="분류", x="건수", orientation="h",
                               title="🚩 지연 사유 유형별 건수",
                               color="건수", color_continuous_scale="Reds")
                fig_d.update_layout(**CHART_TEMPLATE, height=320)
                st.plotly_chart(fig_d, use_container_width=True)
 
            with d2:
                # 월별 지연 추이
                delay_monthly = df_24.groupby(["년월", "지연여부"]).size().reset_index(name="건수")
                fig_dm = px.bar(delay_monthly, x="년월", y="건수", color="지연여부",
                                barmode="stack", title="📅 월별 지연/정상 현황",
                                color_discrete_map={"정상": "#10B981", "지연": "#EF4444"})
                fig_dm.update_layout(**CHART_TEMPLATE, height=320)
                st.plotly_chart(fig_dm, use_container_width=True)
 
            # 지연 건 상세 리스트
            if len(delay_df) > 0:
                with st.expander(f"📋 지연 건 상세 목록 ({len(delay_df)}건)"):
                    show_cols = ["브랜드(영문)", "요청자_정제", "검토자_정제", "국내해외", "지연분류", "지연 사유", "리드타임", "현재단계"]
                    st.dataframe(
                        delay_df[show_cols].sort_values("리드타임", ascending=False),
                        use_container_width=True, hide_index=True
                    )
 
        # ── TAB4: 담당자 성과 ─────────────────────
        with tab4:
            per_rev = df_24.groupby("검토자_정제").agg(
                담당건수=("bool_reg_done", "count"),
                등록완료=("bool_reg_done", "sum"),
                평균리드타임=("리드타임", "mean"),
                지연건수=("지연여부", lambda x: (x == "지연").sum()),
            ).reset_index()
            per_rev["등록률"] = (per_rev["등록완료"] / per_rev["담당건수"] * 100).round(1)
            per_rev["지연률"] = (per_rev["지연건수"] / per_rev["담당건수"] * 100).round(1)
            per_rev = per_rev.sort_values("담당건수", ascending=False)
 
            # 검토자별 바 차트
            fig_rev = make_subplots(rows=1, cols=3,
                subplot_titles=("담당 건수", "등록률 (%)", "평균 리드타임 (일)"))
            for i, (col, cname) in enumerate([("담당건수", "#4F8EF7"), ("등록률", "#10B981"), ("평균리드타임", "#F59E0B")]):
                fig_rev.add_trace(go.Bar(
                    x=per_rev["검토자_정제"],
                    y=per_rev[col].round(1),
                    name=col, marker_color=cname,
                    text=per_rev[col].round(1), textposition="auto",
                ), row=1, col=i+1)
            fig_rev.update_layout(**CHART_TEMPLATE, height=320, showlegend=False,
                                   title_text="검토자별 운영 성과 지표 (2024+)")
            st.plotly_chart(fig_rev, use_container_width=True)
 
            # 요청자별 TOP 등록 건수
            per_req = df_24.groupby("요청자_정제").agg(
                요청건수=("bool_reg_done", "count"),
                등록완료=("bool_reg_done", "sum"),
            ).reset_index()
            per_req["등록률"] = (per_req["등록완료"] / per_req["요청건수"] * 100).round(1)
            per_req = per_req.sort_values("요청건수", ascending=False).head(15)
 
            fig_req = px.bar(per_req, x="요청자_정제", y="요청건수",
                             color="등록률", color_continuous_scale="Blues",
                             title="📦 요청자별 등록 요청 건수 TOP 15 (2024+)",
                             text="요청건수")
            fig_req.update_layout(**CHART_TEMPLATE, height=320)
            st.plotly_chart(fig_req, use_container_width=True)
 
    # ─────────────────────────────────────────
    # SECTION 4: 연도별 YoY 비교
    # ─────────────────────────────────────────
    st.markdown("<div class='section-header-green'>📊 연도별 YoY 성과 비교 (2023 ~ 2026)</div>", unsafe_allow_html=True)
 
    yoy = df.groupby("년도").agg(
        전체건수=("bool_reg_done", "count"),
        등록완료=("bool_reg_done", "sum"),
        평균리드타임=("리드타임", "mean"),
        지연건수=("지연여부", lambda x: (x == "지연").sum()),
    ).reset_index().dropna(subset=["년도"])
    yoy["등록률"] = (yoy["등록완료"] / yoy["전체건수"] * 100).round(1)
    yoy["지연률"] = (yoy["지연건수"] / yoy["전체건수"] * 100).round(1)
    yoy["년도"]  = yoy["년도"].astype(int).astype(str)
 
    y1, y2 = st.columns(2)
    with y1:
        fig_yoy1 = go.Figure()
        fig_yoy1.add_trace(go.Bar(x=yoy["년도"], y=yoy["전체건수"],
                                   name="전체", marker_color="#E5E7EB"))
        fig_yoy1.add_trace(go.Bar(x=yoy["년도"], y=yoy["등록완료"],
                                   name="등록완료", marker_color="#4F8EF7"))
        fig_yoy1.update_layout(**CHART_TEMPLATE, title="연도별 전체 vs 등록완료", barmode="overlay", height=300)
        st.plotly_chart(fig_yoy1, use_container_width=True)
 
    with y2:
        fig_yoy2 = make_subplots(specs=[[{"secondary_y": True}]])
        fig_yoy2.add_trace(go.Bar(x=yoy["년도"], y=yoy["평균리드타임"].round(1),
                                   name="평균 리드타임(일)", marker_color="#8B5CF6"), secondary_y=False)
        fig_yoy2.add_trace(go.Scatter(x=yoy["년도"], y=yoy["지연률"],
                                       name="지연률(%)", mode="lines+markers",
                                       line=dict(color="#EF4444", width=2)), secondary_y=True)
        fig_yoy2.update_layout(**CHART_TEMPLATE, title="연도별 리드타임 vs 지연률", height=300)
        fig_yoy2.update_yaxes(title_text="리드타임(일)", secondary_y=False)
        fig_yoy2.update_yaxes(title_text="지연률(%)", secondary_y=True)
        st.plotly_chart(fig_yoy2, use_container_width=True)
 
    # YoY 수치 테이블
    st.markdown("**연도별 종합 KPI 테이블**")
    st.dataframe(
        yoy.style.format({
            "전체건수": "{:,}", "등록완료": "{:,}", "지연건수": "{:,}",
            "평균리드타임": "{:.1f}일", "등록률": "{:.1f}%", "지연률": "{:.1f}%"
        }).background_gradient(subset=["등록률"], cmap="Greens")
          .background_gradient(subset=["지연률"], cmap="Reds"),
        use_container_width=True, hide_index=True
    )
 
    # ─────────────────────────────────────────
    # SECTION 5: 마스터 트래킹 시트
    # ─────────────────────────────────────────
    st.markdown("<div class='section-header'>📑 마스터 업무 트래킹 시트 (전체 레코드)</div>", unsafe_allow_html=True)
 
    # 단계 배지 색상
    def stage_badge(s):
        if "완료" in s: return f"<span class='badge-done'>{s}</span>"
        if "불가" in s: return f"<span class='badge-fail'>{s}</span>"
        return f"<span class='badge-wip'>{s}</span>"
 
    col_show = ["브랜드(영문)", "요청자_정제", "검토자_정제", "국내해외", "현재단계", "지연분류", "리드타임", "년월", "비고_text"]
    df_display = df[col_show].copy().rename(columns={
        "브랜드(영문)": "브랜드", "요청자_정제": "요청자", "검토자_정제": "검토자",
        "비고_text": "비고", "년월": "등록년월"
    })
 
    # 정렬 옵션
    sort_col = st.selectbox("정렬 기준", ["리드타임(내림)", "등록년월(최신)", "현재단계"], key="sort_master")
    if sort_col == "리드타임(내림)":
        df_display = df_display.sort_values("리드타임", ascending=False)
    elif sort_col == "등록년월(최신)":
        df_display = df_display.sort_values("등록년월", ascending=False)
    else:
        df_display = df_display.sort_values("현재단계")
 
    st.dataframe(df_display, use_container_width=True, hide_index=True, height=400)
 
    # ── 다운로드 ──────────────────────────────
    csv = df_display.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "📥 필터링 데이터 다운로드 (CSV)",
        data=csv,
        file_name=f"1P_Ops_Report_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )
 
    # 파일 새로고침
    st.sidebar.markdown("---")
    if st.sidebar.button("🔄 다른 파일 업로드"):
        del st.session_state["raw_bytes"]
        st.rerun()
 
 
if __name__ == "__main__":
    main()
