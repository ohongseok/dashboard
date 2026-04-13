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
# 0. Page Config & Professional Styling
# ---------------------------
st.set_page_config(page_title="KREAM Ops Pro-Dashboard", layout="wide")

st.markdown("""
    <style>
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    [data-testid="stMetricValue"] { color: #1E1E1E; font-size: 24px; }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------
# 1. Constants & Mappings (원본 100% 복구)
# ---------------------------
HEADER_KEYWORDS = ["요청자", "검토자", "브랜드", "등록 완료일", "국내/해외"]
TRUE_VALUES = {"true", "1", "y", "yes", "완료", "o", "v", "✓", "check", "checked"}
FALSE_VALUES = {"false", "0", "n", "no", "미완료", "x", "-", ""}

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
    "registration_week": ["등록 주차"],
    "country_type": ["국내/해외"],
    "delay_reason": ["지연 사유"],
    "issue_note": ["브랜드별 검토사항"],
    "issue_conclusion": ["브랜드별 검토사항 결론"],
    "remark": ["비고"],
}

# 홍석님이 직접 정의한 매핑 로직 보존
DELAY_MAPPING = {
    "배송/입고": ["배송", "입고", "출고", "리드타임", "arrival", "ship"],
    "샘플/실물확인": ["샘플", "실물", "확인", "수령"],
    "검수/정가품": ["가품", "정가품", "검수", "authentic"],
    "데이터/품번": ["품번", "sku", "데이터", "정보", "리스트업", "모델명"],
    "담당자/커뮤니케이션": ["담당", "회신", "커뮤니케이션", "응답", "전달"],
    "가격/운영판단": ["가격", "원가", "마진", "불가", "보류"],
    "기기 이슈": ["이슈", "지연"],
}

ISSUE_MAPPING = {
    "사이즈/스펙": ["사이즈", "핏", "치수", "스펙"],
    "배송/납기": ["배송", "납기", "입고", "출고"],
    "정가품/검수": ["가품", "정가품", "검수"],
    "가격/마진": ["가격", "마진", "원가"],
    "상품데이터": ["품번", "sku", "이미지", "정보", "상세", "리스트업"],
    "운영협의": ["협의", "논의", "확인", "전달", "요청"],
}

# ---------------------------
# 2. Core Helper Functions
# ---------------------------
def normalize_text(value) -> str:
    if pd.isna(value): return ""
    return str(value).strip()

def normalize_colname(value) -> str:
    return re.sub(r"\s+", " ", normalize_text(value))

def split_people(raw: str) -> List[str]:
    text = normalize_text(raw)
    if not text: return []
    return [t.strip() for t in re.split(r"[,/|·\n]+", text) if t.strip()]

def person_group(token: str) -> str:
    t = re.sub(r"[\s\-\.\(\)]+", "", normalize_text(token))
    if not t: return "Famous"
    if t.upper() == "3P" or re.fullmatch(r"[가-힣]+", t): return "Famous"
    return "KREAM"

def requester_group(raw: str) -> str:
    tokens = split_people(raw)
    if not tokens: return "Famous"
    groups = {person_group(t) for t in tokens}
    if groups == {"KREAM"}: return "KREAM"
    if groups == {"Famous"}: return "Famous"
    return "Mixed"

def parse_bool(v) -> bool:
    if pd.isna(v) or v == "": return False
    if isinstance(v, bool): return v
    s = str(v).strip().lower()
    return s in TRUE_VALUES

def parse_date(v):
    if pd.isna(v) or v == "": return pd.NaT
    v_str = str(v).strip()
    try:
        return pd.to_datetime(v_str, format="%y.%m.%d", errors="coerce")
    except:
        return pd.to_datetime(v_str, errors="coerce")

def category_from_text(text: str, mapping: Dict[str, List[str]], default: str = "기타") -> str:
    t = normalize_text(text).lower()
    if not t or t == "-": return "없음"
    for category, keywords in mapping.items():
        if any(k in t for k in keywords): return category
    return default

def safe_rate(num, den) -> float:
    return round((num / den) * 100, 1) if den else 0.0

# ---------------------------
# 3. Data Processing Engine
# ---------------------------
@st.cache_data(ttl=600)
def load_and_preprocess(values: List[List[str]]):
    if not values: return pd.DataFrame(), {}

    # 헤더 행 자동 탐색 (브랜드(영문) 컬럼이 있는 행)
    header_idx = 0
    for i, row in enumerate(values[:10]):
        if any("브랜드" in str(cell) for cell in row):
            header_idx = i
            break
            
    df = pd.DataFrame(values[header_idx+1:], columns=values[header_idx])
    df.columns = [str(c).strip() for c in df.columns]

    # 컬럼 매핑
    colmap = {}
    for key, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            for col in df.columns:
                if alias.lower() in col.lower():
                    colmap[key] = col
                    break
            if key in colmap: break

    # 데이터 타입 변환 및 가공
    df["등록 완료일_dt"] = df[colmap["registration_done_date"]].apply(parse_date)
    df["년도"] = df["등록 완료일_dt"].dt.year.astype("Int64")
    df["월"] = df["등록 완료일_dt"].dt.month.astype("Int64")
    df["ISO년도"] = df["등록 완료일_dt"].dt.isocalendar().year.astype("Int64")
    df["주차"] = df["등록 완료일_dt"].dt.isocalendar().week.astype("Int64")
    df["년월"] = df["등록 완료일_dt"].dt.strftime("%Y-%m")
    df["년주차"] = df["ISO년도"].astype(str) + "-W" + df["주차"].astype(str).str.zfill(2)

    # 불리언 변환 (원본 로직 반영)
    for k in ["listed", "request_done", "purchase_requested", "purchase_done", "registration_done_flag"]:
        col = colmap.get(k)
        df[f"bool__{k}"] = df[col].apply(parse_bool) if col else False

    # 인력 데이터
    req_col = colmap.get("requester")
    df["요청그룹"] = df[req_col].apply(requester_group) if req_col else "Famous"
    df["대표요청자"] = df[req_col].apply(lambda x: split_people(x)[0] if split_people(x) else "미입력") if req_col else "미입력"
    df["국내해외구분"] = df[colmap.get("country_type")].apply(lambda x: "국내" if "국내" in normalize_text(x) else "해외" if "해외" in normalize_text(x) else "미입력") if colmap.get("country_type") else "미입력"

    # 리드타임
    reg_req_col = colmap.get("registration_request_date")
    df["등록요청일_dt"] = df[reg_req_col].apply(parse_date) if reg_req_col else pd.NaT
    df["등록소요일"] = (df["등록 완료일_dt"] - df["등록요청일_dt"]).dt.days
    df["등록소요일"] = df["등록소요일"].apply(lambda x: x if 0 <= x <= 365 else np.nan)

    # 현재 단계 레이블
    def get_stage(r):
        if r["bool__registration_done_flag"]: return "노출 확인 완료"
        if r["bool__purchase_done"]: return "구매 완료"
        if r["bool__purchase_requested"]: return "구매 요청"
        if r["bool__request_done"]: return "검토/등록 요청 완료"
        if r["bool__listed"]: return "리스트업 완료"
        return "미진행"
    df["현재단계"] = df.apply(get_stage, axis=1)

    # 텍스트 기반 분류 (원본 로직 100% 복구)
    text_cols = [colmap.get(c) for c in ["delay_reason", "issue_note", "issue_conclusion", "remark"] if colmap.get(c)]
    combined_text = df[text_cols].astype(str).agg(' '.join, axis=1)
    df["지연분류"] = combined_text.apply(lambda x: category_from_text(x, DELAY_MAPPING))
    df["이슈분류"] = combined_text.apply(lambda x: category_from_text(x, ISSUE_MAPPING))
    df["신규기성"] = combined_text.apply(lambda x: "신규" if any(k in x.lower() for k in ["신생", "신규", "발굴"]) else "기성/기타")
    
    df["등록제외"] = df.apply(lambda r: pd.isna(r["등록 완료일_dt"]), axis=1)

    return df, colmap

# ---------------------------
# 4. Main UI (원본 필터 100% 복구)
# ---------------------------
def main():
    st.title("🏆 KREAM Ops Advanced Intelligence")

    with st.sidebar:
        st.header("⚙️ Data Connection")
        source = st.radio("데이터 소스", ["Google Sheet", "Excel Upload"])
        
        if source == "Google Sheet":
            s_name = st.text_input("시트 이름", value="1P 상품등록 통합페이지")
            if st.button("동기화", type="primary"):
                try:
                    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
                    creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=scopes)
                    client = gspread.authorize(creds)
                    raw_values = client.open(s_name).worksheet("Summary").get_all_values()
                    st.session_state["raw"] = raw_values
                except Exception as e: st.error(f"연결 에러: {e}")
        else:
            up = st.file_uploader("XLSX 파일 업로드", type="xlsx")
            if up:
                df_excel = pd.read_excel(up, header=None)
                st.session_state["raw"] = [df_excel.columns.tolist()] + df_excel.values.tolist()

    if "raw" not in st.session_state:
        st.info("💡 사이드바에서 데이터를 먼저 불러와주세요.")
        return

    df_base, colmap = load_and_preprocess(st.session_state["raw"])

    # --- 사이드바 필터 (원본 `dash.py` 구성 100% 복구) ---
    with st.sidebar:
        st.markdown("---")
        st.header("📊 Filter Settings")
        
        f_org = st.multiselect("조직 (요청그룹)", options=sorted(df_base["요청그룹"].unique()), default=sorted(df_base["요청그룹"].unique()))
        f_country = st.multiselect("국내/해외", options=sorted(df_base["국내해외구분"].unique()), default=sorted(df_base["국내해외구분"].unique()))
        f_stage = st.multiselect("현재 단계", options=sorted(df_base["현재단계"].unique()), default=sorted(df_base["현재단계"].unique()))
        f_issue = st.multiselect("이슈 분류", options=sorted(df_base["이슈분류"].unique()), default=sorted(df_base["이슈분류"].unique()))
        f_delay = st.multiselect("지연 분류", options=sorted(df_base["지연분류"].unique()), default=sorted(df_base["지연분류"].unique()))
        f_new = st.multiselect("신규/기성", options=sorted(df_base["신규기성"].unique()), default=sorted(df_base["신규기성"].unique()))
        
        req_options = sorted(df_base["대표요청자"].unique())
        f_req = st.multiselect("요청자", options=req_options, default=req_options)
        
        # 년도/월 필터 (2023-2026 범위 필터링)
        years = sorted([y for y in df_base["년도"].dropna().unique() if 2023 <= y <= 2026])
        f_year = st.multiselect("년도", options=years, default=years)
        
        keyword = st.text_input("브랜드/비고/검토사항 검색")
        include_ex = st.checkbox("등록 완료일 없는 데이터 포함 (미진행 건)", value=True)

    # 필터링 엔진 실행
    df = df_base[
        (df_base["요청그룹"].isin(f_org)) &
        (df_base["국내해외구분"].isin(f_country)) &
        (df_base["현재단계"].isin(f_stage)) &
        (df_base["이슈분류"].isin(f_issue)) &
        (df_base["지연분류"].isin(f_delay)) &
        (df_base["신규기성"].isin(f_new)) &
        (df_base["대표요청자"].isin(f_req))
    ].copy()
    
    # 시간 필터: 선택된 년도이거나, 날짜가 아예 없는(진행중인) 행 포함 여부
    year_mask = df["년도"].isin(f_year)
    if include_ex: year_mask = year_mask | df["등록 완료일_dt"].isna()
    df = df[year_mask]

    if keyword:
        df = df[df.apply(lambda r: keyword.lower() in str(r).lower(), axis=1)]

    # --- KPI Dashboard (이미지 지표와 일치화) ---
    total = len(df)
    reg_done = df["bool__request_done"].sum() # '검토 및 등록 요청 완료' 기준
    exposure_done = df["bool__registration_done_flag"].sum() # '앱 노출 시 체크' 기준

    st.subheader("🚀 핵심 성과 지표 (KPI Metrics)")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("총 브랜드 수", f"{total:,}건")
    k2.metric("등록 요청 완료", f"{reg_done:,}건")
    k3.metric("노출 확인 완료", f"{exposure_done:,}건")
    k4.metric("등록 성공률", f"{safe_rate(reg_done, total)}%")
    k5.metric("노출 전환율", f"{safe_rate(exposure_done, total)}%")

    st.markdown("---")

    # --- Visualization Section (전문가급 차트) ---
    tab1, tab2 = st.tabs(["📊 운영 현황 분석", "👥 인력/이슈 분석"])
    
    with tab1:
        c1, c2 = st.columns([6, 4])
        with c1:
            st.markdown("#### 📅 월간 등록 추이")
            trend = df.dropna(subset=["년월"]).groupby("년월").size().reset_index(name="건수")
            fig = px.line(trend, x="년월", y="건수", markers=True, template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            st.markdown("#### 🎯 공정별 퍼널 (Funnel)")
            funnel_data = {
                "단계": ["리스트업", "등록요청", "구매완료", "노출확인"],
                "건수": [df["bool__listed"].sum(), df["bool__request_done"].sum(), df["bool__purchase_done"].sum(), df["bool__registration_done_flag"].sum()]
            }
            fig_f = px.funnel(funnel_data, x="건수", y="단계")
            st.plotly_chart(fig_f, use_container_width=True)

    with tab2:
        st.markdown("#### 🚩 이슈 및 조직별 분포")
        i1, i2 = st.columns(2)
        with i1:
            st.bar_chart(df["현재단계"].value_counts())
        with i2:
            st.bar_chart(df["지연분류"].value_counts())

    st.markdown("---")
    st.subheader("🔍 상세 데이터 리스트")
    cols = [colmap.get("brand"), "대표요청자", "요청그룹", "현재단계", "등록소요일", "국내해외구분", colmap.get("remark")]
    st.dataframe(df[cols].sort_values("등록소요일", ascending=False), use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
