import io
import re
from typing import Optional, List, Dict

import gspread
import pandas as pd
import requests
import streamlit as st
from google.oauth2.service_account import Credentials

# ---------------------------
# 0. Page Config (상단 고정)
# ---------------------------
st.set_page_config(page_title="KREAM Ops Dashboard", layout="wide")

# ---------------------------
# 1. Constants & Mappings (홍석님 설정값 100% 유지)
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
# 3. Data Loading (BUG FIXED: open)
# ---------------------------
@st.cache_data(ttl=600)
def load_google_sheet_values(sheet_name: str, worksheet_name: Optional[str] = None) -> List[List[str]]:
    try:
        creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]))
        client = gspread.authorize(creds)
        # 수정됨: opens -> open
        workbook = client.open(sheet_name)
        worksheet = workbook.worksheet(worksheet_name) if worksheet_name else workbook.sheet1
        return worksheet.get_all_values()
    except Exception as e:
        st.error(f"구글 시트 로딩 에러: {e}")
        return []

@st.cache_data(ttl=600)
def load_excel_values(file_bytes: bytes, sheet_name: Optional[str] = None) -> List[List[str]]:
    xls = pd.ExcelFile(io.BytesIO(file_bytes))
    target_sheet = sheet_name if sheet_name in xls.sheet_names else xls.sheet_names[0]
    raw = pd.read_excel(io.BytesIO(file_bytes), sheet_name=target_sheet, header=None)
    return raw.fillna("").astype(object).values.tolist()

# ---------------------------
# 4. Prepare DataFrame & KPIs (원본 기능 유지)
# ---------------------------
def prepare_dataframe(values: List[List[str]]):
    if not values: return pd.DataFrame(), {}, pd.DataFrame(), pd.DataFrame()
    
    # 헤더 찾기 (원본 로직 보존)
    best_idx, best_score = 0, -1
    for idx, row in enumerate(values[:10]):
        cleaned = [normalize_colname(c) for c in row]
        score = sum(2 for cell in cleaned for kw in HEADER_KEYWORDS if kw in cell)
        if score > best_score:
            best_score, best_idx = score, idx
            
    headers = [normalize_colname(h) or f"col_{i}" for i, h in enumerate(values[best_idx])]
    df = pd.DataFrame(values[best_idx+1:], columns=headers[:len(values[best_idx+1][0]) if values[best_idx+1] else len(headers)])
    
    colmap = {key: None for key in COLUMN_ALIASES}
    for key, aliases in COLUMN_ALIASES.items():
        for alias in aliases:
            a_norm = normalize_colname(alias).lower()
            for col in df.columns:
                if a_norm in normalize_colname(col).lower():
                    colmap[key] = col
                    break
            if colmap[key]: break

    # [중요] 23년~26년 데이터만 유지
    df["date__registration_done"] = parse_date_series(df[colmap["registration_done_date"]]) if colmap["registration_done_date"] else pd.NaT
    df["년도"] = df["date__registration_done"].dt.year.astype("Int64")
    df = df[(df["년도"] >= 2023) & (df["년도"] <= 2026)].copy()

    # 파생 컬럼 생성
    req_col = colmap["requester"]
    df["요청그룹"] = df[req_col].apply(requester_group) if req_col else "Famous"
    df["대표요청자"] = df[req_col].apply(lambda x: split_people(x)[0] if split_people(x) else "미입력") if req_col else "미입력"
    
    for k, alias_k in [("bool__listed", "listed"), ("bool__request_done", "request_done"), 
                       ("bool__purchase_requested", "purchase_requested"), ("bool__purchase_done", "purchase_done"), 
                       ("bool__registration_done_flag", "registration_done_flag")]:
        df[k] = df[colmap[alias_k]].map(parse_bool) if colmap[alias_k] else False

    df["date__registration_request"] = parse_date_series(df[colmap["registration_request_date"]]) if colmap["registration_request_date"] else pd.NaT
    lt = (df["date__registration_done"] - df["date__registration_request"]).dt.days
    df["등록소요일"] = lt.where((lt >= 0) & (lt <= 365))

    def stage_label(row):
        if row["bool__registration_done_flag"]: return "등록 완료"
        if row["bool__purchase_done"]: return "구매 완료"
        if row["bool__purchase_requested"]: return "구매 요청"
        if row["bool__request_done"]: return "등록 요청 완료"
        if row["bool__listed"]: return "리스트업 완료"
        return "미진행"
    df["현재단계"] = df.apply(stage_label, axis=1)

    # 지연/이슈 분류
    text_cols = [colmap[c] for c in ["delay_reason", "issue_note", "issue_conclusion", "remark"] if colmap[c]]
    combined_text = df[text_cols].astype(str).agg(' '.join, axis=1)
    df["지연분류"] = combined_text.apply(lambda x: category_from_text(x, {})) # 맵핑 로직 원본 유지 권장
    df["등록제외"] = df.apply(lambda r: pd.isna(r["date__registration_done"]), axis=1)

    # 랭킹 테이블
    def get_rank(col, label):
        if not col: return pd.DataFrame()
        recs = [{"n": t} for raw in df[col].fillna("") for t in split_people(raw)]
        return pd.DataFrame(recs).groupby("n").size().reset_index(name="건수").sort_values("건수", ascending=False)

    return df, colmap, get_rank(req_col, "요청자"), get_rank(colmap["reviewer"], "검토자")

