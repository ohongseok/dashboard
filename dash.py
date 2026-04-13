import io
import re
from typing import Optional, List, Dict

import gspread
import pandas as pd
import requests
import streamlit as st
from google.oauth2.service_account import Credentials
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
    if pd.isna(value):
        return ""
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
    if not text:
        return []
    return [t.strip() for t in re.split(r"[,/|·\n]+", text) if t.strip()]

def person_group(token: str) -> str:
    t = re.sub(r"[\s\-\.\(\)]+", "", normalize_text(token))
    if not t:
        return "Famous"
    if t.upper() == "3P":
        return "Famous"
    if re.fullmatch(r"[가-힣]+", t):
        return "Famous"
    if re.fullmatch(r"[A-Za-z]+", t):
        return "KREAM"
    return "KREAM"

def requester_group(raw: str) -> str:
    tokens = split_people(raw)
    if not tokens:
        return "Famous"
    groups = {person_group(t) for t in tokens}
    if groups == {"KREAM"}:
        return "KREAM"
    if groups == {"Famous"}:
        return "Famous"
    return "Mixed"

def parse_bool(v) -> bool:
    if pd.isna(v):
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        if pd.isna(v):
            return False
        return float(v) != 0
    s = str(v).strip().lower()
    if s in TRUE_VALUES:
        return True
    if s in FALSE_VALUES:
        return False
    return False

