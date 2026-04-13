import io
import re
from typing import Optional, List, Dict

import gspread
import pandas as pd
import requests
import streamlit as st
from google.oauth2.service_account import Credentials

# ---------------------------
# 1. Configuration & Constants
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
# 2. Data Loading Functions
# ---------------------------
@st.cache_data(ttl=600)
def load_google_sheet_values(sheet_name: str, worksheet_name: Optional[str] = None) -> List[List[str]]:
    """구글 시트에서 데이터를 로드 (오타 수정 완료: opens -> open)"""
    try:
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]),
            scopes=[
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
        )
        client = gspread.authorize(creds)
        
        # 수정됨: client.opens -> client.open
        workbook = client.open(sheet_name)
        worksheet = workbook.worksheet(worksheet_name) if worksheet_name else workbook.sheet1
        return worksheet.get_all_values()
    except Exception as e:
        st.error(f"구글 시트를 불러오는 중 에러 발생: {e}")
        return []

@st.cache_data(ttl=600)
def load_excel_values(file_bytes: bytes, sheet_name: Optional[str] = None) -> List[List[str]]:
    xls = pd.ExcelFile(io.BytesIO(file_bytes))
    target_sheet = sheet_name if sheet_name in xls.sheet_names else xls.sheet_names[0]
    raw = pd.read_excel(io.BytesIO(file_bytes), sheet_name=target_sheet, header=None)
    return raw.fillna("").astype(object).values.tolist()

# ---------------------------
# 3. Helper Functions
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
    if t.upper() == "3P" or re.fullmatch(r"[가-힣]+", t):
        return "Famous"
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
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v) != 0
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
        if any(k in t for k in keywords):
            return category
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
        alias_norm = normalize_colname(alias).lower()
        if alias_norm in normalized_map: return normalized_map[alias_norm]
    lowered = [normalize_colname(a).lower() for a in aliases]
    for col in df.columns:
        col_norm = normalize_colname(col).lower()
        if any(a in col_norm for a in lowered): return col
    return None

def count_people_from_column(df: pd.DataFrame, col: Optional[str], label_name: str) -> pd.DataFrame:
    if not col or col not in df.columns: return pd.DataFrame(columns=[label_name, "소속", "건수"])
    records = [{"label": t, "소속": person_group(t)} for raw in df[col].fillna("") for t in split_people(raw)]
    if not records: return pd.DataFrame(columns=[label_name, "소속", "건수"])
    return pd.DataFrame(records).rename(columns={"label": label_name}).groupby([label_name, "소속"]).size().reset_index(name="건수").sort_values("건수", ascending=False)

def count_people_by_time(df: pd.DataFrame, col: Optional[str], label_name: str, period_choice: str) -> pd.DataFrame:
    if not col or col not in df.columns or df.empty or "date__registration_done" not in df.columns:
        return pd.DataFrame(columns=["기간", label_name, "건수"])
    tmp = df.dropna(subset=["date__registration_done"]).copy()
    iso = tmp["date__registration_done"].dt.isocalendar()
    period_map = {
        "년": tmp["date__registration_done"].dt.year.astype(str),
        "월": tmp["date__registration_done"].dt.strftime("%Y-%m"),
        "주": iso.year.astype(str) + "-W" + iso.week.astype(str).str.zfill(2)
    }
    tmp["기간"] = period_map[period_choice]
    records = [{"기간": row["기간"], "name": t} for _, row in tmp.iterrows() for t in split_people(row[col])]
    if not records: return pd.DataFrame(columns=["기간", label_name, "건수"])
    return pd.DataFrame(records).rename(columns={"name": label_name}).groupby(["기간", label_name]).size().reset_index(name="건수").sort_values(["기간", "건수"], ascending=[True, False])

