import io
import re
from typing import Optional, List, Dict

import gspread
import pandas as pd
import requests
import streamlit as st
from google.oauth2.service_account import Credentials

# ---------------------------
# Page Config (원본 설정 유지)
# ---------------------------
st.set_page_config(page_title="KREAM Ops Dashboard", layout="wide")

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
# helpers
# ---------------------------
def normalize_text(value) -> str:
    if pd.isna(value): return ""
    return str(value).strip()

def normalize_colname(value) -> str:
    return re.sub(r"\s+", " ", normalize_text(value))

def clean_excel_value(value):
    if isinstance(value, str): return ILLEGAL_EXCEL_CHARS_RE.sub("", value)
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

def uniquify_headers(headers: List[str]) -> List[str]:
    seen, out = {}, []
    for i, h in enumerate(headers):
        h = normalize_colname(h) or f"col_{i}"
        cnt = seen.get(h, 0)
        out.append(h if cnt == 0 else f"{h}__{cnt}")
        seen[h] = cnt + 1
    return out

def values_to_dataframe(values: List[List[str]]) -> pd.DataFrame:
    if not values: return pd.DataFrame()
    header_row = find_header_row(values)
    headers = uniquify_headers(values[header_row])
    rows = values[header_row + 1:]
    max_len = max(len(headers), *(len(r) for r in rows)) if rows else len(headers)
    headers = headers + [f"col_{i}" for i in range(len(headers), max_len)]
    padded_rows = [list(row) + [""] * (max_len - len(row)) for row in rows]
    df = pd.DataFrame(padded_rows, columns=headers)
    return df.loc[:, ~df.columns.duplicated()].dropna(how="all").reset_index(drop=True)

def find_column(df: pd.DataFrame, aliases: List[str]) -> Optional[str]:
    normalized_map = {normalize_colname(col).lower(): col for col in df.columns}
    for alias in aliases:
        a_norm = normalize_colname(alias).lower()
        if a_norm in normalized_map: return normalized_map[a_norm]
    for col in df.columns:
        c_norm = normalize_colname(col).lower()
        if any(normalize_colname(a).lower() in c_norm for a in aliases): return col
    return None

def count_people_from_column(df: pd.DataFrame, col: Optional[str], label_name: str) -> pd.DataFrame:
    if not col or col not in df.columns: return pd.DataFrame(columns=[label_name, "소속", "건수"])
    records = []
    for raw in df[col].fillna(""):
        for token in split_people(raw):
            records.append({label_name: token, "소속": person_group(token)})
    if not records: return pd.DataFrame(columns=[label_name, "소속", "건수"])
    return pd.DataFrame(records).groupby([label_name, "소속"], as_index=False).size().rename(columns={"size": "건수"}).sort_values(["건수", label_name], ascending=[False, True]).reset_index(drop=True)

def count_people_by_time(df: pd.DataFrame, col: Optional[str], label_name: str, period_choice: str) -> pd.DataFrame:
    if not col or col not in df.columns or df.empty or "date__registration_done" not in df.columns:
        return pd.DataFrame(columns=["기간", label_name, "건수"])
    tmp = df.dropna(subset=["date__registration_done"]).copy()
    iso = tmp["date__registration_done"].dt.isocalendar()
    tmp["기간_년"] = tmp["date__registration_done"].dt.year.astype(str)
    tmp["기간_월"] = tmp["date__registration_done"].dt.strftime("%Y-%m")
    tmp["기간_주"] = iso.year.astype(str) + "-W" + iso.week.astype(str).str.zfill(2)
    period_col = {"년": "기간_년", "월": "기간_월", "주": "기간_주"}[period_choice]
    records = []
    for _, row in tmp.iterrows():
        for token in split_people(row[col]):
            records.append({"기간": row[period_col], label_name: token, "건수": 1})
    if not records: return pd.DataFrame(columns=["기간", label_name, "건수"])
    return pd.DataFrame(records).groupby(["기간", label_name], as_index=False)["건수"].sum().sort_values(["기간", "건수"], ascending=[True, False]).reset_index(drop=True)

# ---------------------------
# Data Loading (BUG FIXED)
# ---------------------------
@st.cache_data(ttl=600)
def load_google_sheet_values(sheet_name: str, worksheet_name: Optional[str] = None) -> List[List[str]]:
    # invalid_scope 해결을 위해 명확한 Scope 추가
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(dict(st.secrets["gcp_service_account"]), scopes=scopes)
    client = gspread.authorize(creds)
    # 수정: opens -> open
    workbook = client.open(sheet_name)
    worksheet = workbook.worksheet(worksheet_name) if worksheet_name else workbook.sheet1
    return worksheet.get_all_values()

@st.cache_data(ttl=600)
def load_excel_values(file_bytes: bytes, sheet_name: Optional[str] = None) -> List[List[str]]:
    xls = pd.ExcelFile(io.BytesIO(file_bytes))
    target_sheet = sheet_name if sheet_name in xls.sheet_names else xls.sheet_names[0]
    raw = pd.read_excel(xls, sheet_name=target_sheet, header=None)
    return raw.fillna("").astype(object).values.tolist()

