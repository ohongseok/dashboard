import io
import json
import re
import time
import uuid
from datetime import datetime



st.markdown("""
<style>

/* ===== FINAL CLEAN VISIBILITY ===== */

/* remove weird arrow text */
* {
    text-shadow: none !important;
}

/* ensure all text visible */
body, span, div, p, label {
    color:#111 !important;
}

/* card alert fix */
.stAlert {
    background:#ffffff !important;
    color:#111 !important;
    border:1px solid #ddd !important;
}

/* plot text fix */
.plotly text {
    fill:#111 !important;
}

/* unify graph colors */
.js-plotly-plot {
    background:#ffffff !important;
}

/* remove ghost labels */
span:contains("arrow"),
div:contains("arrow") {
    display:none !important;
}

</style>
""", unsafe_allow_html=True)


import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st
import streamlit.components.v1 as components


st.markdown("""
<style>

/* FORCE remove duplicate upload text */
[data-testid="stFileUploader"] button span {display:inline !important;}
[data-testid="stFileUploader"] button span:nth-child(2){display:none !important;}
[data-testid="stFileUploader"] button span:nth-child(3){display:none !important;}

/* remove label text completely */
[data-testid="stFileUploader"] label {display:none !important;}

/* fix white on white text */
.plotly .xtick text, .plotly .ytick text {
    fill:#111 !important;
}

/* arrow text fix */
span:contains("arrow"),
div:contains("arrow") {
    display:none !important;
}

/* section title rename spacing fix */
h1,h2,h3 {color:#111 !important;}

</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# 0. PAGE CONFIG
# ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="1P Ops Intelligence",
    page_icon="⬛",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Pretendard:wght@400;500;600;700;800;900&display=swap');

:root {
    --bg: #f3f6fb;
    --surface: #ffffff;
    --surface-soft: #f8fafc;
    --surface-strong: #f1f5f9;
    --text-1: #0f172a;
    --text-2: #334155;
    --text-3: #64748b;
    --line: #e2e8f0;
    --line-soft: #edf2f7;
    --sidebar: #0f172a;
    --sidebar-2: #111c33;
    --sidebar-line: #23324a;
    --accent: #2563eb;
    --accent-2: #1d4ed8;
    --success: #059669;
    --danger: #ef4444;
    --warning: #d97706;
    --purple: #7c3aed;
    --shadow-sm: 0 4px 12px rgba(15, 23, 42, 0.05);
    --shadow-md: 0 10px 28px rgba(15, 23, 42, 0.08);
    --radius: 18px;
}

html, body, [class*="css"], [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
    font-family: 'Inter', 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, sans-serif !important;
    color: var(--text-1) !important;
    -webkit-font-smoothing: antialiased !important;
    text-rendering: optimizeLegibility !important;
    font-variant-numeric: tabular-nums;
}

*, *::before, *::after { box-sizing: border-box; }

html, body, .main, .stApp, [data-testid="stAppViewContainer"] {
    background: linear-gradient(180deg, #f7f9fd 0%, #f3f6fb 100%) !important;
    color: var(--text-1) !important;
}

.block-container {
    max-width: 100% !important;
    padding: 0 28px 48px 28px !important;
}

h1, h2, h3, h4, h5, h6, p, span, label, div {
    font-family: 'Inter', 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, sans-serif !important;
}

/* ===== Sidebar ===== */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, var(--sidebar) 0%, var(--sidebar-2) 100%) !important;
    border-right: 1px solid var(--sidebar-line) !important;
    width: 360px !important;
    min-width: 360px !important;
    max-width: 360px !important;
}
[data-testid="stSidebar"] > div:first-child {
    width: 360px !important;
}
[data-testid="stSidebar"] > div {
    padding-top: 0 !important;
    padding-left: 24px !important;
    padding-right: 16px !important;
}
[data-testid="stSidebar"] .block-container,
[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
    padding-left: 8px !important;
    padding-right: 4px !important;
}

[data-testid="stSidebar"] label,
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] .stMarkdown p,
[data-testid="stSidebar"] .stCaption,
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"],
[data-testid="stSidebar"] small,
[data-testid="stSidebar"] span,
[data-testid="stSidebar"] div {
    color: #f8fafc !important;
    -webkit-text-fill-color: #f8fafc !important;
    text-shadow: none !important;
}

[data-testid="stSidebar"] .stButton > button {
    background: #ffffff !important;
    color: #0f172a !important;
    border: 1px solid #dbe4f0 !important;
    border-radius: 14px !important;
    font-weight: 900 !important;
    font-size: 13px !important;
    height: 48px !important;
    width: 100% !important;
    transition: all .15s ease !important;
    box-shadow: 0 8px 20px rgba(37, 99, 235, 0.10) !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #f8fafc !important;
    border-color: #cbd5e1 !important;
    transform: translateY(-1px);
}

[data-testid="stSidebar"] [data-baseweb="select"] > div,
[data-testid="stSidebar"] [data-baseweb="input"] > div,
[data-testid="stSidebar"] [data-baseweb="base-input"],
[data-testid="stSidebar"] input,
[data-testid="stSidebar"] textarea {
    background: rgba(255,255,255,0.08) !important;
    color: #ffffff !important;
    border: 1px solid #334155 !important;
    border-radius: 16px !important;
    min-height: 52px !important;
    box-shadow: none !important;
}
[data-testid="stSidebar"] input::placeholder {
    color: #94a3b8 !important;
}
[data-testid="stSidebar"] svg {
    fill: #cbd5e1 !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] * {
    color: #ffffff !important;
    fill: #cbd5e1 !important;
}

/* multiselect chips */
[data-testid="stSidebar"] [data-baseweb="tag"] {
    background: #1e293b !important;
    border: 1px solid #314158 !important;
    color: #ffffff !important;
    border-radius: 12px !important;
    min-height: 34px !important;
    padding: 6px 10px !important;
    box-shadow: none !important;
    margin-right: 6px !important;
}
[data-testid="stSidebar"] [data-baseweb="tag"]::before,
[data-testid="stSidebar"] [data-baseweb="tag"]::after,
[data-testid="stSidebar"] [data-baseweb="tag"] svg:first-child,
[data-testid="stSidebar"] [data-baseweb="tag"] [aria-hidden="true"] {
    display: none !important;
    content: none !important;
}
[data-testid="stSidebar"] [data-baseweb="tag"] * {
    color: #ffffff !important;
    fill: #ffffff !important;
    background: transparent !important;
}
[data-testid="stSidebar"] [data-baseweb="tag"] span {
    padding-left: 0 !important;
    margin-left: 0 !important;
    overflow: visible !important;
    line-height: 1.25 !important;
}

/* hide the internal text cursor/input that was covering chip text */
[data-testid="stSidebar"] [data-baseweb="select"] input {
    opacity: 0 !important;
    width: 2px !important;
    min-width: 2px !important;
    padding: 0 !important;
    margin: 0 !important;
    border: 0 !important;
}

/* dropdown menus */
div[role="listbox"], ul[role="listbox"] {
    background: #0f172a !important;
    border: 1px solid #334155 !important;
    border-radius: 12px !important;
}
div[role="option"], li[role="option"] {
    background: #0f172a !important;
    color: #ffffff !important;
}
div[role="option"]:hover, li[role="option"]:hover {
    background: #1e293b !important;
}

/* uploader */
[data-testid="stSidebar"] [data-testid="stFileUploader"] {
    width: 100% !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] {
    background: linear-gradient(180deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.02) 100%) !important;
    border: 1px dashed #334155 !important;
    border-radius: 18px !important;
    min-height: 136px !important;
    padding: 18px 16px !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] * {
    color: #e2e8f0 !important;
    fill: #e2e8f0 !important;
    -webkit-text-fill-color: #e2e8f0 !important;
}
/* remove duplicate default upload glyph/text clutter */
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzone"] svg {
    display: none !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] > div:first-child {
    display: none !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] button {
    background: #1e293b !important;
    color: #ffffff !important;
    border: 1px solid #334155 !important;
    border-radius: 12px !important;
}
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] button p,
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] button span,
[data-testid="stSidebar"] [data-testid="stFileUploaderDropzoneInstructions"] button div {
    color: #ffffff !important;
}
[data-testid="stSidebar"] button[kind="secondary"] {
    background: #1e293b !important;
    color: #ffffff !important;
    border: 1px solid #334155 !important;
    border-radius: 12px !important;
}

/* ===== top bar ===== */
.topbar {
    background: linear-gradient(90deg, #0f172a 0%, #111c33 100%);
    margin: 0 -28px 28px -28px;
    padding: 0 28px;
    min-height: 70px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 16px;
    flex-wrap: wrap;
    border-bottom: 1px solid #d8e2ef;
    box-shadow: 0 1px 0 rgba(255,255,255,0.5) inset;
}
.topbar-logo {
    font-size: 20px;
    font-weight: 900;
    color: #ffffff;
    letter-spacing: -0.4px;
}
.topbar-logo span { color: #93c5fd; }
.topbar-right {
    display: flex;
    align-items: center;
    gap: 10px;
    flex-wrap: wrap;
}
.topbar-src {
    font-size: 11px;
    color: #dbeafe;
    font-weight: 600;
}
.live-chip {
    background: #ffffff;
    color: #0f172a;
    font-size: 10px;
    font-weight: 900;
    letter-spacing: 1.4px;
    padding: 5px 11px;
    border-radius: 999px;
}

/* ===== section title ===== */
.sec {
    font-size: 11px;
    font-weight: 900;
    letter-spacing: 1.8px;
    text-transform: uppercase;
    color: var(--text-1);
    margin: 34px 0 16px 0;
    display: flex;
    align-items: center;
    gap: 10px;
}
.sec::after {
    content: '';
    flex: 1;
    height: 1px;
    background: #dbe3ee;
}

/* ===== executive KPI cards ===== */
.kcard {
    background: linear-gradient(180deg, #ffffff 0%, #fbfdff 100%);
    border-radius: 22px;
    border: 1px solid #e4ebf3;
    padding: 24px 22px 20px;
    position: relative;
    overflow: hidden;
    min-height: 148px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-shadow: 0 14px 32px rgba(15, 23, 42, 0.08);
}
.kcard:hover {
    transform: translateY(-1px);
    box-shadow: 0 18px 36px rgba(15, 23, 42, 0.10);
}
.kcard-bar {
    position: absolute;
    top: 0; left: 0; right: 0;
    height: 5px;
}
.kcard-label {
    font-size: 10px;
    font-weight: 900;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: var(--text-3);
}
.kcard-value {
    font-size: 40px;
    font-weight: 900;
    color: var(--text-1);
    letter-spacing: -2px;
    line-height: 1;
    font-variant-numeric: tabular-nums;
}
.kcard-unit {
    font-size: 15px;
    font-weight: 700;
    color: var(--text-3);
    margin-left: 4px;
}
.kcard-sub {
    font-size: 11px;
    font-weight: 600;
    color: var(--text-3);
    line-height: 1.5;
}
.kcard-badge {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 11px;
    font-weight: 800;
    padding: 5px 10px;
    border-radius: 999px;
    margin-top: 6px;
}

/* ===== cards / boxes ===== */
.action-box, .info-card, .master-box, .wip-kcard {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 20px;
    box-shadow: var(--shadow-sm);
}
.action-box { padding: 20px; min-height: 220px; }
.info-card { padding: 20px; }
.master-box { padding: 24px; }
.wip-kcard { padding: 22px 20px 18px; position: relative; overflow: hidden; }

.action-box-title, .info-card-title {
    font-size: 11px;
    font-weight: 900;
    color: var(--text-3);
    letter-spacing: 1.4px;
    text-transform: uppercase;
    margin-bottom: 10px;
}
.action-box-value {
    font-size: 34px;
    font-weight: 900;
    color: var(--text-1);
    letter-spacing: -1.4px;
    line-height: 1;
    margin-bottom: 6px;
}
.action-box-sub, .info-card-sub {
    font-size: 12px;
    font-weight: 600;
    color: var(--text-3);
    line-height: 1.7;
}

/* WIP panel */
.wip-stat-row { display: flex; gap: 10px; margin-top: 14px; }
.wip-stat {
    flex: 1;
    border-radius: 14px;
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 3px;
}
.wip-stat-label {
    font-size: 10px;
    font-weight: 900;
    letter-spacing: 1px;
}
.wip-stat-val {
    font-size: 26px;
    font-weight: 900;
    line-height: 1;
}
.wip-rule {
    font-size: 11px;
    color: var(--text-3);
    line-height: 1.6;
    margin-top: 12px;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
    gap: 0 !important;
    background: transparent !important;
    padding: 0 !important;
    border-bottom: 2px solid #dce5f0 !important;
    margin-bottom: 18px !important;
    flex-wrap: wrap !important;
}
.stTabs [data-baseweb="tab"] {
    border-radius: 0 !important;
    font-weight: 800 !important;
    font-size: 13px !important;
    height: 46px !important;
    padding: 0 18px !important;
    border-bottom: 2px solid transparent !important;
    background: transparent !important;
    color: #94a3b8 !important;
    margin-bottom: -2px !important;
}
.stTabs [aria-selected="true"] {
    border-bottom: 2px solid var(--text-1) !important;
    color: var(--text-1) !important;
}

/* Metrics */
[data-testid="metric-container"] {
    background: var(--surface) !important;
    border: 1px solid var(--line) !important;
    border-radius: 18px !important;
    padding: 18px !important;
    box-shadow: var(--shadow-sm) !important;
}
[data-testid="stMetricLabel"] {
    font-size: 10px !important;
    font-weight: 900 !important;
    color: var(--text-3) !important;
    letter-spacing: 1.2px !important;
    text-transform: uppercase !important;
}
[data-testid="stMetricValue"] {
    font-size: 28px !important;
    font-weight: 900 !important;
    color: var(--text-1) !important;
    letter-spacing: -1px !important;
}

/* DataFrame */
[data-testid="stDataFrame"], [data-testid="stDataFrameResizable"] {
    border-radius: 18px !important;
    overflow: hidden !important;
    border: 1px solid var(--line) !important;
    background: var(--surface) !important;
    box-shadow: var(--shadow-sm) !important;
}
[data-testid="stDataFrameResizable"] *,
[data-testid="stDataFrame"] * {
    font-family: 'Inter', 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, sans-serif !important;
}
[data-testid="stDataFrameResizable"] thead th,
[data-testid="stDataFrame"] thead th {
    background: #f8fafc !important;
    color: var(--text-1) !important;
    font-size: 12px !important;
    font-weight: 800 !important;
    border-bottom: 1px solid var(--line) !important;
}
[data-testid="stDataFrameResizable"] tbody td,
[data-testid="stDataFrame"] tbody td {
    color: var(--text-2) !important;
    background: #ffffff !important;
    font-size: 13px !important;
}
[data-testid="stDataFrame"] tbody tr:hover td,
[data-testid="stDataFrameResizable"] tbody tr:hover td {
    background: #f8fbff !important;
}

/* inputs/selects in main content and column filters */
[data-testid="stDataFrame"] input,
[data-testid="stDataFrame"] select,
[data-testid="stDataFrame"] textarea,
[data-testid="stDataFrame"] [data-baseweb="input"] > div,
[data-testid="stDataFrame"] [data-baseweb="select"] > div,
select, input, textarea {
    background: #ffffff !important;
    color: #0f172a !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 12px !important;
}
input::placeholder {
    color: #94a3b8 !important;
}
[data-baseweb="popover"] select,
[data-baseweb="popover"] input,
[data-baseweb="menu"] select,
[data-baseweb="menu"] input {
    background: #ffffff !important;
    color: #0f172a !important;
}
option {
    color: #0f172a !important;
    background: #ffffff !important;
}

/* General controls */
.stRadio label, .stSelectbox label, .stMultiSelect label, .stTextInput label, .stFileUploader label {
    color: var(--text-2) !important;
    font-weight: 700 !important;
}

/* Plotly unified executive theme */
.js-plotly-plot, .plotly, .main-svg {
    font-family: 'Inter', 'Pretendard', -apple-system, BlinkMacSystemFont, system-ui, sans-serif !important;
}
.js-plotly-plot {
    background: transparent !important;
}
.plot-container.plotly {
    border-radius: 18px !important;
}
svg text {
    fill: #334155 !important;
}
.hoverlayer text {
    fill: #0f172a !important;
}
.js-plotly-plot .plotly .hoverlayer .bg {
    fill: #ffffff !important;
    stroke: #cbd5e1 !important;
    stroke-width: 1 !important;
}
.js-plotly-plot .plotly .modebar {
    background: rgba(255,255,255,0.9) !important;
    border-radius: 10px !important;
}

/* Divider */
.kdiv {
    border: none;
    border-top: 1px solid #dce5f0;
    margin: 30px 0;
}

/* Chips */
.note-chip, .sla-chip {
    display: inline-flex;
    align-items: center;
    padding: 4px 10px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 800;
    margin-right: 6px;
}

/* Expander */
details {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: 16px;
    padding: 4px 10px;
}
summary {
    color: var(--text-1) !important;
    font-weight: 800 !important;
}

/* helper texts */
.filter-row-label, .topbar-src, .kcard-sub, .action-box-sub, .info-card-sub {
    color: var(--text-3) !important;
}
</style>
""",
    unsafe_allow_html=True,
)


