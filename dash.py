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
# 1. Constants & Mappings (원본 설정 100% 유지)
# ---------------------------
ILLEGAL_EXCEL_CHARS_RE = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")
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
# 2. Helpers (원본 로직 보존)
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
    if pd.isna(v): return False
    if isinstance(v, bool): return v
    if isinstance(v, (int, float)): return float(v) != 0
    s = str(v).strip().lower()
    return s in TRUE_VALUES

def parse_date_series(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce")
    if parsed.notna().mean() < 0.3:
        parsed = pd.to_datetime(series, errors="coerce", format="%y.%m.%d")
    return parsed

def category_from_text(text: str, mapping: Dict[str, List[str]], default: str = "기타") -> str:
    t = normalize_text(text).lower()
    if not t or t == "-": return "없음"
    for category, keywords in mapping.items():
        if any(k in t for k in keywords): return category
    return default

def safe_rate(num: int, den: int) -> float:
    return round((num / den) * 100, 1) if den else 0.0

def growth(cur: int, prev: int) -> float:
    if prev == 0: return 0.0
    return round(((cur - prev) / prev) * 100, 1)

# ---------------------------
# 3. Data Loading (Authentication & KeyError Fix)
# ---------------------------
@st.cache_data(ttl=600)
def load_google_sheet_values(sheet_name: str, worksheet_name: Optional[str] = None) -> List[List[str]]:
    try:
        scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=scopes)
        client = gspread.authorize(creds)
        workbook = client.open(sheet_name)
        worksheet = workbook.worksheet(worksheet_name) if worksheet_name else workbook.sheet1
        return worksheet.get_all_values()
    except Exception as e:
        st.error(f"구글 시트 로드 에러: {e}")
        return []

@st.cache_data(ttl=600)
def load_excel_values(file_bytes: bytes, sheet_name: Optional[str] = None) -> List[List[str]]:
    xls = pd.ExcelFile(io.BytesIO(file_bytes))
    target_sheet = sheet_name if sheet_name in xls.sheet_names else xls.sheet_names[0]
    raw = pd.read_excel(io.BytesIO(file_bytes), sheet_name=target_sheet, header=None)
    return raw.fillna("").astype(object).values.tolist()

# ---------------------------
# 4. Prepare DataFrame (에러 포인트 수정 및 로직 복구)
# ---------------------------
def find_header_row(values: List[List[str]]) -> int:
    best_idx, best_score = 0, -1
    for idx, row in enumerate(values[:10]):
        cleaned = [normalize_colname(c) for c in row]
        if not any(cleaned): continue
        score = sum(2 for cell in cleaned for kw in HEADER_KEYWORDS if kw in cell)
        score += len([c for c in cleaned if c]) * 0.05
        if score > best_score:
            best_score, best_idx = score, idx
    return best_idx

def values_to_dataframe(values: List[List[str]]) -> pd.DataFrame:
    if not values: return pd.DataFrame()
    header_row = find_header_row(values)
    headers = [normalize_colname(h) or f"col_{i}" for i, h in enumerate(values[header_row])]
    rows = values[header_row + 1:]
    df = pd.DataFrame(rows)
    df.columns = headers[:len(df.columns)]
    return df.dropna(how="all").reset_index(drop=True)

def find_column(df: pd.DataFrame, aliases: List[str]) -> Optional[str]:
    for alias in aliases:
        a_norm = normalize_colname(alias).lower()
        for col in df.columns:
            if a_norm in normalize_colname(col).lower(): return col
    return None

