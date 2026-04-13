import io
import re
from typing import Optional, List, Dict

import gspread
import pandas as pd
import requests
import streamlit as st
from google.oauth2.service_account import Credentials

# ---------------------------
# 0. Page Configuration
# ---------------------------
st.set_page_config(page_title="KREAM Ops Dashboard", layout="wide")

# ---------------------------
# 1. Constants & Mappings (원본 데이터 유지)
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

def clean_excel_value(value):
    if isinstance(value, str):
        return ILLEGAL_EXCEL_CHARS_RE.sub("", value)
    return value

def clean_dataframe_for_excel(df: pd.DataFrame) -> pd.DataFrame:
    cleaned = df.copy()
    object_cols = cleaned.select_dtypes(include=["object"]).columns
    for col in object_cols:
        cleaned[col] = cleaned[col].map(clean_excel_value)
    return cleaned

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
# 3. Data Loading (Authentication Error Fixed)
# ---------------------------
@st.cache_data(ttl=600)
def load_google_sheet_values(sheet_name: str, worksheet_name: Optional[str] = None) -> List[List[str]]:
    """인증 에러 해결을 위해 명확한 Scope 정의 및 opens 오타 수정"""
    try:
        # 전문가 코멘트: 인증 에러 방지를 위해 spreadsheets와 drive 권한을 모두 포함해야 합니다.
        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), 
            scopes=scopes
        )
        client = gspread.authorize(creds)
        
        # 수정됨: opens -> open
        workbook = client.open(sheet_name)
        worksheet = workbook.worksheet(worksheet_name) if worksheet_name else workbook.sheet1
        return worksheet.get_all_values()
    except Exception as e:
        st.error(f"구글 시트 로드 중 에러 발생: {e}")
        return []

@st.cache_data(ttl=600)
def load_excel_values(file_bytes: bytes, sheet_name: Optional[str] = None) -> List[List[str]]:
    xls = pd.ExcelFile(io.BytesIO(file_bytes))
    target_sheet = sheet_name if sheet_name in xls.sheet_names else xls.sheet_names[0]
    raw = pd.read_excel(io.BytesIO(file_bytes), sheet_name=target_sheet, header=None)
    return raw.fillna("").astype(object).values.tolist()

# ---------------------------
# 4. Prepare DataFrame (원본 로직 복구 및 필터 보강)
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
    
    # [핵심] 2023-2026 연도 제한 로직 적용
    if colmap["registration_done_date"]:
        df["date__registration_done"] = parse_date_series(df[colmap["registration_done_date"]])
        df["년도"] = df["date__registration_done"].dt.year.astype("Int64")
        # 2023년 미만, 2027년 이상 데이터 제거
        df = df[(df["년도"] >= 2023) & (df["년도"] <= 2026)].copy()
    else:
        df["date__registration_done"] = pd.NaT
        df["년도"] = pd.NA

    # 브랜드 컬럼 필터
    if colmap["brand"]:
        df = df[df[colmap["brand"]].astype(str).str.strip() != ""].reset_index(drop=True)

    # 파생 변수 및 상태값 (원본 로직 100% 보존)
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

    # 지연/이슈 분류 로직
    text_cols = [colmap[c] for c in ["delay_reason", "issue_note", "issue_conclusion", "remark"] if colmap[c]]
    combined_text = df[text_cols].astype(str).agg(' '.join, axis=1)
    df["지연분류"] = combined_text.apply(lambda x: category_from_text(x, DELAY_MAPPING))
    df["이슈분류"] = combined_text.apply(lambda x: category_from_text(x, ISSUE_MAPPING))
    df["신규기성"] = combined_text.apply(lambda x: "신규" if any(k in x.lower() for k in ["신생", "신규", "new brand", "발굴"]) else "기성/기타")
    
    # 등록 제외 로직
    rem_col = colmap["remark"]
    df["등록제외사유"] = df.apply(lambda r: "등록 불가" if (rem_col and "등록 불가" in normalize_text(r[rem_col])) else "등록 완료일 없음" if pd.isna(r["date__registration_done"]) else "", axis=1)
    df["등록제외"] = df["등록제외사유"] != ""

    # 시간 차원 보강
    df["월"] = df["date__registration_done"].dt.month.astype("Int64")
    df["주차"] = df["date__registration_done"].dt.isocalendar().week.astype("Int64")
    df["ISO년도"] = df["date__registration_done"].dt.isocalendar().year.astype("Int64")
    df["년월"] = df["date__registration_done"].dt.strftime("%Y-%m")
    df["년주차"] = df["ISO년도"].astype(str) + "-W" + df["주차"].astype(str).str.zfill(2)

    # 인력 데이터 (원본 로직 보존)
    def count_people(col, label):
        if not col: return pd.DataFrame(columns=[label, "소속", "건수"])
        recs = [{"n": t, "s": person_group(t)} for raw in df[col].fillna("") for t in split_people(raw)]
        if not recs: return pd.DataFrame(columns=[label, "소속", "건수"])
        return pd.DataFrame(recs).rename(columns={"n": label}).groupby([label, "소속"]).size().reset_index(name="건수").sort_values("건수", ascending=False)

    return df, colmap, count_people(req_col, "요청자"), count_people(colmap["reviewer"], "검토자")

