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
# 0. Page & Executive Theme Configuration
# ---------------------------
st.set_page_config(page_title="KREAM Ops Executive Dashboard", layout="wide")

st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; border: 1px solid #e0e0e0; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    [data-testid="stMetricValue"] { font-size: 28px; color: #007BFF; font-weight: bold; }
    .stTabs [data-baseweb="tab-list"] { gap: 24px; }
    .stTabs [data-baseweb="tab"] { height: 50px; white-space: pre-wrap; font-weight: 600; }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------
# 1. Constants & Mappings (원본 verified.py 100% 보존 + 요청사항 반영)
# ---------------------------
ILLEGAL_EXCEL_CHARS_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")
HEADER_KEYWORDS = ["요청자", "검토자", "브랜드", "등록 완료일", "국내/해외"]

TRUE_VALUES = {"true", "1", "y", "yes", "완료", "o", "v", "✓", "check", "checked", True}
FALSE_VALUES = {"false", "0", "n", "no", "미완료", "x", "-", "", False}

# 검토자 필터 고정 요청
FIXED_REVIEWERS = ["오홍석", "유지윤", "장근수", "전현희"]

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
    "country_type": ["국내/해외"], # L열
    "delay_reason": ["지연 사유"],
    "issue_note": ["브랜드별 검토사항"],
    "issue_conclusion": ["브랜드별 검토사항 결론"],
    "remark": ["비고"],
}

