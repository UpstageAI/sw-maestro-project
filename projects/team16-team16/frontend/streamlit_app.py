import json
import os

import streamlit as st
from pydantic import ValidationError
from streamlit_local_storage import LocalStorage

from app.api_client import BackendError, check_health, fetch_briefing
from app.components.briefing_view import render_briefing
from app.constants import CATEGORY_OPTIONS, CITY_OPTIONS, DEFAULT_LENGTH
from app.mock_data import make_mock_briefing
from app.schemas import BriefingRequest, BriefingResponse

LOCAL_STORAGE_KEY = "morning_briefing_settings"

MOCK_SCENARIOS = {
    "정상": "normal",
    "날씨 실패": "no_weather",
    "뉴스 실패": "no_news",
    "둘 다 실패": "all_failed",
    "LLM 실패": "llm_fail",
}


def _load_saved_settings(local_storage: LocalStorage) -> dict | None:
    raw = local_storage.getItem(LOCAL_STORAGE_KEY)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return None


def _save_settings(
    local_storage: LocalStorage, location: str, categories: list[str]
) -> None:
    payload = json.dumps(
        {"location": location, "categories": categories},
        ensure_ascii=False,
    )
    local_storage.setItem(LOCAL_STORAGE_KEY, payload)


def _resolve_defaults(saved: dict | None) -> tuple[str, list[str]]:
    settings = saved or {}
    location = settings.get("location") or CITY_OPTIONS[0]
    if location not in CITY_OPTIONS:
        location = CITY_OPTIONS[0]
    categories = [c for c in settings.get("categories", []) if c in CATEGORY_OPTIONS]
    if not categories:
        categories = ["IT"]
    return location, categories


def _build_briefing(
    req: BriefingRequest, *, use_mock: bool, mock_scenario: str
) -> BriefingResponse:
    if use_mock:
        return make_mock_briefing(req, scenario=mock_scenario)
    return fetch_briefing(req)


def _run_briefing(
    req: BriefingRequest, *, use_mock: bool, mock_scenario: str, spinner_text: str
) -> None:
    """브리핑을 호출해 session_state에 결과를 저장한다. 마지막 요청도 함께 보존."""
    with st.spinner(spinner_text):
        try:
            st.session_state.briefing = _build_briefing(
                req, use_mock=use_mock, mock_scenario=mock_scenario
            )
            st.session_state.error = None
            st.session_state.last_request = req
        except BackendError as exc:
            st.session_state.briefing = None
            st.session_state.error = str(exc)


st.set_page_config(page_title="☀️ 모닝 브리핑", page_icon="☀️", layout="wide")

st.markdown("""
<style>
#MainMenu {visibility: hidden;}
header {visibility: hidden;}
footer {visibility: hidden;}
[data-testid="stDeployButton"] {display: none;}
</style>
""", unsafe_allow_html=True)

st.markdown("# ☀️ 모닝 브리핑")
st.caption("일어나서 한 번, 오늘 입을 옷 · 우산 여부 · 꼭 알아야 할 뉴스를 한 화면에.")

local_storage = LocalStorage()
saved = _load_saved_settings(local_storage)
default_location, default_categories = _resolve_defaults(saved)

_DEV_MODE = os.environ.get("DEV_MODE", "").lower() in ("1", "true")

with st.sidebar:
    use_mock = False
    mock_scenario_label = "정상"
    if _DEV_MODE:
        st.subheader("개발 모드")
        use_mock = st.toggle(
            "Mock 응답 사용",
            value=False,
            help="백엔드/에이전트 미완성 동안 가짜 응답으로 화면 개발",
        )
        if use_mock:
            mock_scenario_label = st.selectbox(
                "Mock 시나리오",
                list(MOCK_SCENARIOS.keys()),
                index=0,
            )
        else:
            if check_health():
                st.success("연결됨")
            else:
                st.error("연결 실패")
        st.divider()

    st.subheader("⚙️ 내 설정")
    if saved:
        st.caption("✅ 이전 설정을 불러왔습니다.")
    with st.form("settings"):
        location = st.selectbox(
            "📍 위치", CITY_OPTIONS, index=CITY_OPTIONS.index(default_location)
        )
        categories = st.multiselect(
            "📰 관심 카테고리",
            CATEGORY_OPTIONS,
            default=default_categories,
            max_selections=5,
            help="1~5개 선택 가능",
        )
        submitted = st.form_submit_button(
            "☀️ 브리핑 생성", use_container_width=True, type="primary"
        )

    if saved and st.button(
        "설정 초기화",
        use_container_width=True,
        help="저장된 설정을 지우고 처음 상태로 돌아갑니다.",
    ):
        local_storage.deleteItem(LOCAL_STORAGE_KEY)
        for key in ("briefing", "error", "last_request", "_auto_called"):
            st.session_state.pop(key, None)
        st.rerun()

    if submitted:
        if not categories:
            st.warning("카테고리를 1개 이상 선택해 주세요.")
            st.session_state.pop("briefing", None)
            st.session_state.pop("last_request", None)
        else:
            try:
                req = BriefingRequest(
                    location=location,
                    categories=categories,
                    length=DEFAULT_LENGTH,
                )
            except ValidationError as exc:
                st.session_state.briefing = None
                st.session_state.error = f"입력 검증 실패: {exc}"
            else:
                _save_settings(local_storage, location, categories)
                _run_briefing(
                    req,
                    use_mock=use_mock,
                    mock_scenario=MOCK_SCENARIOS[mock_scenario_label],
                    spinner_text="브리핑을 만들고 있습니다…",
                )