# ---------------------------
# 5. KPI Builder (원본 계산식 100% 보장)
# ---------------------------
def build_kpis(df: pd.DataFrame) -> Dict[str, object]:
    total = len(df)
    done = int(df["bool__registration_done_flag"].sum()) if "bool__registration_done_flag" in df else 0
    lt_valid = df["등록소요일"].dropna()
    
    def get_trend(target_df, group_cols, label_col):
        if target_df.empty: return pd.DataFrame(), "-", 0, 0
        grouped = target_df.groupby(group_cols + [label_col]).size().reset_index(name="건수").sort_values(group_cols)
        cur = int(grouped.iloc[-1]["건수"])
        prev = int(grouped.iloc[-2]["건수"]) if len(grouped) > 1 else 0
        return grouped, grouped.iloc[-1][label_col], cur, prev

    w_df, w_lab, w_cur, w_prev = get_trend(df.dropna(subset=["ISO년도", "주차"]), ["ISO년도", "주차"], "년주차")
    m_df, m_lab, m_cur, m_prev = get_trend(df.dropna(subset=["년도", "월"]), ["년도", "월"], "년월")

    return {
        "총 브랜드 수": total, "등록 완료 수": done, "등록 성공률": safe_rate(done, total),
        "평균 리드타임": round(lt_valid.mean(), 1) if not lt_valid.empty else None,
        "이번주": w_cur, "전주": w_prev, "WoW": growth(w_cur, w_prev), "이번주라벨": w_lab, "전주라벨": (w_df.iloc[-2]["년주차"] if len(w_df) > 1 else "-"),
        "이번달": m_cur, "전월": m_prev, "MoM": growth(m_cur, m_prev), "이번달라벨": m_lab, "전월라벨": (m_df.iloc[-2]["년월"] if len(m_df) > 1 else "-"),
        "요청그룹표": df["요청그룹"].value_counts().reset_index(name="건수"),
        "단계표": df["현재단계"].value_counts().reset_index(name="건수"),
        "SLA7일내 완료율": safe_rate(int((lt_valid <= 7).sum()), len(lt_valid)),
        "주간표": w_df, "월간표": m_df, "등록 제외 수": int(df["등록제외"].sum())
    }

# ---------------------------
# 6. Main App & Dashboard (필터 세분화 및 복구)
# ---------------------------
st.title("📊 KREAM Ops Dashboard (Intelligence Ver.)")

with st.sidebar:
    st.header("1. 데이터 소스")
    source_type = st.radio("소스 선택", ["Google Sheet", "Excel 업로드"])
    if source_type == "Google Sheet":
        s_name = st.text_input("구글 시트 제목")
        w_name = st.text_input("워크시트 제목", value="Summary")
        if st.button("데이터 동기화", type="primary"):
            st.session_state["raw_data"] = load_google_sheet_values(s_name, w_name)
    else:
        uploaded = st.file_uploader("파일 선택", type="xlsx")
        if uploaded: st.session_state["raw_data"] = load_excel_values(uploaded.getvalue())