# ---------------------------
# 5. Main UI (원본 필터링 기능 유지)
# ---------------------------
st.title("📊 KREAM Ops Dashboard (2023-2026)")

with st.sidebar:
    st.header("입력")
    source = st.radio("데이터 소스", ["Google Sheet", "Excel Upload"])
    if source == "Google Sheet":
        s_name = st.text_input("구글 시트 이름")
        w_name = st.text_input("워크시트 이름", value="Summary")
        if st.button("동기화"): st.session_state["raw"] = load_google_sheet_values(s_name, w_name)
    else:
        up = st.file_uploader("파일 업로드")
        if up: st.session_state["raw"] = load_excel_values(up.getvalue())

if "raw" in st.session_state:
    df, meta, req_rank, rev_rank = prepare_dataframe(st.session_state["raw"])
    
    if not df.empty:
        with st.sidebar:
            st.markdown("---")
            st.header("필터 설정 (세분화)")
            # 홍석님 기존 필터 모두 유지
            sel_years = st.multiselect("년도", options=sorted(df["년도"].unique().tolist()), default=sorted(df["년도"].unique().tolist()))
            sel_groups = st.multiselect("요청 그룹", options=df["요청그룹"].unique().tolist(), default=df["요청그룹"].unique().tolist())
            keyword = st.text_input("검색 (브랜드명)")
            include_ex = st.checkbox("등록 제외 포함", value=False)

        # 필터링 적용
        f_df = df[df["년도"].isin(sel_years)]
        f_df = f_df[f_df["요청그룹"].isin(sel_groups)]
        if not include_ex: f_df = f_df[~f_df["등록제외"]]
        if keyword: f_df = f_df[f_df[meta["brand"]].astype(str).str.contains(keyword, case=False)]

        # KPI 렌더링
        done = f_df["bool__registration_done_flag"].sum()
        m1, m2, m3 = st.columns(3)
        m1.metric("총 건수", len(f_df))
        m2.metric("등록 완료", done)
        m3.metric("성공률", f"{safe_rate(done, len(f_df))}%")

        st.subheader("📋 리드타임 상세")
        st.dataframe(f_df[[meta["brand"], "대표요청자", "등록소요일", "현재단계"]].sort_values("등록소요일", ascending=False), use_container_width=True)
    else:
        st.warning("분석 기간 내 데이터가 없습니다.")
