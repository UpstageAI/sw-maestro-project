from __future__ import annotations

import re
from typing import Any

from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig

from app.agent.state import ChatState
from app.core.models import CandidateCreate, Criterion, JobCreate
from app.services.pipeline import HireProofPipeline
from app.ui.i18n import get_translator

_pipeline: HireProofPipeline | None = None


def get_pipeline() -> HireProofPipeline:
    global _pipeline
    if _pipeline is None:
        _pipeline = HireProofPipeline()
    return _pipeline


def _t(state: ChatState):
    return get_translator(state.get("locale", "ko"))


def _last_user_text(state: ChatState) -> str:
    for msg in reversed(state.get("messages", []) or []):
        if isinstance(msg, HumanMessage):
            return msg.content if isinstance(msg.content, str) else ""
    return ""


def _runtime_upload(config: RunnableConfig | None) -> dict | None:
    if not config:
        return None
    configurable = config.get("configurable") or {}
    upload = configurable.get("pending_upload")
    if upload and upload.get("bytes"):
        return upload
    return None


def _format_criteria_md(criteria, t) -> str:
    if not criteria:
        return t("chat_no_criteria")
    lines = [
        f"| # | {t('criterion_name')} | {t('criterion_description')} | {t('criterion_weight')} |",
        "|---|---|---|---|",
    ]
    for idx, c in enumerate(criteria, 1):
        lines.append(f"| {idx} | {c.name} | {c.description} | {c.weight} |")
    return "\n".join(lines)


def _format_evaluation(cand, evaluation, t) -> str:
    if not evaluation:
        return ""
    avg = (evaluation.jd_score + evaluation.alignment_score) / 2
    band = "Top" if avg >= 80 else ("Mid" if avg >= 60 else "Review")
    lines = [
        f"**{t('evaluation_summary')}**: {evaluation.summary}",
        "",
        f"- JD: `{evaluation.jd_score}` / Alignment: `{evaluation.alignment_score}` / {t('fit_band')}: `{band}`",
        f"- GitHub: `{cand.github_status}`",
    ]
    return "\n".join(lines)


def _format_ranking(pipeline: HireProofPipeline, job_id: str, t) -> str:
    evals = pipeline.repository.list_evaluations(job_id)
    if not evals:
        return t("no_evaluations")
    cands = {c.id: c for c in pipeline.repository.list_candidates(job_id)}
    rows = sorted(evals, key=lambda e: (e.jd_score + e.alignment_score) / 2, reverse=True)
    lines = [
        f"**{t('ranking')}**",
        "",
        f"| {t('rank')} | {t('candidate_name')} | JD | Align | {t('fit_band')} |",
        "|---|---|---|---|---|",
    ]
    for idx, e in enumerate(rows, 1):
        c = cands.get(e.candidate_id)
        avg = (e.jd_score + e.alignment_score) / 2
        band = "Top" if avg >= 80 else ("Mid" if avg >= 60 else "Review")
        lines.append(f"| {idx} | {c.name if c else '?'} | {e.jd_score} | {e.alignment_score} | {band} |")
    return "\n".join(lines)


def _format_candidate_detail(cand, evaluation, t) -> str:
    if not cand or not evaluation:
        return "?"
    parts = [
        f"**{cand.name}**",
        f"- JD `{evaluation.jd_score}` / Alignment `{evaluation.alignment_score}`",
        f"- {t('evaluation_summary')}: {evaluation.summary}",
    ]
    if cand.github_url:
        parts.append(f"- GitHub: {cand.github_url} (`{cand.github_status}`)")
    if evaluation.evidence:
        parts.append("")
        parts.append(f"**{t('evidence')}**")
        for ev in evaluation.evidence[:5]:
            parts.append(f"- [{ev.source_type}] {ev.snippet} (conf {ev.confidence}%)")
    return "\n".join(parts)


def _parse_criteria_edit(text: str, n: int) -> dict | None:
    text = text.strip()
    patterns = [
        (r"^/(?:remove|삭제)\s+(\d+)$", "remove"),
        (r"^/(?:weight|가중치)\s+(\d+)\s+(\d+)$", "weight"),
        (r"^/(?:edit|편집)\s+(\d+)\s+(.+)$", "edit"),
    ]
    for pattern, kind in patterns:
        m = re.match(pattern, text, re.IGNORECASE)
        if not m:
            continue
        if kind == "remove":
            idx = int(m.group(1))
            if 1 <= idx <= n:
                return {"action": "remove", "index": idx}
        elif kind == "weight":
            idx, w = int(m.group(1)), int(m.group(2))
            if 1 <= idx <= n and 0 <= w <= 100:
                return {"action": "update", "index": idx, "weight": w}
        elif kind == "edit":
            idx = int(m.group(1))
            if 1 <= idx <= n:
                parts = [p.strip() for p in m.group(2).split("|")]
                result: dict[str, Any] = {"action": "update", "index": idx}
                if len(parts) >= 1 and parts[0]:
                    result["name"] = parts[0]
                if len(parts) >= 2 and parts[1]:
                    result["description"] = parts[1]
                if len(parts) >= 3 and parts[2].isdigit():
                    result["weight"] = int(parts[2])
                return result
    return None


