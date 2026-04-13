import io
import re
from typing import Optional, List, Dict

import gspread
import pandas as pd
import requests
import streamlit as st
import plotly.express as px  # 시각화 보완을 위해 추가
import plotly.graph_objects as go
from google.oauth2.service_account import Credentials

# ---------------------------
# 0. Page & Theme Config
# ---------------------------
st.set_page_config(page_title="KREAM Ops Executive Dashboard", layout="wide")

# 대시보드 스타일링
st.markdown("""
    <style>
    .main { background-color: #f8f9fa; }
    .stMetric { background-color: #ffffff; padding: 15px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.05); }
    [data-testid="stMetricValue"] { font-size: 28px; color: #1e1e1e; }
    </style>
    """, unsafe_allow_html=True)

# ---------------------------
# 1. Constants & Mappings (원본 데이터 100% 유지)
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
    s = str(v).strip().lower()
    return s in TRUE_VALUES

def parse_date_series(series: pd.Series) -> pd.Series:
    parsed = pd.to_datetime(series, errors="coerce")
    if parsed.notna().mean() >= 0.3: return parsed
    return pd.to_datetime(series, errors="coerce", format="%y.%m.%d")

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
        alias_norm = normalize_colname(alias).lower()
        if alias_norm in normalized_map: return normalized_map[alias_norm]
    lowered = [normalize_colname(a).lower() for a in aliases]
    for col in df.columns:
        if any(a in normalize_colname(col).lower() for a in lowered): return col
    return None

# ---------------------------
# 3. Core Engine (Bug Fixes & Logic Integration)
# ---------------------------
@st.cache_data(ttl=600)
def load_google_sheet_values(sheet_name: str, worksheet_name: Optional[str] = None) -> List[List[str]]:
    # 인증 정보 에러 방지 (GCP secrets 사용 권장)
    try:
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]),
            scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        )
        client = gspread.authorize(creds)
        # client.opens -> client.open 수정 (Bug Fix)
        workbook = client.open(sheet_name)
        worksheet = workbook.worksheet(worksheet_name) if worksheet_name else workbook.sheet1
        return worksheet.get_all_values()
    except Exception as e:
        st.error(f"구글 시트 로드 중 에러: {e}")
        return []

def prepare_dataframe(values: List[List[str]]):
    df = values_to_dataframe(values)
    if df.empty: return df, {}, pd.DataFrame(), pd.DataFrame()

    colmap = {key: find_column(df, aliases) for key, aliases in COLUMN_ALIASES.items()}

    brand_col = colmap["brand"]
    if brand_col:
        df = df[df[brand_col].astype(str).str.strip() != ""].reset_index(drop=True)

    # 기본 속성 정의
    df["요청그룹"] = df[colmap["requester"]].apply(requester_group) if colmap["requester"] else "Famous"
    df["대표요청자"] = df[colmap["requester"]].apply(lambda x: split_people(x)[0] if split_people(x) else "미입력") if colmap["requester"] else "미입력"
    df["국내해외구분"] = df[colmap["country_type"]].apply(lambda x: "국내" if "국내" in normalize_text(x) else "해외" if "해외" in normalize_text(x) else "미입력") if colmap["country_type"] else "미입력"

    # 상태 불리언
    for k in ["listed", "request_done", "purchase_requested", "purchase_done", "registration_done_flag"]:
        col = colmap[k]
        df[f"bool__{k}"] = df[col].apply(parse_bool) if col else False

    # 날짜 및 리드타임
    df["date__registration_request"] = parse_date_series(df[colmap["registration_request_date"]]) if colmap["registration_request_date"] else pd.NaT
    df["date__registration_done"] = parse_date_series(df[colmap["registration_done_date"]]) if colmap["registration_done_date"] else pd.NaT
    df["등록소요일"] = (df["date__registration_done"] - df["date__registration_request"]).dt.days
    df["등록소요일"] = df["등록소요일"].where((df["등록소요일"] >= 0) & (df["등록소요일"] <= 365))

    # 단계 레이블
    def stage_label(row):
        if row["bool__registration_done_flag"]: return "5.등록 완료"
        if row["bool__purchase_done"]: return "4.구매 완료"
        if row["bool__purchase_requested"]: return "3.구매 요청"
        if row["bool__request_done"]: return "2.등록 요청 완료"
        if row["bool__listed"]: return "1.리스트업 완료"
        return "0.미진행"
    df["현재단계"] = df.apply(stage_label, axis=1)

    # 텍스트 분석
    text_cols = [colmap[c] for c in ["delay_reason", "issue_note", "issue_conclusion", "remark"] if colmap.get(c)]
    combined_text = df[text_cols].astype(str).agg(' '.join, axis=1)
    df["지연분류"] = combined_text.apply(lambda x: category_from_text(x, DELAY_MAPPING))
    df["이슈분류"] = combined_text.apply(lambda x: category_from_text(x, ISSUE_MAPPING))
    df["신규기성"] = combined_text.apply(lambda x: "신규" if any(k in x.lower() for k in ["신생", "신규", "new brand", "발굴"]) else "기성/기타")

    # 시간 차원
    df["년도"] = df["date__registration_done"].dt.year.astype("Int64")
    df["월"] = df["date__registration_done"].dt.month.astype("Int64")
    df["주차"] = df["date__registration_done"].dt.isocalendar().week.astype("Int64")
    df["ISO년도"] = df["date__registration_done"].dt.isocalendar().year.astype("Int64")
    df["년월"] = df["date__registration_done"].dt.strftime("%Y-%m")
    df["년주차"] = df["ISO년도"].astype(str) + "-W" + df["주차"].astype(str).str.zfill(2)
    
    df["등록제외"] = df["date__registration_done"].isna()

    return df, colmap

