"""MeetFlow AI - 회의 생산성 에이전트 프론트엔드 (v2 redesign).

회의 안건과 회의록을 받아 백엔드 /analyze API 를 호출하고
요약 / 누락 안건 / 다음 회의 안건 / 액션 아이템을
모던 SaaS 대시보드 스타일로 렌더링한다.
"""

from __future__ import annotations

import json
import os
import re
import textwrap
import time as _time
from datetime import datetime
from html import escape as html_escape
from typing import Any

import requests
import streamlit as st

try:
    from .samples import SAMPLES
except ImportError:  # streamlit run frontend/ui.py
    from samples import SAMPLES

# ---------------------------------------------------------------------------
# 환경설정
# ---------------------------------------------------------------------------

DEFAULT_BACKEND_URL = "http://localhost:8000/analyze"
BACKEND_URL: str = os.getenv("BACKEND_URL", DEFAULT_BACKEND_URL)
HEALTH_URL: str = BACKEND_URL.rsplit("/", 1)[0] + "/healthz"

REQUEST_TIMEOUT_SEC: int = 30
HEALTH_TIMEOUT_SEC: int = 2
MAX_TRANSCRIPT_CHARS: int = 200_000
MAX_AGENDA_CHARS: int = 5_000

SERVICE_NAME = "MeetFlow AI"
SERVICE_TAGLINE = "회의록을 5초 만에 요약 · 누락 안건 · 다음 안건 · 실행 항목으로 변환"

UNKNOWN_TOKENS = {"", "미정", "unknown", "none", "null", "n/a", "-", "tbd"}


# ---------------------------------------------------------------------------
# 글로벌 디자인 시스템 (Pretendard + 모던 SaaS)
# ---------------------------------------------------------------------------