if "raw_data" in st.session_state and st.session_state["raw_data"]:
    df_raw, meta, req_rank, rev_rank = prepare_dataframe(st.session_state["raw_data"])
    
    if not df_raw.empty:
        # 전문가 세분화 필터 (홍석님 기존 필터 포함)
        with st.sidebar:
            st.markdown("---")
            st.header("2. 필터 설정")
            sel_years = st.multiselect("연도 필터", options=sorted(df_raw["년도"].dropna().unique().tolist()), default=sorted(df_raw["년도"].dropna().unique().tolist()))
            sel_groups = st.multiselect("요청 그룹 필터", options=df_raw["요청그룹"].unique().tolist(), default=df_raw["요청그룹"].unique().tolist())
            sel_stages = st.multiselect("현재 단계 필터", options=df_raw["현재단계"].unique().tolist(), default=df_raw["현재단계"].unique().tolist())
            keyword = st.text_input("키워드 검색 (브랜드/비고)")
            include_ex = st.checkbox("등록 제외건 포함", value=False)
            
            st.markdown("---")
            st.header("3. 전문가 특화 필터")
            only_delay = st.checkbox("14일 이상 지연건만 보기")
            bottleneck_view = st.checkbox("병목(미완료) 구간 집중 보기")

        # 필터링 엔진 실행
        f_df = df_raw[df_raw["년도"].isin(sel_years)].copy()
        f_df = f_df[f_df["요청그룹"].isin(sel_groups)]
        f_df = f_df[f_df["현재단계"].isin(sel_stages)]
        if not include_ex: f_df = f_df[~f_df["등록제외"]]
        if only_delay: f_df = f_df[f_df["등록소요일"] >= 14]
        if bottleneck_view: f_df = f_df[f_df["현재단계"] != "등록 완료"]
        if keyword:
            sc = [meta[c] for c in ["brand", "remark", "issue_note"] if meta.get(c)]
            f_df = f_df[f_df[sc].astype(str).apply(lambda x: x.str.contains(keyword, case=False)).any(axis=1)]

        # KPI 출력
        kpis = build_kpis(f_df)
        cols = st.columns(5)
        cols[0].metric("총 브랜드", f"{kpis['총 브랜드 수']}건")
        cols[1].metric("등록 성공", f"{kpis['등록 완료 수']}건", f"{kpis['등록 성공률']}%")
        cols[2].metric("주간 증감", f"{kpis['이번주']}건", f"{kpis['WoW']}%")
        cols[3].metric("평균 리드타임", f"{kpis['평균 리드타임'] or '-'}일")
        cols[4].metric("SLA 준수(7일)", f"{kpis['SLA7일내 완료율']}%")

        st.markdown("---")
        
        # 차트 및 테이블 레이아웃
        left, right = st.columns(2)
        with left:
            st.subheader("📌 단계별 분포")
            st.bar_chart(kpis["단계표"].set_index("현재단계"))
            st.subheader("🏆 요청자 처리 랭킹")
            st.dataframe(req_rank.head(10), use_container_width=True, hide_index=True)
        with right:
            st.subheader("📈 주간 등록 추이")
            if not kpis["주간표"].empty:
                st.line_chart(kpis["주간표"].set_index("년주차")["건수"])
            st.subheader("🚩 지연/이슈 분류")
            delay_stat = f_df["지연분류"].value_counts().reset_index()
            st.dataframe(delay_stat, use_container_width=True, hide_index=True)

        st.subheader("🔍 상세 데이터 추적")
        st.dataframe(f_df[[meta["brand"], "대표요청자", "등록소요일", "현재단계", "지연분류"]].sort_values("등록소요일", ascending=False), use_container_width=True, hide_index=True)
        
        # 다운로드
        csv = f_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button("📂 필터링 결과 엑셀(CSV) 다운로드", data=csv, file_name="kream_ops_result.csv")
    else:
        st.warning("분석 기간(2023-2026) 내에 해당하는 데이터가 시트에 없습니다.")
else:
    st.info("사이드바에서 데이터 소스를 설정하고 [데이터 동기화]를 눌러주세요.")