# ---------------------------
# Prepare (Original Logic)
# ---------------------------
def prepare_dataframe(values: List[List[str]]):
    df = values_to_dataframe(values)
    if df.empty: return df, {}, pd.DataFrame(), pd.DataFrame()

    colmap = {key: find_column(df, aliases) for key, aliases in COLUMN_ALIASES.items()}
    brand_col, requester_col, reviewer_col = colmap["brand"], colmap["requester"], colmap["reviewer"]

    if brand_col: df = df[df[brand_col].astype(str).str.strip() != ""].reset_index(drop=True)

    df["요청그룹"] = df[requester_col].apply(requester_group) if requester_col else "Famous"
    df["대표요청자"] = df[requester_col].apply(lambda x: split_people(x)[0] if split_people(x) else "미입력") if requester_col else "미입력"
    df["국내해외구분"] = df[colmap["country_type"]].apply(categorize_country) if colmap["country_type"] else "미입력"

    for k, alias_k in [("bool__listed", "listed"), ("bool__request_done", "request_done"), 
                       ("bool__purchase_requested", "purchase_requested"), ("bool__purchase_done", "purchase_done"), 
                       ("bool__registration_done_flag", "registration_done_flag")]:
        df[k] = df[colmap[alias_k]].map(parse_bool) if colmap[alias_k] else False

    df["date__registration_request"] = parse_date_series(df[colmap["registration_request_date"]]) if colmap["registration_request_date"] else pd.NaT
    df["date__registration_done"] = parse_date_series(df[colmap["registration_done_date"]]) if colmap["registration_done_date"] else pd.NaT
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

    combined_text = df[[c for c in [colmap["delay_reason"], colmap["issue_note"], colmap["issue_conclusion"], colmap["remark"]] if c]].astype(str).agg(' '.join, axis=1)
    df["지연분류"] = combined_text.apply(lambda x: category_from_text(x, DELAY_MAPPING))
    df["이슈분류"] = combined_text.apply(lambda x: category_from_text(x, ISSUE_MAPPING))
    df["신규기성"] = combined_text.apply(lambda x: "신규" if any(k in x.lower() for k in ["신생", "신규", "발굴"]) else "기성/기타")
    
    rem_col = colmap["remark"]
    df["등록제외사유"] = df.apply(lambda r: "등록 불가" if (rem_col and "등록 불가" in normalize_text(r[rem_col])) else "등록 완료일 없음" if pd.isna(r["date__registration_done"]) else "", axis=1)
    df["등록제외"] = df["등록제외사유"] != ""

    df["년도"] = df["date__registration_done"].dt.year.astype("Int64")
    df["월"] = df["date__registration_done"].dt.month.astype("Int64")
    df["주차"] = df["date__registration_done"].dt.isocalendar().week.astype("Int64")
    df["ISO년도"] = df["date__registration_done"].dt.isocalendar().year.astype("Int64")
    df["년월"] = df["date__registration_done"].dt.strftime("%Y-%m")
    df["년주차"] = df["ISO년도"].astype(str) + "-W" + df["주차"].astype(str).str.zfill(2)

    return df, colmap, count_people_from_column(df, requester_col, "요청자"), count_people_from_column(df, reviewer_col, "검토자")

def categorize_country(value: str) -> str:
    s = normalize_text(value).lower()
    return "국내" if "국내" in s else "해외" if "해외" in s else "미입력"

def build_kpis(df: pd.DataFrame) -> Dict[str, object]:
    total, done = len(df), int(df["bool__registration_done_flag"].sum()) if "bool__registration_done_flag" in df else 0
    lt = df["등록소요일"].dropna()
    
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
        "평균 리드타임": round(lt.mean(), 1) if not lt.empty else None,
        "이번주": w_cur, "전주": w_prev, "WoW": growth(w_cur, w_prev), "이번주라벨": w_lab, "전주라벨": (w_df.iloc[-2]["년주차"] if len(w_df) > 1 else "-"),
        "이번달": m_cur, "전월": m_prev, "MoM": growth(m_cur, m_prev), "이번달라벨": m_lab, "전월라벨": (m_df.iloc[-2]["년월"] if len(m_df) > 1 else "-"),
        "요청그룹표": df["요청그룹"].value_counts().reset_index(name="건수").rename(columns={"index": "요청그룹"}),
        "단계표": df["현재단계"].value_counts().reset_index(name="건수").rename(columns={"index": "단계"}),
        "국내해외비교표": df.groupby("국내해외구분").agg(브랜드수=("국내해외구분", "size"), 등록완료수=("bool__registration_done_flag", "sum")).reset_index(),
        "주간표": w_df, "월간표": m_df, "등록 제외 수": int(df["등록제외"].sum()),
        "SLA7일내 완료율": safe_rate(int((lt <= 7).sum()), len(lt))
    }