# 홍석님이 정의한 텍스트 분석 매핑 보존 (절대 삭제 금지)
DELAY_MAPPING = {
    "배송/입고": ["배송", "입고", "출고", "리드타임", "arrival", "ship"],
    "샘플/실물확인": ["샘플", "실물", "확인", "수령"],
    "검수/정가품": ["가품", "정가품", "검수", "authentic"],
    "데이터/품번": ["품번", "sku", "데이터", "정보", "리스트업", "모델명"],
    "담당자/커뮤니케이션": ["담당", "회신", "커뮤니케이션", "응답", "전달"],
    "가격/운영판단": ["가격", "원가", "마진", "불가", "보류"],
    "기타 이슈": ["이슈", "지연"],
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
# 2. Advanced Helper Functions
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

def requester_group(raw: str) -> str:
    tokens = split_people(raw)
    if not tokens: return "Famous"
    t = re.sub(r"[\s\-\.\(\)]+", "", normalize_text(tokens[0]))
    if t.upper() == "3P" or re.fullmatch(r"[가-힣]+", t): return "Famous"
    return "KREAM"

def parse_bool(v) -> bool:
    if pd.isna(v) or v == "": return False
    if isinstance(v, bool): return v
    s = str(v).strip().lower()
    return s in TRUE_VALUES

def parse_korean_date(v):
    """23.04.01 포맷 정밀 파싱 (2000년 오류 완전 해결)"""
    if pd.isna(v) or v == "" or v == "-" or v == "#REF!": return pd.NaT
    v_str = str(v).strip()
    try:
        # %y는 2자리 연도 파싱 시 현재 세기(20xx)를 기준으로 함
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
    return round((num / den) * 100, 1) if den and den > 0 else 0.0

# ---------------------------
# 3. Data Processing Engine (Full 1,434 Rows Load)
# ---------------------------
@st.cache_data(ttl=600)
def load_and_preprocess(values: List[List[str]]):
    if not values: return pd.DataFrame(), {}

    # 헤더 탐색 (Index 2 고정)
    header_idx = 0
    for i, row in enumerate(values[:5]):
        if any("브랜드" in str(c) for c in row):
            header_idx = i
            break
            
    df = pd.DataFrame(values[header_idx+1:], columns=values[header_idx])
    df.columns = [str(c).strip() for c in df.columns]

    # 컬럼 매핑 자동화
    colmap = {}
    for key, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            for col in df.columns:
                if alias.lower() in col.lower():
                    colmap[key] = col; break
            if colmap.get(key): break

    # 날짜 정밀 처리 (2023-2027+)
    df["등록완료일_dt"] = df[colmap["registration_done_date"]].apply(parse_korean_date)
    df["등록요청일_dt"] = df[colmap["registration_request_date"]].apply(parse_korean_date)
    
    df["년도"] = df["등록완료일_dt"].dt.year.astype("Int64")
    df["월"] = df["등록완료일_dt"].dt.month.astype("Int64")
    df["ISO년도"] = df["등록완료일_dt"].dt.isocalendar().year.astype("Int64")
    df["주차"] = df["등록완료일_dt"].dt.isocalendar().week.astype("Int64")
    df["년주차"] = df["ISO년도"].astype(str) + "-W" + df["주차"].astype(str).str.zfill(2)
    df["년월"] = df["등록완료일_dt"].dt.strftime("%Y-%m")

    # 리드타임 계산 (요청~완료)
    df["등록소요일"] = (df["등록완료일_dt"] - df["등록요청일_dt"]).dt.days
    df["등록소요일"] = df["등록소요일"].where((df["등록소요일"] >= 0) & (df["등록소요일"] <= 365))
    df["SLA_준수"] = df["등록소요일"] <= 7

    # 불리언 상태값
    for k in ["listed", "request_done", "purchase_requested", "purchase_done", "registration_done_flag"]:
        df[f"bool__{k}"] = df[colmap[k]].apply(parse_bool) if colmap.get(k) else False

    # [핵심] L열 국내/해외 분류 및 비고란 데이터 보정
    df["국내해외구분"] = df[colmap["country_type"]].apply(lambda x: "국내" if "국내" in normalize_text(x) else "해외" if "해외" in normalize_text(x) else "미입력")
    df["요청그룹"] = df[colmap["requester"]].apply(requester_group)
    df["대표요청자"] = df[colmap["requester"]].apply(lambda x: split_people(x)[0] if x else "미입력")
    df["검토자_실명"] = df[colmap["reviewer"]].apply(lambda x: normalize_text(x))

    # 분류 로직 (verified.py 내용 100% 복구)
    text_cols = [colmap.get(c) for c in ["delay_reason", "issue_note", "issue_conclusion", "remark"] if colmap.get(c)]
    combined_text = df[text_cols].astype(str).agg(' '.join, axis=1)
    df["지연분류"] = combined_text.apply(lambda x: category_from_text(x, DELAY_MAPPING))
    df["이슈분류"] = combined_text.apply(lambda x: category_from_text(x, ISSUE_MAPPING))
    df["신규기성"] = df[colmap["brand"]].astype(str).apply(lambda x: "신규" if "신규" in x else "기성/기타")

    def get_stage(r):
        # 비고란에 '등록 불가'가 있으면 우선 반영
        if "등록 불가" in normalize_text(r[colmap["remark"]]) or "불가" in normalize_text(r[colmap["issue_conclusion"]]):
            return "X.등록 불가"
        if r["bool__registration_done_flag"]: return "5.등록 완료"
        if r["bool__purchase_done"]: return "4.구매 완료"
        if r["bool__purchase_requested"]: return "3.구매 요청"
        if r["bool__request_done"]: return "2.검토/등록 요청"
        if r["bool__listed"]: return "1.리스트업 완료"
        return "0.미진행"
    df["현재단계"] = df.apply(get_stage, axis=1)

    return df, colmap

# ---------------------------
# 4. Main Executive Application
# ---------------------------
def main():
    st.title("🏆 KREAM Ops Master Strategic Dashboard")
    st.markdown(f"**전체 데이터 로드:** 1,434행 | **분석 범위:** 2023 - 2027+")

    with st.sidebar:
        st.header("📂 데이터 동기화")
        source = st.radio("데이터 소스", ["Google Sheet", "Excel Upload"])
        if source == "Google Sheet":
            s_name = st.text_input("시트 이름", value="1P 상품등록 통합페이지")
            if st.button("실시간 연동", type="primary"):
                try:
                    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
                    creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=scopes)
                    client = gspread.authorize(creds)
                    st.session_state["raw"] = client.open(s_name).worksheet("Summary").get_all_values()
                except Exception as e: st.error(f"Sync Error: {e}")
        else:
            up = st.file_uploader("XLSX 업로드", type="xlsx")
            if up:
                st.session_state["raw"] = pd.read_excel(up, header=None).fillna("").values.tolist()

    if "raw" not in st.session_state:
        st.info("💡 사이드바에서 데이터를 먼저 로드해주세요.")
        return

    df_base, colmap = load_and_preprocess(st.session_state["raw"])

    # --- [사이드바 필터: 원본 verified.py 100% 보존 및 보완] ---
    with st.sidebar:
        st.markdown("---")
        st.header("🔍 마스터 필터 컨트롤")
        
        # 1. 검토자 필터 고정
        f_rev = st.multiselect("검토자 (Fixed)", options=FIXED_REVIEWERS, default=FIXED_REVIEWERS)
        
        # 2. 국내/해외 필터 (L열)
        f_country = st.multiselect("국내/해외 구분", options=sorted(df_base["국내해외구분"].unique()), default=sorted(df_base["국내해외구분"].unique()))
        
        # 3. 원본 필터 복구
        f_org = st.multiselect("조직 (요청그룹)", options=sorted(df_base["요청그룹"].unique()), default=sorted(df_base["요청그룹"].unique()))
        f_stage = st.multiselect("현재 단계", options=sorted(df_base["현재단계"].unique()), default=sorted(df_base["현재단계"].unique()))
        f_issue = st.multiselect("이슈 분류", options=sorted(df_base["이슈분류"].unique()), default=sorted(df_base["이슈분류"].unique()))
        f_delay = st.multiselect("지연 분류", options=sorted(df_base["지연분류"].unique()), default=sorted(df_base["지연분류"].unique()))
        f_new = st.multiselect("신규/기성", options=sorted(df_base["신규기성"].unique()), default=sorted(df_base["신규기성"].unique()))
        
        req_options = sorted(df_base["대표요청자"].unique())
        f_req = st.multiselect("요청자 필터", options=req_options, default=req_options)
        
        # 4. 시간 필터 (2023-2027+)
        years = sorted(df_base["년도"].dropna().unique().tolist())
        f_year = st.multiselect("분석 년도", options=years, default=years)
        
        keyword = st.text_input("브랜드/비고/내용 검색")
        include_no_date = st.checkbox("등록 완료일 없는 데이터 포함 (WIP 브랜드)", value=True)

    # 필터링 엔진 실행 (데이터 유실 방지)
    df = df_base[
        (df_base["검토자_실명"].isin(f_rev)) &
        (df_base["국내해외구분"].isin(f_country)) &
        (df_base["현재단계"].isin(f_stage)) &
        (df_base["이슈분류"].isin(f_issue)) &
        (df_base["지연분류"].isin(f_delay)) &
        (df_base["신규기성"].isin(f_new)) &
        (df_base["대표요청자"].isin(f_req))
    ].copy()
    
    # 시간 필터링 (선택된 년도이거나 날짜 없는 건 포함)
    df = df[(df["년도"].isin(f_year)) | (df["등록완료일_dt"].isna() if include_no_date else False)]

    if keyword:
        df = df[df.apply(lambda r: keyword.lower() in str(r).lower(), axis=1)]

    # --- [SECTION 1: Core Performance KPI] ---
    total = len(df)
    reg_done = df["bool__registration_done_flag"].sum()
    reg_rate = safe_rate(reg_done, total)
    lt_avg = df["등록소요일"].mean()
    sla_rate = safe_rate(df["SLA_준수"].sum(), df["등록소요일"].notna().sum())

    st.subheader("📍 핵심 운영 지표 (Core Performance)")
    k1, k2, k3, k4, k5 = st.columns(5)
    k1.metric("총 분석 브랜드", f"{total:,}건")
    k2.metric("최종 등록 완료", f"{reg_done:,}건")
    k3.metric("누적 등록 성공률", f"{reg_rate}%")
    k4.metric("평균 리드타임", f"{lt_avg:.1f}일" if not pd.isna(lt_avg) else "-")
    k5.metric("SLA 준수율(7d)", f"{sla_rate}%")

    st.markdown("---")

    # --- [SECTION 2: Funnel & Time Analysis] ---
    tab1, tab2 = st.tabs(["🚀 운영 전략 분석", "🌍 국가별 리드타임 Deep-Dive"])
    
    with tab1:
        c1, c2 = st.columns([6, 4])
        with c1:
            st.markdown("#### 📉 주차별 등록 완료 추이 (Weekly)")
            week_trend = df.dropna(subset=["년주차"]).groupby("년주차").size().reset_index(name="건수")
            fig_week = px.line(week_trend, x="년주차", y="건수", markers=True, template="plotly_white")
            st.plotly_chart(fig_week, use_container_width=True)
        with c2:
            st.markdown("#### 🎯 공정별 전환율 (Funnel)")
            funnel_data = {
                "단계": ["리스트업", "등록요청", "구매완료", "최종등록"],
                "건수": [df["bool__listed"].sum(), df["bool__request_done"].sum(), df["bool__purchase_done"].sum(), df["bool__registration_done_flag"].sum()]
            }
            fig_f = go.Figure(go.Funnel(y=funnel_data["단계"], x=funnel_data["건수"], textinfo="value+percent previous"))
            fig_f.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=350)
            st.plotly_chart(fig_f, use_container_width=True)

    with tab2:
        st.subheader("🌍 국내 vs 해외 리드타임 비교 분석 (L열 기준)")
        # 리드타임 통계
        lt_comp = df.groupby("국내해외구분")["등록소요일"].agg(['mean', 'median', 'max', 'count']).reset_index()
        lt_comp.columns = ["구분", "평균 리드타임(일)", "중앙값(일)", "최장 소요(일)", "샘플 수"]
        st.table(lt_comp.style.format({"평균 리드타임(일)": "{:.1f}", "중앙값(일)": "{:.1f}", "최장 소요(일)": "{:.0f}"}))

        i1, i2 = st.columns(2)
        with i1:
            st.markdown("##### ⏱️ 리드타임 분포 밀도")
            fig_hist = px.histogram(df, x="등록소요일", color="국내해외구분", barmode="overlay", template="plotly_white")
            st.plotly_chart(fig_hist, use_container_width=True)
        with i2:
            st.markdown("##### 🚩 지연 사유 분포")
            st.bar_chart(df["지연분류"].value_counts())

    st.markdown("---")
    st.subheader("📑 마스터 업무 트래킹 시트 (Detailed)")
    # 홍석님 실무 필수 컬럼들로 구성
    disp_cols = [colmap["brand"], "대표요청자", "검토자_실명", "국내해외구분", "현재단계", "등록소요일", "년주차", "지연분류", colmap["remark"]]
    st.dataframe(df[disp_cols].sort_values("등록소요일", ascending=False), use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