# ---------------------------
# 4. Analysis & KPI Builder (C-Level 보완)
# ---------------------------
def build_kpis(df: pd.DataFrame) -> Dict[str, object]:
    total = len(df)
    reg_done = int(df["bool__registration_done_flag"].sum())
    
    # 리드타임 효율
    lt_valid = df["등록소요일"].dropna()
    avg_lt = round(lt_valid.mean(), 1) if not lt_valid.empty else None
    sla_rate = safe_rate(int((lt_valid <= 7).sum()), len(lt_valid))

    # 추이 분석
    def get_trend(target_df, group_col):
        if target_df.empty: return pd.DataFrame(), "-", 0, 0
        grouped = target_df.groupby(group_col).size().reset_index(name="건수")
        cur = int(grouped.iloc[-1]["건수"])
        prev = int(grouped.iloc[-2]["건수"]) if len(grouped) > 1 else 0
        return grouped, grouped.iloc[-1][group_col], cur, prev

    w_df, w_lab, w_cur, w_prev = get_trend(df.dropna(subset=["년주차"]), "년주차")
    m_df, m_lab, m_cur, m_prev = get_trend(df.dropna(subset=["년월"]), "년월")

    return {
        "총 브랜드 수": total,
        "등록 완료 수": reg_done,
        "등록 성공률": safe_rate(reg_done, total),
        "평균 리드타임": avg_lt,
        "SLA준수율(7일내)": sla_rate,
        "WoW": growth(w_cur, w_prev),
        "MoM": growth(m_cur, m_prev),
        "이번주라벨": w_lab, "이번달라벨": m_lab,
        "이번주건수": w_cur, "이번달건수": m_cur,
        "단계표": df["현재단계"].value_counts().reset_index(name="건수"),
        "조직표": df["요청그룹"].value_counts().reset_index(name="건수"),
        "주간추이": w_df, "월간추이": m_df
    }

# ---------------------------
# 5. UI Rendering
# ---------------------------
def render_executive_dashboard(df, kpis, colmap):
    # 1. 상단 핵심 지표 카드 (요청하신 대로 KPI 선별)
    st.markdown("### 📊 Executive Summary")
    c1, c2, c3, kpi4, kpi5 = st.columns(5)
    c1.metric("총 분석 브랜드", f"{kpis['총 브랜드 수']:,}건")
    c2.metric("최종 등록 완료", f"{kpis['등록 완료 수']:,}건")
    c3.metric("누적 등록 성공률", f"{kpis['등록 성공률']}%")
    kpi4.metric(f"주간 성과 ({kpis['이번주라벨']})", f"{kpis['이번주건수']}건", f"{kpis['WoW']}%")
    kpi5.metric("SLA 준수율 (7일)", f"{kpis['SLA준수율(7일내)']}%")

    st.markdown("---")

    # 2. C-Level 전략 시각화 (Plotly 보완)
    col_a, col_b = st.columns([6, 4])
    
    with col_a:
        st.markdown("#### 📈 등록 완료 추이 (Monthly)")
        if not kpis["월간추이"].empty:
            fig = px.line(kpis["월간추이"], x="년월", y="건수", markers=True, 
                          text="건수", template="plotly_white", color_discrete_sequence=['#007BFF'])
            fig.update_traces(textposition="top center")
            st.plotly_chart(fig, use_container_width=True)

    with col_b:
        st.markdown("#### 🎯 공정별 병목 구간 (Funnel)")
        # 퍼널 데이터를 위해 단계별 누적 합계 계산
        stages = ["1.리스트업 완료", "2.등록 요청 완료", "3.구매 요청", "4.구매 완료", "5.등록 완료"]
        counts = [df[f"bool__{k}"].sum() for k in ["listed", "request_done", "purchase_requested", "purchase_done", "registration_done_flag"]]
        fig_funnel = go.Figure(go.Funnel(y=stages, x=counts, textinfo="value+percent initial"))
        fig_funnel.update_layout(margin=dict(l=20, r=20, t=20, b=20), height=350)
        st.plotly_chart(fig_funnel, use_container_width=True)

    st.markdown("---")
    
    # 3. 상세 분석 섹션
    row2_1, row2_2, row2_3 = st.columns(3)
    with row2_1:
        st.markdown("#### 🚩 지연 사유 분포")
        delay_counts = df["지연분류"].value_counts().reset_index()
        fig_delay = px.pie(delay_counts, values='count', names='지연분류', hole=.4, color_discrete_sequence=px.colors.qualitative.Pastel)
        st.plotly_chart(fig_delay, use_container_width=True)
    
    with row2_2:
        st.markdown("#### 👥 조직별 리드타임 효율")
        org_lt = df.groupby("요청그룹")["등록소요일"].mean().reset_index()
        fig_org = px.bar(org_lt, x="요청그룹", y="등록소요일", color="요청그룹", template="plotly_white")
        st.plotly_chart(fig_org, use_container_width=True)

    with row2_3:
        st.markdown("#### 🛡️ 이슈 유형별 현황")
        issue_counts = df["이슈분류"].value_counts().reset_index()
        st.dataframe(issue_counts, hide_index=True, use_container_width=True)

    st.markdown("---")
    st.markdown("#### 📑 필터링 데이터 상세 리스트")
    st.dataframe(df.sort_values("등록소요일", ascending=False), use_container_width=True)

