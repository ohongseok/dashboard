import io
import re
from typing import Optional, List, Dict

import gspread
import pandas as pd
import requests
import streamlit as st
from google.oauth2.service_account import Credentials

# ---------------------------
# 0. Page Config
# ---------------------------
st.set_page_config(page_title="KREAM Ops Dashboard", layout="wide")

# ---------------------------
# 1. Constants & Mappings (원본 유지)
# ---------------------------
ILLEGAL_EXCEL_CHARS_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")
HEADER_KEYWORDS = ["요청자", "검토자", "브랜드", "등록 완료일", "국내/해외"]

BOOL_COLUMNS = [
    "리스트업 완료",
    "검토 및 등록 요청 완료",
    "상품 구매 요청",
    "상품 구매 완료",
    "등록 완료 (앱 노출 시 체크)",
]

TRUE_VALUES = {"true", "1", "y", "yes", "완료", "o", "v", "✓", "check", "checked"}
FALSE_VALUES = {"false", "0", "n", "no", "미완료", "x", "-", ""}

COLUMN_ALIASES = {
    "brand": ["브랜드(영문)", "브랜드"],
    "requester": ["요청자"],
    "reviewer": ["검토자"],
    "listed": ["리스트업 완료"],
    "request_done": ["검토 및 등록 요청 완료"], # 이미지의 '등록 완료' 지표
    "purchase_requested": ["상품 구매 요청"],
    "purchase_done": ["상품 구매 완료"],
    "registration_request_date": ["등록 요청일"],
    "registration_done_flag": ["등록 완료 (앱 노출 시 체크)", "등록 완료"], # 이미지의 '노출 확인' 지표
    "registration_done_date": ["등록 완료일"],
    "registration_week": ["등록 주차"],
    "country_type": ["국내/해외"],
    "delay_reason": ["지연 사유"],
    "issue_note": ["브랜드별 검토사항"],
    "issue_conclusion": ["브랜드별 검토사항 결론"],
    "remark": ["비고"],
}

# ---------------------------
# 2. Helpers (원본 로직 및 보정)
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
    if not t: return "Unknown"
    if t.upper() == "3P" or re.fullmatch(r"[가-힣]+", t): return "Famous"
    if re.fullmatch(r"[A-Za-z]+", t): return "KREAM"
    return "Unknown"

def requester_group(raw: str) -> str:
    tokens = split_people(raw)
    if not tokens: return "Unknown"
    groups = {person_group(t) for t in tokens}
    if groups == {"KREAM"}: return "KREAM"
    if groups == {"Famous"}: return "Famous"
    return "Mixed"

def parse_bool(v) -> bool:
    if pd.isna(v): return False
    if isinstance(v, bool): return v
    s = str(v).strip().lower()
    if s in TRUE_VALUES: return True
    if s in FALSE_VALUES: return False
    return False

def parse_date_series(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce")
    if parsed.notna().mean() >= 0.3: return parsed
    return pd.to_datetime(series, errors="coerce", format="%y.%m.%d")

def safe_rate(num: int, den: int) -> float:
    return round((num / den) * 100, 1) if den else 0.0

# ---------------------------
# 3. Data Loading (헤더 인덱스 수정 및 인증 수정)
# ---------------------------
@st.cache_data(ttl=600)
def load_google_sheet_values(sheet_name: str, worksheet_name: Optional[str] = None) -> List[List[str]]:
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"]),
        scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    )
    client = gspread.authorize(creds)
    workbook = client.open(sheet_name) # opens -> open 수정
    worksheet = workbook.worksheet(worksheet_name) if worksheet_name else workbook.sheet1
    return worksheet.get_all_values()

@st.cache_data(ttl=600)
def load_excel_values(file_bytes: bytes, sheet_name: Optional[str] = None) -> List[List[str]]:
    xls = pd.ExcelFile(io.BytesIO(file_bytes))
    target_sheet = sheet_name if sheet_name in xls.sheet_names else xls.sheet_names[0]
    raw = pd.read_excel(io.BytesIO(file_bytes), sheet_name=target_sheet, header=None)
    return raw.fillna("").astype(object).values.tolist()

def find_header_row(values: List[List[str]]) -> int:
    # 로우 데이터 분석 결과 헤더는 인덱스 2(3행)에 위치함
    for idx, row in enumerate(values[:10]):
        cleaned = [normalize_colname(c) for c in row]
        if any("브랜드" in c for c in cleaned) and any("요청자" in c for c in cleaned):
            return idx
    return 0

