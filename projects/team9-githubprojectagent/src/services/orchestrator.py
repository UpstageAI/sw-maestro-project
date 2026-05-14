"""LangGraph StateGraph 오케스트레이터.

전체 흐름:
  fetch → compress → interview → wait_for_answers (interrupt)
       → merge_answers → generate (병렬) → validate
       → conditional: pass→diagram | fail→refine→validate
       → diagram → merge → END

사용자 인터뷰 응답은 LangGraph interrupt() 메커니즘으로 처리.
프론트는 Session 객체를 폴링 — 각 노드가 session.set_state로 진행상황 푸시.

디버깅 가시성:
  - 모든 노드 진입/완료를 터미널에 ▶ ✓ 로 출력 (어디서 막혔는지 즉시 보임)
  - 노드 진입 시 abort_event 체크 → 사용자가 /abort 호출 시 즉시 RuntimeError
"""
import logging
import threading
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from typing import Optional, TypedDict

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from src import config
from src.agents import (
    architecture_agent,
    cause_agent,
    dataflow_agent,
    interview_agent,
    merge_agent,
    problem_agent,
    result_agent,
    status_agent,
    validator_agent,
)
from src.models.repo import RepoContext
from src.models.story import SECTION_ORDER, Section, StoryDraft, Verdict
from src.services import context_builder, github_loader, notion_publisher
from src.services.session_manager import Session, State
from src.templates import get as get_template
from src.tools.cost_tracker import tracker

log = logging.getLogger(__name__)

SECTION_AGENTS = {
    "problem": problem_agent.run,
    "status": status_agent.run,
    "cause": cause_agent.run,
    "result": result_agent.run,
}


# ------------------------------------------------------------
# State 정의
# ------------------------------------------------------------

class PortfolioState(TypedDict, total=False):
    session_id: str
    repo_url: str
    pat: Optional[str]
    user_attached_info: Optional[str]

    repo_ctx: RepoContext
    questions: list[str]
    answers: list[str]

    problem: Optional[Section]
    status: Optional[Section]
    cause: Optional[Section]
    result: Optional[Section]

    architecture: Optional[str]
    dataflow: Optional[str]
    merged: Optional[str]

    verdict: Optional[Verdict]
    history: list[Verdict]
    iter_n: int


def _session(state: PortfolioState) -> Session:
    """세션 객체 가져오기 (set_state로 진행상황 푸시용)."""
    from src.services.session_manager import manager
    s = manager().get(state["session_id"])
    if s is None:
        raise RuntimeError(f"세션 못 찾음: {state['session_id']}")
    return s


def _build_draft(state: PortfolioState) -> StoryDraft:
    return StoryDraft(
        problem=state.get("problem"),
        status=state.get("status"),
        cause=state.get("cause"),
        result=state.get("result"),
        architecture=state.get("architecture"),
        dataflow=state.get("dataflow"),
        merged=state.get("merged"),
    )


def node(name: str):
    """노드 데코레이터 — entry/exit 로그 + abort 체크 + 예외 표시."""
    def decorator(fn):
        @wraps(fn)
        def wrapper(state: PortfolioState):
            s = _session(state)
            s.check_abort()
            t0 = time.time()
            log.info("▶ node[%s] start", name)
            try:
                result = fn(state)
                log.info("✓ node[%s] done in %.2fs", name, time.time() - t0)
                return result
            except RuntimeError as e:
                if "aborted" in str(e).lower():
                    log.warning("⏹ node[%s] aborted", name)
                    raise
                log.exception("✗ node[%s] failed in %.2fs", name, time.time() - t0)
                raise
            except Exception as e:
                log.exception("✗ node[%s] failed in %.2fs: %s", name, time.time() - t0, e)
                raise
        return wrapper
    return decorator


# ------------------------------------------------------------
# Node 함수들
# ------------------------------------------------------------

@node("fetch")
def fetch_node(state: PortfolioState) -> dict:
    s = _session(state)
    s.set_state(State.FETCHING, f"레포 fetch: {state['repo_url']}")
    tracker()._usage.clear()  # noqa: SLF001  — 세션 단위 비용 리셋

    def progress(msg: str) -> None:
        s.log.append(f"  → {msg}")

    ctx = github_loader.fetch_repo(
        state["repo_url"],
        pat=state.get("pat"),
        progress=progress,
    )
    ctx.user_attached_info = state.get("user_attached_info")
    ctx = context_builder.sanitize_files(ctx)
    s.ctx = ctx
    return {"repo_ctx": ctx}


