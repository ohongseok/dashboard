import io
import re
from typing import Optional, List, Dict

import gspread
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from google.oauth2.service_account import Credentials
from datetime import datetime

# ---------------------------
# 0. Page & Theme Configuration
# ---------------------------
st.set_page_config(
    page_title="KREAM Ops Intelligence Dashboard", 
    layout="wide", 
    initial_sidebar_state="expanded"
)

# 커스텀 CSS (대기업 대시보드 느낌의 깔끔한 스타일링)
st.markdown("""
    <style>
    [data-testid="stMetricValue"] { font-size: 28px; color: #007BFF; }
    .main { background-color: #F8F9FA; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------
# 1. Constants & Mappings
# ---------------------------
COLUMN_ALIASES = {
    "brand": ["브랜드(영문)", "브랜드"],
    "requester": ["요청자"],
    "reviewer": ["검토자"],
    "listed": ["리스트업 완료"],
    "request_done": ["검토 및 등록 요청 완료"],
    "purchase_requested": ["상품 구매 요청"],
    "purchase_done": ["상품 구매 완료"],
    "registration_request_date": ["등록 요청일"],
    "registration_done_flag": ["등록 완료 (앱 노출 시 체크)", "등록 완료"],
    "registration_done_date": ["등록 완료일"],
    "country_type": ["국내/해외"],
    "delay_reason": ["지연 사유"],
    "issue_note": ["브랜드별 검토사항"],
    "issue_conclusion": ["브랜드별 검토사항 결론"],
    "remark": ["비고"],
}

TRUE_VALUES = {"true", "1", "y", "yes", "완료", "o", "v", "✓", "check", "checked"}

# ---------------------------
# 2. Advanced Helper Functions
# ---------------------------
def normalize_text(value) -> str:
    if pd.isna(value): return ""
    return str(value).strip()

def split_people(raw: str) -> List[str]:
    text = normalize_text(raw)
    if not text: return []
    return [t.strip() for t in re.split(r"[,/|·\n]+", text) if t.strip()]

def person_group(token: str) -> str:
    t = re.sub(r"[\s\-\.\(\)]+", "", normalize_text(token))
    if not t: return "Unknown"
    if t.upper() == "3P" or re.fullmatch(r"[가-힣]+", t): return "Famous"
    return "KREAM"

def parse_bool(v) -> bool:
    if pd.isna(v): return False
    if isinstance(v, bool): return v
    s = str(v).strip().lower()
    return s in TRUE_VALUES

def parse_date(v):
    if pd.isna(v) or v == "": return pd.NaT
    try:
        # 23.02.20 형식 처리
        return pd.to_datetime(v, format="%y.%m.%d", errors="coerce")
    except:
        return pd.to_datetime(v, errors="coerce")

# ---------------------------
# 3. Data Processing Engine
# ---------------------------
@st.cache_data(ttl=600)
def load_and_preprocess(values: List[List[str]]):
    if not values or len(values) < 2: return pd.DataFrame(), {}

    # 원본 데이터의 2번째 줄(인덱스 1)이 헤더임
    header_row = 0
    for i, row in enumerate(values[:5]):
        if "브랜드" in str(row):
            header_row = i
            break
            
    df = pd.DataFrame(values[header_row+1:], columns=values[header_row])
    df.columns = [re.sub(r"\s+", " ", str(c)).strip() for c in df.columns]

    # 컬럼 매핑
    colmap = {}
    for key, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            for col in df.columns:
                if alias.lower() in col.lower():
                    colmap[key] = col
                    break
            if key in colmap: break

    # 데이터 타입 변환 및 정제
    df["등록 완료일_dt"] = df[colmap["registration_done_date"]].apply(parse_date)
    df["년도"] = df["등록 완료일_dt"].dt.year.astype("Int64")
    
    # [핵심] 홍석님 요청: 2023-2026 연도 제한
    df = df[(df["년도"] >= 2023) & (df["년도"] <= 2026)].copy()

    # 불리언 변환
    for k in ["listed", "request_done", "purchase_requested", "purchase_done", "registration_done_flag"]:
        if colmap.get(k):
            df[f"is_{k}"] = df[colmap[k]].apply(parse_bool)
        else:
            df[f"is_{k}"] = False

    # 인력 그룹화
    req_col = colmap["requester"]
    df["조직"] = df[req_col].apply(lambda x: person_group(split_people(x)[0] if split_people(x) else ""))
    df["대표요청자"] = df[req_col].apply(lambda x: split_people(x)[0] if split_people(x) else "미입력")
    
    # 리드타임 계산
    req_date_col = colmap["registration_request_date"]
    df["등록요청일_dt"] = df[req_date_col].apply(parse_date)
    df["리드타임"] = (df["등록 완료일_dt"] - df["등록요청일_dt"]).dt.days
    df["리드타임"] = df["리드타임"].apply(lambda x: x if 0 <= x <= 365 else np.nan)

    # 현재 단계 정의 (최종 도달 지점 기준)
    def get_stage(r):
        if r["is_registration_done_flag"]: return "5.등록 완료"
        if r["is_purchase_done"]: return "4.구매 완료"
        if r["is_purchase_requested"]: return "3.구매 요청"
        if r["is_request_done"]: return "2.검토/등록 요청"
        if r["is_listed"]: return "1.리스트업 완료"
        return "0.미진행"
    df["현재단계"] = df.apply(get_stage, axis=1)

    return df, colmap

# ---------------------------
# 4. Main Application
# ---------------------------
def main():
    st.title("🏆 KREAM Ops Intelligence Dashboard")
    st.markdown(f"**Data Range:** 2023 - 2026 | **Generated at:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # --- Sidebar Filters ---
    with st.sidebar:
        st.image("https://upload.wikimedia.org/wikipedia/commons/d/de/Google_Sheets_logo_%282014-2020%29.svg", width=50)
        st.header("Control Panel")
        
        source = st.radio("데이터 소스", ["Google Sheet", "Excel 업로드"])
        raw_values = None
        
        if source == "Google Sheet":
            sheet_name = st.text_input("구글 시트 이름", value="1P 상품등록 통합페이지")
            if st.button("데이터 동기화", type="primary"):
                try:
                    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
                    creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=scopes)
                    client = gspread.authorize(creds)
                    worksheet = client.open(sheet_name).worksheet("Summary")
                    raw_values = worksheet.get_all_values()
                    st.session_state["raw"] = raw_values
                except Exception as e: st.error(f"연결 실패: {e}")
        else:
            uploaded = st.file_uploader("XLSX 파일 업로드", type="xlsx")
            if uploaded:
                raw_values = pd.read_excel(uploaded, sheet_name=None)
                # 첫 번째 시트 사용
                sheet1 = list(raw_values.values())[0]
                raw_values = [sheet1.columns.tolist()] + sheet1.values.tolist()
                st.session_state["raw"] = raw_values

    if "raw" not in st.session_state:
        st.info("💡 사이드바에서 데이터를 먼저 불러와주세요.")
        return

    df_base, colmap = load_and_preprocess(st.session_state["raw"])
    
    if df_base.empty:
        st.warning("유효한 데이터가 없습니다 (2023-2026 범위 확인).")
        return

    # --- 전문가용 세부 필터 (사이드바 하단) ---
    with st.sidebar:
        st.markdown("---")
        st.subheader("Filters")
        f_org = st.multiselect("조직", options=df_base["조직"].unique(), default=df_base["조직"].unique())
        f_country = st.multiselect("국내/해외", options=df_base["국내해외구분"].unique(), default=df_base["국내해외구분"].unique())
        f_stage = st.multiselect("현재 단계", options=sorted(df_base["현재단계"].unique()), default=df_base["현재단계"].unique())
        f_year = st.multiselect("년도", options=sorted(df_base["년도"].dropna().unique().tolist()), default=sorted(df_base["년도"].dropna().unique().tolist()))
        
        keyword = st.text_input("브랜드/비고 검색")
        include_ex = st.checkbox("등록 완료일 없는 데이터 포함", value=True)

    # 필터링 적용
    df = df_base[
        (df_base["조직"].isin(f_org)) &
        (df_base["국내해외구분"].isin(f_country)) &
        (df_base["현재단계"].isin(f_stage)) &
        (df_base["년도"].isin(f_year))
    ].copy()
    
    if not include_ex: df = df[df["등록 완료일_dt"].notna()]
    if keyword:
        df = df[df[colmap["brand"]].astype(str).str.contains(keyword, case=False) | 
                df[colmap["remark"]].astype(str).str.contains(keyword, case=False)]

    # --- Main Dashboard Tabs ---
    tab1, tab2, tab3 = st.tabs(["📊 운영 요약 (Executive)", "👥 인력/성과 (Performance)", "📑 상세 데이터 (Raw)"])

    with tab1:
        # 1. 상단 KPI Metrics
        kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)
        total_brands = len(df)
        reg_done = df["is_registration_done_flag"].sum()
        reg_rate = safe_rate(reg_done, total_brands)
        avg_lt = df["리드타임"].mean()
        
        kpi1.metric("총 브랜드 수", f"{total_brands}건")
        kpi2.metric("등록 완료 수", f"{reg_done}건")
        kpi3.metric("등록 성공률", f"{reg_rate}%")
        kpi4.metric("평균 리드타임", f"{avg_lt:.1f}일" if not pd.isna(avg_lt) else "-")
        kpi5.metric("노출 전환율", f"{safe_rate(df['is_purchase_done'].sum(), total_brands)}%")

        st.markdown("---")
        
        # 2. 운영 차트 섹션
        c1, c2 = st.columns([6, 4])
        with c1:
            st.markdown("#### 📅 월간 등록 완료 추이")
            trend = df.dropna(subset=["년월"]).groupby("년월").size().reset_index(name="건수")
            fig_trend = px.line(trend, x="년월", y="건수", markers=True, template="plotly_white", color_discrete_sequence=['#007BFF'])
            st.plotly_chart(fig_trend, use_container_width=True)
            
        with c2:
            st.markdown("#### 🎯 공정별 퍼널 (Funnel)")
            funnel_data = {
                "단계": ["리스트업", "등록요청", "구매완료", "등록완료"],
                "건수": [df["is_listed"].sum(), df["is_request_done"].sum(), df["is_purchase_done"].sum(), df["is_registration_done_flag"].sum()]
            }
            fig_funnel = px.funnel(funnel_data, x='건수', y='단계', color_discrete_sequence=['#6C757D'])
            st.plotly_chart(fig_funnel, use_container_width=True)

        st.markdown("---")
        c3, c4 = st.columns(2)
        with c3:
            st.markdown("#### 🌏 국내 vs 해외 비중")
            fig_pie = px.pie(df, names="국내해외구분", hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
            st.plotly_chart(fig_pie, use_container_width=True)
        with c4:
            st.markdown("#### ⏱️ 리드타임 분포")
            fig_hist = px.histogram(df, x="리드타임", nbins=20, template="plotly_white", color_discrete_sequence=['#FFC107'])
            st.plotly_chart(fig_hist, use_container_width=True)

    with tab2:
        st.markdown("#### 🏆 인력 생산성 및 성과 지표")
        p1, p2 = st.columns(2)
        
        with p1:
            st.markdown("##### 요청자별 처리 건수 (Top 15)")
            req_rank = df.groupby(["대표요청자", "조직"]).size().reset_index(name="건수").sort_values("건수", ascending=False)
            fig_req = px.bar(req_rank.head(15), x="건수", y="대표요청자", color="조직", orientation='h', template="plotly_white")
            st.plotly_chart(fig_req, use_container_width=True)
            
        with p2:
            st.markdown("##### 검토자별 처리 건수")
            rev_col = colmap["reviewer"]
            rev_rank = df.groupby(rev_col).size().reset_index(name="건수").sort_values("건수", ascending=False)
            fig_rev = px.bar(rev_rank.head(15), x="건수", y=rev_col, template="plotly_white", color_discrete_sequence=['#28A745'])
            st.plotly_chart(fig_rev, use_container_width=True)

        st.markdown("---")
        st.markdown("##### 🧪 조직별 리드타임 및 효율 비교")
        org_stats = df.groupby("조직").agg(건수=("조직", "count"), 평균리드타임=("리드타임", "mean"), 등록완료=("is_registration_done_flag", "sum")).reset_index()
        org_stats["성공률"] = (org_stats["등록완료"] / org_stats["건수"] * 100).round(1)
        st.table(org_stats.style.background_gradient(subset=["성공률"], cmap="Blues"))

    with tab3:
        st.markdown("#### 📑 필터링된 데이터 상세 내역")
        # 보기 편하게 컬럼 순서 조정
        cols_to_show = [colmap["brand"], "대표요청자", "조직", "현재단계", "등록 완료일_dt", "리드타임", "국내해외구분", colmap["remark"]]
        st.dataframe(df[cols_to_show].sort_values("등록 완료일_dt", ascending=False), use_container_width=True, hide_index=True)
        
        # 엑셀 다운로드 기능
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 현재 필터 결과 엑셀(CSV) 다운로드",
            data=csv,
            file_name=f"KREAM_Ops_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv",
        )

if __name__ == "__main__":
    main()