CUSTOM_CSS = """
<style>
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/static/pretendard.min.css');
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500&display=swap');

:root {
    --bg: #fafbfd;
    --bg-soft: #f1f3f9;
    --surface: #ffffff;
    --surface-2: #f8fafc;
    --border: #e5e7eb;
    --border-strong: #d1d5db;
    --text: #0f172a;
    --text-muted: #64748b;
    --text-soft: #94a3b8;
    --primary: #6366f1;
    --primary-strong: #4f46e5;
    --primary-soft: #eef2ff;
    --success: #10b981;
    --success-soft: #ecfdf5;
    --warning: #f59e0b;
    --warning-soft: #fffbeb;
    --danger: #ef4444;
    --danger-soft: #fef2f2;
    --info: #0ea5e9;
    --info-soft: #f0f9ff;
    --radius-sm: 8px;
    --radius: 14px;
    --radius-lg: 20px;
    --shadow-sm: 0 1px 2px rgba(15, 23, 42, 0.04);
    --shadow: 0 1px 3px rgba(15, 23, 42, 0.06), 0 1px 2px rgba(15, 23, 42, 0.04);
    --shadow-md: 0 4px 6px -1px rgba(15, 23, 42, 0.06), 0 2px 4px -1px rgba(15, 23, 42, 0.04);
}

html, body, [class*="css"], .stApp {
    font-family: 'Pretendard', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
    color: var(--text);
}
.stApp {
    background:
        radial-gradient(circle at 0% 0%, rgba(99, 102, 241, 0.06) 0%, transparent 35%),
        radial-gradient(circle at 100% 0%, rgba(168, 85, 247, 0.04) 0%, transparent 40%),
        var(--bg);
    min-height: 100vh;
}
.block-container {
    padding-top: 1.2rem !important;
    padding-bottom: 4rem !important;
    max-width: 1400px !important;
}
header[data-testid="stHeader"] { background: transparent; height: 0; }
#MainMenu, footer, [data-testid="stToolbar"] { display: none !important; }

/* Sidebar */
[data-testid="stSidebar"] {
    background: var(--surface) !important;
    border-right: 1px solid var(--border);
}
[data-testid="stSidebar"] > div:first-child { padding-top: 1.5rem; }

.mf-brand {
    display: flex; align-items: center; gap: 10px;
    padding: 4px 4px 18px 4px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 18px;
}
.mf-brand-logo {
    width: 38px; height: 38px;
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
    border-radius: 10px;
    display: flex; align-items: center; justify-content: center;
    color: white; font-weight: 800; font-size: 16px;
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.35);
}
.mf-brand-name { font-size: 15px; font-weight: 700; color: var(--text); letter-spacing: -0.01em; }
.mf-brand-tag { font-size: 11px; color: var(--text-muted); margin-top: 1px; }

.mf-side-section {
    font-size: 11px; font-weight: 700; color: var(--text-soft);
    text-transform: uppercase; letter-spacing: 0.08em;
    margin: 18px 0 8px 4px;
}
.mf-status {
    display: flex; align-items: center; gap: 12px;
    padding: 12px 14px;
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    font-size: 13px; margin-bottom: 8px;
}
.mf-pulse { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; }
.mf-status.ok .mf-pulse {
    background: var(--success);
    box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.18);
    animation: mf-pulse 2s infinite;
}
.mf-status.bad .mf-pulse {
    background: var(--danger);
    box-shadow: 0 0 0 4px rgba(239, 68, 68, 0.18);
}
.mf-status-col { display: flex; flex-direction: column; }
.mf-status-label { font-weight: 600; color: var(--text); }
.mf-status-sub { font-size: 11px; color: var(--text-muted); margin-top: 2px; }

@keyframes mf-pulse {
    0%, 100% { box-shadow: 0 0 0 4px rgba(16, 185, 129, 0.18); }
    50%      { box-shadow: 0 0 0 7px rgba(16, 185, 129, 0.08); }
}

.mf-side-meta {
    font-size: 11.5px; color: var(--text-muted);
    padding: 6px 4px; line-height: 1.65; word-break: break-all;
}
.mf-side-meta code {
    font-family: 'JetBrains Mono', monospace;
    font-size: 10.5px;
    background: var(--bg-soft);
    padding: 1px 6px; border-radius: 4px;
    color: var(--primary-strong);
}

/* Hero */
.mf-hero {
    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #ec4899 100%);
    border-radius: var(--radius-lg);
    padding: 32px 36px;
    margin-bottom: 24px;
    color: white;
    position: relative;
    overflow: hidden;
    box-shadow: 0 20px 40px -10px rgba(79, 70, 229, 0.35);
}
.mf-hero::before {
    content: ''; position: absolute;
    top: -50%; right: -10%;
    width: 400px; height: 400px;
    background: radial-gradient(circle, rgba(255,255,255,0.18) 0%, transparent 60%);
    border-radius: 50%; pointer-events: none;
}
.mf-hero-pill {
    display: inline-flex; align-items: center; gap: 6px;
    background: rgba(255,255,255,0.18);
    border: 1px solid rgba(255,255,255,0.28);
    padding: 5px 12px; border-radius: 999px;
    font-size: 11px; font-weight: 600;
    margin-bottom: 14px;
    backdrop-filter: blur(8px);
}
.mf-dot-live {
    width: 6px; height: 6px; border-radius: 50%;
    background: #4ade80; box-shadow: 0 0 8px #4ade80;
}
.mf-hero h1 {
    font-size: 32px; font-weight: 800;
    margin: 0 0 8px 0; letter-spacing: -0.03em; line-height: 1.2;
}
.mf-hero p {
    margin: 0 0 18px 0; font-size: 15px; opacity: 0.95;
    max-width: 640px; line-height: 1.5;
}
.mf-hero-features { display: flex; flex-wrap: wrap; gap: 8px; position: relative; z-index: 1; }
.mf-hero-feat {
    background: rgba(255,255,255,0.14);
    border: 1px solid rgba(255,255,255,0.22);
    padding: 6px 12px; border-radius: 8px;
    font-size: 12px; font-weight: 500; backdrop-filter: blur(6px);
}

/* Cards */
.mf-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 22px 24px;
    box-shadow: var(--shadow);
    margin-bottom: 16px;
}
.mf-card-head {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 14px; gap: 10px;
}
.mf-card-title {
    display: flex; align-items: center; gap: 10px;
    font-size: 15px; font-weight: 700; color: var(--text); margin: 0;
}
.mf-card-icon {
    width: 28px; height: 28px;
    border-radius: 8px;
    background: var(--primary-soft); color: var(--primary-strong);
    display: flex; align-items: center; justify-content: center;
    font-size: 14px;
}
.mf-card-count {
    background: var(--bg-soft); color: var(--text-muted);
    font-size: 11px; font-weight: 700;
    padding: 3px 10px; border-radius: 999px;
    font-family: 'JetBrains Mono', monospace;
}

/* KPI grid */
.mf-kpi-grid {
    display: grid; grid-template-columns: repeat(4, 1fr);
    gap: 14px; margin-bottom: 18px;
}
.mf-kpi {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 18px 20px;
    box-shadow: var(--shadow-sm);
    position: relative; overflow: hidden;
}
.mf-kpi::after {
    content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
    background: var(--accent, var(--primary));
    border-radius: var(--radius) var(--radius) 0 0;
}
.mf-kpi.indigo  { --accent: #6366f1; }
.mf-kpi.amber   { --accent: #f59e0b; }
.mf-kpi.cyan    { --accent: #06b6d4; }
.mf-kpi.emerald { --accent: #10b981; }
.mf-kpi-label {
    font-size: 11px; color: var(--text-muted); font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.06em;
    margin: 0 0 8px 0;
}
.mf-kpi-value {
    font-size: 28px; font-weight: 800; color: var(--text);
    line-height: 1; margin: 0; font-feature-settings: 'tnum';
}
.mf-kpi-sub { font-size: 11px; color: var(--text-soft); margin-top: 6px; }

/* Summary */
.mf-summary {
    background: linear-gradient(135deg, #eef2ff 0%, #faf5ff 100%);
    border: 1px solid #e0e7ff;
    border-radius: var(--radius);
    padding: 18px 22px;
    color: var(--text);
    font-size: 14.5px; line-height: 1.75;
    position: relative;
}
.mf-summary.empty {
    background: var(--surface-2); border-color: var(--border);
    color: var(--text-muted); font-style: italic;
}

/* Agenda list */
.mf-agenda { list-style: none; padding: 0; margin: 0; }
.mf-agenda li {
    display: flex; align-items: flex-start; gap: 12px;
    padding: 12px 14px;
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    margin-bottom: 8px;
    font-size: 14px; color: var(--text); line-height: 1.5;
    transition: all 0.15s;
}
.mf-agenda li:hover {
    background: var(--primary-soft); border-color: #c7d2fe;
    transform: translateX(2px);
}
.mf-agenda li:last-child { margin-bottom: 0; }
.mf-num {
    flex-shrink: 0; width: 24px; height: 24px;
    background: var(--surface);
    border: 1px solid var(--border-strong);
    color: var(--primary-strong);
    border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    font-size: 11px; font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
}
.mf-empty {
    padding: 24px; text-align: center;
    color: var(--text-soft); font-size: 13px;
    background: var(--surface-2);
    border-radius: var(--radius-sm);
    border: 1px dashed var(--border-strong);
}
.mf-empty-icon { font-size: 28px; display: block; margin-bottom: 6px; opacity: 0.5; }

/* Tickets */
.mf-ticket {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 16px 18px;
    margin-bottom: 12px;
    box-shadow: var(--shadow-sm);
    transition: all 0.15s;
    position: relative; overflow: hidden;
}
.mf-ticket::before {
    content: ''; position: absolute; left: 0; top: 0; bottom: 0; width: 3px;
    background: var(--primary);
}
.mf-ticket:hover {
    border-color: var(--primary);
    box-shadow: 0 4px 14px -2px rgba(99, 102, 241, 0.15);
}
.mf-ticket-top {
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 10px; gap: 8px;
}
.mf-ticket-id {
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px; font-weight: 600; color: var(--text-soft);
    letter-spacing: 0.04em;
}
.mf-ticket-status {
    font-size: 10.5px; font-weight: 700;
    padding: 3px 9px; border-radius: 999px;
    background: var(--info-soft); color: #0369a1;
    border: 1px solid #bae6fd;
    text-transform: uppercase; letter-spacing: 0.06em;
}
.mf-ticket-title {
    font-size: 14.5px; font-weight: 600; color: var(--text);
    line-height: 1.5; margin: 0 0 12px 0;
}
.mf-ticket-desc {
    font-size: 12.5px; color: var(--text-muted);
    line-height: 1.55; margin: -4px 0 12px 0;
}
.mf-ticket-meta { display: flex; flex-wrap: wrap; gap: 6px; }
.mf-subtasks {
    margin-top: 12px; padding-top: 12px;
    border-top: 1px solid var(--border);
}
.mf-subtask {
    display: grid; grid-template-columns: 24px 1fr;
    gap: 8px; padding: 8px 0;
}
.mf-subtask + .mf-subtask { border-top: 1px dashed var(--border); }
.mf-subtask-num {
    width: 22px; height: 22px; border-radius: 6px;
    display: flex; align-items: center; justify-content: center;
    background: var(--primary-soft); color: var(--primary-strong);
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px; font-weight: 700;
}
.mf-subtask-body { min-width: 0; }
.mf-subtask-title {
    font-size: 12.5px; line-height: 1.5;
    color: var(--text); margin-bottom: 6px;
}
.mf-subtask-meta { display: flex; flex-wrap: wrap; gap: 5px; }
.mf-subtask-meta .mf-chip { font-size: 11px; padding: 3px 8px; }
.mf-chip {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 4px 10px;
    background: var(--surface-2);
    border: 1px solid var(--border);
    border-radius: 999px;
    font-size: 12px; color: var(--text);
}
.mf-chip-key { color: var(--text-muted); font-size: 11px; }
.mf-chip.warn { background: var(--warning-soft); border-color: #fde68a; color: #92400e; }
.mf-chip.user { background: #eef2ff; border-color: #c7d2fe; color: #4338ca; }
.mf-chip.date { background: #f0fdf4; border-color: #bbf7d0; color: #15803d; }

/* Banner */
.mf-banner {
    display: flex; align-items: center; gap: 10px;
    padding: 12px 16px;
    border-radius: var(--radius-sm);
    border: 1px solid;
    margin-bottom: 14px;
    font-size: 13.5px; font-weight: 500;
}
.mf-banner.success { background: var(--success-soft); border-color: #a7f3d0; color: #065f46; }
.mf-banner.warn    { background: var(--warning-soft); border-color: #fde68a; color: #92400e; }
.mf-banner.error   { background: var(--danger-soft);  border-color: #fecaca; color: #991b1b; }
.mf-banner-icon {
    width: 22px; height: 22px; border-radius: 50%;
    display: flex; align-items: center; justify-content: center;
    font-weight: 700; flex-shrink: 0;
}
.mf-banner.success .mf-banner-icon { background: var(--success); color: white; }
.mf-banner.warn    .mf-banner-icon { background: var(--warning); color: white; }
.mf-banner.error   .mf-banner-icon { background: var(--danger);  color: white; }

.mf-counter {
    font-size: 11.5px; color: var(--text-muted);
    text-align: right; margin-top: -4px; margin-bottom: 6px;
    font-family: 'JetBrains Mono', monospace;
}
.mf-counter.over { color: var(--danger); font-weight: 700; }

.mf-placeholder {
    text-align: center;
    padding: 60px 30px;
    background: var(--surface);
    border: 2px dashed var(--border-strong);
    border-radius: var(--radius);
    color: var(--text-muted);
}
.mf-placeholder-icon { font-size: 48px; margin-bottom: 12px; opacity: 0.4; }
.mf-placeholder h4 { font-size: 16px; font-weight: 700; color: var(--text); margin: 0 0 6px 0; }
.mf-placeholder p { margin: 0; font-size: 13px; }

/* Streamlit overrides */
.stButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 13.5px !important;
    transition: all 0.15s !important;
    border: 1px solid var(--border) !important;
    background: var(--surface) !important;
    color: var(--text) !important;
}
.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow: var(--shadow-md) !important;
    background: var(--surface) !important;
    color: var(--primary-strong) !important;
    border-color: var(--primary) !important;
}
.stButton > button p,
.stButton > button span,
.stButton > button div {
    color: inherit !important;
}
[data-testid="stSidebar"] .stButton > button {
    background: var(--surface) !important;
    color: var(--text) !important;
    border: 1px solid var(--border-strong) !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: var(--primary-soft) !important;
    color: var(--primary-strong) !important;
    border-color: var(--primary) !important;
}
.stDownloadButton > button {
    border-radius: 10px !important;
    font-weight: 600 !important;
    font-size: 13.5px !important;
    background: var(--surface) !important;
    color: var(--text) !important;
    border: 1px solid var(--border-strong) !important;
}
.stDownloadButton > button:hover {
    background: var(--primary-soft) !important;
    color: var(--primary-strong) !important;
    border-color: var(--primary) !important;
}
.stButton > button[kind="primary"] {
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
    border: none !important;
    color: white !important;
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.35) !important;
}
.stButton > button[kind="primary"]:hover {
    box-shadow: 0 6px 20px rgba(99, 102, 241, 0.45) !important;
}
.stButton > button:disabled {
    background: var(--bg-soft) !important;
    color: var(--text-soft) !important;
    cursor: not-allowed !important;
    box-shadow: none !important;
}
.stTextArea textarea, .stTextInput input {
    border-radius: 10px !important;
    border: 1px solid var(--border) !important;
    font-size: 14px !important;
    font-family: 'Pretendard', sans-serif !important;
    transition: border-color 0.15s, box-shadow 0.15s !important;
}
.stTextArea textarea:focus, .stTextInput input:focus {
    border-color: var(--primary) !important;
    box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.15) !important;
}
.stTabs [data-baseweb="tab-list"] {
    gap: 4px;
    background: var(--surface-2);
    padding: 4px;
    border-radius: 10px;
    border: 1px solid var(--border);
}
.stTabs [data-baseweb="tab"] {
    height: 36px;
    border-radius: 7px !important;
    padding: 0 14px !important;
    font-size: 13px !important;
    font-weight: 600 !important;
    color: var(--text-muted) !important;
    background: transparent !important;
}
.stTabs [aria-selected="true"] {
    background: var(--surface) !important;
    color: var(--primary-strong) !important;
    box-shadow: var(--shadow-sm);
}
.stFileUploader > section {
    border: 2px dashed var(--border-strong) !important;
    border-radius: 10px !important;
    background: var(--surface-2) !important;
}
.streamlit-expanderHeader {
    border-radius: 10px !important;
    font-size: 13px !important;
    font-weight: 600 !important;
}

@media (max-width: 1100px) { .mf-kpi-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 700px) {
    .mf-kpi-grid { grid-template-columns: 1fr; }
    .mf-hero { padding: 24px; }
    .mf-hero h1 { font-size: 24px; }
}

/* ── Agent Log Terminal ── */
.mf-log-terminal {
    background: #0d1117;
    border: 1px solid #30363d;
    border-radius: var(--radius);
    padding: 16px 18px;
    font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
    font-size: 12.5px;
    line-height: 1.7;
    color: #c9d1d9;
    min-height: 60px;
    max-height: 280px;
    overflow-y: auto;
    margin-top: 14px;
    box-shadow: inset 0 2px 8px rgba(0,0,0,0.4);
    white-space: pre-wrap;
    word-break: break-word;
}
.mf-log-terminal .log-info { color: #58a6ff; font-weight: 600; }
.mf-log-terminal .log-pass { color: #3fb950; font-weight: 600; }
.mf-log-terminal .log-warn { color: #d29922; font-weight: 600; }
.mf-log-terminal .log-err  { color: #f85149; font-weight: 600; }
.mf-log-terminal .log-msg  { color: #c9d1d9; }
</style>
"""