@node("compress")
def compress_node(state: PortfolioState) -> dict:
    s = _session(state)
    s.set_state(State.COMPRESSING, "커밋/README 압축 요약")
    ctx = context_builder.compress_context(state["repo_ctx"])
    s.ctx = ctx
    return {"repo_ctx": ctx}


@node("interview")
def interview_node(state: PortfolioState) -> dict:
    s = _session(state)
    s.set_state(State.INTERVIEWING, "추가 정보 필요한지 분석")
    questions = interview_agent.run(state["repo_ctx"])
    s.questions = questions
    s.log.append(f"  → 질문 {len(questions)}개")
    return {"questions": questions}


@node("wait")
def wait_for_answers_node(state: PortfolioState) -> dict:
    """질문이 있으면 interrupt — 사용자 응답 대기. 없으면 통과."""
    questions = state.get("questions") or []
    if not questions:
        return {"answers": []}
    s = _session(state)
    s.set_state(State.INTERVIEWING, f"사용자 답변 대기 중 ({len(questions)}개 질문)")
    log.info("⏸ interrupt — waiting for user answers (%d questions)", len(questions))
    answers = interrupt({"questions": questions})
    log.info("▶ resumed with %d answers", len(answers) if answers else 0)
    return {"answers": answers}


@node("merge_answers")
def merge_answers_node(state: PortfolioState) -> dict:
    s = _session(state)
    answers = state.get("answers") or []
    questions = state.get("questions") or []
    if any(a.strip() for a in answers):
        extras = "\n".join(
            f"Q: {q}\nA: {a}"
            for q, a in zip(questions, answers)
            if a.strip()
        )
        ctx = state["repo_ctx"]
        base = ctx.user_attached_info or ""
        ctx.user_attached_info = base + ("\n\n" if base else "") + "[사용자 답변]\n" + extras
        s.ctx = ctx
        s.answers = answers
        s.log.append("  → 사용자 답변을 컨텍스트에 병합")
        return {"repo_ctx": ctx}
    return {}


@node("generate")
def generate_node(state: PortfolioState) -> dict:
    s = _session(state)
    s.set_state(State.GENERATING, "4섹션 병렬 생성")
    ctx = state["repo_ctx"]
    updates: dict = {}
    # 병렬 2 — Upstage Solar의 분당 rate limit 분산 (4 동시 → burst → 429)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {n: pool.submit(SECTION_AGENTS[n], ctx) for n in SECTION_ORDER}
        for n, f in futures.items():
            try:
                section: Section = f.result(timeout=600)  # 10분 안전장치
            except Exception as e:
                log.exception("agent[%s] 실패: %s", n, e)
                raise
            updates[n] = section
            s.draft.set(n, section)
            s.log.append(f"  → 섹션 생성: {n} ({len(section.content)}자)")
    return updates


@node("validate")
def validate_node(state: PortfolioState) -> dict:
    s = _session(state)
    s.set_state(State.VALIDATING, "4섹션 채점")
    draft = _build_draft(state)
    verdict = validator_agent.run(draft, threshold=config.SCORE_THRESHOLD)
    history = state.get("history", []) + [verdict]
    iter_n = state.get("iter_n", 0) + 1
    s.verdict = verdict
    s.history = history
    s.log.append(
        f"  → R{iter_n}: " + ", ".join(f"{x.name}={x.score}" for x in verdict.scores)
        + f" pass={verdict.overall_pass}"
    )
    return {"verdict": verdict, "history": history, "iter_n": iter_n}


def should_refine(state: PortfolioState) -> str:
    v: Verdict = state["verdict"]
    if v.overall_pass:
        return "diagram"
    if state.get("iter_n", 0) >= config.MAX_REFINE_ITER:
        return "diagram"
    return "refine"


@node("refine")
def refine_node(state: PortfolioState) -> dict:
    s = _session(state)
    weakest = state["verdict"].weakest
    idx = SECTION_ORDER.index(weakest)
    targets = list(SECTION_ORDER)[idx:]
    s.set_state(State.REFINING, f"R{state['iter_n']+1}: weakest={weakest} → {','.join(targets)} 재생성")
    ctx = state["repo_ctx"]
    updates: dict = {}
    # 병렬 2 — Upstage Solar의 분당 rate limit 분산 (4 동시 → burst → 429)
    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = {n: pool.submit(SECTION_AGENTS[n], ctx) for n in targets}
        for n, f in futures.items():
            section = f.result(timeout=600)
            updates[n] = section
            s.draft.set(n, section)
    return updates


