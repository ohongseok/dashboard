import io
import re
from typing import Optional, List, Dict

import gspread
import pandas as pd
import numpy as np
import plotly.express as px
import streamlit as st
from google.oauth2.service_account import Credentials
from datetime import datetime

# ---------------------------
# 0. Page Configuration
# ---------------------------
st.set_page_config(page_title="KREAM Ops Dashboard", layout="wide")

# ---------------------------
# 1. Constants & Mappings (원본 유지)
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

TRUE_VALUES = {"true", "1", "y", "yes", "완료", "o", "v", "✓", "check", "checked", True}

# ---------------------------
# 2. Helper Functions
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
    v_str = str(v).strip()
    try:
        # 23.02.20 형식 대응
        return pd.to_datetime(v_str, format="%y.%m.%d", errors="coerce")
    except:
        return pd.to_datetime(v_str, errors="coerce")

def safe_rate(num, den) -> float:
    return round((num / den) * 100, 1) if den else 0.0

# ---------------------------
# 3. Data Loading Logic
# ---------------------------
@st.cache_data(ttl=600)
def load_and_preprocess(values: List[List[str]]):
    if not values: return pd.DataFrame(), {}

    # 로우 데이터 특성상 2번째 줄(Index 1)이 실제 헤더인 경우가 많음
    header_idx = 0
    for i, row in enumerate(values[:5]):
        if "브랜드" in str(row) or "요청자" in str(row):
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
                    colmap[key] = col
                    break
            if key in colmap: break

    # [핵심] KeyError 방지를 위해 필터에서 사용하는 컬럼들을 강제로 생성
    # 1. 날짜 및 연도 (2023-2026 필터용)
    done_date_col = colmap.get("registration_done_date")
    df["등록 완료일_dt"] = df[done_date_col].apply(parse_date) if done_date_col else pd.NaT
    df["년도"] = df["등록 완료일_dt"].dt.year.astype("Int64")
    
    # 홍석님 가이드: 2023-2026 범위 데이터만 유지
    df = df[(df["년도"] >= 2023) & (df["년도"] <= 2026)].copy()

    # 2. 조직 및 인력
    req_col = colmap.get("requester")
    df["대표요청자"] = df[req_col].apply(lambda x: split_people(x)[0] if split_people(x) else "미입력") if req_col else "미입력"
    df["조직"] = df["대표요청자"].apply(person_group)

    # 3. 국내/해외 (에러 발생 포인트 해결)
    country_col = colmap.get("country_type")
    if country_col:
        df["국내해외구분"] = df[country_col].apply(lambda x: "국내" if "국내" in normalize_text(x) else "해외" if "해외" in normalize_text(x) else "미입력")
    else:
        df["국내해외구분"] = "미입력"

    # 4. 상태값 및 단계
    for k in ["listed", "request_done", "purchase_requested", "purchase_done", "registration_done_flag"]:
        col = colmap.get(k)
        df[f"is_{k}"] = df[col].apply(parse_bool) if col else False

    def get_stage(r):
        if r["is_registration_done_flag"]: return "등록 완료"
        if r["is_purchase_done"]: return "구매 완료"
        if r["is_purchase_requested"]: return "구매 요청"
        if r["is_request_done"]: return "등록 요청 완료"
        if r["is_listed"]: return "리스트업 완료"
        return "미진행"
    df["현재단계"] = df.apply(get_stage, axis=1)

    # 5. 리드타임
    req_date_col = colmap.get("registration_request_date")
    df["등록요청일_dt"] = df[req_date_col].apply(parse_date) if req_date_col else pd.NaT
    df["등록소요일"] = (df["등록 완료일_dt"] - df["등록요청일_dt"]).dt.days
    df["등록소요일"] = df["등록소요일"].apply(lambda x: x if 0 <= x <= 365 else np.nan)

    # 6. 시간 차원
    df["월"] = df["등록 완료일_dt"].dt.month.astype("Int64")
    df["년월"] = df["등록 완료일_dt"].dt.strftime("%Y-%m")
    
    # 7. 등록제외
    df["등록제외"] = df["등록 완료일_dt"].isna()

    return df, colmap

# ---------------------------
# 4. Main App Interface
# ---------------------------
def main():
    st.title("🏆 KREAM Ops Dashboard")

    with st.sidebar:
        st.header("데이터 소스")
        source = st.radio("선택", ["Google Sheet", "Excel Upload"])
        raw_values = None
        
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
            up = st.file_uploader("XLSX 업로드", type="xlsx")
            if up:
                df_excel = pd.read_excel(up, header=None)
                raw_values = [df_excel.columns.tolist()] + df_excel.values.tolist()
                st.session_state["raw"] = raw_values

    if "raw" not in st.session_state:
        st.info("사이드바에서 데이터를 로드해주세요.")
        return

    df_base, colmap = load_and_preprocess(st.session_state["raw"])
    
    if df_base.empty:
        st.warning("분석 가능한 데이터가 없습니다 (2023-2026 범위).")
        return

    # --- 필터 (이미지 기준 복구) ---
    with st.sidebar:
        st.markdown("---")
        st.header("필터")
        f_org = st.multiselect("조직", options=df_base["조직"].unique(), default=df_base["조직"].unique())
        f_country = st.multiselect("국내/해외", options=df_base["국내해외구분"].unique(), default=df_base["국내해외구분"].unique())
        f_stage = st.multiselect("현재 단계", options=df_base["현재단계"].unique(), default=df_base["현재단계"].unique())
        f_year = st.multiselect("년도", options=sorted(df_base["년도"].dropna().unique().tolist()), default=sorted(df_base["년도"].dropna().unique().tolist()))
        
        keyword = st.text_input("브랜드/비고 검색")
        include_ex = st.checkbox("등록 완료일 없는 데이터 포함", value=True)

    # 필터 적용
    df = df_base[
        (df_base["조직"].isin(f_org)) &
        (df_base["국내해외구분"].isin(f_country)) &
        (df_base["현재단계"].isin(f_stage)) &
        (df_base["년도"].isin(f_year))
    ].copy()
    
    if not include_ex: df = df[df["등록 완료일_dt"].notna()]
    if keyword:
        b_col = colmap.get("brand")
        r_col = colmap.get("remark")
        df = df[df[b_col].astype(str).str.contains(keyword, case=False) | 
                df[r_col].astype(str).str.contains(keyword, case=False)]

    # --- 대시보드 출력 ---
    k1, k2, k3, k4 = st.columns(4)
    total = len(df)
    done = df["is_registration_done_flag"].sum()
    k1.metric("총 브랜드 수", f"{total}건")
    k2.metric("등록 완료 수", f"{done}건")
    k3.metric("등록 성공률", f"{safe_rate(done, total)}%")
    k4.metric("평균 리드타임", f"{df['등록소요일'].mean():.1f}일" if not df['등록소요일'].isna().all() else "-")

    st.markdown("---")
    
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("📊 단계별 현황")
        st.bar_chart(df["현재단계"].value_counts())
    with c2:
        st.subheader("📈 월간 등록 추이")
        if not df.dropna(subset=["년월"]).empty:
            trend = df.groupby("년월").size().reset_index(name="건수")
            fig = px.line(trend, x="년월", y="건수", markers=True)
            st.plotly_chart(fig, use_container_width=True)

    st.subheader("📋 상세 트래킹 리스트")
    st.dataframe(df.sort_values("등록 완료일_dt", ascending=False), use_container_width=True, hide_index=True)

if __name__ == "__main__":
    main()
