from __future__ import annotations

import sys
import uuid
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage

from app.agent.graph import get_compiled_graph
from app.agent.nodes import get_pipeline
from app.ui.i18n import get_translator

st.set_page_config(page_title="HireProof Chat", layout="wide")

graph = get_compiled_graph()
pipeline = get_pipeline()


def _thread_id_for_job(job_id: str) -> str:
    return f"job-{job_id}"


def _seed_thread(thread_id: str, job_id: str | None, locale: str) -> None:
    config = {"configurable": {"thread_id": thread_id}}
    snapshot = graph.get_state(config)
    if snapshot.values:
        return
    t = get_translator(locale)
    if job_id:
        job = pipeline.repository.get_job(job_id)
        if job:
            evaluations = pipeline.repository.list_evaluations(job_id)
            candidates = pipeline.repository.list_candidates(job_id)
            if evaluations:
                stage = "results"
            elif job.status == "criteria_confirmed" or candidates:
                stage = "candidate_intake"
            else:
                stage = "criteria_review"
            from app.agent.nodes import _format_criteria_md, _format_ranking

            if stage == "results":
                content = (
                    t("chat_intro").split("\n\n")[0]
                    + f"\n\n📂 `{job.title}` (status: `{job.status}`)\n\n"
                    + _format_ranking(pipeline, job_id, t)
                    + "\n\n"
                    + t("chat_results_help")
                )
            elif stage == "candidate_intake":
                content = (
                    f"📂 `{job.title}` (status: `{job.status}`)\n\n"
                    + t("chat_candidate_help")
                )
            else:
                content = (
                    f"📂 `{job.title}`\n\n"
                    + _format_criteria_md(job.criteria, t)
                    + "\n\n"
                    + t("chat_criteria_help")
                )
            graph.update_state(
                config,
                {
                    "job_id": job_id,
                    "stage": stage,
                    "locale": locale,
                    "pending_candidate": {},
                    "messages": [AIMessage(content=content)],
                },
            )
            return
    graph.update_state(
        config,
        {
            "job_id": None,
            "stage": "awaiting_jd",
            "locale": locale,
            "pending_candidate": {},
            "messages": [AIMessage(content=t("chat_intro"))],
        },
    )


with st.sidebar:
    language = st.selectbox("Language / 언어", ["ko", "en"], index=0, key="locale_select")
    t = get_translator(language)

    st.markdown(f"### {t('select_job')}")
    jobs = pipeline.repository.list_jobs()
    options: dict[str, str] = {t("chat_new_job"): "__new__"}
    for job in jobs:
        options[f"{job.title} ({job.id[:8]})"] = job.id

    pending_job_id = st.session_state.pop("pending_job_id", None)
    if pending_job_id:
        pending_label = next(
            (label for label, value in options.items() if value == pending_job_id),
            None,
        )
        if pending_label:
            st.session_state["job_radio"] = pending_label

    selected_label = st.radio(
        t("select_job"),
        list(options.keys()),
        key="job_radio",
        label_visibility="collapsed",
    )
    selected_value = options[selected_label]

    if selected_value == "__new__":
        if "draft_thread_id" not in st.session_state:
            st.session_state.draft_thread_id = f"draft-{uuid.uuid4().hex[:12]}"
        thread_id = st.session_state.draft_thread_id
        active_job_id = None
    else:
        thread_id = _thread_id_for_job(selected_value)
        active_job_id = selected_value

    st.divider()
    st.caption(f"Thread: `{thread_id}`")
    st.caption(f"Evaluator: `{pipeline.settings.evaluator_mode}`")
    if pipeline.settings.evaluator_mode != "mock":
        st.caption(f"Model: `{pipeline.settings.upstage_model}`")

st.title(t("chat_title"))
st.caption(t("chat_subtitle"))

_seed_thread(thread_id, active_job_id, language)

config = {"configurable": {"thread_id": thread_id}}
snapshot = graph.get_state(config)
state_values = snapshot.values or {}

if state_values.get("locale") != language:
    graph.update_state(config, {"locale": language})
    state_values = graph.get_state(config).values or {}

stage = state_values.get("stage", "awaiting_jd")
job_id_in_state = state_values.get("job_id")

for msg in state_values.get("messages", []) or []:
    role = "assistant" if isinstance(msg, AIMessage) else "user"
    with st.chat_message(role):
        st.markdown(msg.content if isinstance(msg.content, str) else str(msg.content))

upload_payload: dict | None = None
trigger_eval = False

if stage == "candidate_intake":
    with st.expander(f"📤 {t('chat_upload_section')}", expanded=True):
        uploaded_file = st.file_uploader(
            t("resume_file"),
            type=["txt", "md", "pdf", "docx"],
            key=f"uploader_{thread_id}",
        )
        col1, col2 = st.columns(2)
        with col1:
            cand_name = st.text_input(
                t("candidate_name"),
                key=f"name_{thread_id}",
                value=(state_values.get("pending_candidate") or {}).get("name", ""),
            )
        with col2:
            cand_github = st.text_input(
                t("github_url"),
                key=f"github_{thread_id}",
                value=(state_values.get("pending_candidate") or {}).get("github_url", ""),
            )
        cand_portfolio = st.text_input(
            t("portfolio_url"),
            key=f"portfolio_{thread_id}",
            value=(state_values.get("pending_candidate") or {}).get("portfolio_url", ""),
        )
        st.caption(t("chat_upload_hint"))
        eval_clicked = st.button(
            f"▶️ {t('chat_start_evaluation')}",
            type="primary",
            disabled=uploaded_file is None or not cand_name.strip(),
            key=f"eval_btn_{thread_id}",
        )
        if eval_clicked and uploaded_file is not None:
            upload_payload = {
                "filename": uploaded_file.name,
                "bytes": uploaded_file.getvalue(),
                "name": cand_name.strip() or None,
                "github_url": cand_github.strip() or None,
                "portfolio_url": cand_portfolio.strip() or None,
            }
            trigger_eval = True

user_input = st.chat_input(t("chat_input_placeholder"))


def _run_turn(text: str, upload: dict | None) -> None:
    runtime_config: dict = {"configurable": {"thread_id": thread_id}}
    if upload:
        runtime_config["configurable"]["pending_upload"] = upload
    inputs = {"messages": [HumanMessage(content=text)]}
    graph.invoke(inputs, runtime_config)


did_invoke = False
if trigger_eval and upload_payload:
    _run_turn(f"[upload: {upload_payload['filename']}]", upload_payload)
    did_invoke = True
elif user_input:
    _run_turn(user_input, None)
    did_invoke = True

if did_invoke:
    new_state = graph.get_state(config).values or {}
    new_job_id = new_state.get("job_id")
    if active_job_id is None and new_job_id:
        target_thread = _thread_id_for_job(new_job_id)
        if target_thread != thread_id:
            graph.update_state(
                {"configurable": {"thread_id": target_thread}},
                new_state,
            )
            st.session_state.pop("draft_thread_id", None)
            st.session_state["pending_job_id"] = new_job_id
    st.rerun()