# ---------------------------
# UI Rendering (Full Restoration)
# ---------------------------
def render_summary(kpis, req_total, rev_total):
    st.markdown("### 통합 요약")
    m = st.columns(6)
    m[0].metric("총 브랜드", kpis["총 브랜드 수"])
    m[1].metric("등록 완료", kpis["등록 완료 수"])
    m[2].metric("성공률", f"{kpis['등록 성공률']}%")
    m[3].metric("평균 리드타임", f"{kpis['평균 리드타임'] or '-'}일")
    m[4].metric("등록 제외", kpis["등록 제외 수"])
    m[5].metric("SLA 7일 완료율", f"{kpis['SLA7일내 완료율']}%")

    l, r = st.columns(2)
    with l: 
        st.dataframe(kpis["요청그룹표"], hide_index=True, use_container_width=True)
        st.dataframe(kpis["단계표"], hide_index=True, use_container_width=True)
    with r:
        st.dataframe(req_total.head(15), hide_index=True, use_container_width=True)
        st.dataframe(rev_total.head(15), hide_index=True, use_container_width=True)

# ---------------------------
# MAIN
# ---------------------------
st.title("KREAM Ops Dashboard")

with st.sidebar:
    st.header("설정")
    source_type = st.radio("데이터 소스", ["Google Sheet", "Excel 업로드"])
    if source_type == "Google Sheet":
        s_name = st.text_input("구글 시트 이름", value="1P 상품등록 통합페이지")
        w_name = st.text_input("워크시트 이름", value="Summary")
        if st.button("데이터 불러오기", type="primary"):
            st.session_state["raw"] = load_google_sheet_values(s_name, w_name)
    else:
        uploaded = st.file_uploader("파일 업로드", type=["xlsx"])
        if uploaded and st.button("데이터 불러오기", type="primary"):
            st.session_state["raw"] = load_excel_values(uploaded.getvalue())

if "raw" in st.session_state:
    df_raw, meta, req_total, rev_total = prepare_dataframe(st.session_state["raw"])
    
    if not df_raw.empty:
        # 사이드바 필터 (이미지 기준 100% 복구)
        with st.sidebar:
            st.markdown("### 필터")
            sel_years = st.multiselect("년도", options=sorted(df_raw["년도"].dropna().unique().tolist()), default=sorted(df_raw["년도"].dropna().unique().tolist()))
            sel_groups = st.multiselect("조직 (요청그룹)", options=sorted(df_raw["요청그룹"].unique().tolist()), default=sorted(df_raw["요청그룹"].unique().tolist()))
            sel_country = st.multiselect("국내/해외", options=sorted(df_raw["국내해외구분"].unique().tolist()), default=sorted(df_raw["국내해외구분"].unique().tolist()))
            sel_stages = st.multiselect("현재 단계", options=sorted(df_raw["현재단계"].unique().tolist()), default=sorted(df_raw["현재단계"].unique().tolist()))
            
            req_col = meta["requester_col"]
            req_list = sorted(df_raw[req_col].dropna().unique().tolist()) if req_col else []
            sel_reqs = st.multiselect("요청자", options=req_list, default=req_list)
            
            rev_col = meta["reviewer_col"]
            rev_list = sorted(df_raw[rev_col].dropna().unique().tolist()) if rev_col else []
            sel_revs = st.multiselect("검토자", options=rev_list, default=rev_list)
            
            keyword = st.text_input("브랜드/비고 검색")
            include_ex = st.checkbox("등록 제외건 포함", value=False)
            period_choice = st.selectbox("추이 기준", ["주", "월", "년"])

        # 필터링 엔진
        f_df = df_raw[df_raw["년도"].isin(sel_years)].copy()
        f_df = f_df[f_df["요청그룹"].isin(sel_groups)]
        f_df = f_df[f_df["국내해외구분"].isin(sel_country)]
        f_df = f_df[f_df["현재단계"].isin(sel_stages)]
        if req_col: f_df = f_df[f_df[req_col].isin(sel_reqs)]
        if rev_col: f_df = f_df[f_df[rev_col].isin(sel_revs)]
        if not include_ex: f_df = f_df[~f_df["등록제외"]]
        if keyword:
            sc = [c for c in [meta["brand_col"], meta["remark_col"]] if c]
            f_df = f_df[f_df[sc].astype(str).apply(lambda x: x.str.contains(keyword, case=False)).any(axis=1)]

        kpis = build_kpis(f_df)
        render_summary(kpis, req_total, rev_total)

        # 차트 레이아웃
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 단계별 현황")
            st.bar_chart(f_df["현재단계"].value_counts())
        with c2:
            st.markdown("#### 조직별 현황")
            st.bar_chart(f_df["요청그룹"].value_counts())

        st.markdown("#### 상세 데이터")
        st.dataframe(f_df.sort_values("등록소요일", ascending=False), use_container_width=True)