def parse_date_series(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce")
    if parsed.notna().mean() >= 0.3:
        return parsed
    parsed = pd.to_datetime(series, errors="coerce", format="%y.%m.%d")
    return parsed

def category_from_text(text: str, mapping: Dict[str, List[str]], default: str = "기타") -> str:
    t = normalize_text(text).lower()
    if not t or t == "-":
        return "없음"
    for category, keywords in mapping.items():
        if any(k in t for k in keywords):
            return category
    return default

def safe_rate(num: int, den: int) -> float:
    return round((num / den) * 100, 1) if den else 0.0

def growth(cur: int, prev: int) -> float:
    if prev == 0:
        return 0.0
    return round(((cur - prev) / prev) * 100, 1)

def style_table(df: pd.DataFrame):
    if df.empty:
        return df
    try:
        return df.style.format(precision=1, na_rep="-").set_properties(**{"text-align": "center"})
    except Exception:
        return df

def find_header_row(values: List[List[str]]) -> int:
    best_idx = 0
    best_score = -1
    for idx, row in enumerate(values[:10]):
        cleaned = [normalize_colname(c) for c in row]
        if not any(cleaned):
            continue
        score = 0
        for cell in cleaned:
            for kw in HEADER_KEYWORDS:
                if kw in cell:
                    score += 2
            if cell:
                score += 0.05
        if score > best_score:
            best_score = score
            best_idx = idx
    return best_idx

def uniquify_headers(headers: List[str]) -> List[str]:
    seen = {}
    out = []
    for i, h in enumerate(headers):
        h = normalize_colname(h) or f"col_{i}"
        cnt = seen.get(h, 0)
        out.append(h if cnt == 0 else f"{h}__{cnt}")
        seen[h] = cnt + 1
    return out

def values_to_dataframe(values: List[List[str]]) -> pd.DataFrame:
    if not values:
        return pd.DataFrame()
    header_row = find_header_row(values)
    headers = uniquify_headers(values[header_row])
    rows = values[header_row + 1:]
    max_len = max(len(headers), *(len(r) for r in rows)) if rows else len(headers)
    headers = headers + [f"col_{i}" for i in range(len(headers), max_len)]
    padded_rows = []
    for row in rows:
        row = list(row) + [""] * (max_len - len(row))
        padded_rows.append(row[:max_len])
    df = pd.DataFrame(padded_rows, columns=headers)
    df = df.loc[:, ~df.columns.duplicated()].copy()
    df = df.dropna(how="all").reset_index(drop=True)
    return df

def find_column(df: pd.DataFrame, aliases: List[str]) -> Optional[str]:
    normalized_map = {normalize_colname(col).lower(): col for col in df.columns}
    for alias in aliases:
        alias_norm = normalize_colname(alias).lower()
        if alias_norm in normalized_map:
            return normalized_map[alias_norm]
    lowered = [normalize_colname(a).lower() for a in aliases]
    for col in df.columns:
        col_norm = normalize_colname(col).lower()
        if any(a in col_norm for a in lowered):
            return col
    return None

def count_people_from_column(df: pd.DataFrame, col: Optional[str], label_name: str) -> pd.DataFrame:
    if not col or col not in df.columns:
        return pd.DataFrame(columns=[label_name, "소속", "건수"])
    records = []
    for raw in df[col].fillna(""):
        tokens = split_people(raw)
        for token in tokens:
            records.append({label_name: token, "소속": person_group(token)})
    if not records:
        return pd.DataFrame(columns=[label_name, "소속", "건수"])
    people = pd.DataFrame(records)
    out = (
        people.groupby([label_name, "소속"], as_index=False)
        .size()
        .rename(columns={"size": "건수"})
        .sort_values(["건수", label_name], ascending=[False, True])
        .reset_index(drop=True)
    )
    return out

def count_people_by_time(df: pd.DataFrame, col: Optional[str], label_name: str, period_choice: str) -> pd.DataFrame:
    if not col or col not in df.columns or df.empty or "date__registration_done" not in df.columns:
        return pd.DataFrame(columns=["기간", label_name, "건수"])
    tmp = df.dropna(subset=["date__registration_done"]).copy()
    if tmp.empty:
        return pd.DataFrame(columns=["기간", label_name, "건수"])
    iso = tmp["date__registration_done"].dt.isocalendar()
    tmp["기간_년"] = tmp["date__registration_done"].dt.year.astype(int).astype(str)
    tmp["기간_월"] = tmp["date__registration_done"].dt.strftime("%Y-%m")
    tmp["기간_주"] = iso.year.astype(int).astype(str) + "-W" + iso.week.astype(int).astype(str).str.zfill(2)
    period_col = {"년": "기간_년", "월": "기간_월", "주": "기간_주"}[period_choice]

    records = []
    for _, row in tmp[[col, period_col]].iterrows():
        tokens = split_people(row[col])
        for token in tokens:
            records.append({"기간": row[period_col], label_name: token, "건수": 1})
    if not records:
        return pd.DataFrame(columns=["기간", label_name, "건수"])
    out = (
        pd.DataFrame(records)
        .groupby(["기간", label_name], as_index=False)["건수"]
        .sum()
        .sort_values(["기간", "건수"], ascending=[True, False])
        .reset_index(drop=True)
    )
    return out

def dataframe_to_excel_bytes(df: pd.DataFrame) -> bytes:
    output = io.BytesIO()
    safe_df = clean_dataframe_for_excel(df)
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        safe_df.to_excel(writer, index=False, sheet_name="filtered_data")
    return output.getvalue()

def build_slack_text(kpis: Dict[str, object]) -> str:
    lines = [
        "📊 업무 운영 리포트",
        f"- 총 브랜드 수: {kpis['총 브랜드 수']}",
        f"- 등록 완료 수: {kpis['등록 완료 수']}",
        f"- 등록 성공률: {kpis['등록 성공률']}%",
        f"- 평균 리드타임: {'-' if kpis['평균 리드타임'] is None else str(kpis['평균 리드타임']) + '일'}",
        f"- 중앙 리드타임: {'-' if kpis['중앙 리드타임'] is None else str(kpis['중앙 리드타임']) + '일'}",
        f"- 주간 증감: {kpis['이번주라벨']} {kpis['이번주']}건 vs {kpis['전주라벨']} {kpis['전주']}건 ({kpis['WoW']}%)",
        f"- 월간 증감: {kpis['이번달라벨']} {kpis['이번달']}건 vs {kpis['전월라벨']} {kpis['전월']}건 ({kpis['MoM']}%)",
    ]
    return "\n".join(lines)

def send_to_slack(webhook_url: str, text: str):
    try:
        resp = requests.post(webhook_url, json={"text": text}, timeout=15)
        resp.raise_for_status()
        return True, "ok"
    except Exception as e:
        return False, str(e)

# ---------------------------
# data loading
# ---------------------------
@st.cache_data(ttl=600)
def load_google_sheet_values(sheet_name: str, worksheet_name: Optional[str] = None) -> List[List[str]]:
    creds = Credentials.from_service_account_info(
        dict(st.secrets["gcp_service_account"])
    )
    client = gspread.authorize(creds)
    workbook = client.open(sheet_name)
    worksheet = workbook.worksheet(worksheet_name) if worksheet_name else workbook.sheet1
    return worksheet.get_all_values()

@st.cache_data(ttl=600)
def load_excel_values(file_bytes: bytes, sheet_name: Optional[str] = None) -> List[List[str]]:
    xls = pd.ExcelFile(io.BytesIO(file_bytes))
    target_sheet = sheet_name if sheet_name in xls.sheet_names else xls.sheet_names[0]
    raw = pd.read_excel(io.BytesIO(file_bytes), sheet_name=target_sheet, header=None)
    return raw.fillna("").astype(object).values.tolist()

# ---------------------------
# prepare
# ---------------------------
def prepare_dataframe(values: List[List[str]]):
    df = values_to_dataframe(values)
    if df.empty:
        return df, {}, pd.DataFrame(), pd.DataFrame()

    colmap = {key: find_column(df, aliases) for key, aliases in COLUMN_ALIASES.items()}

    brand_col = colmap["brand"]
    requester_col = colmap["requester"]
    reviewer_col = colmap["reviewer"]
    country_col = colmap["country_type"]
    delay_col = colmap["delay_reason"]
    issue_col = colmap["issue_note"]
    issue_conclusion_col = colmap["issue_conclusion"]
    remark_col = colmap["remark"]

    if brand_col:
        df = df[df[brand_col].astype(str).str.strip() != ""].reset_index(drop=True)

    if requester_col:
        df["요청그룹"] = df[requester_col].apply(requester_group)
        df["대표요청자"] = df[requester_col].apply(lambda x: split_people(x)[0] if split_people(x) else "미입력")
    else:
        df["요청그룹"] = "Famous"
        df["대표요청자"] = "미입력"

    if country_col:
        df["국내해외구분"] = df[country_col].apply(categorize_country)
    else:
        df["국내해외구분"] = "미입력"

    for key, col_alias_key in [
        ("bool__listed", "listed"),
        ("bool__request_done", "request_done"),
        ("bool__purchase_requested", "purchase_requested"),
        ("bool__purchase_done", "purchase_done"),
        ("bool__registration_done_flag", "registration_done_flag"),
    ]:
        col = colmap[col_alias_key]
        if col:
            df[key] = df[col].map(parse_bool)
        else:
            df[key] = False

    reg_req_col = colmap["registration_request_date"]
    reg_done_col = colmap["registration_done_date"]
    df["date__registration_request"] = parse_date_series(df[reg_req_col]) if reg_req_col else pd.NaT
    df["date__registration_done"] = parse_date_series(df[reg_done_col]) if reg_done_col else pd.NaT

    leadtime = (df["date__registration_done"] - df["date__registration_request"]).dt.days
    leadtime = leadtime.where((leadtime >= 0) & (leadtime <= 365))
    df["등록소요일"] = leadtime

    reg_week_col = colmap["registration_week"]
    if reg_week_col:
        df["등록주차계산"] = pd.to_numeric(df[reg_week_col], errors="coerce")
    else:
        df["등록주차계산"] = df["date__registration_done"].dt.isocalendar().week.astype("Float64")

    def stage_label(row):
        if row["bool__registration_done_flag"]:
            return "등록 완료"
        if row["bool__purchase_done"]:
            return "구매 완료"
        if row["bool__purchase_requested"]:
            return "구매 요청"
        if row["bool__request_done"]:
            return "등록 요청 완료"
        if row["bool__listed"]:
            return "리스트업 완료"
        return "미진행"

    df["현재단계"] = df.apply(stage_label, axis=1)

    combined_text = pd.Series([""] * len(df), index=df.index)
    for col in [delay_col, issue_col, issue_conclusion_col, remark_col]:
        if col:
            combined_text = combined_text + " " + df[col].astype(str)

    df["지연분류"] = combined_text.apply(lambda x: category_from_text(x, DELAY_MAPPING))
    df["이슈분류"] = combined_text.apply(lambda x: category_from_text(x, ISSUE_MAPPING))

    def classify_newness(text):
        t = normalize_text(text).lower()
        if not t or t == "-":
            return "미분류"
        if any(k in t for k in ["신생", "신규", "new brand", "발굴", "첫 진행"]):
            return "신규"
        return "기성/기타"

    df["신규기성"] = combined_text.apply(classify_newness)

    def exception_reason(row):
        remark_val = normalize_text(row[remark_col]) if remark_col else ""
        if "등록 불가" in remark_val:
            return "등록 불가"
        if pd.isna(row["date__registration_done"]):
            return "등록 완료일 없음"
        return ""

    df["등록제외사유"] = df.apply(exception_reason, axis=1)
    df["등록제외"] = df["등록제외사유"] != ""

    done_iso = df["date__registration_done"].dt.isocalendar()
    df["년도"] = df["date__registration_done"].dt.year.astype("Int64")
    df["월"] = df["date__registration_done"].dt.month.astype("Int64")
    df["주차"] = done_iso.week.astype("Int64")
    df["ISO년도"] = done_iso.year.astype("Int64")
    df["년월"] = df["date__registration_done"].dt.strftime("%Y-%m")
    df["년주차"] = df["ISO년도"].astype(str) + "-W" + df["주차"].astype(str).str.zfill(2)

    requester_people = count_people_from_column(df, requester_col, "요청자")
    reviewer_people = count_people_from_column(df, reviewer_col, "검토자")

    meta = {
        "brand_col": brand_col,
        "requester_col": requester_col,
        "reviewer_col": reviewer_col,
        "delay_col": delay_col,
        "issue_col": issue_col,
        "remark_col": remark_col,
        "reg_req_col": reg_req_col,
        "reg_done_col": reg_done_col,
    }
    return df, meta, requester_people, reviewer_people

def categorize_country(value: str) -> str:
    s = normalize_text(value).lower()
    if not s:
        return "미입력"
    if "국내" in s:
        return "국내"
    if "해외" in s:
        return "해외"
    return s

# ---------------------------
# KPI
# ---------------------------
def build_kpis(df: pd.DataFrame) -> Dict[str, object]:
    total = len(df)
    listed = int(df["bool__listed"].sum()) if "bool__listed" in df else 0
    request_done = int(df["bool__request_done"].sum()) if "bool__request_done" in df else 0
    purchase_done = int(df["bool__purchase_done"].sum()) if "bool__purchase_done" in df else 0
    registration_done = int(df["bool__registration_done_flag"].sum()) if "bool__registration_done_flag" in df else 0
    exceptions = int(df["등록제외"].sum()) if "등록제외" in df else 0

    lead_valid = df["등록소요일"].dropna()
    avg_lt = round(lead_valid.mean(), 1) if not lead_valid.empty else None
    med_lt = round(lead_valid.median(), 1) if not lead_valid.empty else None
    p90_lt = round(lead_valid.quantile(0.9), 1) if not lead_valid.empty else None
    sla7 = safe_rate(int((lead_valid <= 7).sum()), int(lead_valid.shape[0])) if not lead_valid.empty else 0.0

    weekly = (
        df.dropna(subset=["ISO년도", "주차"])
        .groupby(["ISO년도", "주차", "년주차"], as_index=False)
        .size()
        .rename(columns={"size": "건수"})
        .sort_values(["ISO년도", "주차"])
        .reset_index(drop=True)
    )
    monthly = (
        df.dropna(subset=["년도", "월"])
        .groupby(["년도", "월", "년월"], as_index=False)
        .size()
        .rename(columns={"size": "건수"})
        .sort_values(["년도", "월"])
        .reset_index(drop=True)
    )

    if weekly.empty:
        week_label = prev_week_label = "-"
        cur_week = prev_week = 0
    else:
        cur_week = int(weekly.iloc[-1]["건수"])
        week_label = weekly.iloc[-1]["년주차"]
        if len(weekly) > 1:
            prev_week = int(weekly.iloc[-2]["건수"])
            prev_week_label = weekly.iloc[-2]["년주차"]
        else:
            prev_week = 0
            prev_week_label = "-"

    if monthly.empty:
        month_label = prev_month_label = "-"
        cur_month = prev_month = 0
    else:
        cur_month = int(monthly.iloc[-1]["건수"])
        month_label = monthly.iloc[-1]["년월"]
        if len(monthly) > 1:
            prev_month = int(monthly.iloc[-2]["건수"])
            prev_month_label = monthly.iloc[-2]["년월"]
        else:
            prev_month = 0
            prev_month_label = "-"

    compare = (
        df.groupby("국내해외구분", as_index=False)
        .agg(
            브랜드수=("국내해외구분", "size"),
            등록완료수=("bool__registration_done_flag", "sum"),
            평균등록소요일=("등록소요일", "mean"),
            중앙등록소요일=("등록소요일", "median"),
        )
    )
    if not compare.empty:
        compare["등록성공률(%)"] = compare.apply(lambda r: safe_rate(int(r["등록완료수"]), int(r["브랜드수"])), axis=1)
        compare["평균등록소요일"] = compare["평균등록소요일"].round(1)
        compare["중앙등록소요일"] = compare["중앙등록소요일"].round(1)

    requester_group_table = (
        df["요청그룹"].value_counts()
        .rename_axis("요청그룹")
        .reset_index(name="건수")
    )

    stage_table = (
        df["현재단계"].value_counts()
        .rename_axis("단계")
        .reset_index(name="건수")
    )

    return {
        "총 브랜드 수": total,
        "리스트업 완료 수": listed,
        "등록 요청 완료 수": request_done,
        "구매 완료 수": purchase_done,
        "등록 완료 수": registration_done,
        "등록 제외 수": exceptions,
        "등록 성공률": safe_rate(registration_done, total),
        "평균 리드타임": avg_lt,
        "중앙 리드타임": med_lt,
        "P90 리드타임": p90_lt,
        "SLA7일내 완료율": sla7,
        "이번주": cur_week,
        "전주": prev_week,
        "WoW": growth(cur_week, prev_week),
        "이번달": cur_month,
        "전월": prev_month,
        "MoM": growth(cur_month, prev_month),
        "이번주라벨": week_label,
        "전주라벨": prev_week_label,
        "이번달라벨": month_label,
        "전월라벨": prev_month_label,
        "국내해외비교표": compare,
        "요청그룹표": requester_group_table,
        "단계표": stage_table,
        "주간표": weekly,
        "월간표": monthly,
    }

# ---------------------------
# filtering
# ---------------------------
def integrated_window(df: pd.DataFrame) -> pd.DataFrame:
    # 전체 통합 요약은 실제 브랜드 전체를 유지
    # 2023년 이전 브랜드가 있더라도, 날짜 컬럼이 비어 있는 케이스를 떨어뜨리지 않음
    return df.copy()

def filtered_window(df: pd.DataFrame, years, months, weeks, include_exceptions: bool) -> pd.DataFrame:
    out = df.copy()
    out = out[out["date__registration_done"].notna()].copy()
    out = out[out["년도"].ge(2025).fillna(False)].copy()
    if years:
        out = out[out["년도"].isin(years)]
    if months:
        out = out[out["월"].isin(months)]
    if weeks:
        out = out[out["주차"].isin(weeks)]
    if not include_exceptions and "등록제외" in out.columns:
        out = out[~out["등록제외"]].copy()
    return out

# ---------------------------
# render
# ---------------------------
def render_integrated_summary(total_df, total_kpis, requester_people_total, reviewer_people_total):
    st.markdown("### 통합 요약 (2023년~현재 전체 브랜드 기준)")
    cols = st.columns(6)
    cols[0].metric("총 브랜드 수", total_kpis["총 브랜드 수"])
    cols[1].metric("등록 완료 수", total_kpis["등록 완료 수"])
    cols[2].metric("등록 성공률", f"{total_kpis['등록 성공률']}%")
    cols[3].metric("평균 리드타임", "-" if total_kpis["평균 리드타임"] is None else f"{total_kpis['평균 리드타임']}일")
    cols[4].metric("중앙 리드타임", "-" if total_kpis["중앙 리드타임"] is None else f"{total_kpis['중앙 리드타임']}일")
    cols[5].metric("등록 제외 수", total_kpis["등록 제외 수"])

    left, right = st.columns(2)
    with left:
        st.dataframe(total_kpis["요청그룹표"], use_container_width=True, hide_index=True)
        st.dataframe(total_kpis["단계표"], use_container_width=True, hide_index=True)
    with right:
        if not requester_people_total.empty:
            st.dataframe(requester_people_total.head(20), use_container_width=True, hide_index=True)
        if not reviewer_people_total.empty:
            st.dataframe(reviewer_people_total.head(20), use_container_width=True, hide_index=True)

def render_filtered_section(filtered_df, filtered_kpis, requester_people_filtered, reviewer_people_filtered, requester_time_df, reviewer_time_df, delayed_df, meta, period_choice):
    st.markdown("### 필터 적용 결과")
    cols = st.columns(6)
    cols[0].metric("필터 건수", filtered_kpis["총 브랜드 수"])
    cols[1].metric("등록 완료 수", filtered_kpis["등록 완료 수"])
    cols[2].metric("등록 성공률", f"{filtered_kpis['등록 성공률']}%")
    cols[3].metric(f"주간 증감 ({filtered_kpis['이번주라벨']} vs {filtered_kpis['전주라벨']})", filtered_kpis["이번주"], f"{filtered_kpis['WoW']}%")
    cols[4].metric(f"월간 증감 ({filtered_kpis['이번달라벨']} vs {filtered_kpis['전월라벨']})", filtered_kpis["이번달"], f"{filtered_kpis['MoM']}%")
    cols[5].metric("SLA 7일내 완료율", f"{filtered_kpis['SLA7일내 완료율']}%")

    a, b = st.columns(2)
    with a:
        st.bar_chart(filtered_kpis["요청그룹표"].set_index("요청그룹")["건수"])
        st.dataframe(filtered_kpis["요청그룹표"], use_container_width=True, hide_index=True)
    with b:
        st.bar_chart(filtered_kpis["단계표"].set_index("단계")["건수"])
        st.dataframe(filtered_kpis["단계표"], use_container_width=True, hide_index=True)

    c1, c2 = st.columns(2)
    with c1:
        if not requester_people_filtered.empty:
            st.markdown("#### 요청자별 건수")
            st.bar_chart(requester_people_filtered.head(20).set_index("요청자")["건수"])
            st.dataframe(requester_people_filtered, use_container_width=True, hide_index=True)
    with c2:
        if not reviewer_people_filtered.empty:
            st.markdown("#### 검토자별 건수")
            st.bar_chart(reviewer_people_filtered.head(20).set_index("검토자")["건수"])
            st.dataframe(reviewer_people_filtered, use_container_width=True, hide_index=True)

    d1, d2 = st.columns(2)
    with d1:
        st.markdown(f"#### 요청자별 {period_choice} 추이")
        if not requester_time_df.empty:
            top_req = requester_time_df.groupby("요청자")["건수"].sum().sort_values(ascending=False).head(10).index.tolist()
            pivot = requester_time_df[requester_time_df["요청자"].isin(top_req)].pivot_table(index="기간", columns="요청자", values="건수", aggfunc="sum").fillna(0)
            st.line_chart(pivot)
            st.dataframe(requester_time_df, use_container_width=True, hide_index=True)
    with d2:
        st.markdown(f"#### 검토자별 {period_choice} 추이")
        if not reviewer_time_df.empty:
            top_rev = reviewer_time_df.groupby("검토자")["건수"].sum().sort_values(ascending=False).head(10).index.tolist()
            pivot = reviewer_time_df[reviewer_time_df["검토자"].isin(top_rev)].pivot_table(index="기간", columns="검토자", values="건수", aggfunc="sum").fillna(0)
            st.line_chart(pivot)
            st.dataframe(reviewer_time_df, use_container_width=True, hide_index=True)

    e1, e2 = st.columns(2)
    with e1:
        st.markdown("#### 국내 vs 해외")
        compare = filtered_kpis["국내해외비교표"]
        if not compare.empty:
            st.bar_chart(compare.set_index("국내해외구분")[["브랜드수", "등록완료수"]])
            st.dataframe(compare, use_container_width=True, hide_index=True)
    with e2:
        st.markdown("#### 시간 추이")
        if not filtered_kpis["주간표"].empty:
            st.line_chart(filtered_kpis["주간표"].set_index("년주차")["건수"])
        if not filtered_kpis["월간표"].empty:
            st.bar_chart(filtered_kpis["월간표"].set_index("년월")["건수"])

    f1, f2 = st.columns(2)
    with f1:
        st.markdown("#### 지연 분류")
        delay_table = (
            filtered_df["지연분류"].value_counts()
            .rename_axis("지연분류")
            .reset_index(name="건수")
        )
        st.bar_chart(delay_table.set_index("지연분류")["건수"])
        st.dataframe(delay_table, use_container_width=True, hide_index=True)
    with f2:
        st.markdown("#### 이슈 분류")
        issue_table = (
            filtered_df["이슈분류"].value_counts()
            .rename_axis("이슈분류")
            .reset_index(name="건수")
        )
        st.bar_chart(issue_table.set_index("이슈분류")["건수"])
        st.dataframe(issue_table, use_container_width=True, hide_index=True)

    st.markdown("#### 리드타임 상세")
    detail_cols = [
        c for c in [
            meta.get("brand_col"),
            meta.get("requester_col"),
            meta.get("reviewer_col"),
            meta.get("reg_req_col"),
            meta.get("reg_done_col"),
            "등록소요일",
            "지연분류",
            "이슈분류",
            meta.get("delay_col"),
            meta.get("remark_col"),
            "현재단계",
            "국내해외구분",
        ]
        if c and c in delayed_df.columns
    ]
    if detail_cols:
        st.dataframe(
            delayed_df[detail_cols].sort_values("등록소요일", ascending=False, na_position="last"),
            use_container_width=True,
            hide_index=True,
        )

# ---------------------------
# main
# ---------------------------
st.title("KREAM Ops Dashboard")

source_type = st.sidebar.radio("데이터 소스", ["Google Sheet", "Excel 업로드"])
view_mode = st.sidebar.radio("보기 방식", ["대시보드", "보고서"])

values = None
if source_type == "Google Sheet":
    sheet_name = st.text_input("구글 시트 이름", value="")
    worksheet_name = st.text_input("워크시트 이름(선택)", value="Summary")
    if st.button("구글 시트 불러오기", type="primary"):
        values = load_google_sheet_values(sheet_name, worksheet_name or None)
        st.session_state["sheet_values"] = values
else:
    uploaded = st.file_uploader("엑셀 파일 업로드", type=["xlsx"])
    worksheet_name_excel = st.text_input("엑셀 시트 이름(선택)", value="Summary")
    if uploaded and st.button("엑셀 불러오기", type="primary"):
        values = load_excel_values(uploaded.getvalue(), worksheet_name_excel or None)
        st.session_state["sheet_values"] = values

if "sheet_values" in st.session_state:
    values = st.session_state["sheet_values"]

if values:
    df_raw, meta, requester_people_total, reviewer_people_total = prepare_dataframe(values)

    if df_raw.empty:
        st.warning("읽을 데이터가 없습니다.")
    else:
        integrated_df = integrated_window(df_raw)
        total_kpis = build_kpis(integrated_df)

        render_integrated_summary(integrated_df, total_kpis, requester_people_total, reviewer_people_total)

        requester_col = meta.get("requester_col")
        reviewer_col = meta.get("reviewer_col")
        brand_col = meta.get("brand_col")

        with st.sidebar:
            st.markdown("### 필터")
            selected_groups = st.multiselect("요청 그룹", options=sorted(integrated_df["요청그룹"].dropna().unique().tolist()), default=sorted(integrated_df["요청그룹"].dropna().unique().tolist()))
            selected_country = st.multiselect("국내/해외", options=sorted(integrated_df["국내해외구분"].dropna().unique().tolist()), default=sorted(integrated_df["국내해외구분"].dropna().unique().tolist()))
            selected_stage = st.multiselect("현재 단계", options=sorted(integrated_df["현재단계"].dropna().unique().tolist()), default=sorted(integrated_df["현재단계"].dropna().unique().tolist()))
            selected_issue = st.multiselect("이슈 분류", options=sorted(integrated_df["이슈분류"].dropna().unique().tolist()), default=sorted(integrated_df["이슈분류"].dropna().unique().tolist()))
            selected_delay = st.multiselect("지연 분류", options=sorted(integrated_df["지연분류"].dropna().unique().tolist()), default=sorted(integrated_df["지연분류"].dropna().unique().tolist()))
            selected_newness = st.multiselect("신규/기성", options=sorted(integrated_df["신규기성"].dropna().unique().tolist()), default=sorted(integrated_df["신규기성"].dropna().unique().tolist()))
            requester_options = sorted(integrated_df[requester_col].replace("", pd.NA).dropna().unique().tolist()) if requester_col else []
            selected_requesters = st.multiselect("요청자", options=requester_options, default=requester_options)
            reviewer_options = sorted(integrated_df[reviewer_col].replace("", pd.NA).dropna().unique().tolist()) if reviewer_col else []
            selected_reviewers = st.multiselect("검토자", options=reviewer_options, default=reviewer_options)
            keyword = st.text_input("브랜드/비고/검토내용 검색", value="")

            st.markdown("### 시간 필터 (등록 완료일 기준, 2025년 이후)")
            filter_source = integrated_df[integrated_df["년도"].ge(2025).fillna(False)].copy()
            years = sorted(filter_source["년도"].dropna().astype(int).unique().tolist()) if not filter_source.empty else []
            months = sorted(filter_source["월"].dropna().astype(int).unique().tolist()) if not filter_source.empty else []
            weeks = sorted(filter_source["주차"].dropna().astype(int).unique().tolist()) if not filter_source.empty else []
            sel_years = st.multiselect("년도", options=years, default=years)
            sel_months = st.multiselect("월", options=months, default=months)
            sel_weeks = st.multiselect("주차", options=weeks, default=weeks)
            include_exceptions = st.checkbox("등록 제외(등록 불가/등록 완료일 없음) 포함", value=False)

            period_choice = st.selectbox("인력 추이 기준", ["년", "월", "주"])

        filtered_base = integrated_df.copy()
        if selected_groups:
            filtered_base = filtered_base[filtered_base["요청그룹"].isin(selected_groups)]
        if selected_country:
            filtered_base = filtered_base[filtered_base["국내해외구분"].isin(selected_country)]
        if selected_stage:
            filtered_base = filtered_base[filtered_base["현재단계"].isin(selected_stage)]
        if selected_issue:
            filtered_base = filtered_base[filtered_base["이슈분류"].isin(selected_issue)]
        if selected_delay:
            filtered_base = filtered_base[filtered_base["지연분류"].isin(selected_delay)]
        if selected_newness:
            filtered_base = filtered_base[filtered_base["신규기성"].isin(selected_newness)]
        if requester_col and selected_requesters:
            filtered_base = filtered_base[filtered_base[requester_col].isin(selected_requesters)]
        if reviewer_col and selected_reviewers:
            filtered_base = filtered_base[filtered_base[reviewer_col].isin(selected_reviewers)]
        if keyword:
            search_cols = [c for c in [brand_col, meta.get("issue_col"), meta.get("remark_col"), meta.get("delay_col")] if c and c in filtered_base.columns]
            if search_cols:
                mask = False
                for col in search_cols:
                    mask = mask | filtered_base[col].astype(str).str.contains(keyword, case=False, na=False)
                filtered_base = filtered_base[mask]

        filtered_df = filtered_window(filtered_base, sel_years, sel_months, sel_weeks, include_exceptions)
        filtered_kpis = build_kpis(filtered_df)

        requester_people_filtered = count_people_from_column(filtered_df, requester_col, "요청자")
        reviewer_people_filtered = count_people_from_column(filtered_df, reviewer_col, "검토자")
        requester_time_df = count_people_by_time(filtered_df, requester_col, "요청자", period_choice)
        reviewer_time_df = count_people_by_time(filtered_df, reviewer_col, "검토자", period_choice)

        lead_series = filtered_df["등록소요일"].dropna()
        min_lt = int(lead_series.min()) if not lead_series.empty else 0
        max_lt = int(lead_series.max()) if not lead_series.empty else 0
        with st.sidebar:
            lead_min, lead_max = st.slider("리드타임(day)", min_value=min_lt, max_value=max_lt if max_lt >= min_lt else min_lt, value=(min_lt, max_lt if max_lt >= min_lt else min_lt))

        delayed_df = filtered_df.copy()
        if not delayed_df.empty:
            delayed_df = delayed_df[delayed_df["등록소요일"].between(lead_min, lead_max, inclusive="both")]

        info_cols = st.columns(4)
        info_cols[0].info(f"감지된 요청자 컬럼: {requester_col or '없음'}")
        info_cols[1].info(f"감지된 검토자 컬럼: {reviewer_col or '없음'}")
        info_cols[2].info(f"필터 적용 결과: {len(filtered_df)}건")
        info_cols[3].info(f"리드타임 상세 결과: {len(delayed_df)}건")

        render_filtered_section(filtered_df, filtered_kpis, requester_people_filtered, reviewer_people_filtered, requester_time_df, reviewer_time_df, delayed_df, meta, period_choice)

        st.markdown("### 내보내기 / 공유")
        left, right = st.columns([1, 1])
        with left:
            excel_bytes = dataframe_to_excel_bytes(filtered_df)
            st.download_button(
                "필터 결과 엑셀 다운로드",
                data=excel_bytes,
                file_name="kream_ops_filtered.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        with right:
            webhook = st.text_input("Slack Webhook URL", type="password")
            if st.button("Slack 리포트 전송"):
                ok, msg = send_to_slack(webhook, build_slack_text(filtered_kpis))
                if ok:
                    st.success("Slack 전송 완료")
                else:
                    st.error(f"Slack 전송 실패: {msg}")