@node("diagram")
def diagram_node(state: PortfolioState) -> dict:
    s = _session(state)
    s.set_state(State.DIAGRAMMING, "아키텍처 + 데이터플로우 다이어그램 생성")
    ctx = state["repo_ctx"]
    arch = architecture_agent.run(ctx)
    df = dataflow_agent.run(ctx)
    s.draft.architecture = arch
    s.draft.dataflow = df
    s.log.append(f"  → architecture {len(arch)}자, dataflow {len(df)}자")
    return {"architecture": arch, "dataflow": df}


@node("merge")
def merge_node(state: PortfolioState) -> dict:
    s = _session(state)
    s.set_state(State.MERGING, "최종 머지")
    draft = _build_draft(state)
    merged = merge_agent.run(draft, state["repo_ctx"])
    s.draft.merged = merged
    s.cost_report = tracker().report()
    s.set_state(
        State.READY_FOR_TEMPLATE,
        f"완료. pass={state['verdict'].overall_pass}, R={state['iter_n']}",
    )
    return {"merged": merged}


# ------------------------------------------------------------
# Graph 컴파일
# ------------------------------------------------------------

def _build_graph():
    g = StateGraph(PortfolioState)
    g.add_node("fetch", fetch_node)
    g.add_node("compress", compress_node)
    g.add_node("interview", interview_node)
    g.add_node("wait", wait_for_answers_node)
    g.add_node("merge_answers", merge_answers_node)
    g.add_node("generate", generate_node)
    g.add_node("validate", validate_node)
    g.add_node("refine", refine_node)
    g.add_node("diagram", diagram_node)
    g.add_node("merge", merge_node)

    g.add_edge(START, "fetch")
    g.add_edge("fetch", "compress")
    g.add_edge("compress", "interview")
    g.add_edge("interview", "wait")
    g.add_edge("wait", "merge_answers")
    g.add_edge("merge_answers", "generate")
    g.add_edge("generate", "validate")
    g.add_conditional_edges(
        "validate",
        should_refine,
        {"refine": "refine", "diagram": "diagram"},
    )
    g.add_edge("refine", "validate")
    g.add_edge("diagram", "merge")
    g.add_edge("merge", END)

    return g.compile(checkpointer=MemorySaver())


GRAPH = _build_graph()


# ------------------------------------------------------------
# 외부 인터페이스 — Session 기반
# ------------------------------------------------------------

def _run_graph(session: Session, payload) -> None:
    """LangGraph 실행. payload는 초기 state (dict) 또는 Command(resume=...)."""
    config_ = {"configurable": {"thread_id": session.id}, "recursion_limit": 50}
    log.info("══ graph stream start: session=%s ══", session.id)
    try:
        for _event in GRAPH.stream(payload, config=config_, stream_mode="values"):
            if session.abort_event.is_set():
                log.warning("⏹ stream loop detected abort, breaking")
                break
        log.info("══ graph stream end: session=%s ══", session.id)
    except RuntimeError as e:
        if "aborted" in str(e).lower():
            log.warning("⏹ graph aborted: session=%s", session.id)
            return
        log.exception("graph 실행 실패")
        session.error = str(e)
        session.set_state(State.ERROR, str(e))
    except Exception as e:
        log.exception("graph 실행 실패 (예상 못 한 예외)")
        session.error = f"{type(e).__name__}: {e}"
        session.set_state(State.ERROR, session.error)


def start_session(session: Session) -> None:
    initial: PortfolioState = {
        "session_id": session.id,
        "repo_url": session.repo_url,
        "pat": session.pat,
        "user_attached_info": session.user_attached_info,
        "history": [],
        "iter_n": 0,
    }
    log.info("▶▶ start_session: %s — %s", session.id, session.repo_url)
    threading.Thread(target=_run_graph, args=(session, initial), daemon=True).start()


def submit_answers(session: Session, answers: list[str]) -> None:
    session.answers = answers
    log.info("▶▶ submit_answers: %s — %d answers", session.id, len(answers))
    threading.Thread(
        target=_run_graph,
        args=(session, Command(resume=answers)),
        daemon=True,
    ).start()


def publish_session(session: Session, template_id: str) -> None:
    """동기 호출 — Notion 발행 자체는 빠름."""
    session.set_state(State.PUBLISHING, f"발행 중: {template_id}")
    try:
        result = notion_publisher.publish(
            story=session.draft,
            ctx=session.ctx,
            template=get_template(template_id),
            parent_page_id=session.notion_parent_page_id,
            notion_token=session.notion_token,
        )
        session.publish_result = result
        session.set_state(State.DONE, f"success={result['success']}")
    except Exception as e:
        log.exception("publish 실패")
        session.error = str(e)
        session.set_state(State.ERROR, str(e))