# ---------------------------------------------------------------------------
# 유틸
# ---------------------------------------------------------------------------


def _is_blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and not value.strip())


def html_escape(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def render_html(markup: str) -> None:
    st.markdown(textwrap.dedent(markup).strip(), unsafe_allow_html=True)


def split_numbered_text(text: Any) -> list[str]:
    if _is_blank(text):
        return []
    if isinstance(text, list):
        return [str(item).strip() for item in text if str(item).strip()]
    if not isinstance(text, str):
        text = str(text)
    items: list[str] = []
    for line in re.split(r"[\n;]+", text):
        line = line.strip()
        if not line:
            continue
        cleaned = re.sub(r"^\s*(?:\d+[.)]|[-•*])\s*", "", line).strip()
        if cleaned:
            items.append(cleaned)
    return items


def normalize_action_items(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return [
            {"title": line, "who": "", "when": "", "what": line, "sub_items": []}
            for line in split_numbered_text(raw)
        ]
    if not isinstance(raw, list):
        return []
    out: list[dict[str, Any]] = []
    for item in raw:
        if isinstance(item, dict):
            title = str(item.get("title") or "").strip()
            who = str(item.get("who") or "").strip()
            when = str(item.get("when") or "").strip()
            what = str(item.get("what") or "").strip()
            sub_items = normalize_sub_action_items(item.get("sub_items") or item.get("children"))
            if title or who or when or what or sub_items:
                out.append(
                    {
                        "title": title,
                        "who": who,
                        "when": when,
                        "what": what,
                        "sub_items": sub_items,
                    }
                )
        elif isinstance(item, str) and item.strip():
            out.append({"title": item.strip(), "who": "", "when": "", "what": item.strip(), "sub_items": []})
    return out


def normalize_sub_action_items(raw: Any) -> list[dict[str, str]]:
    if raw is None:
        return []
    if isinstance(raw, str):
        return [{"who": "", "when": "", "what": line} for line in split_numbered_text(raw)]
    if not isinstance(raw, list):
        return []
    out: list[dict[str, str]] = []
    for item in raw:
        if isinstance(item, dict):
            who = str(item.get("who") or "").strip()
            when = str(item.get("when") or "").strip()
            what = str(item.get("what") or "").strip()
            if who or when or what:
                out.append({"who": who, "when": when, "what": what})
        elif isinstance(item, str) and item.strip():
            out.append({"who": "", "when": "", "what": item.strip()})
    return out


def normalize_response(payload: Any) -> dict[str, Any]:
    if not isinstance(payload, dict):
        payload = {}
    summary = payload.get("summary") or ""
    return {
        "summary": summary.strip() if isinstance(summary, str) else "",
        "missed_agenda": payload.get("missed_agenda") or "",
        "next_agenda": payload.get("next_agenda") or "",
        "action_items": normalize_action_items(payload.get("action_items")),
        "logs": payload.get("logs") or [],
    }


def is_unknown(value: str) -> bool:
    return value.strip().lower() in UNKNOWN_TOKENS


# ---------------------------------------------------------------------------
# 백엔드 호출
# ---------------------------------------------------------------------------


@st.cache_data(ttl=10, show_spinner=False)
def check_backend_health() -> tuple[bool, str]:
    try:
        r = requests.get(HEALTH_URL, timeout=HEALTH_TIMEOUT_SEC)
        if r.status_code == 200:
            data = r.json()
            return True, data.get("provider", "unknown")
        return False, f"HTTP {r.status_code}"
    except Exception:
        return False, "연결 실패"


def call_analyze_api(agenda: str, transcript: str) -> tuple[dict[str, Any] | None, str | None]:
    try:
        resp = requests.post(
            BACKEND_URL,
            json={"agenda": agenda, "transcript": transcript},
            timeout=REQUEST_TIMEOUT_SEC,
        )
    except requests.exceptions.ConnectTimeout:
        return None, "백엔드 서버 연결 시간 초과. 서버 상태를 확인해 주세요."
    except requests.exceptions.ReadTimeout:
        return None, f"분석이 {REQUEST_TIMEOUT_SEC}초 안에 완료되지 않았습니다."
    except requests.exceptions.ConnectionError:
        return None, f"백엔드 서버 연결 실패. BACKEND_URL({BACKEND_URL}) 을 확인해 주세요."
    except requests.exceptions.RequestException as exc:
        return None, f"요청 오류: {exc}"

    if resp.status_code >= 500:
        return None, f"백엔드 서버 오류 ({resp.status_code})."
    if resp.status_code == 422:
        return None, "입력값이 올바르지 않습니다 (길이 또는 형식)."
    if resp.status_code >= 400:
        return None, f"요청이 거절되었습니다 ({resp.status_code})."

    try:
        return normalize_response(resp.json()), None
    except json.JSONDecodeError:
        return None, "응답 형식이 올바르지 않습니다."


# ---------------------------------------------------------------------------
# 내보내기
# ---------------------------------------------------------------------------


def build_markdown_report(result: dict[str, Any]) -> str:
    summary = result.get("summary") or "_요약 결과가 없습니다._"
    missed = split_numbered_text(result.get("missed_agenda"))
    nxt = split_numbered_text(result.get("next_agenda"))
    actions = normalize_action_items(result.get("action_items"))

    parts: list[str] = [
        f"# {SERVICE_NAME} 회의 분석 리포트",
        "",
        f"_생성: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_",
        "",
        "## 1. 회의 요약",
        "",
        summary,
        "",
        "## 2. 놓친 회의 안건",
        "",
    ]
    parts.extend([f"- {x}" for x in missed] or ["_놓친 안건이 없습니다._"])
    parts += ["", "## 3. 다음 회의 안건", ""]
    parts.extend([f"- {x}" for x in nxt] or ["_제안된 다음 안건이 없습니다._"])
    parts += ["", "## 4. 액션 아이템", ""]
    if actions:
        parts.append("| # | 유형 | 담당자 | 마감일 | 작업 내용 |")
        parts.append("|---|------|--------|--------|-----------|")
        for i, a in enumerate(actions, 1):
            who = a["who"] or "확인 필요"
            when = a["when"] or "확인 필요"
            what = (a["what"] or a["title"] or "").replace("|", "\\|")
            parts.append(f"| MF-{i:03d} | 상위 | {who} | {when} | {what} |")
            for j, sub in enumerate(a.get("sub_items") or [], 1):
                sub_who = sub["who"] or who
                sub_when = sub["when"] or when
                sub_what = (sub["what"] or "").replace("|", "\\|")
                parts.append(f"| MF-{i:03d}-{j} | 하위 | {sub_who} | {sub_when} | {sub_what} |")
    else:
        parts.append("_추출된 액션 아이템이 없습니다._")
    return "\n".join(parts)


def build_csv_report(result: dict[str, Any]) -> str:
    actions = normalize_action_items(result.get("action_items"))
    lines = ["id,parent_id,type,담당자,마감일,작업내용"]
    for i, a in enumerate(actions, 1):
        who = (a["who"] or "").replace('"', '""')
        when = (a["when"] or "").replace('"', '""')
        what = (a["what"] or a["title"] or "").replace('"', '""')
        parent_id = f"MF-{i:03d}"
        lines.append(f'{parent_id},,parent,"{who}","{when}","{what}"')
        for j, sub in enumerate(a.get("sub_items") or [], 1):
            sub_who = (sub["who"] or a["who"] or "").replace('"', '""')
            sub_when = (sub["when"] or a["when"] or "").replace('"', '""')
            sub_what = (sub["what"] or "").replace('"', '""')
            lines.append(f'{parent_id}-{j},{parent_id},sub,"{sub_who}","{sub_when}","{sub_what}"')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 컴포넌트 렌더링
# ---------------------------------------------------------------------------


def render_sidebar() -> None:
    with st.sidebar:
        render_html(
            f"""
            <div class="mf-brand">
                <div class="mf-brand-logo">M</div>
                <div>
                    <div class="mf-brand-name">{SERVICE_NAME}</div>
                    <div class="mf-brand-tag">v1.0 · 회의 생산성 에이전트</div>
                </div>
            </div>
            """
        )

        st.markdown('<div class="mf-side-section">시스템 상태</div>', unsafe_allow_html=True)
        ok, info = check_backend_health()
        if ok:
            render_html(
                f"""
                <div class="mf-status ok">
                    <div class="mf-pulse"></div>
                    <div class="mf-status-col">
                        <span class="mf-status-label">백엔드 정상</span>
                        <span class="mf-status-sub">LLM Provider · {html_escape(info)}</span>
                    </div>
                </div>
                """
            )
        else:
            render_html(
                f"""
                <div class="mf-status bad">
                    <div class="mf-pulse"></div>
                    <div class="mf-status-col">
                        <span class="mf-status-label">백엔드 연결 불가</span>
                        <span class="mf-status-sub">{html_escape(info)}</span>
                    </div>
                </div>
                """
            )

        st.markdown('<div class="mf-side-section">연결 정보</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="mf-side-meta">API: <code>{html_escape(BACKEND_URL)}</code></div>',
            unsafe_allow_html=True,
        )

        st.markdown('<div class="mf-side-section">예시 데이터</div>', unsafe_allow_html=True)
        selected_sample = st.selectbox(
            "회의 유형 선택",
            options=list(SAMPLES.keys()),
            key="sample_select",
            label_visibility="collapsed",
        )
        if st.button("📋 예시 데이터 채우기", use_container_width=True, key="sb_sample"):
            sample = SAMPLES[selected_sample]
            st.session_state["agenda_input"] = sample["agenda"]
            st.session_state["transcript_input"] = sample["transcript"]
            st.rerun()

        st.markdown('<div class="mf-side-section">빠른 동작</div>', unsafe_allow_html=True)
        if st.button("🔄 모두 초기화", use_container_width=True, key="sb_reset"):
            for k in ("agenda_input", "transcript_input", "result", "error", "uploaded_name", "is_dummy", "elapsed_ms"):
                st.session_state.pop(k, None)
            st.rerun()

        st.markdown('<div class="mf-side-section">단축 가이드</div>', unsafe_allow_html=True)
        render_html(
            """
            <div class="mf-side-meta">
            • 안건은 <code>1. 항목</code> 형식 권장<br>
            • 회의록은 <code>[10:00] 이름:</code> 형식 권장<br>
            • <code>.txt</code> 업로드 지원<br>
            • LLM 키 미설정 시 오프라인 모드 자동
            </div>
            """
        )


def render_hero() -> None:
    render_html(
        f"""
        <div class="mf-hero">
            <div class="mf-hero-pill">
                <div class="mf-dot-live"></div>
                AI Agent · Korean Optimized
            </div>
            <h1>{SERVICE_NAME}</h1>
            <p>{SERVICE_TAGLINE}</p>
            <div class="mf-hero-features">
                <div class="mf-hero-feat">⚡ 평균 10ms 응답</div>
                <div class="mf-hero-feat">🇰🇷 한국어 특화 추출</div>
                <div class="mf-hero-feat">🔄 자동 폴백</div>
                <div class="mf-hero-feat">🔌 Multi-LLM 지원</div>
            </div>
        </div>
        """
    )


def _render_card_head(icon: str, title: str, count: int | None = None) -> None:
    count_html = f'<span class="mf-card-count">{count}</span>' if count is not None else ""
    render_html(
        f"""
        <div class="mf-card-head">
            <div class="mf-card-title">
                <div class="mf-card-icon">{icon}</div>
                <span>{html_escape(title)}</span>
            </div>
            {count_html}
        </div>
        """
    )


def render_input_panel() -> tuple[str, str, bool]:
    st.markdown('<div class="mf-card">', unsafe_allow_html=True)
    _render_card_head("✏️", "입력")

    agenda = st.text_area(
        "회의 안건",
        key="agenda_input",
        placeholder="예) 1. Q3 마케팅 전략 검토\n2. 신규 기능 로드맵 논의\n3. 예산 배분 확정",
        height=140,
    )
    a_len = len(agenda or "")
    over_a = a_len > MAX_AGENDA_CHARS
    st.markdown(
        f'<div class="mf-counter{" over" if over_a else ""}">'
        f"{a_len:,} / {MAX_AGENDA_CHARS:,} 자</div>",
        unsafe_allow_html=True,
    )

    st.markdown("**회의 녹취록 / 회의록**")
    tab_text, tab_file = st.tabs(["✍️ 직접 입력", "📎 .txt 업로드"])
    with tab_text:
        st.text_area(
            "녹취록",
            key="transcript_input",
            placeholder="회의 내용을 붙여넣거나 .txt 파일을 업로드하세요.\n예) [10:00] 김철수: ...",
            height=280,
            label_visibility="collapsed",
        )
    with tab_file:
        uploaded = st.file_uploader("회의록 .txt", type=["txt"], label_visibility="collapsed")
        if uploaded is not None and st.session_state.get("uploaded_name") != uploaded.name:
            try:
                raw = uploaded.read()
                text = ""
                try:
                    text = raw.decode("utf-8")
                except UnicodeDecodeError:
                    try:
                        text = raw.decode("cp949")
                    except UnicodeDecodeError:
                        st.error("UTF-8 또는 CP949로 저장된 .txt 파일만 지원합니다.")
                if text:
                    st.session_state["transcript_input"] = text
                    st.session_state["uploaded_name"] = uploaded.name
                    st.success(f"'{uploaded.name}' 파일을 입력란에 반영했습니다.")
                    st.rerun()
            except Exception as exc:  # noqa: BLE001
                st.error(f"파일 읽기 오류: {exc}")

    transcript = st.session_state.get("transcript_input", "") or ""
    t_len = len(transcript)
    over_t = t_len > MAX_TRANSCRIPT_CHARS
    st.markdown(
        f'<div class="mf-counter{" over" if over_t else ""}">'
        f"{t_len:,} / {MAX_TRANSCRIPT_CHARS:,} 자</div>",
        unsafe_allow_html=True,
    )

    can_submit = (
        bool((agenda or "").strip())
        and bool(transcript.strip())
        and not over_a
        and not over_t
    )
    st.markdown("</div>", unsafe_allow_html=True)
    return agenda, transcript, can_submit


def render_kpis(result: dict[str, Any], elapsed_ms: float | None = None) -> None:
    actions = normalize_action_items(result.get("action_items"))
    missed = split_numbered_text(result.get("missed_agenda"))
    nxt = split_numbered_text(result.get("next_agenda"))
    summary_chars = len((result.get("summary") or "").strip())
    elapsed_html = f"{elapsed_ms:.0f}ms" if elapsed_ms is not None else "—"

    render_html(
        f"""
        <div class="mf-kpi-grid">
            <div class="mf-kpi indigo">
                <p class="mf-kpi-label">액션 아이템</p>
                <p class="mf-kpi-value">{len(actions)}</p>
                <p class="mf-kpi-sub">담당자 자동 추출</p>
            </div>
            <div class="mf-kpi amber">
                <p class="mf-kpi-label">놓친 안건</p>
                <p class="mf-kpi-value">{len(missed)}</p>
                <p class="mf-kpi-sub">자카드 유사도 기반</p>
            </div>
            <div class="mf-kpi cyan">
                <p class="mf-kpi-label">다음 안건</p>
                <p class="mf-kpi-value">{len(nxt)}</p>
                <p class="mf-kpi-sub">차기 회의 제안</p>
            </div>
            <div class="mf-kpi emerald">
                <p class="mf-kpi-label">처리 시간</p>
                <p class="mf-kpi-value">{elapsed_html}</p>
                <p class="mf-kpi-sub">요약 {summary_chars:,}자</p>
            </div>
        </div>
        """
    )


def render_summary_card(summary: str) -> None:
    st.markdown('<div class="mf-card">', unsafe_allow_html=True)
    _render_card_head("📝", "회의 요약")
    if summary and summary.strip():
        body = html_escape(summary).replace("\n", "<br>")
        st.markdown(f'<div class="mf-summary">{body}</div>', unsafe_allow_html=True)
    else:
        st.markdown(
            '<div class="mf-summary empty">요약 결과가 비어 있습니다.</div>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


def render_agenda_card(icon: str, title: str, raw: Any, empty_msg: str) -> None:
    items = split_numbered_text(raw)
    st.markdown('<div class="mf-card">', unsafe_allow_html=True)
    _render_card_head(icon, title, count=len(items))
    if items:
        lis = "".join(
            f'<li><div class="mf-num">{i}</div><div>{html_escape(x)}</div></li>'
            for i, x in enumerate(items, 1)
        )
        st.markdown(f'<ul class="mf-agenda">{lis}</ul>', unsafe_allow_html=True)
    else:
        st.markdown(
            f'<div class="mf-empty"><span class="mf-empty-icon">✓</span>{html_escape(empty_msg)}</div>',
            unsafe_allow_html=True,
        )
    st.markdown("</div>", unsafe_allow_html=True)


def render_action_ticket_html(idx: int, item: dict[str, Any]) -> str:
    title = item.get("title", "")
    who = item.get("who", "")
    when = item.get("when", "")
    what = item.get("what", "") or "(작업 내용 없음)"
    sub_items = item.get("sub_items") or []

    if is_unknown(who):
        owner_chip = '<span class="mf-chip warn"><span class="mf-chip-key">담당자</span>확인 필요</span>'
    else:
        owner_chip = (
            f'<span class="mf-chip user"><span class="mf-chip-key">👤</span>{html_escape(who)}</span>'
        )
    if is_unknown(when):
        date_chip = '<span class="mf-chip warn"><span class="mf-chip-key">마감일</span>확인 필요</span>'
    else:
        date_chip = (
            f'<span class="mf-chip date"><span class="mf-chip-key">📅</span>{html_escape(when)}</span>'
        )

    display_title = title or what
    desc_html = ""
    if title and what and title != what:
        desc_html = f'<p class="mf-ticket-desc">{html_escape(what)}</p>'

    sub_html = ""
    if sub_items:
        rows = []
        for sub_idx, sub in enumerate(sub_items, 1):
            sub_who = sub.get("who", "") or who
            sub_when = sub.get("when", "") or when
            sub_what = sub.get("what", "") or "(하위 작업 내용 없음)"
            sub_owner = (
                '<span class="mf-chip warn"><span class="mf-chip-key">담당자</span>확인 필요</span>'
                if is_unknown(sub_who)
                else f'<span class="mf-chip user"><span class="mf-chip-key">👤</span>{html_escape(sub_who)}</span>'
            )
            sub_date = (
                '<span class="mf-chip warn"><span class="mf-chip-key">마감일</span>확인 필요</span>'
                if is_unknown(sub_when)
                else f'<span class="mf-chip date"><span class="mf-chip-key">📅</span>{html_escape(sub_when)}</span>'
            )
            rows.append(
                '<div class="mf-subtask">'
                f'<div class="mf-subtask-num">{sub_idx}</div>'
                '<div class="mf-subtask-body">'
                f'<div class="mf-subtask-title">{html_escape(sub_what)}</div>'
                f'<div class="mf-subtask-meta">{sub_owner}{sub_date}</div>'
                '</div>'
                '</div>'
            )
        sub_html = f'<div class="mf-subtasks">{"".join(rows)}</div>'

    return (
        '<div class="mf-ticket">'
        '<div class="mf-ticket-top">'
        f'<span class="mf-ticket-id">MF-{idx:03d}</span>'
        f'<span class="mf-ticket-status">{len(sub_items)} Sub</span>'
        '</div>'
        f'<p class="mf-ticket-title">{html_escape(display_title)}</p>'
        f'{desc_html}'
        f'<div class="mf-ticket-meta">{owner_chip}{date_chip}</div>'
        f'{sub_html}'
        '</div>'
    )


def render_action_items_card(items: list[dict[str, Any]]) -> None:
    st.markdown('<div class="mf-card">', unsafe_allow_html=True)
    _render_card_head("🎯", "액션 아이템", count=len(items))

    if not items:
        st.markdown(
            '<div class="mf-empty"><span class="mf-empty-icon">📭</span>'
            "추출된 액션 아이템이 없습니다.</div>",
            unsafe_allow_html=True,
        )
        st.markdown("</div>", unsafe_allow_html=True)
        return

    cols_per_row = 2
    for i in range(0, len(items), cols_per_row):
        row = st.columns(cols_per_row, gap="small")
        for j, item in enumerate(items[i : i + cols_per_row]):
            with row[j]:
                st.markdown(render_action_ticket_html(i + j + 1, item), unsafe_allow_html=True)

    st.caption(
        "💡 본 화면은 데모 티켓 미리보기입니다. JIRA/Trello/Notion 연동은 로드맵에 포함되어 있습니다."
    )
    st.markdown("</div>", unsafe_allow_html=True)


def render_export_card(result: dict[str, Any]) -> None:
    md = build_markdown_report(result)
    csv = build_csv_report(result)

    st.markdown('<div class="mf-card">', unsafe_allow_html=True)
    _render_card_head("📤", "결과 내보내기")

    cols = st.columns(3)
    with cols[0]:
        st.download_button(
            "📄 마크다운 (.md)",
            data=md.encode("utf-8"),
            file_name=f"meeting_{datetime.now():%Y%m%d_%H%M}.md",
            mime="text/markdown",
            use_container_width=True,
        )
    with cols[1]:
        st.download_button(
            "📊 액션 CSV (.csv)",
            data=csv.encode("utf-8-sig"),
            file_name=f"actions_{datetime.now():%Y%m%d_%H%M}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with cols[2]:
        st.download_button(
            "🔧 원본 JSON (.json)",
            data=json.dumps(result, ensure_ascii=False, indent=2).encode("utf-8"),
            file_name=f"raw_{datetime.now():%Y%m%d_%H%M}.json",
            mime="application/json",
            use_container_width=True,
        )

    with st.expander("📋 마크다운 미리보기 / 복사"):
        st.code(md, language="markdown")

    st.markdown("</div>", unsafe_allow_html=True)


def render_results() -> None:
    err = st.session_state.get("error")
    if err:
        render_html(
            f"""
            <div class="mf-banner error">
                <div class="mf-banner-icon">!</div>
                <div>{html_escape(err)}</div>
            </div>
            """
        )

    result = st.session_state.get("result")
    if not result:
        render_html(
            """
            <div class="mf-placeholder">
                <div class="mf-placeholder-icon">🗂️</div>
                <h4>분석 대기 중</h4>
                <p>왼쪽에 회의 안건과 회의록을 입력한 뒤 <b>AI 분석 시작</b> 버튼을 눌러주세요.</p>
            </div>
            """
        )
        return

    elapsed = st.session_state.get("elapsed_ms")
    msg = "분석이 완료되었습니다."
    if elapsed is not None:
        msg += f" ({elapsed:.0f}ms)"
    render_html(
        f"""
        <div class="mf-banner success">
            <div class="mf-banner-icon">✓</div>
            <div>{msg}</div>
        </div>
        """
    )

    render_kpis(result, elapsed)

    tab_summary, tab_agenda, tab_actions, tab_export = st.tabs(
        ["📝 요약", "📌 안건", "🎯 액션 아이템", "📤 내보내기"]
    )
    with tab_summary:
        render_summary_card(result.get("summary", ""))
    with tab_agenda:
        render_agenda_card(
            "⚠️", "놓친 회의 안건", result.get("missed_agenda"),
            "놓친 안건이 없습니다 — 모든 안건이 다뤄졌습니다.",
        )
        render_agenda_card(
            "📅", "다음 회의 안건", result.get("next_agenda"),
            "제안된 다음 안건이 없습니다.",
        )
    with tab_actions:
        render_action_items_card(normalize_action_items(result.get("action_items")))
    with tab_export:
        render_export_card(result)


# ---------------------------------------------------------------------------
# 메인
# ---------------------------------------------------------------------------


def _fmt_log_line(line: str) -> str:
    line_esc = html_escape(line)
    m = re.match(r"^(\[(?:INFO|PASS|WARN|ERR)\])\s*(.*)", line_esc, re.DOTALL)
    if m:
        tag, rest = m.group(1), m.group(2)
        css = {
            "[INFO]": "log-info",
            "[PASS]": "log-pass",
            "[WARN]": "log-warn",
            "[ERR]": "log-err",
        }.get(tag, "log-msg")
        return f'<span class="{css}">{tag}</span> <span class="log-msg">{rest}</span>'
    return f'<span class="log-msg">{line_esc}</span>'


def render_log_terminal() -> None:
    logs: list[str] = st.session_state.get("logs", [])
    if not logs:
        return

    if st.session_state.get("logs_shown", False):
        html_lines = "".join(f"<div>{_fmt_log_line(ln)}</div>" for ln in logs)
        st.markdown(f'<div class="mf-log-terminal">{html_lines}</div>', unsafe_allow_html=True)
        return

    placeholder = st.empty()
    displayed: list[str] = []
    for line in logs:
        displayed.append(line)
        html_lines = "".join(f"<div>{_fmt_log_line(ln)}</div>" for ln in displayed)
        placeholder.markdown(
            f'<div class="mf-log-terminal">{html_lines}</div>',
            unsafe_allow_html=True,
        )
        _time.sleep(0.04)

    st.session_state["logs_shown"] = True


def _do_analyze(agenda: str, transcript: str) -> None:
    st.session_state["error"] = None
    st.session_state["logs"] = []
    st.session_state["logs_shown"] = False
    start = datetime.now()
    with st.spinner("AI가 회의록을 분석하는 중..."):
        result, err = call_analyze_api(agenda, transcript)
    st.session_state["elapsed_ms"] = (datetime.now() - start).total_seconds() * 1000

    if err:
        st.session_state["error"] = err
        st.session_state["result"] = None
    else:
        st.session_state["logs"] = result.pop("logs", []) if result else []
        st.session_state["result"] = result


def main() -> None:
    st.set_page_config(
        page_title=f"{SERVICE_NAME} · 회의 생산성 에이전트",
        page_icon="🗂️",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

    for k, v in {
        "agenda_input": "",
        "transcript_input": "",
        "result": None,
        "error": None,
        "elapsed_ms": None,
        "logs": [],
        "logs_shown": False,
    }.items():
        st.session_state.setdefault(k, v)

    render_sidebar()
    render_hero()

    left, right = st.columns([1, 1.2], gap="large")

    with left:
        agenda, transcript, can_submit = render_input_panel()

        clicked = st.button(
            "✨ AI 분석 시작",
            type="primary",
            use_container_width=True,
            disabled=not can_submit,
            help="회의 안건과 녹취록을 모두 입력하면 활성화됩니다." if not can_submit else None,
        )
        if clicked:
            _do_analyze(agenda.strip(), transcript.strip())
            st.rerun()

        render_log_terminal()

    with right:
        render_results()


if __name__ == "__main__":
    main()