# ─────────────────────────────────────────────────────────────
# 0-1. ACCESS GATE
# ─────────────────────────────────────────────────────────────
def check_password() -> bool:
    secret_pw = (
        st.secrets.get("password")
        or st.secrets.get("app_password")
        or st.secrets.get("login_password")
        or "ohs"
    )
    if st.session_state.get("_auth_ok", False):
        return True

    st.markdown(
        """
        <div style='max-width:420px;margin:56px auto 8px;background:#ffffff;border:1px solid #e8e8e8;border-radius:18px;padding:28px 24px;box-shadow:0 10px 24px rgba(0,0,0,0.05);'>
          <div style='font-size:24px;font-weight:900;color:#111;letter-spacing:-0.8px;'>Dashboard Access</div>
          <div style='font-size:12px;color:#777;margin-top:8px;line-height:1.7;'>권한이 있는 사용자만 대시보드에 접근할 수 있습니다.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    pw = st.text_input("비밀번호", type="password", key="app_password_input")
    login = st.button("입장", type="primary", use_container_width=True, key="app_password_submit")
    if login:
        if pw == str(secret_pw):
            st.session_state["_auth_ok"] = True
            st.rerun()
        else:
            st.error("비밀번호가 올바르지 않습니다.")
    return False



st.markdown("""
<style>
/* ===== FINAL UI HOTFIX ===== */
[data-testid="stSidebar"] .stButton > button,
[data-testid="stSidebar"] button {
    background: #ffffff !important;
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
    border: 1px solid #cbd5e1 !important;
    border-radius: 14px !important;
    font-weight: 900 !important;
    text-shadow: none !important;
}
[data-testid="stSidebar"] .stButton > button:hover,
[data-testid="stSidebar"] button:hover {
    background: #f8fafc !important;
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
    border-color: #cbd5e1 !important;
}
[data-testid="stSidebar"] .stButton > button p,
[data-testid="stSidebar"] .stButton > button span,
[data-testid="stSidebar"] .stButton > button div {
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
    opacity: 1 !important;
}

[data-testid="stFileUploader"] section > div:first-child,
[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzone"] svg,
[data-testid="stFileUploader"] [data-testid="stFileUploaderDropzoneInstructions"] > div:first-child {
    display: none !important;
}

[data-testid="stFileUploader"] button span + span {
    display: none !important;
}
[data-testid="stFileUploader"] button {
    background: #1e293b !important;
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
    border: 1px solid #334155 !important;
    border-radius: 12px !important;
    font-size: 13px !important;
    font-weight: 800 !important;
}
[data-testid="stFileUploader"] button p,
[data-testid="stFileUploader"] button span,
[data-testid="stFileUploader"] button div {
    color: #ffffff !important;
    -webkit-text-fill-color: #ffffff !important;
}

[data-testid="stSidebar"] [data-baseweb="select"] input {
    position: absolute !important;
    left: -9999px !important;
    width: 1px !important;
    min-width: 1px !important;
    opacity: 0 !important;
    pointer-events: none !important;
}
[data-testid="stSidebar"] [data-baseweb="tag"] {
    position: relative !important;
    z-index: 2 !important;
}
[data-testid="stSidebar"] [data-baseweb="tag"]::before,
[data-testid="stSidebar"] [data-baseweb="tag"]::after,
[data-testid="stSidebar"] [data-baseweb="tag"] svg:first-child,
[data-testid="stSidebar"] [data-baseweb="tag"] [aria-hidden="true"] {
    display: none !important;
    content: none !important;
}

summary::marker {
    color: #0f172a !important;
}
details summary {
    color: #0f172a !important;
}

[data-testid="stDataFrame"] select,
[data-testid="stDataFrame"] input,
[data-testid="stDataFrameResizable"] select,
[data-testid="stDataFrameResizable"] input,
div[role="listbox"],
ul[role="listbox"],
div[role="option"],
li[role="option"] {
    background: #ffffff !important;
    color: #0f172a !important;
    -webkit-text-fill-color: #0f172a !important;
    border-color: #cbd5e1 !important;
}

.js-plotly-plot .plotly .modebar {
    background: rgba(255,255,255,0.96) !important;
}
.js-plotly-plot .plotly .hoverlayer text {
    fill: #0f172a !important;
}
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# 1. CONSTANTS
# ─────────────────────────────────────────────────────────────
SPREADSHEET_ID = "1e-uxQVNCCF3qS8e3a_S8sZbCx5qj343ycsEfkIF2POA"
SHEET_NAME = "Summary"
FIXED_REVIEWERS = ["오홍석", "유지윤", "전현희", "장근수"]
TRUE_VALUES = {"true", "1", "y", "yes", "완료", "o", "v", "✓", "check", "checked", "t", "true "}

STAGE_COLORS = {
    "5.등록 완료": "#05c072",
    "4.구매 완료": "#3b82f6",
    "3.구매 요청": "#8b5cf6",
    "2.검토/등록 요청": "#f5a623",
    "1.리스트업 완료": "#888888",
    "0.미진행": "#c7c7c7",
    "X.등록 불가": "#f04452",
}
STAGE_BG = {k: v + "18" for k, v in STAGE_COLORS.items()}

DELAY_MAP = {
    "해외배송/리드타임": ["해외배송", "해외 배송", "배송", "입고", "출고", "리드타임", "묶음"],
    "샘플/실물확인": ["샘플", "실물", "확인후 등록"],
    "가품검수/정가품": ["가품", "정가품", "검수"],
    "데이터/품번이슈": ["품번", "sku", "모델명"],
    "가격/운영판단": ["가격", "원가", "마진", "보류"],
    "담당자/행정": ["담당자", "부재", "행정"],
    "구매지연": ["구매 지연", "구매지연"],
}

CHART_TPL = dict(
    template="plotly_white",
    font=dict(family="Inter, Pretendard, sans-serif", size=12, color="#334155"),
    margin=dict(l=20, r=20, t=52, b=20),
    paper_bgcolor="#ffffff",
    plot_bgcolor="#ffffff",
    hoverlabel=dict(
        bgcolor="#ffffff",
        bordercolor="#cbd5e1",
        font=dict(color="#0f172a", family="Inter, Pretendard, sans-serif", size=13),
    ),
)

# ─────────────────────────────────────────────────────────────
# 2. GOOGLE SHEETS
# ─────────────────────────────────────────────────────────────
def load_from_gsheet():
    try:
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive",
        ]
        creds = Credentials.from_service_account_info(
            dict(st.secrets["gcp_service_account"]), scopes=scopes
        )
        ws = gspread.authorize(creds).open_by_key(SPREADSHEET_ID).worksheet(SHEET_NAME)
        return ws.get_all_values(), None
    except Exception as e:
        return None, str(e)

# ─────────────────────────────────────────────────────────────
# 3. HELPERS
# ─────────────────────────────────────────────────────────────
def pb(v) -> bool:
    if pd.isna(v) or v == "":
        return False
    if isinstance(v, bool):
        return v
    if isinstance(v, (int, float)):
        return bool(v)
    s = str(v).strip()
    return s.lower() in TRUE_VALUES or s.upper() == "TRUE"


def parse_date(v):
    if pd.isna(v):
        return pd.NaT
    if isinstance(v, pd.Timestamp):
        return v if not pd.isna(v) else pd.NaT
    s = str(v).strip()
    if s in ["", "-", "#REF!", "nan", "NaT", "None"]:
        return pd.NaT
    for fmt in ["%y.%m.%d", "%Y.%m.%d", "%Y-%m-%d", "%y-%m-%d"]:
        try:
            return pd.to_datetime(s, format=fmt)
        except Exception:
            pass
    return pd.to_datetime(s, errors="coerce")


def h_filled(v) -> bool:
    if pd.isna(v):
        return False
    s = str(v).strip()
    return s not in ["", "nan", "NaT", "-", "#REF!", "None", "NaN"]


def is_filled_text(v) -> bool:
    if pd.isna(v):
        return False
    s = str(v).strip()
    return s not in ["", "nan", "NaT", "-", "#REF!", "None", "NaN"]


def safe_rate(n, d) -> float:
    return round(n / d * 100, 1) if d and d > 0 else 0.0


def classify_delay(v) -> str:
    if pd.isna(v):
        return "없음"
    s = str(v).strip()
    if s in ["", "-"]:
        return "없음"
    sl = s.lower()
    for cat, kws in DELAY_MAP.items():
        if any(k.lower() in sl for k in kws):
            return cat
    return "기타"


def norm_req(v) -> str:
    if pd.isna(v) or str(v).strip() == "":
        return "미입력"
    return re.split(r"[,/|·\n\s]+", str(v).strip())[0].strip()


def first_valid_column(df: pd.DataFrame, candidates: list[str]) -> str | None:
    for col in candidates:
        if col in df.columns:
            return col
    return None

# ─────────────────────────────────────────────────────────────
# 4. PREPROCESSING
# ─────────────────────────────────────────────────────────────
def _build(values: list) -> pd.DataFrame:
    hi = 2
    for i, row in enumerate(values[:10]):
        if any("브랜드" in str(c) for c in row):
            hi = i
            break

    raw = pd.DataFrame(values[hi + 1 :], columns=values[hi])
    raw.columns = [str(c).strip().replace("\n", " ").replace("\r", " ") for c in raw.columns]

    brand_col = first_valid_column(raw, ["브랜드(영문)"])
    requester_col = raw.columns[1] if len(raw.columns) > 1 else first_valid_column(raw, ["요청자"])
    reviewer_col = raw.columns[2] if len(raw.columns) > 2 else first_valid_column(raw, ["검토자"])
    e_col = raw.columns[4] if len(raw.columns) > 4 else first_valid_column(raw, ["검토 및 등록 요청 완료"])
    i_col = raw.columns[8] if len(raw.columns) > 8 else first_valid_column(raw, ["등록 완료 (앱 노출 시 체크)"])
    review_note_col = raw.columns[14] if len(raw.columns) > 14 else first_valid_column(raw, ["브랜드별 검토사항 결론"])
    remark_col = raw.columns[15] if len(raw.columns) > 15 else first_valid_column(raw, ["비고"])

    if brand_col is None:
        raise ValueError("'브랜드(영문)' 컬럼을 찾지 못했습니다.")
    if requester_col is None:
        raise ValueError("'요청자' 컬럼을 찾지 못했습니다.")
    if reviewer_col is None:
        raise ValueError("'검토자' 컬럼을 찾지 못했습니다.")
    if e_col is None:
        raise ValueError("E열(검토 및 등록 요청 완료) 컬럼을 찾지 못했습니다.")
    if i_col is None:
        raise ValueError("I열(등록 완료 체크) 컬럼을 찾지 못했습니다.")

    reg_done_date_col = first_valid_column(raw, ["등록 완료일"])
    reg_req_date_col = first_valid_column(raw, ["등록 요청일"])
    delay_reason_col = first_valid_column(raw, ["지연 사유"])
    country_col = first_valid_column(raw, ["국내/해외"])
    d_col = first_valid_column(raw, ["리스트업 완료"])
    f_col = first_valid_column(raw, ["상품 구매 요청"])
    g_col = first_valid_column(raw, ["상품 구매 완료"])

    base_mask = raw[brand_col].apply(lambda x: bool(str(x).strip()) and str(x).strip() not in ["", "nan"])
    if reg_done_date_col and reg_done_date_col in raw.columns:
        base_mask = base_mask & (raw[reg_done_date_col].astype(str).str.strip() != "#REF!")
    df = raw[base_mask].copy().reset_index(drop=True)

    df["등록완료일_dt"] = df[reg_done_date_col].apply(parse_date) if reg_done_date_col else pd.NaT
    df["등록요청일_dt"] = df[reg_req_date_col].apply(parse_date) if reg_req_date_col else pd.NaT

    iso = df["등록요청일_dt"].dt.isocalendar()
    df["년도"] = df["등록요청일_dt"].dt.year.astype("Int64")
    df["년월"] = df["등록요청일_dt"].dt.strftime("%Y-%m")
    df["분기"] = "Q" + df["등록요청일_dt"].dt.quarter.astype("Int64").astype(str)
    df["년분기"] = df["년도"].astype(str) + "-" + df["분기"]
    df["주차"] = iso.week.astype("Int64")
    df["년주차"] = iso.year.astype(str) + "-W" + df["주차"].astype(str).str.zfill(2)

    df["리드타임"] = (df["등록완료일_dt"] - df["등록요청일_dt"]).dt.days
    df["리드타임"] = df["리드타임"].where((df["리드타임"] >= 0) & (df["리드타임"] <= 180))
    today = pd.Timestamp.today().normalize()
    df["진행경과일"] = (today - df["등록요청일_dt"]).dt.days
    df["진행경과일"] = df["진행경과일"].where(df["진행경과일"] >= 0)

    df["D_listed"] = df[d_col].apply(pb) if d_col else False
    df["E_req_done"] = df[e_col].apply(pb)
    df["F_purchase_req"] = df[f_col].apply(pb) if f_col else False
    df["G_purchase_done"] = df[g_col].apply(pb) if g_col else False
    df["I_reg_done"] = df[i_col].apply(pb)
    df["H_filled"] = df[reg_req_date_col].apply(h_filled) if reg_req_date_col else False

    def country(v):
        s = str(v).strip() if pd.notna(v) else ""
        if "국내" in s:
            return "국내"
        if "해외" in s:
            return "해외"
        return "미입력"

    df["국내해외"] = df[country_col].apply(country) if country_col else "미입력"
    df["요청자_정제"] = df[requester_col].apply(norm_req)
    df["검토자_정제"] = df[reviewer_col].apply(lambda x: str(x).strip() if pd.notna(x) and str(x).strip() else "미입력")

    df["비고_txt"] = df[remark_col].apply(lambda x: str(x).strip() if pd.notna(x) else "") if remark_col else ""
    df["브랜드별검토사항결론_txt"] = df[review_note_col].apply(lambda x: str(x).strip() if pd.notna(x) else "") if review_note_col else ""
    df["지연분류"] = df[delay_reason_col].apply(classify_delay) if delay_reason_col else "없음"

    combined_not_allowed = df["브랜드별검토사항결론_txt"].fillna("") + " " + df["비고_txt"].fillna("")
    df["is_불가"] = combined_not_allowed.str.contains(r"등록\s*불가", na=False)

    def blocked_reason(row):
        parts = []
        if row.get("브랜드별검토사항결론_txt", "") and re.search(r"등록\s*불가", str(row.get("브랜드별검토사항결론_txt", ""))):
            parts.append(f"결론: {row['브랜드별검토사항결론_txt']}")
        if row.get("비고_txt", "") and re.search(r"등록\s*불가", str(row.get("비고_txt", ""))):
            parts.append(f"비고: {row['비고_txt']}")
        if not parts:
            if row.get("브랜드별검토사항결론_txt", ""):
                parts.append(f"결론: {row['브랜드별검토사항결론_txt']}")
            if row.get("비고_txt", ""):
                parts.append(f"비고: {row['비고_txt']}")
        return " | ".join(parts)

    df["불가사유"] = df.apply(lambda r: blocked_reason(r) if r["is_불가"] else "", axis=1)

    def stage(r):
        if r["is_불가"]:
            return "X.등록 불가"
        if r["I_reg_done"]:
            return "5.등록 완료"
        if r["G_purchase_done"]:
            return "4.구매 완료"
        if r["F_purchase_req"]:
            return "3.구매 요청"
        if r["E_req_done"]:
            return "2.검토/등록 요청"
        if r["D_listed"]:
            return "1.리스트업 완료"
        return "0.미진행"

    df["현재단계"] = df.apply(stage, axis=1)
    df["지연여부"] = df["지연분류"].apply(lambda x: "지연" if x != "없음" else "정상")

    df["B_exists"] = df[requester_col].apply(is_filled_text)
    df["wip_검토"] = df["B_exists"] & (~df["E_req_done"]) & (~df["I_reg_done"]) & (~df["is_불가"])
    df["wip_등록"] = df["B_exists"] & df["E_req_done"] & (~df["I_reg_done"]) & (~df["is_불가"])

    df["wip_종류"] = ""
    df.loc[df["wip_검토"], "wip_종류"] = "검토 진행중"
    df.loc[df["wip_등록"], "wip_종류"] = "등록 진행중"

    SLA_DAYS = 3
    df["SLA기준일"] = SLA_DAYS

    def sla_status(row):
        days = row.get("진행경과일")
        if pd.isna(days):
            return "미측정"
        if row.get("is_불가", False):
            return "클로즈"
        if days <= SLA_DAYS:
            return "정상"
        if days <= 5:
            return "주의"
        return "위반"

    df["SLA상태"] = df.apply(sla_status, axis=1)
    df["등록병목"] = df["wip_등록"] & (df["진행경과일"].fillna(0) > 5)
    df["include_in_scope"] = True
    df["I_reg_done_valid"] = df["I_reg_done"]
    df["분석모수"] = df[brand_col].apply(is_filled_text)

    return df


@st.cache_data(ttl=300, show_spinner=False)
def from_bytes(b: bytes) -> pd.DataFrame:
    raw = pd.read_excel(io.BytesIO(b), sheet_name="Summary", header=None)
    vals = raw.fillna("").astype(str).values.tolist()
    return _build(vals)


@st.cache_data(ttl=300, show_spinner=False)
def from_gsheet(_key: str, vals: list) -> pd.DataFrame:
    return _build(vals)


def render_header_filter_table(
    df: pd.DataFrame,
    *,
    height: int = 360,
    key: str | None = None,
    accent: str = "#111111",
):
    """Interactive table with click-to-open header filters."""
    if df is None or df.empty:
        return

    safe_df = df.copy()
    for col in safe_df.columns:
        safe_df[col] = safe_df[col].apply(lambda x: "" if pd.isna(x) else str(x))

    table_id = f"tbl_{key or uuid.uuid4().hex[:8]}"
    rows_json = json.dumps(safe_df.to_dict(orient="records"), ensure_ascii=False)
    cols_json = json.dumps(list(safe_df.columns), ensure_ascii=False)

    html_code = f"""
    <div id="{table_id}" class="oa-grid-wrap">
      <div class="oa-grid-toolbar">
        <div class="oa-grid-title">ALL DATA</div>
        <div class="oa-grid-meta">헤더 클릭 → 필터 열기</div>
      </div>
      <div class="oa-grid-scroller">
        <table class="oa-grid" id="{table_id}_table">
          <thead id="{table_id}_thead"></thead>
          <tbody id="{table_id}_tbody"></tbody>
        </table>
      </div>
    </div>

    <style>
      .oa-grid-wrap {{
        background: #ffffff;
        border: 1px solid #e8e8ee;
        border-radius: 14px;
        overflow: hidden;
        box-shadow: 0 6px 18px rgba(15, 23, 42, 0.04);
      }}
      .oa-grid-toolbar {{
        display:flex; align-items:center; justify-content:space-between;
        padding: 12px 14px; background:#fafafc; border-bottom:1px solid #ededf2;
      }}
      .oa-grid-title {{
        font-size: 11px; font-weight: 900; letter-spacing: 1.4px; color:{accent};
      }}
      .oa-grid-meta {{
        font-size: 11px; color:#8b8b95; font-weight:700;
      }}
      .oa-grid-scroller {{
        overflow:auto; max-height:{height}px;
      }}
      .oa-grid {{
        width:100%; border-collapse: separate; border-spacing:0; min-width: 1020px;
        font-family: Pretendard, -apple-system, BlinkMacSystemFont, sans-serif;
      }}
      .oa-grid thead th {{
        position: sticky; top: 0; z-index: 3;
        background:#f8f8fa; color:#111111; font-size:13px; font-weight:800;
        text-align:left; padding:0; border-bottom:1px solid #e9e9ef; white-space:nowrap;
      }}
      .oa-head-btn {{
        all: unset; display:flex; width:100%; align-items:center; justify-content:space-between;
        padding: 12px 12px; cursor:pointer; box-sizing:border-box;
      }}
      .oa-head-btn:hover {{
        background:#f0f1f5;
      }}
      .oa-filter-chip {{
        font-size:10px; color:#8f8f99; font-weight:900; letter-spacing:.5px;
      }}
      .oa-grid tbody td {{
        padding: 11px 12px; font-size:13px; color:#222; border-bottom:1px solid #f2f2f6;
        background:#fff; vertical-align: top;
      }}
      .oa-grid tbody tr:hover td {{
        background:#fcfcfd;
      }}
      .oa-filter-row td {{
        background:#ffffff; border-bottom:1px solid #ececf2; padding:10px 12px;
      }}
      .oa-filter-box {{
        display:none;
      }}
      .oa-filter-box.open {{
        display:block;
      }}
      .oa-filter-select, .oa-filter-input {{
        width:100%; border:1px solid #dcdee5; border-radius:10px; background:#fff;
        color:#111; font-size:12px; padding:8px 10px; outline:none;
      }}
      .oa-filter-actions {{
        display:flex; gap:8px; margin-top:8px;
      }}
      .oa-mini-btn {{
        border:none; border-radius:9px; padding:6px 10px; font-size:11px; font-weight:800; cursor:pointer;
      }}
      .oa-mini-btn.apply {{
        background:{accent}; color:#fff;
      }}
      .oa-mini-btn.reset {{
        background:#f2f3f6; color:#555;
      }}
      .oa-empty {{
        padding:22px 16px; color:#808089; font-size:13px; font-weight:700;
      }}
    </style>

    <script>
      const rows = {rows_json};
      const cols = {cols_json};
      const state = Object.fromEntries(cols.map(c => [c, ""]));

      const thead = document.getElementById("{table_id}_thead");
      const tbody = document.getElementById("{table_id}_tbody");

      function uniqValues(col) {{
        const vals = [...new Set(rows.map(r => (r[col] ?? "").toString()).filter(v => v !== ""))];
        vals.sort((a,b) => a.localeCompare(b, 'ko'));
        return vals;
      }}

      function buildHeader() {{
        const headTr = document.createElement("tr");
        cols.forEach(col => {{
          const th = document.createElement("th");
          const btn = document.createElement("button");
          btn.className = "oa-head-btn";
          btn.innerHTML = `<span>${{col}}</span><span class="oa-filter-chip">${{state[col] ? "FILTERED" : "ALL"}}</span>`;
          btn.onclick = () => toggleFilter(col);
          th.appendChild(btn);
          headTr.appendChild(th);
        }});
        thead.innerHTML = "";
        thead.appendChild(headTr);

        const filterTr = document.createElement("tr");
        filterTr.className = "oa-filter-row";
        cols.forEach(col => {{
          const td = document.createElement("td");
          const box = document.createElement("div");
          box.className = "oa-filter-box";
          box.id = `${{col}}_box_{table_id}`;

          const values = uniqValues(col);
          const shortList = values.length > 0 && values.length <= 50;

          if (shortList) {{
            const select = document.createElement("select");
            select.className = "oa-filter-select";
            select.id = `${{col}}_input_{table_id}`;
            const base = document.createElement("option");
            base.value = "";
            base.textContent = "ALL";
            select.appendChild(base);
            values.forEach(v => {{
              const opt = document.createElement("option");
              opt.value = v;
              opt.textContent = v;
              if (state[col] === v) opt.selected = true;
              select.appendChild(opt);
            }});
            box.appendChild(select);
          }} else {{
            const input = document.createElement("input");
            input.className = "oa-filter-input";
            input.id = `${{col}}_input_{table_id}`;
            input.placeholder = "검색어 입력";
            input.value = state[col] || "";
            box.appendChild(input);
          }}

          const actions = document.createElement("div");
          actions.className = "oa-filter-actions";
          actions.innerHTML = `
            <button class="oa-mini-btn apply" onclick="window.applyFilter_{table_id}('${{col}}')">적용</button>
            <button class="oa-mini-btn reset" onclick="window.resetFilter_{table_id}('${{col}}')">초기화</button>
          `;
          box.appendChild(actions);
          td.appendChild(box);
          filterTr.appendChild(td);
        }});
        thead.appendChild(filterTr);
      }}

      function toggleFilter(col) {{
        cols.forEach(c => {{
          const el = document.getElementById(`${{c}}_box_{table_id}`);
          if (!el) return;
          if (c === col) {{
            el.classList.toggle("open");
          }} else {{
            el.classList.remove("open");
          }}
        }});
      }}

      function renderBody() {{
        const filtered = rows.filter(r => cols.every(col => {{
          const q = (state[col] ?? "").toString().trim().toLowerCase();
          if (!q) return true;
          const v = (r[col] ?? "").toString().toLowerCase();
          return v.includes(q);
        }}));

        tbody.innerHTML = "";
        if (filtered.length === 0) {{
          const tr = document.createElement("tr");
          const td = document.createElement("td");
          td.colSpan = cols.length;
          td.className = "oa-empty";
          td.textContent = "조건에 맞는 데이터가 없습니다.";
          tr.appendChild(td);
          tbody.appendChild(tr);
          return;
        }}

        filtered.forEach(row => {{
          const tr = document.createElement("tr");
          cols.forEach(col => {{
            const td = document.createElement("td");
            td.textContent = (row[col] ?? "").toString();
            tr.appendChild(td);
          }});
          tbody.appendChild(tr);
        }});
      }}

      window.applyFilter_{table_id} = function(col) {{
        const el = document.getElementById(`${{col}}_input_{table_id}`);
        state[col] = el ? el.value : "";
        buildHeader();
        renderBody();
      }}

      window.resetFilter_{table_id} = function(col) {{
        state[col] = "";
        buildHeader();
        renderBody();
      }}

      buildHeader();
      renderBody();
    </script>
    """
    components.html(html_code, height=height + 72, scrolling=False)



# ─────────────────────────────────────────────────────────────
# 5. SIDEBAR
# ─────────────────────────────────────────────────────────────
def sidebar(df: pd.DataFrame):
    with st.sidebar:
        st.markdown(
            """
        <div style='padding:20px 16px 14px;border-bottom:1px solid #1f1f1f;'>
          <div style='font-size:20px;font-weight:900;color:#fff;letter-spacing:-0.5px;line-height:1.1;'>
            OPS<span style='color:#d4ff00;'>·</span>INTEL
          </div>
          <div style='font-size:9px;color:#747474;margin-top:5px;letter-spacing:2.5px;font-weight:800;'>
            KREAM · 1P PRODUCT REGISTRATION
          </div>
        </div>
        """,
            unsafe_allow_html=True,
        )

        st.markdown("<div style='height:14px;'></div>", unsafe_allow_html=True)

        if st.button("↻  구글 시트 동기화", use_container_width=True, key="sync_btn_sidebar_main"):
            with st.spinner("연결 중..."):
                vals, err = load_from_gsheet()
            if err:
                st.error(f"연결 실패: {err}")
            else:
                from_gsheet.clear()
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.session_state.update(
                    {
                        "gsheet_values": vals,
                        "gsheet_ts": ts,
                        "source": "gsheet",
                    }
                )
                st.success("동기화 완료")
                time.sleep(0.4)
                st.rerun()

        if st.session_state.get("gsheet_ts"):
            st.markdown(
                f"<div style='font-size:10px;color:#8a8a8a;text-align:center;padding:5px 0 2px;'>"
                f"Last sync · {st.session_state['gsheet_ts']}</div>",
                unsafe_allow_html=True,
            )

        st.markdown(
            "<p style='color:#d6d6d6;font-size:10px;margin:14px 0 3px;font-weight:700;letter-spacing:0.5px;'>"
            "XLSX 보조 업로드</p>",
            unsafe_allow_html=True,
        )
        uploaded = st.file_uploader("", type=["xlsx"], label_visibility="collapsed", key="sidebar_file_uploader_main")
        if uploaded:
            from_bytes.clear()
            st.session_state["xlsx_bytes"] = uploaded.read()
            st.session_state["source"] = "xlsx"
            st.rerun()

        src = st.session_state.get("source", "none")
        label = {"gsheet": "● Google Sheet", "xlsx": "● Excel 파일"}.get(src, "● 연결 없음")
        color = {"gsheet": "#d4ff00", "xlsx": "#f5a623"}.get(src, "#6f6f6f")
        st.markdown(
            f"<div style='font-size:11px;color:{color};text-align:center;padding:6px 0 14px;font-weight:800;'>{label}</div>",
            unsafe_allow_html=True,
        )

        st.markdown(
            "<div style='border-top:1px solid #1f1f1f;padding-top:14px;'>"
            "<p style='color:#9a9a9a;font-size:9px;letter-spacing:2px;font-weight:900;margin-bottom:12px;'>FILTERS</p>",
            unsafe_allow_html=True,
        )

        avail = [r for r in FIXED_REVIEWERS if r in df["검토자_정제"].unique()]
        f_rev = st.multiselect("검토자", FIXED_REVIEWERS, default=avail, key="sidebar_filter_reviewer")

        c_opts = sorted(df["국내해외"].dropna().unique().tolist())
        f_country = st.multiselect("국내 / 해외", c_opts, default=c_opts, key="sidebar_filter_country")

        y_opts = sorted([y for y in df["년도"].dropna().unique().tolist() if int(y) >= 2024])
        f_year = st.multiselect("분석 연도", y_opts, default=y_opts, key="sidebar_filter_year")

        s_opts = sorted(df["현재단계"].dropna().unique().tolist())
        f_stage = st.multiselect("진행 단계", s_opts, default=s_opts, key="sidebar_filter_stage")

        f_delay = st.multiselect("지연 여부", ["정상", "지연"], default=["정상", "지연"], key="sidebar_filter_delay")
        keyword = st.text_input("브랜드 검색", placeholder="예: Jellycat", key="sidebar_filter_keyword")

        st.markdown("</div>", unsafe_allow_html=True)
        st.markdown(
            f"<div style='border-top:1px solid #1f1f1f;padding-top:10px;font-size:10px;color:#8a8a8a;text-align:center;'>"
            f"Total {len(df):,}행 · {datetime.now().strftime('%Y-%m-%d')}</div>",
            unsafe_allow_html=True,
        )

    return f_rev, f_country, f_year, f_stage, f_delay, keyword

# ─────────────────────────────────────────────────────────────
# 6. LANDING
# ─────────────────────────────────────────────────────────────
def landing():
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown(
            """
        <div style='text-align:center;padding:90px 0 28px;'>
          <div style='font-size:48px;font-weight:900;letter-spacing:-2px;color:#111;line-height:1;'>
            OPS<span style='background:#111;color:#d4ff00;padding:0 8px;border-radius:6px;'>·</span>INTEL
          </div>
          <p style='color:#8a8a8a;font-size:12px;margin-top:10px;letter-spacing:2px;font-weight:800;text-transform:uppercase;'>
            KREAM · 1P Product Registration · Executive Dashboard
          </p>
        </div>
        <div style='background:#111;border-radius:16px;padding:28px;'>
          <p style='color:#d4ff00;font-size:9px;font-weight:900;letter-spacing:2.5px;margin:0 0 14px;text-transform:uppercase;'>Quick Start</p>
          <ol style='color:#c6c6c6;line-height:2.3;font-size:14px;margin:0;padding-left:18px;'>
            <li>왼쪽 사이드바 → <b style='color:#fff;'>↻ 구글 시트 동기화</b> 클릭</li>
            <li>실시간 Summary 시트 자동 로드</li>
            <li>검토자 / 국가 / 연도 / 단계 필터 조정</li>
          </ol>
        </div>
        """,
            unsafe_allow_html=True,
        )

# ─────────────────────────────────────────────────────────────
# 7. DASHBOARD
# ─────────────────────────────────────────────────────────────
def dashboard(df: pd.DataFrame, src: str, df_scope_wip: pd.DataFrame):
    df_kpi = df[df["년도"].isin([2024, 2025, 2026]) | df["년도"].isna()].copy()
    df_24 = df[(df["등록요청일_dt"] >= "2024-01-01") | df["등록요청일_dt"].isna()].copy()
    scope_wip = df_scope_wip.copy()
    scope_wip = scope_wip[(scope_wip["년도"].fillna(2024).astype("Int64") >= 2024) | scope_wip["년도"].isna()]

    ts = st.session_state.get("gsheet_ts", datetime.now().strftime("%Y-%m-%d %H:%M"))
    tag = "Google Sheet · LIVE" if src == "gsheet" else "Excel Upload"
    st.markdown(
        f"""
    <div class='topbar'>
      <div class='topbar-logo'>OPS<span>·</span>INTEL</div>
      <div class='topbar-right'>
        <span class='topbar-src'>{tag} · {ts}</span>
        <span class='live-chip'>LIVE</span>
      </div>
    </div>
    """,
        unsafe_allow_html=True,
    )

    # ══════════════════════════════════════════════
    # SECTION 1 — KPI (2024–2026)
    # ══════════════════════════════════════════════
    st.markdown("<div class='sec'>종합 운영 지표</div>", unsafe_allow_html=True)

    total = int(df_kpi["분석모수"].sum()) if "분석모수" in df_kpi.columns else len(df_kpi)
    done = int(df_kpi["I_reg_done"].sum())
    lt_avg = df_kpi["리드타임"].mean()
    lt_med = df_kpi["리드타임"].median()
    delayed = int((df_kpi["지연여부"] == "지연").sum())

    wip_reg = scope_wip[scope_wip["wip_등록"]].copy()
    wip_rev = scope_wip[scope_wip["wip_검토"]].copy()
    blocked_df = scope_wip[scope_wip["is_불가"]].copy()
    wip_tot = len(wip_reg) + len(wip_rev)

    c1, c2, c3, c4, c5 = st.columns(5)

    def kcard(col, label, num, unit, sub, bar_color, badge="", badge_bg="", badge_fg=""):
        b = (
            f"<div class='kcard-badge' style='background:{badge_bg};color:{badge_fg};'>{badge}</div>"
            if badge
            else ""
        )
        col.markdown(
            f"""
        <div class='kcard'>
          <div class='kcard-bar' style='background:{bar_color};'></div>
          <div class='kcard-label'>{label}</div>
          <div>
            <span class='kcard-value'>{num}</span>
            <span class='kcard-unit'>{unit}</span>
          </div>
          {b}
          <div class='kcard-sub'>{sub}</div>
        </div>
        """,
            unsafe_allow_html=True,
        )

    kcard(c1, "전체 분석 건수", f"{total:,}", "건", "A열 브랜드 기준", "#111111")
    kcard(
        c2,
        "최종 등록 완료",
        f"{done:,}",
        "건",
        "I열 체크 기준",
        "#05c072",
        f"등록률 {safe_rate(done, total)}%",
        "#05c07220",
        "#05c072",
    )
    kcard(
        c3,
        "평균 리드타임",
        f"{lt_avg:.1f}" if pd.notna(lt_avg) else "N/A",
        "일",
        f"중앙값 {lt_med:.0f}일" if pd.notna(lt_med) else "-",
        "#8b5cf6",
    )
    kcard(
        c4,
        "지연 발생 건수",
        f"{delayed:,}",
        "건",
        "지연 사유 기입 건",
        "#f04452",
        f"지연률 {safe_rate(delayed, total)}%",
        "#f0445220",
        "#f04452",
    )
    kcard(c5, "진행 중 WIP", f"{wip_tot:,}", "건", "검토 + 등록 진행중 합계", "#d4ff00")

    # ══════════════════════════════════════════════
    # SECTION 1-4 — 등록 불가
    # ══════════════════════════════════════════════
    st.markdown("<div class='sec'>핵심 운영 보드 · Main Control Board</div>", unsafe_allow_html=True)
    st.markdown("<div class='sec'>🔴 등록 불가 클로즈 케이스</div>", unsafe_allow_html=True)
    if blocked_df.empty:
        st.success("현재 등록 불가 클로즈 케이스 없음")
    else:
        blocked_show = blocked_df[["브랜드(영문)", "요청자_정제", "검토자_정제", "국내해외", "현재단계", "비고_txt", "불가사유"]].rename(columns={"브랜드(영문)":"브랜드", "요청자_정제":"요청자", "검토자_정제":"검토자", "비고_txt":"비고"})
        render_header_filter_table(blocked_show, height=320, key="blocked_main", accent="#f04452")

    # ══════════════════════════════════════════════
    # SECTION 1-5 — 검토 진행중 브랜드
    # ══════════════════════════════════════════════
    st.markdown("<div class='sec'>🟡 검토 진행중 브랜드</div>", unsafe_allow_html=True)
    review_cols = ["브랜드(영문)", "요청자_정제", "검토자_정제", "국내해외", "현재단계", "비고_txt"]
    review_show = wip_rev[review_cols].rename(columns={"브랜드(영문)":"브랜드", "요청자_정제":"요청자", "검토자_정제":"검토자", "비고_txt":"비고"})
    if review_show.empty:
        st.success("현재 검토 진행중 브랜드 없음")
    else:
        review_show = review_show.sort_values(["브랜드", "요청자"], ascending=[True, True])
        render_header_filter_table(review_show, height=350, key="review_main", accent="#f5a623")

    # ══════════════════════════════════════════════
    # SECTION 1-6 — 등록 진행중 브랜드
    # ══════════════════════════════════════════════
    st.markdown("<div class='sec'>🔵 등록 진행중 브랜드</div>", unsafe_allow_html=True)
    reg_cols = ["브랜드(영문)", "요청자_정제", "검토자_정제", "국내해외", "현재단계", "진행경과일", "SLA상태", "비고_txt"]
    reg_show = wip_reg[reg_cols].rename(columns={"브랜드(영문)":"브랜드", "요청자_정제":"요청자", "검토자_정제":"검토자", "비고_txt":"비고"})
    if reg_show.empty:
        st.success("현재 등록 진행중 브랜드 없음")
    else:
        reg_show = reg_show.sort_values(["진행경과일", "브랜드"], ascending=[False, True])
        render_header_filter_table(reg_show, height=350, key="reg_main", accent="#3b82f6")

    st.markdown("<hr class='kdiv'>", unsafe_allow_html=True)
    # ══════════════════════════════════════════════
    # SECTION 2 — 파이프라인 (2024–2026)
    # ══════════════════════════════════════════════
    st.markdown("<div class='sec'>등록 파이프라인</div>", unsafe_allow_html=True)

    p1, p2, p3 = st.columns(3)

    with p1:
        fig = go.Figure(
            go.Funnel(
                y=["전체 분석", "검토 진행", "검토/등록 요청", "최종 등록"],
                x=[
                    int(df_kpi["분석모수"].sum()) if "분석모수" in df_kpi.columns else len(df_kpi),
                    int((df_kpi["B_exists"] & ~df_kpi["I_reg_done"] & ~df_kpi["is_불가"]).sum()),
                    int(df_kpi.loc[~df_kpi["is_불가"], "E_req_done"].sum()),
                    int(df_kpi["I_reg_done"].sum()),
                ],
                textinfo="value+percent previous",
                textfont=dict(size=13, color="#ffffff"),
                marker=dict(color=["#444444", "#666666", "#888888", "#05c072"]),
                connector=dict(line=dict(color="#eeeeee", width=1.5)),
            )
        )
        fig.update_layout(**CHART_TPL, title="<b>등록 전환 Funnel</b>", height=320)
        st.plotly_chart(fig, use_container_width=True)

    with p2:
        sc = df_kpi["현재단계"].value_counts().reset_index()
        sc.columns = ["단계", "건수"]
        fig = go.Figure(
            go.Pie(
                labels=sc["단계"],
                values=sc["건수"],
                hole=0.62,
                marker=dict(
                    colors=[STAGE_COLORS.get(s, "#cccccc") for s in sc["단계"]],
                    line=dict(color="#ffffff", width=2),
                ),
                textinfo="percent",
                textfont=dict(size=12),
            )
        )
        fig.update_layout(
            **CHART_TPL,
            title="<b>단계별 분포</b>",
            height=320,
            legend=dict(font=dict(size=11), x=1.02, y=0.5),
        )
        st.plotly_chart(fig, use_container_width=True)

    with p3:
        cross = (
            df_kpi[df_kpi["국내해외"].isin(["국내", "해외"])]
            .groupby(["국내해외", "현재단계"])
            .size()
            .reset_index(name="건수")
        )
        fig = px.bar(
            cross,
            x="국내해외",
            y="건수",
            color="현재단계",
            color_discrete_map=STAGE_COLORS,
            barmode="stack",
            title="<b>국내 / 해외별 단계</b>",
        )
        fig.update_layout(
            **CHART_TPL,
            height=320,
            legend=dict(font=dict(size=11), x=1.02, y=0.5),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.markdown("<hr class='kdiv'>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════
    # SECTION 3 — 2024+ 심화 분석
    # ══════════════════════════════════════════════
    st.markdown("<div class='sec'>운영 지표 딥 케이스</div>", unsafe_allow_html=True)

    if df_24.empty:
        st.info("선택 필터 내 2024년 이후 데이터가 없습니다.")
    else:
        tab1, tab2, tab3, tab4 = st.tabs(["시계열 트렌드", "리드타임 분석", "지연 분석", "담당자 성과"])

        with tab1:
            view = st.radio("집계 단위", ["월별", "주차별", "분기별"], horizontal=True, key="timeseries_granularity")
            gc = {"월별": "년월", "주차별": "년주차", "분기별": "년분기"}[view]
            ts_df = (
                df_24.dropna(subset=[gc])
                .groupby(gc)
                .agg(
                    등록완료=("I_reg_done", "sum"),
                    전체건수=("분석모수", "sum"),
                    평균리드타임=("리드타임", "mean"),
                )
                .reset_index()
            )
            ts_df.columns = ["기간", "등록완료", "전체건수", "평균리드타임"]
            ts_df["등록률"] = (ts_df["등록완료"] / ts_df["전체건수"] * 100).round(1)

            fig = make_subplots(
                rows=2,
                cols=1,
                subplot_titles=("등록 완료 vs 전체", "등록률 (%)"),
                vertical_spacing=0.14,
                shared_xaxes=True,
            )
            fig.add_trace(
                go.Bar(x=ts_df["기간"], y=ts_df["전체건수"], name="전체", marker_color="#ebebeb"),
                row=1,
                col=1,
            )
            fig.add_trace(
                go.Bar(x=ts_df["기간"], y=ts_df["등록완료"], name="등록완료", marker_color="#111111"),
                row=1,
                col=1,
            )
            fig.add_trace(
                go.Scatter(
                    x=ts_df["기간"],
                    y=ts_df["등록률"],
                    name="등록률",
                    mode="lines+markers",
                    line=dict(color="#05c072", width=2.5),
                    marker=dict(size=5),
                    fill="tozeroy",
                    fillcolor="rgba(5,192,114,0.07)",
                ),
                row=2,
                col=1,
            )
            fig.update_layout(**CHART_TPL, height=460, barmode="overlay")
            fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
            st.plotly_chart(fig, use_container_width=True)
            with st.expander("상세 수치"):
                st.dataframe(
                    ts_df.style.format(
                        {
                            "등록완료": "{:,}",
                            "전체건수": "{:,}",
                            "평균리드타임": "{:.1f}",
                            "등록률": "{:.1f}%",
                        }
                    ),
                    use_container_width=True,
                    hide_index=True,
                )

        with tab2:
            lt = df_24[df_24["리드타임"].notna()].copy()
            r1, r2 = st.columns(2)
            cm = {"국내": "#111111", "해외": "#888888", "미입력": "#cccccc"}
            with r1:
                fig = px.box(
                    lt,
                    x="국내해외",
                    y="리드타임",
                    color="국내해외",
                    title="<b>리드타임 분포</b>",
                    points="outliers",
                    color_discrete_map=cm,
                )
                fig.update_layout(**CHART_TPL, height=350, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            with r2:
                fig = px.histogram(
                    lt,
                    x="리드타임",
                    color="국내해외",
                    nbins=30,
                    barmode="overlay",
                    opacity=0.75,
                    title="<b>리드타임 빈도 분포</b>",
                    color_discrete_map=cm,
                )
                fig.update_layout(**CHART_TPL, height=350)
                st.plotly_chart(fig, use_container_width=True)

            stat = (
                lt.groupby("국내해외")["리드타임"]
                .agg(건수="count", 평균="mean", 중앙값="median", 최솟값="min", 최댓값="max")
                .reset_index()
                .round(1)
            )
            st.dataframe(
                stat.style.format(
                    {
                        "평균": "{:.1f}일",
                        "중앙값": "{:.1f}일",
                        "최솟값": "{:.0f}일",
                        "최댓값": "{:.0f}일",
                    }
                ),
                use_container_width=True,
                hide_index=True,
            )

        with tab3:
            ddf = df_24[df_24["지연여부"] == "지연"]
            ca, cb, cc = st.columns(3)
            ca.metric("지연 건수", f"{len(ddf):,}건")
            cb.metric("정상 건수", f"{len(df_24) - len(ddf):,}건")
            cc.metric("지연률", f"{safe_rate(len(ddf), len(df_24))}%")
            d1, d2 = st.columns(2)
            with d1:
                dc = df_24["지연분류"].value_counts().reset_index()
                dc.columns = ["분류", "건수"]
                dc = dc[dc["분류"] != "없음"]
                fig = px.bar(
                    dc,
                    y="분류",
                    x="건수",
                    orientation="h",
                    title="<b>지연 사유 유형별 건수</b>",
                    color="건수",
                    color_continuous_scale=["#f5f5f5", "#f04452"],
                )
                fig.update_layout(**CHART_TPL, height=330)
                st.plotly_chart(fig, use_container_width=True)
            with d2:
                dm = df_24.groupby(["년월", "지연여부"]).size().reset_index(name="건수")
                fig = px.bar(
                    dm,
                    x="년월",
                    y="건수",
                    color="지연여부",
                    barmode="stack",
                    title="<b>월별 지연 / 정상 현황</b>",
                    color_discrete_map={"정상": "#05c072", "지연": "#f04452"},
                )
                fig.update_layout(**CHART_TPL, height=330)
                st.plotly_chart(fig, use_container_width=True)
            if len(ddf) > 0:
                with st.expander(f"지연 건 상세 ({len(ddf)}건)"):
                    sc = [
                        "브랜드(영문)",
                        "요청자_정제",
                        "검토자_정제",
                        "국내해외",
                        "지연분류",
                        "지연 사유",
                        "리드타임",
                        "현재단계",
                    ]
                    st.dataframe(
                        ddf[sc].sort_values("리드타임", ascending=False),
                        use_container_width=True,
                        hide_index=True,
                    )

        with tab4:
            pr = (
                df_24.groupby("검토자_정제")
                .agg(
                    담당건수=("I_reg_done", "count"),
                    등록완료=("I_reg_done", "sum"),
                    평균리드타임=("리드타임", "mean"),
                    지연건수=("지연여부", lambda x: (x == "지연").sum()),
                )
                .reset_index()
            )
            pr["등록률"] = (pr["등록완료"] / pr["담당건수"] * 100).round(1)
            pr["지연률"] = (pr["지연건수"] / pr["담당건수"] * 100).round(1)
            pr = pr.sort_values("담당건수", ascending=False)

            fig = make_subplots(rows=1, cols=3, subplot_titles=("담당 건수", "등록률 (%)", "평균 리드타임 (일)"))
            for i, (c_, col_) in enumerate(
                [("담당건수", "#111111"), ("등록률", "#05c072"), ("평균리드타임", "#f5a623")]
            ):
                fig.add_trace(
                    go.Bar(
                        x=pr["검토자_정제"],
                        y=pr[c_].round(1),
                        name=c_,
                        marker_color=col_,
                        text=pr[c_].round(1),
                        textposition="outside",
                        textfont=dict(size=12, color="#333333"),
                    ),
                    row=1,
                    col=i + 1,
                )
            fig.update_layout(**CHART_TPL, height=360, showlegend=False)
            st.plotly_chart(fig, use_container_width=True)

            preq = (
                df_24.groupby("요청자_정제")
                .agg(요청건수=("분석모수", "sum"), 등록완료=("I_reg_done", "sum"))
                .reset_index()
            )
            preq["등록률"] = (preq["등록완료"] / preq["요청건수"] * 100).round(1)
            preq = preq.sort_values("요청건수", ascending=False).head(15)
            fig = px.bar(
                preq,
                x="요청자_정제",
                y="요청건수",
                color="등록률",
                color_continuous_scale=["#e8e8e8", "#111111"],
                title="<b>요청자별 등록 요청 건수 TOP 15</b>",
                text="요청건수",
            )
            fig.update_layout(**CHART_TPL, height=330)
            st.plotly_chart(fig, use_container_width=True)

    st.markdown("<hr class='kdiv'>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════
    # SECTION 4 — YoY (2023–2026)
    # ══════════════════════════════════════════════
    st.markdown("<div class='sec'>연도별 YoY</div>", unsafe_allow_html=True)

    yoy = (
        df.groupby("년도")
        .agg(
            전체건수=("분석모수", "sum"),
            등록완료=("I_reg_done", "sum"),
            평균리드타임=("리드타임", "mean"),
            지연건수=("지연여부", lambda x: (x == "지연").sum()),
        )
        .reset_index()
        .dropna(subset=["년도"])
    )
    yoy["등록률"] = (yoy["등록완료"] / yoy["전체건수"] * 100).round(1)
    yoy["지연률"] = (yoy["지연건수"] / yoy["전체건수"] * 100).round(1)
    yoy["년도"] = yoy["년도"].astype(int).astype(str)

    y1, y2 = st.columns(2)
    with y1:
        fig = go.Figure()
        fig.add_trace(
            go.Bar(
                x=yoy["년도"],
                y=yoy["전체건수"],
                name="전체",
                marker_color="#e8e8e8",
                text=yoy["전체건수"],
                textposition="outside",
            )
        )
        fig.add_trace(
            go.Bar(
                x=yoy["년도"],
                y=yoy["등록완료"],
                name="등록완료",
                marker_color="#111111",
                text=yoy["등록완료"],
                textposition="outside",
            )
        )
        fig.update_layout(**CHART_TPL, title="<b>연도별 전체 vs 등록완료</b>", barmode="overlay", height=330)
        st.plotly_chart(fig, use_container_width=True)
    with y2:
        fig = make_subplots(specs=[[{"secondary_y": True}]])
        fig.add_trace(
            go.Bar(
                x=yoy["년도"],
                y=yoy["평균리드타임"].round(1),
                name="리드타임(일)",
                marker_color="#888888",
                text=yoy["평균리드타임"].round(1),
                textposition="outside",
            ),
            secondary_y=False,
        )
        fig.add_trace(
            go.Scatter(
                x=yoy["년도"],
                y=yoy["지연률"],
                name="지연률(%)",
                mode="lines+markers+text",
                text=[f"{v}%" for v in yoy["지연률"]],
                textposition="top center",
                textfont=dict(color="#f04452", size=12),
                line=dict(color="#f04452", width=2.5),
                marker=dict(size=8, color="#f04452"),
            ),
            secondary_y=True,
        )
        fig.update_layout(**CHART_TPL, title="<b>연도별 리드타임 vs 지연률</b>", height=330)
        fig.update_yaxes(title_text="리드타임(일)", secondary_y=False, showgrid=True, gridcolor="#f0f0f0")
        fig.update_yaxes(title_text="지연률(%)", secondary_y=True, showgrid=False)
        st.plotly_chart(fig, use_container_width=True)

    st.dataframe(
        yoy.style.format(
            {
                "전체건수": "{:,}",
                "등록완료": "{:,}",
                "지연건수": "{:,}",
                "평균리드타임": "{:.1f}일",
                "등록률": "{:.1f}%",
                "지연률": "{:.1f}%",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("<hr class='kdiv'>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════
    # SECTION 1-2 — REVIEWER KPI
    # ══════════════════════════════════════════════
    st.markdown("<div class='sec'>검토자별 성과 KPI · Performance Analytics</div>", unsafe_allow_html=True)

    reviewer_kpi = (
        scope_wip.groupby("검토자_정제")
        .agg(
            담당건수=("브랜드(영문)", "count"),
            검토진행중=("wip_검토", "sum"),
            등록진행중=("wip_등록", "sum"),
            등록완료=("I_reg_done", "sum"),
            등록불가=("is_불가", "sum"),
            SLA위반=("SLA상태", lambda x: (x == "위반").sum()),
            평균진행경과일=("진행경과일", "mean"),
            평균리드타임=("리드타임", "mean"),
        )
        .reset_index()
        .sort_values(["담당건수", "등록완료"], ascending=[False, False])
    )
    reviewer_kpi["등록완료율"] = (reviewer_kpi["등록완료"] / (reviewer_kpi["담당건수"] - reviewer_kpi["등록불가"]).replace(0, pd.NA) * 100).round(1)
    st.dataframe(
        reviewer_kpi.style.format({
            "평균진행경과일": "{:.1f}일",
            "평균리드타임": "{:.1f}일",
            "등록완료율": "{:.1f}%",
        }),
        use_container_width=True,
        hide_index=True,
        height=260,
    )

    if False:
        pass

    # ══════════════════════════════════════════════
    # SECTION 1-3 — SLA
    # ══════════════════════════════════════════════
    if False:
        st.markdown("<div class='sec'>브랜드별 SLA 트래킹 · Monitoring</div>", unsafe_allow_html=True)
        sla_left, sla_right = st.columns([4, 6])

        with sla_left:
            st.markdown(
                """
                <div class='info-card'>
                  <div class='info-card-title'>SLA 정의</div>
                  <div class='info-card-sub'>
                    <span class='sla-chip' style='background:#eaf8ef;color:#05c072;'>정상 · 3일 이내</span>
                    <span class='sla-chip' style='background:#fff5df;color:#f5a623;'>주의 · 4~5일</span>
                    <span class='sla-chip' style='background:#ffe8ea;color:#f04452;'>위반 · 6일 이상</span>
                    <span class='sla-chip' style='background:#f2f2f2;color:#777777;'>클로즈 · 등록 불가</span>
                  </div>
                  <div class='info-card-sub' style='margin-top:10px;'>진행경과일 = 오늘 - 등록요청일 기준입니다. 등록 불가 케이스는 WIP에서 제외하고 별도 클로즈로 관리합니다.</div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with sla_right:
            sla_stat = scope_wip["SLA상태"].value_counts().reset_index()
            if not sla_stat.empty:
                sla_stat.columns = ["상태", "건수"]
                fig = px.bar(
                    sla_stat,
                    x="상태",
                    y="건수",
                    color="상태",
                    color_discrete_map={"정상":"#05c072","주의":"#f5a623","위반":"#f04452","클로즈":"#7a7a7a","미측정":"#c7c7c7"},
                    title="<b>SLA 상태 분포</b>",
                    text="건수",
                )
                fig.update_layout(**CHART_TPL, height=260, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)

        sla_cols = ["브랜드(영문)", "요청자_정제", "검토자_정제", "현재단계", "진행경과일", "SLA상태", "비고_txt"]
        sla_show = scope_wip[sla_cols].rename(columns={"브랜드(영문)":"브랜드", "요청자_정제":"요청자", "검토자_정제":"검토자", "비고_txt":"비고"})
        st.dataframe(sla_show.sort_values(["진행경과일", "브랜드"], ascending=[False, True]), use_container_width=True, hide_index=True, height=260)

    # ══════════════════════════════════════════════
    
# SECTION 4-2 — 등록 병목
    # ══════════════════════════════════════════════
    st.markdown("<div class='sec'>등록 병목 브랜드 · 5일 초과</div>", unsafe_allow_html=True)
    bottleneck_df = wip_reg[wip_reg["진행경과일"].fillna(0) > 5].copy()
    if bottleneck_df.empty:
        st.success("현재 등록 병목 브랜드 없음")
    else:
        st.markdown(
            f"<div class='info-card' style='margin-bottom:14px;'><div class='info-card-title'>자동 병목 알림</div><div class='action-box-value' style='color:#f04452;'>{len(bottleneck_df):,}건</div><div class='info-card-sub'>등록 요청 이후 5일을 초과한 등록 진행중 브랜드입니다.</div></div>",
            unsafe_allow_html=True,
        )
        bt_show = bottleneck_df[["브랜드(영문)", "요청자_정제", "검토자_정제", "진행경과일", "SLA상태", "비고_txt"]].rename(columns={"브랜드(영문)":"브랜드", "요청자_정제":"요청자", "검토자_정제":"검토자", "비고_txt":"비고"})
        st.dataframe(bt_show.sort_values(["진행경과일", "브랜드"], ascending=[False, True]), use_container_width=True, hide_index=True, height=260)

    st.markdown("<hr class='kdiv'>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════
    # SECTION 5 — 마스터 트래킹 (2024–2026)
    # ══════════════════════════════════════════════
    st.markdown("<div class='sec'>마스터 업무 트래킹</div>", unsafe_allow_html=True)

    MCOLS = [
        "브랜드(영문)",
        "요청자_정제",
        "검토자_정제",
        "국내해외",
        "현재단계",
        "wip_종류",
        "지연분류",
        "리드타임",
        "년월",
        "비고_txt",
    ]
    MREN = {
        "브랜드(영문)": "브랜드",
        "요청자_정제": "요청자",
        "검토자_정제": "검토자",
        "비고_txt": "비고",
        "년월": "등록년월",
        "wip_종류": "WIP구분",
    }

    master = df[MCOLS].rename(columns=MREN).copy()

    st.markdown("<div class='master-box'>", unsafe_allow_html=True)
    st.markdown("<div class='filter-row-label'>Column Filters</div>", unsafe_allow_html=True)

    fc = st.columns(7)

    def csel(container, label, series, key):
        opts = ["전체"] + sorted([x for x in series.dropna().unique() if str(x).strip() not in ["", "nan"]])
        return container.selectbox(label, opts, key=key)

    s_rev = csel(fc[0], "검토자", master["검토자"], "m_rev")
    s_req = csel(fc[1], "요청자", master["요청자"], "m_req")
    s_nat = csel(fc[2], "국내/해외", master["국내해외"], "m_nat")
    s_stage = csel(fc[3], "현재단계", master["현재단계"], "m_stage")
    s_wip = csel(fc[4], "WIP구분", master["WIP구분"], "m_wip")
    s_delay = csel(fc[5], "지연분류", master["지연분류"], "m_delay")
    s_month = csel(fc[6], "등록년월", master["등록년월"], "m_month")

    view = master.copy()
    if s_rev != "전체":
        view = view[view["검토자"] == s_rev]
    if s_req != "전체":
        view = view[view["요청자"] == s_req]
    if s_nat != "전체":
        view = view[view["국내해외"] == s_nat]
    if s_stage != "전체":
        view = view[view["현재단계"] == s_stage]
    if s_wip != "전체":
        view = view[view["WIP구분"] == s_wip]
    if s_delay != "전체":
        view = view[view["지연분류"] == s_delay]
    if s_month != "전체":
        view = view[view["등록년월"] == s_month]

    sc1, _, _ = st.columns([2, 2, 6])
    sort_by = sc1.selectbox("정렬", ["등록년월 최신순", "리드타임 내림차순", "현재단계"], key="msort")
    if sort_by == "등록년월 최신순":
        view = view.sort_values("등록년월", ascending=False)
    elif sort_by == "리드타임 내림차순":
        view = view.sort_values("리드타임", ascending=False)
    else:
        view = view.sort_values("현재단계")

    st.caption(f"표시 {len(view):,}건 / 전체 {len(master):,}건")

    def sc_stage(v):
        c = STAGE_COLORS.get(v, "#888888")
        bg = STAGE_BG.get(v, "#eeeeee")
        return f"background-color:{bg};color:{c};font-weight:800;"

    def sc_delay(v):
        return "color:#f04452;font-weight:700;" if v != "없음" else "color:#c0c0c0;"

    def sc_lt(v):
        try:
            n = float(v)
            if n > 30:
                return "color:#f04452;font-weight:700;"
            if n > 14:
                return "color:#f5a623;font-weight:700;"
            return "color:#05c072;font-weight:700;"
        except Exception:
            return ""

    def sc_wip(v):
        if v == "검토 진행중":
            return "background-color:#eff6ff;color:#3b82f6;font-weight:800;"
        if v == "등록 진행중":
            return "background-color:#fff8ec;color:#f5a623;font-weight:800;"
        return ""

    st.dataframe(
        view.style.map(sc_stage, subset=["현재단계"]).map(sc_wip, subset=["WIP구분"]).map(sc_delay, subset=["지연분류"]).map(sc_lt, subset=["리드타임"]).format(
            {"리드타임": lambda x: f"{int(x)}일" if pd.notna(x) else "-"}
        ),
        use_container_width=True,
        hide_index=True,
        height=520,
    )

    csv = view.to_csv(index=False).encode("utf-8-sig")
    st.download_button(
        "↓ CSV 다운로드",
        data=csv,
        file_name=f"1P_Ops_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv",
    )
    st.markdown("</div>", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────
# 8. MAIN
# ─────────────────────────────────────────────────────────────
def main():
    if not check_password():
        st.stop()
    src = st.session_state.get("source", "none")

    if src == "gsheet" and "gsheet_values" in st.session_state:
        df = from_gsheet(st.session_state.get("gsheet_ts", ""), st.session_state["gsheet_values"])
    elif src == "xlsx" and "xlsx_bytes" in st.session_state:
        df = from_bytes(st.session_state["xlsx_bytes"])
    else:
        has_secret = False
        try:
            _ = st.secrets["gcp_service_account"]
            has_secret = True
        except Exception:
            pass

        if has_secret and "auto_tried" not in st.session_state:
            st.session_state["auto_tried"] = True
            with st.spinner("구글 시트 자동 연결 중..."):
                vals, err = load_from_gsheet()
            if not err:
                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                st.session_state.update({"gsheet_values": vals, "gsheet_ts": ts, "source": "gsheet"})
                st.rerun()
            else:
                st.warning(f"자동 연결 실패: {err}")
                landing()
                return
        else:
            landing()
            return

    df = df[df["include_in_scope"]].copy()
    f_rev, f_country, f_year, f_stage, f_delay, keyword = sidebar(df)

    dff_base = df.copy()
    if f_rev:
        dff_base = dff_base[dff_base["검토자_정제"].isin(f_rev)]
    if f_country:
        dff_base = dff_base[dff_base["국내해외"].isin(f_country)]
    if f_year:
        dff_base = dff_base[dff_base["년도"].isin(f_year) | dff_base["년도"].isna()]
    if f_delay:
        dff_base = dff_base[dff_base["지연여부"].isin(f_delay)]
    if keyword:
        kw = keyword.strip().lower()
        dff_base = dff_base[
            dff_base.apply(
                lambda r: kw in " ".join([str(v).lower() for v in r.values if pd.notna(v)]),
                axis=1,
            )
        ]

    dff = dff_base.copy()
    if f_stage:
        dff = dff[dff["현재단계"].isin(f_stage)]

    dashboard(dff, src, dff_base)


if __name__ == "__main__":
    main()