# ---------------------------
# 6. Main execution
# ---------------------------
def main():
    st.title("KREAM Ops Dashboard")

    with st.sidebar:
        st.header("📂 데이터 설정")
        source = st.radio("데이터 소스", ["Google Sheet", "Excel Upload"])
        
        raw_values = None
        if source == "Google Sheet":
            s_name = st.text_input("구글 시트 제목", value="1P 상품등록 통합페이지")
            if st.button("데이터 동기화", type="primary"):
                raw_values = load_google_sheet_values(s_name, "Summary")
                st.session_state["raw"] = raw_values
        else:
            up = st.file_uploader("XLSX 업로드", type="xlsx")
            if up:
                # 1,434개 행 전체를 읽기 위해 header=None으로 로드 후 내부에서 처리
                df_excel = pd.read_excel(up, header=None)
                raw_values = df_excel.fillna("").values.tolist()
                st.session_state["raw"] = raw_values

    if "raw" not in st.session_state:
        st.info("💡 사이드바에서 데이터를 먼저 로드해주세요.")
        return

    # 데이터 전처리 (1,434행 전체 대상)
    df_raw, colmap = prepare_dataframe(st.session_state["raw"])
    
    if not df_raw.empty:
        # --- 홍석님 원본 필터 100% 복구 ---
        with st.sidebar:
            st.markdown("---")
            st.header("🔍 세부 필터")
            f_org = st.multiselect("조직 (요청그룹)", options=sorted(df_raw["요청그룹"].unique()), default=sorted(df_raw["요청그룹"].unique()))
            f_country = st.multiselect("국내/해외", options=sorted(df_raw["국내해외구분"].unique()), default=sorted(df_raw["국내해외구분"].unique()))
            f_stage = st.multiselect("현재 단계", options=sorted(df_raw["현재단계"].unique()), default=sorted(df_raw["현재단계"].unique()))
            f_issue = st.multiselect("이슈 분류", options=sorted(df_raw["이슈분류"].unique()), default=sorted(df_raw["이슈분류"].unique()))
            f_delay = st.multiselect("지연 분류", options=sorted(df_raw["지연분류"].unique()), default=sorted(df_raw["지연분류"].unique()))
            f_new = st.multiselect("신규/기성", options=sorted(df_raw["신규기성"].unique()), default=sorted(df_raw["신규기성"].unique()))
            
            # 인력 필터
            all_requesters = sorted(df_raw["대표요청자"].unique())
            f_req = st.multiselect("요청자", options=all_requesters, default=all_requesters)
            
            # 시간 필터
            years = sorted(df_raw["년도"].dropna().unique().tolist())
            f_year = st.multiselect("년도 필터", options=years, default=years)
            
            keyword = st.text_input("브랜드/비고 검색")
            include_ex = st.checkbox("등록 완료일 없는 미진행 건 포함", value=True)

        # 필터링 엔진
        df = df_raw[
            (df_raw["요청그룹"].isin(f_org)) &
            (df_raw["국내해외구분"].isin(f_country)) &
            (df_raw["현재단계"].isin(f_stage)) &
            (df_raw["이슈분류"].isin(f_issue)) &
            (df_raw["지연분류"].isin(f_delay)) &
            (df_raw["신규기성"].isin(f_new)) &
            (df_raw["대표요청자"].isin(f_req))
        ].copy()

        # 시간 필터링
        if not include_ex:
            df = df[df["date__registration_done"].notna()]
        if f_year:
            df = df[(df["년도"].isin(f_year)) | (df["date__registration_done"].isna())]
            
        if keyword:
            df = df[df.apply(lambda r: keyword.lower() in str(r).lower(), axis=1)]

        # KPI & 대시보드 렌더링
        kpis = build_kpis(df)
        render_executive_dashboard(df, kpis, colmap)
        
    else:
        st.warning("데이터가 없거나 형식이 맞지 않습니다.")

if __name__ == "__main__":
    main()
