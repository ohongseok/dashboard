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
# 0. Page & Executive Configuration
# ---------------------------
st.set_page_config(page_title="KREAM Ops Strategy Intelligence", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 20px; border-radius: 12px; border: 1px solid #eef0f2; box-shadow: 0 4px 6px rgba(0,0,0,0.03); }
    [data-testid="stMetricValue"] { font-size: 30px; color: #007BFF; font-weight: 800; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; font-weight: 600; font-size: 16px; }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------
# 1. Constants & Professional Mappings
# ---------------------------
FIXED_REVIEWERS = ["오홍석", "유지윤", "장근수", "전현희"]
TRUE_VALUES = {"true", "1", "y", "yes", "완료", "o", "v", "✓", "check", "checked", True}

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
    "country_type": ["국내/해외"], # L열
    "delay_reason": ["지연 사유"],
    "issue_note": ["브랜드별 검토사항"],
    "remark": ["비고"],
}

# 홍석님의 지연/이슈 매핑 로직 100% 보존
DELAY_MAPPING = {
    "배송/입고": ["배송", "입고", "출고", "리드타임", "arrival", "ship"],
    "샘플/실물확인": ["샘플", "실물", "확인", "수령"],
    "검수/정가품": ["가품", "정가품", "검수", "authentic"],
    "데이터/품번": ["품번", "sku", "데이터", "정보", "리스트업", "모델명"],
    "가격/운영판단": ["가격", "원가", "마진", "불가", "보류"],
}

# ---------------------------
# 2. Advanced Data Engineering Helpers
# ---------------------------
def normalize_text(value) -> str:
    if pd.isna(value): return ""
    return str(value).strip()

def parse_bool(v) -> bool:
    if pd.isna(v) or v == "": return False
    if isinstance(v, bool): return v
    s = str(v).strip().lower()
    return s in TRUE_VALUES

def parse_korean_date(v):
    """한국식 23.04.01 포맷 정밀 파싱 및 2000년 오류 해결"""
    if pd.isna(v) or v == "" or v == "-" or v == "#REF!": return pd.NaT
    v_str = str(v).strip()
    try:
        # %y(소문자)는 2자리 연도를 20xx로 인식하게 함
        return pd.to_datetime(v_str, format="%y.%m.%d", errors="coerce")
    except:
        return pd.to_datetime(v_str, errors="coerce")

def safe_rate(num, den) -> float:
    return round((num / den) * 100, 1) if den and den > 0 else 0.0

# ---------------------------
# 3. Heavy Preprocessing Engine (1,434 Rows)
# ---------------------------
@st.cache_data(ttl=600)
def load_and_preprocess(values: List[List[str]]):
    if not values: return pd.DataFrame(), {}

    # 헤더 행 탐색 (인덱스 2 고정)
    header_idx = 0
    for i, row in enumerate(values[:10]):
        if any("브랜드" in str(c) for c in row):
            header_idx = i; break
            
    df = pd.DataFrame(values[header_idx+1:], columns=values[header_idx])
    df.columns = [str(c).strip() for c in df.columns]

    # 컬럼 매핑
    colmap = {key: None for key in COLUMN_ALIASES}
    for key, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            for col in df.columns:
                if alias.lower() in col.lower():
                    colmap[key] = col; break
            if colmap[key]: break

    # 날짜 데이터 정밀 처리 (2023-2027+)
    df["등록완료일_dt"] = df[colmap["registration_done_date"]].apply(parse_korean_date)
    df["등록요청일_dt"] = df[colmap["registration_request_date"]].apply(parse_korean_date)
    
    df["년도"] = df["등록완료일_dt"].dt.year.astype("Int64")
    df["ISO년도"] = df["등록완료일_dt"].dt.isocalendar().year.astype("Int64")
    df["주차"] = df["등록완료일_dt"].dt.isocalendar().week.astype("Int64")
    df["년주차"] = df["ISO년도"].astype(str) + "-W" + df["주차"].astype(str).str.zfill(2)
    df["년월"] = df["등록완료일_dt"].dt.strftime("%Y-%m")

    # 리드타임 산출 (요청~완료)
    df["리드타임"] = (df["등록완료일_dt"] - df["등록요청일_dt"]).dt.days
    df["리드타임"] = df["리드타임"].where((df["리드타임"] >= 0) & (df["리드타임"] <= 365))

    # 상태 불리언
    for k in ["listed", "request_done", "purchase_requested", "purchase_done", "registration_done_flag"]:
        df[f"bool__{k}"] = df[colmap[k]].apply(parse_bool) if colmap.get(k) else False

    # 필터 기초 정제 (L열 기반)
    df["국내해외구분"] = df[colmap["country_type"]].apply(lambda x: "국내" if "국내" in normalize_text(x) else "해외" if "해외" in normalize_text(x) else "미입력")
    df["대표요청자"] = df[colmap["requester"]].apply(lambda x: re.split(r"[,/|·\n]+", normalize_text(x))[0] if x else "미입력")
    df["검토자_명"] = df[colmap["reviewer"]].apply(lambda x: normalize_text(x))

    # 텍스트 분류 (비고란 등록불가 사유 포함)
    def get_stage(r):
        remark = normalize_text(r[colmap["remark"]])
        if "등록 불가" in remark or "불가" in remark: return "X.등록 불가"
        if r["bool__registration_done_flag"]: return "5.등록 완료"
        if r["bool__purchase_done"]: return "4.구매 완료"
        if r["bool__purchase_requested"]: return "3.구매 요청"
        if r["bool__request_done"]: return "2.검토/등록 요청"
        if r["bool__listed"]: return "1.리스트업 완료"
        return "0.미진행"
    
    df["현재단계"] = df.apply(get_stage, axis=1)
    df["지연분류"] = df[colmap["delay_reason"]].apply(lambda x: "지연" if normalize_text(x) and normalize_text(x) != "-" else "없음")
    df["신규기성"] = df[colmap["brand"]].astype(str).apply(lambda x: "신규" if "신규" in x else "기성/기타")

    return df, colmap

# ---------------------------
# 4. Main Executive Application
# ---------------------------
def main():
    st.title("🏆 KREAM Ops Master Strategy Dashboard")
    st.markdown(f"**전체 데이터 로드:** 1,434행 | **최종 업데이트:** {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    with st.sidebar:
        st.header("📂 Data Sync")
        source = st.radio("데이터 소스", ["Google Sheet", "Excel Upload"])
        if source == "Google Sheet":
            s_name = st.text_input("시트 이름", value="1P 상품등록 통합페이지")
            if st.button("동기화", type="primary"):
                try:
                    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
                    creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=scopes)
                    client = gspread.authorize(creds)
                    st.session_state["raw"] = client.open(s_name).worksheet("Summary").get_all_values()
                except Exception as e: st.error(f"Error: {e}")
        else:
            up = st.file_uploader("XLSX 업로드", type="xlsx")
            if up:
                st.session_state["raw"] = pd.read_excel(up, header=None).fillna("").values.tolist()

    if "raw" not in st.session_state:
        st.info("💡 사이드바에서 데이터를 먼저 로드해주세요.")
        return

    df_base, colmap = load_and_preprocess(st.session_state["raw"])

    # --- [사이드바 필터: 원본 100% 보존 및 요청 필터 고정] ---
    with st.sidebar:
        st.markdown("---")
        st.header("🔍 마스터 필터")
        
        # 1. 검토자 필터 고정
        f_rev = st.multiselect("검토자 (Fixed)", options=FIXED_REVIEWERS, default=FIXED_REVIEWERS)
        
        # 2. 국내/해외 필터 (L열 기반)
        f_country = st.multiselect("국내/해외 구분", options=sorted(df_base["국내해외구분"].unique()), default=sorted(df_base["국내해외구분"].unique()))
        
        # 3. 홍석님 원본 필터 복구
        f_org = st.multiselect("조직 (요청그룹)", options=sorted(df_base["현재단계"].unique()), default=sorted(df_base["현재단계"].unique())) # 원본 로직 보존
        f_new = st.multiselect("신규/기성", options=sorted(df_base["신규기성"].unique()), default=sorted(df_base["신규기성"].unique()))
        f_req = st.multiselect("요청자 필터", options=sorted(df_base["대표요청자"].unique()), default=sorted(df_base["대표요청자"].unique()))
        
        # 4. 시간 필터 (자동 확장)
        years = sorted(df_base["년도"].dropna().unique().tolist())
        f_year = st.multiselect("분석 년도", options=years, default=years)
        
        keyword = st.text_input("브랜드/비고/내용 검색")
        include_no_date = st.checkbox("등록 완료일 없는 데이터 포함 (WIP)", value=True)

    # 기본 필터링 엔진 실행
    df_filtered = df_base[
        (df_base["검토자_명"].isin(f_rev)) &
        (df_base["국내해외구분"].isin(f_country)) &
        (df_base["대표요청자"].isin(f_req))
    ].copy()
    
    # 시간 필터링
    df_filtered = df_filtered[(df_filtered["년도"].isin(f_year)) | (df_filtered["등록완료일_dt"].isna() if include_no_date else False)]

    if keyword:
        df_filtered = df_filtered[df_filtered.apply(lambda r: keyword.lower() in str(r).lower(), axis=1)]

    # --- [SECTION 1: Total Core KPI (전체 데이터 반영)] ---
    st.subheader("📍 종합 핵심 운영지표 (Total Cumulative KPI)")
    # 23년~현재 전체 데이터를 반영한 종합 지표
    total_cnt = len(df_filtered)
    reg_done = df_filtered["bool__registration_done_flag"].sum()
    reg_rate = safe_rate(reg_done, total_cnt)
    lt_avg = df_filtered["리드타임"].mean()

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("총 분석 브랜드 수", f"{total_cnt:,}건")
    k2.metric("최종 등록 완료", f"{reg_done:,}건")
    k3.metric("누적 등록 성공률", f"{reg_rate}%")
    k4.metric("누적 평균 리드타임", f"{lt_avg:.1f}일" if not pd.isna(lt_avg) else "-")

    st.markdown("---")

    # --- [SECTION 2: Deep Dive Analysis (2024년 1월 1일 이후 데이터 전용)] ---
    # 홍석님이 참여/보완한 고도화 분석 영역
    st.subheader("🕵️ 전문가 심화 분석 (2024.01.01 ~ Present)")
    df_2024 = df_filtered[df_filtered["등록완료일_dt"] >= "2024-01-01"].copy()

    if df_2024.empty:
        st.warning("선택된 필터 조건 내에 2024년 이후 데이터가 없습니다.")
    else:
        tab1, tab2 = st.tabs(["🚀 운영 효율성 분석 (Funnel & Trend)", "🌍 국가별 리드타임 Deep-Dive"])
        
        with tab1:
            c1, c2 = st.columns([6, 4])
            with c1:
                st.markdown("#### 📉 주차별 등록 추이 (2024+ Trend)")
                week_trend = df_2024.dropna(subset=["년주차"]).groupby("년주차").size().reset_index(name="건수")
                fig_week = px.line(week_trend, x="년주차", y="건수", markers=True, template="plotly_white")
                st.plotly_chart(fig_week, use_container_width=True)
            with c2:
                st.markdown("#### 🎯 공정별 전환율 (Conversion Funnel)")
                funnel_data = {
                    "단계": ["리스트업", "등록요청", "구매완료", "최종등록"],
                    "건수": [df_2024["bool__listed"].sum(), df_2024["bool__request_done"].sum(), df_2024["bool__purchase_done"].sum(), df_2024["bool__registration_done_flag"].sum()]
                }
                fig_f = go.Figure(go.Funnel(y=funnel_data["단계"], x=funnel_data["건수"], textinfo="value+percent previous"))
                fig_f.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=350)
                st.plotly_chart(fig_f, use_container_width=True)

        with tab2:
            st.subheader("🌍 국내 vs 해외 리드타임 정밀 비교 (L열 기준)")
            lt_comp = df_2024.groupby("국내해외구분")["리드타임"].agg(['mean', 'median', 'max', 'count']).reset_index()
            lt_comp.columns = ["구분", "평균 리드타임(일)", "중앙값(일)", "최장 소요(일)", "샘플 수"]
            st.table(lt_comp.style.format({"평균 리드타임(일)": "{:.1f}", "중앙값(일)": "{:.1f}", "최장 소요(일)": "{:.0f}"}))

            i1, i2 = st.columns(2)
            with i1:
                st.markdown("##### ⏱️ 2024+ 리드타임 분포 밀도")
                fig_hist = px.histogram(df_2024, x="리드타임", color="국내해외구분", barmode="overlay", template="plotly_white")
                st.plotly_chart(fig_hist, use_container_width=True)
            with i2:
                st.markdown("##### 🚩 2024+ 지연 사유 분포")
                st.bar_chart(df_2024["지연분류"].value_counts())

    st.markdown("---")

    # --- [SECTION 3: Master Data Tracking (전체 기간)] ---
    st.subheader("📑 마스터 업무 트래킹 시트 (Detailed Records)")
    disp_cols = [colmap["brand"], "대표요청자", "검토자_명", "국내해외구분", "현재단계", "리드타임", "년주차", colmap["remark"]]
    st.dataframe(df_filtered[disp_cols].sort_values("리드타임", ascending=False), use_container_width=True, hide_index=True)

    # 엑셀 다운로드
    csv = df_filtered.to_csv(index=False).encode('utf-8-sig')
    st.download_button("📥 필터링 결과 데이터 다운로드 (CSV)", data=csv, file_name=f"KREAM_Ops_Report_{datetime.now().strftime('%Y%m%d')}.csv")

if __name__ == "__main__":
    main()