def values_to_dataframe(values: List[List[str]]) -> pd.DataFrame:
    if not values: return pd.DataFrame()
    header_idx = find_header_row(values)
    headers = [normalize_colname(h) or f"col_{i}" for i, h in enumerate(values[header_idx])]
    rows = values[header_idx + 1:]
    df = pd.DataFrame(rows, columns=headers[:len(rows[0])])
    return df.dropna(how="all").reset_index(drop=True)

def find_column(df: pd.DataFrame, aliases: List[str]) -> Optional[str]:
    for alias in aliases:
        a_norm = normalize_colname(alias).lower()
        for col in df.columns:
            if a_norm in normalize_colname(col).lower(): return col
    return None

# ---------------------------
# 4. Prepare Engine (이미지 지표 반영)
# ---------------------------
def prepare_dataframe(values: List[List[str]]):
    df = values_to_dataframe(values)
    if df.empty: return df, {}, pd.DataFrame(), pd.DataFrame()

    colmap = {key: find_column(df, aliases) for key, aliases in COLUMN_ALIASES.items()}
    
    # 기본 전처리
    brand_col = colmap["brand"]
    if brand_col: df = df[df[brand_col].astype(str).str.strip() != ""].reset_index(drop=True)

    df["요청그룹"] = df[colmap["requester"]].apply(requester_group) if colmap["requester"] else "Unknown"
    df["대표요청자"] = df[colmap["requester"]].apply(lambda x: split_people(x)[0] if split_people(x) else "미입력") if colmap["requester"] else "미입력"
    df["국내해외구분"] = df[colmap["country_type"]].apply(lambda x: "국내" if "국내" in normalize_text(x) else "해외" if "해외" in normalize_text(x) else "미입력") if colmap["country_type"] else "미입력"

    # Boolean 파싱 (상품 구매 완료 등)
    for k in ["listed", "request_done", "purchase_requested", "purchase_done", "registration_done_flag"]:
        col = colmap[k]
        df[f"bool__{k}"] = df[col].apply(parse_bool) if col else False

    # 날짜 처리
    df["date__registration_done"] = parse_date_series(df[colmap["registration_done_date"]]) if colmap["registration_done_date"] else pd.NaT
    df["년도"] = df["date__registration_done"].dt.year.astype("Int64")
    df["월"] = df["date__registration_done"].dt.month.astype("Int64")
    df["주차"] = df["date__registration_done"].dt.isocalendar().week.astype("Int64")
    df["년주차"] = df["date__registration_done"].dt.strftime("%Y-W%V")

    # 단계 레이블 (이미지 바 차트 기준)
    def stage_label(row):
        if row["bool__registration_done_flag"]: return "노출 확인 완료"
        if row["bool__purchase_done"]: return "구매 완료"
        if row["bool__purchase_requested"]: return "구매 요청"
        if row["bool__request_done"]: return "검토/등록 요청 완료"
        if row["bool__listed"]: return "리스트업 완료"
        return "미진행"
    df["현재단계"] = df.apply(stage_label, axis=1)

    # 기타 분류
    df["이슈분류"] = df[colmap["issue_note"]].apply(lambda x: "이슈있음" if normalize_text(x) and normalize_text(x) != "-" else "없음") if colmap["issue_note"] else "없음"
    df["지연분류"] = df[colmap["delay_reason"]].apply(lambda x: "지연" if normalize_text(x) and normalize_text(x) != "-" else "없음") if colmap["delay_reason"] else "없음"
    df["신규기성"] = df[colmap["brand"]].apply(lambda x: "신규" if "신규" in normalize_text(x) else "기성/기타")

    meta = {key: colmap[key] for key in colmap if colmap[key]}
    return df, meta

# ---------------------------
# 5. KPI & UI Rendering
# ---------------------------
def build_kpis(df: pd.DataFrame) -> Dict[str, object]:
    total = len(df)
    request_done = int(df["bool__request_done"].sum()) # 이미지의 '등록 완료 수'
    registration_done = int(df["bool__registration_done_flag"].sum()) # 이미지의 '노출 확인 수'
    
    return {
        "총 브랜드 수": total,
        "등록 완료 수": request_done,
        "노출 확인 수": registration_done,
        "등록 성공률": safe_rate(request_done, total),
        "노출 전환율": safe_rate(registration_done, total),
    }

