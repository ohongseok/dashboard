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

# ---------------------------
# 핵심 수정된 부분 🔥
# ---------------------------
@st.cache_data(ttl=600)
def load_google_sheet_values(sheet_name: str, worksheet_name: Optional[str] = None) -> List[List[str]]:
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"]
    )

    client = gspread.authorize(creds)

    workbook = client.open(sheet_name)

    if worksheet_name:
        worksheet = workbook.worksheet(worksheet_name)
    else:
        worksheet = workbook.sheet1

    return worksheet.get_all_values()

# ---------------------------
# 나머지 그대로 유지 (문제 없음)
# ---------------------------

def normalize_text(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()

def split_people(raw: str) -> List[str]:
    text = normalize_text(raw)
    if not text:
        return []
    return [t.strip() for t in re.split(r"[,/|·\n]+", text) if t.strip()]

def parse_bool(v) -> bool:
    if pd.isna(v):
        return False
    s = str(v).strip().lower()
    return s in TRUE_VALUES

def parse_date_series(series: pd.Series) -> pd.Series:
    return pd.to_datetime(series, errors="coerce")

def values_to_dataframe(values: List[List[str]]) -> pd.DataFrame:
    if not values:
        return pd.DataFrame()

    header = values[0]
    rows = values[1:]

    df = pd.DataFrame(rows, columns=header)
    df = df.dropna(how="all").reset_index(drop=True)
    return df

def build_kpis(df: pd.DataFrame) -> Dict[str, object]:
    total = len(df)
    done = int(df["등록 완료"].sum()) if "등록 완료" in df else 0

    return {
        "총 브랜드 수": total,
        "등록 완료 수": done,
        "등록 성공률": round(done / total * 100, 1) if total else 0,
    }

# ---------------------------
# UI
# ---------------------------
st.title("KREAM Ops Dashboard")

sheet_name = st.text_input("구글 시트 이름")
worksheet_name = st.text_input("워크시트 이름", value="Summary")

if st.button("불러오기"):
    values = load_google_sheet_values(sheet_name, worksheet_name)
    df = values_to_dataframe(values)

    if df.empty:
        st.warning("데이터 없음")
    else:
        st.dataframe(df)

        kpis = build_kpis(df)

        st.metric("총 브랜드 수", kpis["총 브랜드 수"])
        st.metric("등록 완료 수", kpis["등록 완료 수"])
        st.metric("등록 성공률", f"{kpis['등록 성공률']}%")