def router_node(state: ChatState, config: RunnableConfig) -> dict:
    return {}


def route_by_stage(state: ChatState) -> str:
    text = _last_user_text(state).strip()
    lowered = text.lower()

    if lowered in {"/restart", "/리셋", "/재시작", "/reset"}:
        return "restart"
    if lowered in {"/help", "/도움말", "/?"}:
        return "help"

    job_id = state.get("job_id")
    if lowered in {"/results", "/결과", "/랭킹", "/ranking"} and job_id:
        return "results"

    stage = state.get("stage", "awaiting_jd")
    return {
        "awaiting_jd": "create_job",
        "criteria_review": "criteria",
        "candidate_intake": "candidate",
        "results": "results",
    }.get(stage, "help")


def create_job_node(state: ChatState, config: RunnableConfig) -> dict:
    text = _last_user_text(state).strip()
    t = _t(state)
    pipeline = get_pipeline()

    pending_title = state.get("pending_jd_title")
    if not pending_title:
        if "\n" not in text and len(text) <= 80:
            return {
                "pending_jd_title": text,
                "messages": [AIMessage(content=t("chat_ask_jd_body").format(title=text))],
            }
        first_line, _, rest = text.partition("\n")
        title = first_line.strip()
        body = rest.strip()
        if not body:
            return {
                "pending_jd_title": title,
                "messages": [AIMessage(content=t("chat_ask_jd_body").format(title=title))],
            }
    else:
        title = pending_title
        body = text

    if not title or not body:
        return {"messages": [AIMessage(content=t("chat_jd_required"))]}

    job = pipeline.create_job(JobCreate(title=title, jd_text=body))
    return {
        "job_id": job.id,
        "stage": "criteria_review",
        "pending_jd_title": None,
        "messages": [
            AIMessage(
                content=(
                    t("chat_job_created").format(title=title)
                    + "\n\n"
                    + _format_criteria_md(job.criteria, t)
                    + "\n\n"
                    + t("chat_criteria_help")
                )
            )
        ],
    }


def criteria_node(state: ChatState, config: RunnableConfig) -> dict:
    text = _last_user_text(state).strip()
    lowered = text.lower()
    t = _t(state)
    pipeline = get_pipeline()
    job_id = state.get("job_id")
    if not job_id:
        return {"messages": [AIMessage(content=t("chat_no_job"))]}
    job = pipeline.repository.get_job(job_id)
    if not job:
        return {"messages": [AIMessage(content=t("chat_no_job"))]}

    if lowered in {"/confirm", "/확정", "확정", "confirm", "ok", "예", "yes"}:
        pipeline.confirm_criteria(job_id, [c.model_dump() for c in job.criteria])
        return {
            "stage": "candidate_intake",
            "messages": [AIMessage(content=t("chat_criteria_confirmed_next"))],
        }

    parsed = _parse_criteria_edit(text, len(job.criteria))
    if parsed:
        if parsed["action"] == "remove":
            new_criteria = [c for i, c in enumerate(job.criteria, 1) if i != parsed["index"]]
        else:
            new_criteria = list(job.criteria)
            i = parsed["index"] - 1
            curr = new_criteria[i]
            new_criteria[i] = Criterion(
                name=parsed.get("name") or curr.name,
                description=parsed.get("description") or curr.description,
                weight=parsed.get("weight", curr.weight),
            )
        job.criteria = new_criteria
        pipeline.repository.upsert_job(job)
        return {
            "messages": [
                AIMessage(
                    content=_format_criteria_md(new_criteria, t) + "\n\n" + t("chat_criteria_help")
                )
            ]
        }

    return {
        "messages": [
            AIMessage(
                content=_format_criteria_md(job.criteria, t) + "\n\n" + t("chat_criteria_help")
            )
        ]
    }