def prepare_dataframe(values: List[List[str]]):
    df = values_to_dataframe(values)
    if df.empty: return df, {}, pd.DataFrame(), pd.DataFrame()

    colmap = {key: find_column(df, aliases) for key, aliases in COLUMN_ALIASES.items()}
    
    # [중요] 연도 필터링 (2023-2026)
    if colmap["registration_done_date"]:
        df["date__registration_done"] = parse_date_series(df[colmap["registration_done_date"]])
        df["년도"] = df["date__registration_done"].dt.year.astype("Int64")
        df = df[(df["년도"] >= 2023) & (df["년도"] <= 2026)].copy()
    else:
        df["년도"] = pd.NA

    # 파생 변수 및 상태값 (원본 로직 유지)
    req_col = colmap["requester"]
    df["요청그룹"] = df[req_col].apply(requester_group) if req_col else "Famous"
    
    for k, alias_k in [("bool__listed", "listed"), ("bool__request_done", "request_done"), 
                       ("bool__purchase_requested", "purchase_requested"), ("bool__purchase_done", "purchase_done"), 
                       ("bool__registration_done_flag", "registration_done_flag")]:
        df[k] = df[colmap[alias_k]].map(parse_bool) if colmap[alias_k] else False

    df["date__registration_request"] = parse_date_series(df[colmap["registration_request_date"]]) if colmap["registration_request_date"] else pd.NaT
    lt = (df["date__registration_done"] - df["date__registration_request"]).dt.days
    df["등록소요일"] = lt.where((lt >= 0) & (lt <= 365))

    # [KeyError 해결 핵심] count_people 함수 내 컬럼 생성 일치화
    def count_people(col, label):
        if not col or col not in df.columns: return pd.DataFrame(columns=[label, "소속", "건수"])
        records = []
        for raw in df[col].fillna(""):
            tokens = split_people(raw)
            for token in tokens:
                # 여기서 "소속" 컬럼을 명확히 생성하여 전달합니다.
                records.append({label: token, "소속": person_group(token)})
        if not records: return pd.DataFrame(columns=[label, "소속", "건수"])
        return pd.DataFrame(records).groupby([label, "소속"]).size().reset_index(name="건수").sort_values("건수", ascending=False)

    req_rank = count_people(req_col, "요청자")
    rev_rank = count_people(colmap["reviewer"], "검토자")

    # 단계 레이블
    def stage_label(row):
        if row["bool__registration_done_flag"]: return "등록 완료"
        if row["bool__purchase_done"]: return "구매 완료"
        if row["bool__purchase_requested"]: return "구매 요청"
        if row["bool__request_done"]: return "등록 요청 완료"
        if row["bool__listed"]: return "리스트업 완료"
        return "미진행"
    df["현재단계"] = df.apply(stage_label, axis=1)

    return df, colmap, req_rank, rev_rank

# ---------------------------
# 5. Main Dashboard (원본 필터링 100% 복구)
# ---------------------------
st.title("📊 KREAM Ops Dashboard (Stable Ver.)")

with st.sidebar:
    st.header("1. 데이터 소스")
    source = st.radio("데이터 소스", ["Google Sheet", "Excel Upload"])
    if source == "Google Sheet":
        s_name = st.text_input("구글 시트 이름")
        w_name = st.text_input("워크시트 이름", value="Summary")
        if st.button("데이터 동기화", type="primary"):
            st.session_state["raw_data"] = load_google_sheet_values(s_name, w_name)
    else:
        up = st.file_uploader("파일 선택", type="xlsx")
        if up: st.session_state["raw_data"] = load_excel_values(up.getvalue())

if "raw_data" in st.session_state and st.session_state["raw_data"]:
    df_raw, meta, req_rank, rev_rank = prepare_dataframe(st.session_state["raw_data"])
    
    if not df_raw.empty:
        with st.sidebar:
            st.markdown("---")
            st.header("2. 상세 필터")
            # 홍석님 기존 필터 모두 복구
            sel_years = st.multiselect("연도 필터", options=sorted(df_raw["년도"].dropna().unique().tolist()), default=sorted(df_raw["년도"].dropna().unique().tolist()))
            sel_groups = st.multiselect("요청 그룹 필터", options=df_raw["요청그룹"].unique().tolist(), default=df_raw["요청그룹"].unique().tolist())
            keyword = st.text_input("검색 (브랜드명/비고)")

        # 필터링 적용
        f_df = df_raw[df_raw["년도"].isin(sel_years)].copy()
        f_df = f_df[f_df["요청그룹"].isin(sel_groups)]
        if keyword:
            sc = [meta[c] for c in ["brand", "remark", "issue_note"] if meta.get(c)]
            f_df = f_df[f_df[sc].astype(str).apply(lambda x: x.str.contains(keyword, case=False)).any(axis=1)]

        # KPI 출력
        done = f_df["bool__registration_done_flag"].sum()
        c1, c2, c3 = st.columns(3)
        c1.metric("총 브랜드", f"{len(f_df)}건")
        c2.metric("등록 완료", f"{done}건")
        c3.metric("성공률", f"{safe_rate(done, len(f_df))}%")

        st.markdown("---")
        
        # 데이터 레이아웃
        left, right = st.columns(2)
        with left:
            st.subheader("📌 요청자 처리 현황")
            st.dataframe(req_rank.head(10), use_container_width=True, hide_index=True)
        with right:
            st.subheader("📈 브랜드 현재 단계")
            st.bar_chart(f_df["현재단계"].value_counts())

        st.subheader("🔍 상세 데이터")
        st.dataframe(f_df[[meta["brand"], "현재단계", "등록소요일"]].sort_values("등록소요일", ascending=False), use_container_width=True, hide_index=True)
        
    else:
        st.warning("분석 기간(2023-2026) 내에 유효한 데이터가 없습니다.")