def dataframe_to_excel_bytes(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        clean_dataframe_for_excel(df).to_excel(writer, index=False, sheet_name="filtered_data")
    return output.getvalue()

def build_slack_text(kpis: Dict[str, object]) -> str:
    return (f"📊 업무 운영 리포트\n- 총 브랜드 수: {kpis['총 브랜드 수']}\n- 등록 완료 수: {kpis['등록 완료 수']}\n"
            f"- 등록 성공률: {kpis['등록 성공률']}%\n- 평균 리드타임: {kpis['평균 리드타임'] or '-'}일\n"
            f"- WoW: {kpis['WoW']}%\n- MoM: {kpis['MoM']}%")

def send_to_slack(webhook_url: str, text: str):
    try:
        resp = requests.post(webhook_url, json={"text": text}, timeout=15)
        resp.raise_for_status()
        return True, "ok"
    except Exception as e:
        return False, str(e)

def categorize_country(value: str) -> str:
    s = normalize_text(value).lower()
    if not s: return "미입력"
    if "국내" in s: return "국내"
    if "해외" in s: return "해외"
    return s

# ---------------------------
# 4. Core Logic (Prepare & KPI)
# ---------------------------
def prepare_dataframe(values: List[List[str]]):
    df = values_to_dataframe(values)
    if df.empty: return df, {}, pd.DataFrame(), pd.DataFrame()

    colmap = {key: find_column(df, aliases) for key, aliases in COLUMN_ALIASES.items()}
    brand_col = colmap["brand"]
    if brand_col: df = df[df[brand_col].astype(str).str.strip() != ""].reset_index(drop=True)

    # 기본 파생 변수 생성
    req_col = colmap["requester"]
    df["요청그룹"] = df[req_col].apply(requester_group) if req_col else "Famous"
    df["대표요청자"] = df[req_col].apply(lambda x: split_people(x)[0] if split_people(x) else "미입력") if req_col else "미입력"
    df["국내해외구분"] = df[colmap["country_type"]].apply(categorize_country) if colmap["country_type"] else "미입력"

    # 불리언 변환
    bool_keys = [("bool__listed", "listed"), ("bool__request_done", "request_done"), 
                 ("bool__purchase_requested", "purchase_requested"), ("bool__purchase_done", "purchase_done"), 
                 ("bool__registration_done_flag", "registration_done_flag")]
    for key, alias in bool_keys:
        df[key] = df[colmap[alias]].map(parse_bool) if colmap[alias] else False

    # 날짜 및 리드타임
    df["date__registration_request"] = parse_date_series(df[colmap["registration_request_date"]]) if colmap["registration_request_date"] else pd.NaT
    df["date__registration_done"] = parse_date_series(df[colmap["registration_done_date"]]) if colmap["registration_done_date"] else pd.NaT
    df["등록소요일"] = (df["date__registration_done"] - df["date__registration_request"]).dt.days.clip(0, 365)

    # 단계/분류 로직
    df["현재단계"] = df.apply(lambda r: "등록 완료" if r["bool__registration_done_flag"] else "구매 완료" if r["bool__purchase_done"] else "구매 요청" if r["bool__purchase_requested"] else "등록 요청 완료" if r["bool__request_done"] else "리스트업 완료" if r["bool__listed"] else "미진행", axis=1)
    
    combined_text = df[[c for c in [colmap["delay_reason"], colmap["issue_note"], colmap["issue_conclusion"], colmap["remark"]] if c]].astype(str).agg(' '.join, axis=1)
    df["지연분류"] = combined_text.apply(lambda x: category_from_text(x, DELAY_MAPPING))
    df["이슈분류"] = combined_text.apply(lambda x: category_from_text(x, ISSUE_MAPPING))
    df["신규기성"] = combined_text.apply(lambda x: "신규" if any(k in x.lower() for k in ["신생", "신규", "new brand", "발굴"]) else "기성/기타")

    # 제외 사유
    rem_col = colmap["remark"]
    df["등록제외"] = df.apply(lambda r: ("등록 불가" in normalize_text(r[rem_col]) if rem_col else False) or pd.isna(r["date__registration_done"]), axis=1)

    # 시간 차원
    df["년도"] = df["date__registration_done"].dt.year.astype("Int64")
    df["월"] = df["date__registration_done"].dt.month.astype("Int64")
    df["주차"] = df["date__registration_done"].dt.isocalendar().week.astype("Int64")
    df["ISO년도"] = df["date__registration_done"].dt.isocalendar().year.astype("Int64")
    df["년월"] = df["date__registration_done"].dt.strftime("%Y-%m")
    df["년주차"] = df["ISO년도"].astype(str) + "-W" + df["주차"].astype(str).str.zfill(2)

    return df, colmap, count_people_from_column(df, req_col, "요청자"), count_people_from_column(df, colmap["reviewer"], "검토자")

def build_kpis(df: pd.DataFrame) -> Dict[str, object]:
    total = len(df)
    done = int(df["bool__registration_done_flag"].sum()) if "bool__registration_done_flag" in df else 0
    lt = df["등록소요일"].dropna()
    
    def get_periodic_stats(df, group_cols, label_col):
        if df.empty: return pd.DataFrame(), "-", 0
        grouped = df.groupby(group_cols + [label_col]).size().reset_index(name="건수").sort_values(group_cols)
        return grouped, grouped.iloc[-1][label_col] if not grouped.empty else "-", int(grouped.iloc[-1]["건수"]) if not grouped.empty else 0

    weekly_df, w_lab, w_cur = get_periodic_stats(df.dropna(subset=["ISO년도", "주차"]), ["ISO년도", "주차"], "년주차")
    monthly_df, m_lab, m_cur = get_periodic_stats(df.dropna(subset=["년도", "월"]), ["년도", "월"], "년월")
    
    w_prev = int(weekly_df.iloc[-2]["건수"]) if len(weekly_df) > 1 else 0
    m_prev = int(monthly_df.iloc[-2]["건수"]) if len(monthly_df) > 1 else 0

    return {
        "총 브랜드 수": total, "등록 완료 수": done, "등록 성공률": safe_rate(done, total),
        "평균 리드타임": round(lt.mean(), 1) if not lt.empty else None,
        "이번주": w_cur, "WoW": growth(w_cur, w_prev), "이번주라벨": w_lab, "전주라벨": (weekly_df.iloc[-2]["년주차"] if len(weekly_df) > 1 else "-"),
        "이번달": m_cur, "MoM": growth(m_cur, m_prev), "이번달라벨": m_lab, "전월라벨": (monthly_df.iloc[-2]["년월"] if len(monthly_df) > 1 else "-"),
        "요청그룹표": df["요청그룹"].value_counts().reset_index(name="건수"),
        "단계표": df["현재단계"].value_counts().reset_index(name="건수"),
        "주간표": weekly_df, "월간표": monthly_df, "등록 제외 수": int(df["등록제외"].sum()) if "등록제외" in df else 0,
        "SLA7일내 완료율": safe_rate(int((lt <= 7).sum()), len(lt)) if not lt.empty else 0.0,
        "국내해외비교표": df.groupby("국내해외구분").agg(브랜드수=("브랜드수" if False else "국내해외구분", "size"), 등록완료수=("bool__registration_done_flag", "sum")).reset_index()
    }

# ---------------------------
# 5. Rendering Functions
# ---------------------------
def render_integrated_summary(total_kpis, req_total, rev_total):
    st.markdown("### 통합 요약 (전체 브랜드 기준)")
    m1, m2, m3, m4, m5, m6 = st.columns(6)
    m1.metric("총 브랜드 수", total_kpis["총 브랜드 수"])
    m2.metric("등록 완료 수", total_kpis["등록 완료 수"])
    m3.metric("등록 성공률", f"{total_kpis['등록 성공률']}%")
    m4.metric("평균 리드타임", f"{total_kpis['평균 리드타임'] or '-'}일")
    m5.metric("등록 제외 수", total_kpis["등록 제외 수"])
    m6.metric("SLA 7일 완료율", f"{total_kpis['SLA7일내 완료율']}%")

def render_filtered_section(filtered_df, filtered_kpis, req_f, rev_f, req_t, rev_t, delayed_df, meta, period_choice):
    st.markdown("---")
    st.markdown(f"### 필터 적용 결과 ({len(filtered_df)}건)")
    
    c1, c2, c3 = st.columns(3)
    c1.metric(f"주간 ({filtered_kpis['이번주라벨']})", filtered_kpis["이번주"], f"{filtered_kpis['WoW']}%")
    c2.metric(f"월간 ({filtered_kpis['이번달라벨']})", filtered_kpis["이번달"], f"{filtered_kpis['MoM']}%")
    c3.metric("필터 내 성공률", f"{filtered_kpis['등록 성공률']}%")

    col_a, col_b = st.columns(2)
    with col_a:
        st.markdown("#### 요청자/검토자 건수")
        st.dataframe(req_f.head(10), use_container_width=True, hide_index=True)
        st.bar_chart(filtered_kpis["단계표"].set_index("현재단계")["건수"])
    with col_b:
        st.markdown(f"#### {period_choice}별 추이")
        if not req_t.empty:
            pivot = req_t.pivot_table(index="기간", columns="요청자", values="건수", aggfunc="sum").fillna(0)
            st.line_chart(pivot)

    st.markdown("#### 상세 데이터 (리드타임 순)")
    disp_cols = [c for c in [meta.get("brand"), "대표요청자", "등록소요일", "현재단계", "지연분류"] if c in delayed_df.columns or c in ["대표요청자", "등록소요일", "현재단계", "지연분류"]]
    st.dataframe(delayed_df[disp_cols].sort_values("등록소요일", ascending=False), use_container_width=True, hide_index=True)

# ---------------------------
# 6. Main Execution
# ---------------------------
st.set_page_config(page_title="KREAM Ops Dashboard", layout="wide")
st.title("📊 KREAM Ops Dashboard")

with st.sidebar:
    source_type = st.radio("데이터 소스", ["Google Sheet", "Excel 업로드"])
    if source_type == "Google Sheet":
        sheet_name = st.text_input("구글 시트 이름", value="")
        worksheet_name = st.text_input("워크시트 이름", value="Summary")
        if st.button("데이터 불러오기", type="primary"):
            st.session_state["sheet_values"] = load_google_sheet_values(sheet_name, worksheet_name)
    else:
        uploaded = st.file_uploader("엑셀 파일", type=["xlsx"])
        if uploaded and st.button("데이터 불러오기", type="primary"):
            st.session_state["sheet_values"] = load_excel_values(uploaded.getvalue())

if "sheet_values" in st.session_state and st.session_state["sheet_values"]:
    df_raw, meta, req_total, rev_total = prepare_dataframe(st.session_state["sheet_values"])
    
    if not df_raw.empty:
        total_kpis = build_kpis(df_raw)
        render_integrated_summary(total_kpis, req_total, rev_total)

        # 사이드바 필터 로직
        with st.sidebar:
            st.markdown("### 필터링 설정")
            sel_years = st.multiselect("년도", options=sorted(df_raw["년도"].dropna().unique().tolist()), default=sorted(df_raw["년도"].dropna().unique().tolist()))
            include_ex = st.checkbox("등록 제외 브랜드 포함", value=False)
            period_choice = st.selectbox("추이 기준", ["주", "월", "년"])
            keyword = st.text_input("키워드 검색 (브랜드명 등)")

        # 필터 적용
        f_df = df_raw[df_raw["년도"].isin(sel_years)].copy()
        if not include_ex: f_df = f_df[~f_df["등록제외"]]
        if keyword: f_df = f_df[f_df[meta["brand"]].astype(str).str.contains(keyword, case=False, na=False)]
        
        f_kpis = build_kpis(f_df)
        req_f = count_people_from_column(f_df, meta["requester"], "요청자")
        rev_f = count_people_from_column(f_df, meta["reviewer"], "검토자")
        req_t = count_people_by_time(f_df, meta["requester"], "요청자", period_choice)
        rev_t = count_people_by_time(f_df, meta["reviewer"], "검토자", period_choice)

        render_filtered_section(f_df, f_kpis, req_f, rev_f, req_t, rev_t, f_df, meta, period_choice)

        # 하단 내보내기
        st.markdown("---")
        if st.button("Slack으로 요약 전송"):
            webhook = st.secrets.get("slack_webhook_url", "")
            if webhook:
                ok, msg = send_to_slack(webhook, build_slack_text(f_kpis))
                st.success("전송 성공") if ok else st.error(f"실패: {msg}")
            else:
                st.warning("Secrets에 slack_webhook_url이 설정되지 않았습니다.")
else:
    st.info("사이드바에서 데이터를 먼저 불러와주세요.")