def candidate_node(state: ChatState, config: RunnableConfig) -> dict:
    text = _last_user_text(state).strip()
    lowered = text.lower()
    t = _t(state)
    pipeline = get_pipeline()
    job_id = state.get("job_id")
    if not job_id:
        return {"messages": [AIMessage(content=t("chat_no_job"))]}

    if lowered in {"/done", "/끝", "done", "끝", "/results", "/결과"}:
        return {
            "stage": "results",
            "messages": [
                AIMessage(content=_format_ranking(pipeline, job_id, t) + "\n\n" + t("chat_results_help"))
            ],
        }

    pending = dict(state.get("pending_candidate") or {})
    upload = _runtime_upload(config)

    if upload:
        name = (upload.get("name") or pending.get("name") or "").strip() or "Unknown Candidate"
        github_url = upload.get("github_url") or pending.get("github_url")
        portfolio_url = upload.get("portfolio_url") or pending.get("portfolio_url")
        try:
            cand = pipeline.add_candidate_from_upload(
                job_id,
                name,
                upload["filename"],
                upload["bytes"],
                github_url=github_url,
                portfolio_url=portfolio_url,
            )
        except ValueError as exc:
            return {"messages": [AIMessage(content=f"⚠️ {exc}")]}
        evaluation = next(
            (
                e
                for e in reversed(pipeline.repository.list_evaluations(job_id))
                if e.candidate_id == cand.id
            ),
            None,
        )
        return {
            "pending_candidate": {},
            "messages": [
                AIMessage(
                    content=(
                        t("chat_candidate_added").format(name=name)
                        + "\n\n"
                        + _format_evaluation(cand, evaluation, t)
                        + "\n\n"
                        + t("chat_next_candidate")
                    )
                )
            ],
        }

    slot_handlers = [
        ("/name ", "name", "chat_candidate_name_set"),
        ("/이름 ", "name", "chat_candidate_name_set"),
        ("/github ", "github_url", "chat_candidate_github_set"),
        ("/portfolio ", "portfolio_url", "chat_candidate_portfolio_set"),
    ]
    for prefix, field, key in slot_handlers:
        if lowered.startswith(prefix):
            value = text[len(prefix):].strip()
            pending[field] = value
            return {
                "pending_candidate": pending,
                "messages": [AIMessage(content=t(key).format(value=value, name=value, url=value))],
            }

    if len(text) >= 200 and pending.get("name"):
        try:
            cand = pipeline.add_candidate(
                job_id,
                CandidateCreate(
                    name=pending["name"],
                    resume_text=text,
                    github_url=pending.get("github_url"),
                    portfolio_url=pending.get("portfolio_url"),
                ),
            )
        except ValueError as exc:
            return {"messages": [AIMessage(content=f"⚠️ {exc}")]}
        evaluation = next(
            (
                e
                for e in reversed(pipeline.repository.list_evaluations(job_id))
                if e.candidate_id == cand.id
            ),
            None,
        )
        return {
            "pending_candidate": {},
            "messages": [
                AIMessage(
                    content=(
                        t("chat_candidate_added").format(name=pending["name"])
                        + "\n\n"
                        + _format_evaluation(cand, evaluation, t)
                        + "\n\n"
                        + t("chat_next_candidate")
                    )
                )
            ],
        }

    return {"messages": [AIMessage(content=t("chat_candidate_help"))]}


def results_node(state: ChatState, config: RunnableConfig) -> dict:
    t = _t(state)
    pipeline = get_pipeline()
    job_id = state.get("job_id")
    if not job_id:
        return {"messages": [AIMessage(content=t("chat_no_job"))]}
    text = _last_user_text(state).strip()
    lowered = text.lower()

    if lowered in {"/back", "/돌아가", "/추가", "/add"}:
        return {
            "stage": "candidate_intake",
            "messages": [AIMessage(content=t("chat_candidate_help"))],
        }

    m = re.match(r"^/(?:detail|상세)\s+(\d+)$", text, re.IGNORECASE)
    if m:
        idx = int(m.group(1))
        evals = sorted(
            pipeline.repository.list_evaluations(job_id),
            key=lambda e: (e.jd_score + e.alignment_score) / 2,
            reverse=True,
        )
        if 1 <= idx <= len(evals):
            e = evals[idx - 1]
            cand = next(
                (c for c in pipeline.repository.list_candidates(job_id) if c.id == e.candidate_id),
                None,
            )
            return {"messages": [AIMessage(content=_format_candidate_detail(cand, e, t))]}

    return {
        "messages": [
            AIMessage(content=_format_ranking(pipeline, job_id, t) + "\n\n" + t("chat_results_help"))
        ]
    }


def help_node(state: ChatState, config: RunnableConfig) -> dict:
    t = _t(state)
    return {"messages": [AIMessage(content=t("chat_help_global"))]}


def restart_node(state: ChatState, config: RunnableConfig) -> dict:
    t = _t(state)
    return {
        "stage": "awaiting_jd",
        "job_id": None,
        "pending_jd_title": None,
        "pending_candidate": {},
        "messages": [AIMessage(content=t("chat_intro"))],
    }