# ---------------------------
# 6. Main execution
# ---------------------------
st.title("KREAM Ops Dashboard")

# 데이터 소스 선택
with st.sidebar:
    st.header("데이터 소스")
    source_type = st.radio("선택", ["Google Sheet", "Excel 업로드"])
    view_mode = st.radio("보기 방식", ["대시보드", "보고서"])

values = None
if source_type == "Google Sheet":
    s_name = st.text_input("구글 시트 이름", value="1P 상품등록 통합페이지")
    w_name = st.text_input("워크시트 이름", value="Summary")
    if st.button("시트 불러오기", type="primary"):
        values = load_google_sheet_values(s_name, w_name)
        st.session_state["sheet_values"] = values
else:
    uploaded = st.file_uploader("엑셀 파일", type=["xlsx"])
    if uploaded and st.button("엑셀 불러오기", type="primary"):
        values = load_excel_values(uploaded.getvalue())
        st.session_state["sheet_values"] = values

if "sheet_values" in st.session_state:
    df_raw, meta = prepare_dataframe(st.session_state["sheet_values"])
    
    if not df_raw.empty:
        # 필터링 (홍석님 가이드 반영: 23~26년 및 날짜 없는 건 보존)
        with st.sidebar:
            st.markdown("### 필터")
            f_org = st.multiselect("조직", options=df_raw["요청그룹"].unique(), default=df_raw["요청그룹"].unique())
            f_country = st.multiselect("국내/해외", options=df_raw["국내해외구분"].unique(), default=df_raw["국내해외구분"].unique())
            f_stage = st.multiselect("현재 단계", options=df_raw["현재단계"].unique(), default=df_raw["현재단계"].unique())
            
            # 년도 필터 (23~26년 엄격 적용, 단 날짜 없는 행은 보존)
            years_available = sorted([y for y in df_raw["년도"].dropna().unique() if 2023 <= y <= 2026])
            f_year = st.multiselect("년도", options=years_available, default=years_available)
            
            f_req = st.multiselect("요청자", options=sorted(df_raw["대표요청자"].unique()), default=sorted(df_raw["대표요청자"].unique()))
            keyword = st.text_input("브랜드/비고 검색")

        # 필터 적용
        mask = (df_raw["요청그룹"].isin(f_org)) & \
               (df_raw["국내해외구분"].isin(f_country)) & \
               (df_raw["현재단계"].isin(f_stage)) & \
               (df_raw["대표요청자"].isin(f_req))
        
        # 년도 필터링: 선택된 년도이거나, 날짜가 아예 없는 행 포함
        year_mask = (df_raw["년도"].isin(f_year)) | (df_raw["date__registration_done"].isna())
        df_filtered = df_raw[mask & year_mask].copy()
        
        if keyword:
            df_filtered = df_filtered[df_filtered.apply(lambda r: keyword.lower() in str(r).lower(), axis=1)]

        # KPI 출력 (이미지 지표와 동일)
        kpis = build_kpis(df_df := df_filtered)
        st.info(f"감지된 요청자 컬럼: {meta.get('requester')} | 총 필터 결과: {len(df_df)}건")
        
        m = st.columns(5)
        m[0].metric("총 브랜드 수", kpis["총 브랜드 수"])
        m[1].metric("등록 완료 수", kpis["등록 완료 수"])
        m[2].metric("노출 확인 수", kpis["노출 확인 수"])
        m[3].metric("등록 성공률", f"{kpis['등록 성공률']}%")
        m[4].metric("노출 전환율", f"{kpis['노출 전환율']}%")

        # 차트 영역 (이미지 바 차트 복구)
        st.markdown("### 운영 현황")
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("**단계별 브랜드 수**")
            st.bar_chart(df_df["현재단계"].value_counts())
        with c2:
            st.markdown("**조직별 브랜드 수**")
            st.bar_chart(df_df["요청그룹"].value_counts())

        st.markdown("### 국내 vs 해외")
        st.bar_chart(df_df["국내해외구분"].value_counts())

        # 상세 리스트
        st.markdown("### 상세 데이터")
        st.dataframe(df_df.sort_values("date__registration_done", ascending=False), use_container_width=True)
    else:
        st.warning("데이터가 없습니다.")