# 저장된 설정이 있으면 페이지 진입 시 자동으로 한 번 호출 (기획서 §3 자동 생성)
auto_call_eligible = (
    saved is not None
    and not submitted
    and st.session_state.get("briefing") is None
    and st.session_state.get("error") is None
    and not st.session_state.get("_auto_called", False)
)
if auto_call_eligible:
    st.session_state._auto_called = True
    try:
        auto_req = BriefingRequest(
            location=default_location,
            categories=default_categories,
            length=DEFAULT_LENGTH,
        )
    except ValidationError as exc:
        st.session_state.error = f"저장된 설정이 유효하지 않습니다: {exc}"
    else:
        _run_briefing(
            auto_req,
            use_mock=use_mock,
            mock_scenario=MOCK_SCENARIOS[mock_scenario_label],
            spinner_text="저장된 설정으로 브리핑을 불러오고 있습니다…",
        )

if st.session_state.get("error"):
    st.error(st.session_state.error)

PRESETS = {
    "직장인": {"location": "서울", "categories": ["IT", "경제"]},
    "대학생": {"location": "서울", "categories": ["사회", "문화"]},
    "종합": {"location": "서울", "categories": ["IT", "경제", "사회"]},
}

briefing = st.session_state.get("briefing")
if briefing is None:
    if saved is None:
        st.markdown("")
        st.markdown("#### 빠른 시작")
        st.caption(
            "아래 프리셋 중 하나를 누르면 바로 브리핑을 받을 수 있어요. "
            "나중에 왼쪽 사이드바에서 위치와 카테고리를 자유롭게 바꿀 수 있습니다."
        )
        cols = st.columns(len(PRESETS))
        for col, (label, preset) in zip(cols, PRESETS.items()):
            with col:
                icon = {"직장인": "💼", "대학생": "🎓", "종합": "📋"}.get(label, "📋")
                st.button(
                    f"{icon} {label}",
                    key=f"preset_{label}",
                    use_container_width=True,
                    help=f"{preset['location']} / {', '.join(preset['categories'])}",
                )
        for label, preset in PRESETS.items():
            if st.session_state.get(f"preset_{label}"):
                preset_req = BriefingRequest(
                    location=preset["location"],
                    categories=preset["categories"],
                    length=DEFAULT_LENGTH,
                )
                _save_settings(
                    local_storage, preset["location"], preset["categories"]
                )
                _run_briefing(
                    preset_req,
                    use_mock=use_mock,
                    mock_scenario=MOCK_SCENARIOS[mock_scenario_label],
                    spinner_text="브리핑을 만들고 있습니다…",
                )
                st.rerun()

        st.divider()
        st.markdown("##### 사용 방법")
        st.markdown(
            "1. **위치 선택** — 왼쪽 사이드바에서 날씨를 확인할 도시를 고르세요.\n"
            "2. **카테고리 선택** — 관심 있는 뉴스 분야를 1~5개 골라 주세요.\n"
            "3. **브리핑 생성** — 버튼을 누르면 오늘의 날씨와 뉴스를 AI가 요약해 드려요.\n"
            "4. **다시 생성** — 같은 설정으로 최신 정보를 다시 받을 수 있어요."
        )
    else:
        st.info("왼쪽 사이드바에서 '브리핑 생성'을 눌러 주세요.")
else:
    last_req: BriefingRequest | None = st.session_state.get("last_request")
    info_col, refresh_col = st.columns([5, 1])
    with info_col:
        if last_req:
            st.caption(
                f"📍 {last_req.location}  ·  📰 {', '.join(last_req.categories)}"
            )
    with refresh_col:
        if st.button(
            "🔄 다시 생성",
            use_container_width=True,
            disabled=last_req is None,
            help="같은 설정으로 즉시 재호출합니다.",
        ) and last_req is not None:
            _run_briefing(
                last_req,
                use_mock=use_mock,
                mock_scenario=MOCK_SCENARIOS[mock_scenario_label],
                spinner_text="다시 생성하고 있습니다…",
            )
            st.rerun()
    render_briefing(briefing)
