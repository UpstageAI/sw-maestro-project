"""LangGraph node implementations.

Each node:
1. Reads what it needs from State.
2. Calls Solar with a structured-output schema.
3. Returns a partial dict to merge into State.

Mock fallbacks live here so the frontend can be developed without a Solar key.
The mocks are *content-aware* — they extract the topic from the question and
assemble plausible analysis around it, rather than returning hardcoded sample
data that's unrelated to the actual question.
"""

from __future__ import annotations

import re

import random

from app.config import get_settings
from app.graph.prompts import (
    ANALYZER_SYSTEM,
    EVALUATOR_SYSTEM,
    QUESTION_GENERATOR_SYSTEM,
    SEED_GENERATOR_SYSTEM,
    TERM_EXTRACTOR_SYSTEM,
)
from app.graph.schema import (
    AnalysisNote,
    AnalysisOutput,
    Chunk,
    Citation,
    EvaluationOutput,
    FollowUpOutput,
    FollowUpQuestion,
    GraphState,
    SeedQuestion,
    SeedRequest,
    SeedResponse,
    TermOutput,
    UserFeedback,
)

# Import search_chunks from BE storage layer — may not exist yet while
# backend-developer is still implementing it. Fail gracefully.
try:
    from app.storage.chroma import search_chunks as _search_chunks_impl
    _CHROMA_AVAILABLE = True
except Exception:  # ImportError or any initialisation error
    _CHROMA_AVAILABLE = False
    _search_chunks_impl = None  # type: ignore[assignment]
from app.graph.tools import WEB_SEARCH_TOOL_SPEC, dispatch_tool_call
from app.graph.tools.web_search import tavily_search
from app.ingestion.pipeline import _strip_html as _clean_html
from app.llm.solar import (
    structured_chat,
    structured_chat_after_tools,
    tool_calling_chat,
)

import logging
logger = logging.getLogger(__name__)


# Chunks shorter than this (after HTML stripping & whitespace normalization)
# are treated as too thin to count as a real RAG hit. They get dropped at
# retrieval time so a sparse-but-non-empty material doesn't pin Solar to a
# stub piece of content. When all chunks fall below the threshold, the
# downstream code naturally falls back to AI-only generation:
#   - seed: `_try_material_seed` returns None → static topic pool path fires
#           and Solar phrases the question from domain knowledge
#   - follow-up: `retrieved_context` is empty → the prompt's "컨텍스트가 빈
#           경우 ... 일반 지식으로 진행한다" rule activates
_USEFUL_CHUNK_MIN_CHARS = 80


# ---------- Mock helpers ----------

# Strip common Korean question scaffolding to recover the actual topic phrase.
_QUESTION_TAILS = [
    "에 대해 설명해주세요",
    "에 대해 설명해 주세요",
    "을 설명해주세요",
    "를 설명해주세요",
    "을 설명해 주세요",
    "를 설명해 주세요",
    "에 대해 말씀해주세요",
    "은 무엇입니까",
    "는 무엇입니까",
    "을 비교해주세요",
    "를 비교해주세요",
    "은 어떻게 처리하시겠습니까",
    "는 어떻게 처리하시겠습니까",
    "은 무엇인가요",
    "는 무엇인가요",
]


def _extract_topic(question: str) -> str:
    """Best-effort extraction of the topic phrase from a Korean interview question.

    Examples:
        "프로세스와 스레드의 차이를 설명해주세요." → "프로세스와 스레드의 차이"
        "TCP와 UDP의 차이를 비교해주세요." → "TCP와 UDP의 차이"
        "Spring DI 의 동작 원리는?" → "Spring DI 의 동작 원리"
    """
    cleaned = question.strip().rstrip("?.!")
    for tail in _QUESTION_TAILS:
        if cleaned.endswith(tail):
            cleaned = cleaned[: -len(tail)].rstrip(" ?.!")
            break
    return cleaned or question


def _key_term(question: str) -> str:
    """Pick the most prominent multi-character term from the question for follow-up phrasing."""
    topic = _extract_topic(question)
    # Prefer the chunk before "의 차이" / "의 동작" — typically the subject.
    for marker in ["의 차이", "의 동작", "의 원리", "의 구조"]:
        if marker in topic:
            return topic.split(marker)[0].strip()
    # Fall back to first phrase of 1–4 words.
    words = re.split(r"\s+", topic)
    if not words:
        return topic
    return " ".join(words[:3])


def _short_answer_excerpt(answer: str, max_chars: int = 50) -> str:
    """Return a short verbatim slice of the answer for the analysis 'quote' field."""
    cleaned = answer.strip().split("\n")[0]
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[:max_chars].rstrip() + "…"


_DONT_KNOW_PHRASES = [
    "잘 모르겠",
    "잘 모릅",
    "모르겠습",
    "모르겠어",
    "처음 들어",
    "기억이 안",
    "모릅니다",
]


def _detect_quality(answer: str) -> tuple[str, str]:
    """Heuristic quality detector for mock mode.
    Returns (answer_quality, explanation_or_empty)."""
    cleaned = answer.strip()
    if any(p in cleaned for p in _DONT_KNOW_PHRASES) or len(cleaned) < 30:
        return ("uncertain", "")
    return ("good", "")


def _build_mock_analysis(question: str, answer: str) -> AnalysisOutput:
    topic = _extract_topic(question)
    quality, _ = _detect_quality(answer)
    intent = (
        f"이 질문은 {topic} 에 대한 기본적인 이해를 확인하려는 의도입니다. "
        "구체적으로는 (1) 핵심 개념의 정의를 본인 말로 설명할 수 있는지, "
        "(2) 두 개념·요소 간 차이나 동작 흐름을 짚어낼 수 있는지, "
        "(3) 실무 맥락에서 어떤 트레이드오프가 있는지를 봅니다."
    )

    if quality == "uncertain":
        return AnalysisOutput(
            answer_quality="uncertain",
            explanation=(
                f"{topic} 관련 모범답안을 짚어드리면, 핵심 개념의 정의와 가장 중요한 작동 "
                "원리·차이점을 묶어서 답변하시면 됩니다. (Mock 모드 — 실제 운영 환경에서는 "
                "Solar API가 질문에 맞는 구체적 모범답안을 직접 생성합니다.)"
            ),
            question_intent=intent,
            notes=[
                AnalysisNote(
                    label="답변 부재 — 잘 모르겠다고 응답",
                    detail="해당 주제에 대한 답변이 충분히 제시되지 않았습니다.",
                    severity="critical",
                )
            ],
        )

    return AnalysisOutput(
        answer_quality="good",
        explanation="",
        question_intent=intent,
        notes=[
            AnalysisNote(
                label=f"내부 메커니즘 설명 부족 — {topic}",
                detail=(
                    "정의 수준의 답변에 머물러, 면접관이 기대하는 동작 원리·"
                    "구현 디테일·자료구조 레벨의 설명이 빠졌습니다."
                ),
                severity="moderate",
            ),
            AnalysisNote(
                label="실무 트레이드오프와 대안 부재",
                detail=(
                    "언제 사용하고 언제 피해야 하는지, 다른 선택지와의 비교가 "
                    "답변에 드러나지 않습니다."
                ),
                severity="moderate",
            ),
            AnalysisNote(
                label="구체적 예시·시나리오 누락",
                detail=(
                    "개념 위주로 서술되어 실제 사용 사례나 발생 가능한 문제 상황이 "
                    "제시되지 않았습니다."
                ),
                severity="minor",
            ),
        ],
    )


def _build_mock_terms(question: str, answer: str) -> TermOutput:
    """Pick out plausible technical terms from the question + answer for context."""
    topic = _extract_topic(question)
    candidates: list[str] = []
    # First word(s) of the topic
    candidates.append(_key_term(question))
    # Any English-letter run from question or answer (likely a tech term)
    for source in (question, answer):
        for match in re.findall(r"[A-Za-z][A-Za-z0-9+_./-]{1,}", source):
            if match not in candidates:
                candidates.append(match)
            if len(candidates) >= 6:
                break
        if len(candidates) >= 6:
            break
    return TermOutput(terms=[t for t in candidates if t][:6] or [topic])


def _build_mock_follow_ups(
    question: str,
    answer: str,
    feedback: "UserFeedback | None" = None,
    feedback_count: int = 0,
) -> FollowUpOutput:
    """Build a single mock probing follow-up.

    Returns exactly one question — the new "drill-down" model has no level
    rotation. feedback_count is used as a version suffix so repeated calls
    in the same turn produce visually different text (mock-only).
    """
    topic = _extract_topic(question)
    key = _key_term(question)
    suffix = f" (v{feedback_count})" if feedback_count > 0 else ""
    action = feedback.action if feedback else None

    if action == "refine_easier":
        text = f"[쉬운 버전] 방금 {key} 얘기 짧게 해주셨는데, 한 줄만 더 풀어서 설명해주실 수 있을까요?{suffix}"
        rationale = "정의 수준 보충 (더 쉬운 버전)"
    elif action == "refine_harder":
        text = f"[심화 버전] {key}를 실제 운영 환경에서 쓸 때 마주칠 트레이드오프 한 가지만 짚어주실래요?{suffix}"
        rationale = "트레이드오프 인지 검증 (심화)"
    else:
        text = f"방금 {key}에 대해 짧게만 말씀해주셨는데, 그러면 구체적으로 어떻게 동작하는지 좀 더 풀어 주실 수 있을까요?{suffix}"
        rationale = f"'{topic}' 정의 수준 답변 — 동작 원리 파고들기"

    return FollowUpOutput(
        follow_ups=[
            FollowUpQuestion(
                level="intermediate",
                text=text,
                rationale=rationale,
                domain_label=topic,
            )
        ]
    )


def _build_mock_eval() -> EvaluationOutput:
    return EvaluationOutput(score=0.82, pass_threshold=True, reason="모의 데이터 통과")


# Topic → mock chunk data map for knowledge_retriever mock mode.
_MOCK_CHUNK_DB: dict[str, list[dict]] = {
    "프로세스": [
        {
            "text": "프로세스는 운영체제로부터 자원을 할당받는 작업의 단위이며, 독립된 메모리 공간(코드, 데이터, 힙, 스택)을 가진다. 각 프로세스는 별도의 주소 공간을 사용하므로 다른 프로세스와 직접 메모리를 공유하지 않는다.",
            "file_name": "os_basics.md",
            "heading": "프로세스 vs 스레드",
            "score": 0.91,
        },
        {
            "text": "스레드는 프로세스 내에서 실행되는 흐름의 단위로, 같은 프로세스의 스레드들은 코드·데이터·힙 영역을 공유하고 스택만 각자 가진다. 이 공유 덕분에 컨텍스트 스위칭 비용이 프로세스보다 낮다.",
            "file_name": "os_basics.md",
            "heading": "스레드 모델",
            "score": 0.87,
        },
    ],
    "스레드": [
        {
            "text": "스레드는 프로세스 내에서 실행되는 흐름의 단위로, 같은 프로세스의 스레드들은 코드·데이터·힙 영역을 공유하고 스택만 각자 가진다. 이 공유 덕분에 컨텍스트 스위칭 비용이 프로세스보다 낮다.",
            "file_name": "os_basics.md",
            "heading": "스레드 모델",
            "score": 0.93,
        },
        {
            "text": "멀티스레딩 환경에서 공유 자원에 대한 동시 접근을 제어하기 위해 mutex, semaphore 같은 동기화 기법을 사용한다. 적절한 동기화 없이는 race condition이나 deadlock이 발생할 수 있다.",
            "file_name": "concurrency.md",
            "heading": "동기화 기법",
            "score": 0.85,
        },
    ],
    "TCP": [
        {
            "text": "TCP(Transmission Control Protocol)는 연결 지향적 프로토콜로 3-way handshake를 통해 연결을 수립한다. 데이터 전달 순서 보장, 재전송, 흐름 제어, 혼잡 제어를 제공해 신뢰성 있는 통신을 보장한다.",
            "file_name": "network_basics.md",
            "heading": "TCP vs UDP",
            "score": 0.92,
        },
        {
            "text": "UDP(User Datagram Protocol)는 비연결 지향적으로 핸드셰이크 없이 데이터를 전송한다. 오버헤드가 낮아 실시간 스트리밍, DNS, 게임 서버처럼 지연 시간이 중요한 상황에 사용된다.",
            "file_name": "network_basics.md",
            "heading": "TCP vs UDP",
            "score": 0.88,
        },
    ],
    "데이터베이스": [
        {
            "text": "인덱스는 특정 컬럼 값을 빠르게 검색하기 위한 자료구조다. B+Tree 인덱스는 균형 트리 구조로 O(log n) 탐색을 제공하며, 범위 검색에도 효율적이다.",
            "file_name": "db_fundamentals.md",
            "heading": "인덱스 구조",
            "score": 0.90,
        },
        {
            "text": "트랜잭션의 ACID 속성: 원자성(Atomicity)은 트랜잭션이 전부 성공하거나 전부 실패함을 보장, 일관성(Consistency)은 DB가 항상 유효한 상태를 유지, 고립성(Isolation)은 동시 트랜잭션이 서로 간섭하지 않음, 지속성(Durability)은 커밋된 데이터는 영구 보존됨을 의미한다.",
            "file_name": "db_fundamentals.md",
            "heading": "ACID",
            "score": 0.86,
        },
    ],
}

_MOCK_CHUNK_DEFAULT = [
    {
        "text": "기술 면접에서 핵심 개념의 정의를 명확히 설명하고, 관련된 트레이드오프와 사용 시나리오를 함께 제시하면 좋은 평가를 받을 수 있다.",
        "file_name": "interview_guide.md",
        "heading": "답변 전략",
        "score": 0.75,
    },
]


def _build_mock_chunks(question: str) -> list[Chunk]:
    """Return 2-3 plausible mock Chunk objects based on topic extracted from question."""
    topic = _extract_topic(question)
    # Try to match topic against known keywords in mock DB
    for key, entries in _MOCK_CHUNK_DB.items():
        if key in topic or key in question:
            return [
                Chunk(text=e["text"], source="public", file_name=e["file_name"], heading=e["heading"], score=e["score"])
                for e in entries
            ]
    # Fallback: generic interview guide chunk
    return [
        Chunk(text=e["text"], source="public", file_name=e["file_name"], heading=e["heading"], score=e["score"])
        for e in _MOCK_CHUNK_DEFAULT
    ]


# ---------- Nodes ----------

# Demo logging — every node entry/exit is surfaced so the LangGraph flow
# is readable on a recorded walkthrough.
from app.log_format import stage  # noqa: E402


async def analyzer_node(state: GraphState) -> dict:
    stage(
        "▶ [ANALYZER] start",
        question=state["question"],
        answer_len=len(state["answer"]),
    )
    if get_settings().use_mock_llm:
        stage("✓ [ANALYZER] done", mode="mock")
        return {"analysis": _build_mock_analysis(state["question"], state["answer"])}
    out = await structured_chat(
        AnalysisOutput,
        system=ANALYZER_SYSTEM,
        user=f"면접 질문:\n{state['question']}\n\n지원자 답변:\n{state['answer']}",
        temperature=0.2,
    )
    stage(
        "✓ [ANALYZER] done",
        quality=out.answer_quality,
        notes=len(out.notes),
        has_explanation=bool(out.explanation),
    )
    return {"analysis": out}


async def term_extractor_node(state: GraphState) -> dict:
    stage("▶ [TERMS] start", answer_len=len(state["answer"]))
    if get_settings().use_mock_llm:
        stage("✓ [TERMS] done", mode="mock")
        return {"terms": _build_mock_terms(state["question"], state["answer"])}
    out = await structured_chat(
        TermOutput,
        system=TERM_EXTRACTOR_SYSTEM,
        user=f"답변:\n{state['answer']}",
        temperature=0.0,
        reasoning_effort="low",
    )
    stage("✓ [TERMS] done", count=len(out.terms), terms=out.terms[:5])
    return {"terms": out}


async def knowledge_retriever_node(state: GraphState) -> dict:
    """Retrieve relevant document chunks from Chroma and attach to state.

    Builds a search query from extracted terms + analysis notes + question + domains,
    then calls app.storage.chroma.search_chunks (provided by backend-developer).
    Falls back to mock chunks when USE_MOCK_LLM=true or when Chroma is unavailable.
    Always returns {"retrieved_context": [...]}, never raises — graph must complete.
    """
    question = state.get("question", "")
    settings = get_settings()
    material_ids_in: list[str] = state.get("material_ids") or []
    stage(
        "▶ [RETRIEVER] start",
        material_ids=len(material_ids_in),
        web_enabled=settings.use_web_search,
    )

    # Mock mode — skip Chroma entirely
    if settings.use_mock_llm or not _CHROMA_AVAILABLE:
        stage("✓ [RETRIEVER] done", mode="mock")
        return {"retrieved_context": _build_mock_chunks(question)}

    # Build search query from available state
    terms_obj = state.get("terms")
    terms: list[str] = terms_obj.terms if terms_obj else []

    analysis = state.get("analysis")
    notes_text = ""
    if analysis and analysis.notes:
        notes_text = " ".join(n.label for n in analysis.notes[:3])

    domains: list[str] = state.get("domains") or []
    material_ids: list[str] = state.get("material_ids") or []

    query_parts = [question]
    if terms:
        query_parts.append(" ".join(terms[:5]))
    if notes_text:
        query_parts.append(notes_text)
    if domains:
        query_parts.append(" ".join(domains))
    query = " ".join(query_parts)[:500]  # guard against excessively long queries

    try:
        raw_chunks: list[dict] = await _search_chunks_impl(  # type: ignore[misc]
            query=query,
            material_ids=material_ids,
            top_k=5,
        )
        chunks = []
        for c in (raw_chunks or []):
            text = _clean_html(c.get("text", ""))
            if len(text) < _USEFUL_CHUNK_MIN_CHARS:
                continue  # too thin to ground a probe — let LLM use general knowledge
            chunks.append(
                Chunk(
                    text=text,
                    source=c.get("source", "public"),
                    file_name=c.get("file_name", ""),
                    heading=_clean_html(c.get("heading", "")),
                    score=float(c.get("score", 0.0)),
                )
            )
    except Exception:
        # Chroma unavailable or query failed — safe fallback, graph continues
        chunks = []

    # Web search fallback: fires only when Chroma is genuinely thin.
    # Skip when we already have ≥2 chunks with at least one decent score —
    # the tail-end web hits add little signal but cost 2-5s of latency, and
    # local dev hits the Next.js proxy timeout when this stacks with the
    # downstream Solar calls.
    if settings.use_web_search:
        chunk_scores = [c.score for c in chunks]
        good_local = (
            len(chunks) >= 2
            and chunk_scores
            and max(chunk_scores) >= 0.4
        )
        needs_web = (not good_local) and (
            (not chunks) or (max(chunk_scores) < 0.5 if chunk_scores else True)
        )
        if needs_web:
            web_hits = await tavily_search(query, max_results=3)
            for h in web_hits:
                chunks.append(
                    Chunk(
                        text=h.snippet[:1200],
                        source="web",
                        file_name=h.title or h.url,
                        heading="",
                        score=h.score,
                        url=h.url,
                    )
                )
            if web_hits:
                chunks.sort(key=lambda c: c.score, reverse=True)
                logger.info("knowledge_retriever: web fallback added %d hits", len(web_hits))

    user_chunks = sum(1 for c in chunks if c.source == "user")
    web_chunks = sum(1 for c in chunks if c.source == "web")
    public_chunks = sum(1 for c in chunks if c.source == "public")
    stage(
        "✓ [RETRIEVER] done",
        total=len(chunks),
        user=user_chunks,
        web=web_chunks,
        public=public_chunks,
    )
    return {"retrieved_context": chunks}


async def question_generator_node(state: GraphState) -> dict:
    fb_in: UserFeedback | None = state.get("feedback")
    iter_in = state.get("iteration_count", 0)
    stage(
        "▶ [QGEN] start",
        iteration=iter_in,
        feedback=fb_in.action if fb_in else None,
        retrieved=len(state.get("retrieved_context") or []),
    )
    if get_settings().use_mock_llm:
        feedback_count = state.get("feedback_count", 0)
        out_mock = _build_mock_follow_ups(
            state["question"],
            state["answer"],
            feedback=fb_in,
            feedback_count=feedback_count,
        )
        stage("✓ [QGEN] done", mode="mock", count=len(out_mock.follow_ups))
        return {
            "follow_ups": out_mock,
            "iteration_count": iter_in + 1,
        }

    analysis = state["analysis"].model_dump_json(indent=2)
    terms = ", ".join(state["terms"].terms) if state.get("terms") else "(없음)"
    iteration = state.get("iteration_count", 0)
    domains = state.get("domains") or []
    keywords = state.get("keywords") or []

    scope_lines = []
    if domains:
        scope_lines.append(f"면접 분야 범위: {', '.join(domains)}")
    if keywords:
        scope_lines.append(f"사용자 추가 키워드: {', '.join(keywords)}")
    if scope_lines:
        scope_lines.append(
            "위 범위 안에서 답변 내용에 다른 분야·키워드 관련 용어가 등장하면 "
            "꼬리 질문 중 하나는 그쪽으로 자연스럽게 전환하세요 (분야 전환 원칙 7번 참조)."
        )
    scope_line = "\n" + "\n".join(scope_lines) if scope_lines else ""

    # Format retrieved context for the prompt
    retrieved: list = state.get("retrieved_context") or []
    context_section = ""
    if retrieved:
        context_lines = []
        for chunk in retrieved:
            if chunk.source == "web":
                url_line = f"\nURL: {chunk.url}" if chunk.url else ""
                label = f"[출처: {chunk.file_name} (web){url_line}]"
            else:
                label = f"[자료: {chunk.file_name}"
                if chunk.heading:
                    label += f"#{chunk.heading}"
                label += "]"
            context_lines.append(f"{label}\n{chunk.text}")
        context_section = "\n\n검색된 참고 자료:\n" + "\n\n".join(context_lines)

    user_prompt = f"""면접 질문:
{state['question']}

지원자 답변:
{state['answer']}

분석 결과:
{analysis}

추출된 핵심 용어: {terms}{scope_line}{context_section}

위 정보를 바탕으로 난이도별 꼬리 질문 3개를 생성하세요."""

    if iteration > 0:
        user_prompt += (
            f"\n\n참고: 이전 시도가 품질 기준을 통과하지 못했습니다 (시도 #{iteration + 1}). "
            "이전보다 더 구체적이고 답변에 밀착된 질문을 생성하세요."
        )

    # Incorporate user feedback when regenerating after HITL
    fb: UserFeedback | None = state.get("feedback")
    if fb:
        if fb.action == "regenerate":
            user_prompt += (
                f"\n\n사용자가 이전 follow-up을 거절했어. "
                f"다른 각도로 새로 만들어줘. 사유: {fb.reason or '(없음)'}"
            )
        elif fb.action == "refine_easier":
            user_prompt += (
                f"\n\n이전 질문이 너무 어려웠대. "
                f"같은 분야로 한 단계 더 쉽게 다시. 사유: {fb.reason or '(없음)'}"
            )
        elif fb.action == "refine_harder":
            user_prompt += (
                f"\n\n이전 질문이 너무 쉬웠대. "
                f"같은 분야로 한 단계 더 어렵게 다시. 사유: {fb.reason or '(없음)'}"
            )

        # Attach previous follow-ups as history to avoid duplicates
        prev = state.get("follow_ups")
        if prev and prev.follow_ups:
            prev_lines = "\n".join(f"- {q.text}" for q in prev.follow_ups[:3])
            user_prompt += f"\n\n## 이전에 생성됐던 (피하기)\n{prev_lines}"

    settings = get_settings()
    if settings.enable_llm_tool_calling and settings.use_web_search:
        # LLM may call web_search to enrich the question with fresh info.
        msgs = await tool_calling_chat(
            system=QUESTION_GENERATOR_SYSTEM,
            user=user_prompt,
            tools=[WEB_SEARCH_TOOL_SPEC],
            tool_dispatcher=dispatch_tool_call,
            temperature=0.7,
            max_iters=1,
        )
        out = await structured_chat_after_tools(
            FollowUpOutput,
            messages=msgs,
            temperature=0.3,
        )
    else:
        out = await structured_chat(
            FollowUpOutput,
            system=QUESTION_GENERATOR_SYSTEM,
            user=user_prompt,
            temperature=0.7,
        )
    first = out.follow_ups[0] if out.follow_ups else None
    stage(
        "✓ [QGEN] done",
        count=len(out.follow_ups),
        first_level=first.level if first else None,
        first_text=first.text if first else None,
    )
    return {"follow_ups": out, "iteration_count": iteration + 1}


async def generate_seed_question(req: SeedRequest) -> SeedResponse:
    """One-shot Solar call (no graph) that generates the first interview question.

    Two paths:

    1. **Material-driven** — when the user has uploaded materials, mine a
       random chunk from those materials and ask Solar to phrase a question
       on the chunk's topic. Topic diversity is bounded by the material
       content, not by a static pool, so each first question is grounded in
       what the user actually wants to be asked about. Citations are returned.

    2. **Static pool fallback** — when no materials are attached (or Chroma
       returns nothing useful), fall back to a curated per-domain topic pool.
       BE pre-picks the topic randomly and instructs Solar to phrase only
       that topic. A keyword-overlap check catches Solar drifting back to
       the canonical Q for the 분야 (e.g. 운영체제 → 프로세스/스레드) and
       triggers a retry.

    Mock mode (`USE_MOCK_LLM=true`) always uses the deterministic static mock.
    """
    if get_settings().use_mock_llm:
        return _mock_seed(req)

    domains_line = ", ".join(req.domains) if req.domains else "(없음)"
    keywords_line = ", ".join(req.keywords) if req.keywords else "(없음)"
    track_label = "CS 기초" if req.track == "cs" else "기술 스택"

    excluded_norm = [_seed_keyword_set(q) for q in req.exclude_questions]

    # ---------- Path 1: material-driven ----------
    if req.material_ids and _CHROMA_AVAILABLE:
        material_seed = await _try_material_seed(req, excluded_norm, track_label)
        if material_seed is not None:
            return material_seed

    # ---------- Path 2: static pool ----------
    # Server-side random pick — this is what actually creates diversity when
    # we have no material to mine.
    suggested = _pick_seed_angle(req, excluded_norm)

    if suggested is not None:
        sample_q, suggested_label = suggested
        # Topic-first prompt: putting the chosen topic before the 분야 list
        # prevents Solar from anchoring on the canonical Q for the 분야
        # (e.g. 운영체제 → 프로세스/스레드). The 분야/keyword list is demoted
        # to "참고 정보" so Solar treats it as context, not a menu.
        user_prompt = f"""[필수] 다음 토픽으로 첫 면접 질문을 한 문장 만들어주세요.

토픽: "{sample_q}"
분야: {suggested_label}

규칙:
1. 위 토픽 외 다른 토픽으로 절대 바꾸지 마세요.
   특히 '운영체제 → 프로세스/스레드 차이', '네트워크 → TCP/UDP 차이' 같은
   분야명만 보고 캐노니컬 질문으로 바꾸는 자동 변환은 금지입니다.
2. 토픽이 가리키는 주제(개념·기능·작동 원리·차이 등)는 유지하되,
   문장 표현은 반드시 본인 말로 자연스럽게 변형해주세요. 토픽 문장을 통째로
   복사·붙여넣기 하면 실패입니다. (예: "쿠버네티스에 대해 알고 계신 내용을
   자유롭게 설명해주세요." 같은 일반 표현은 금지. 대신 "쿠버네티스가 컨테이너
   오케스트레이션에서 어떤 문제를 해결해주는지 들어보셨어요?" 처럼 구체적으로.)
3. 한국어 존댓말, 한 문장.
4. domain_label 에는 '{suggested_label}' 을 그대로 넣으세요.

(참고 정보)
- 트랙: {track_label}
- 사용자가 선택한 분야 전체: {domains_line}
- 사용자 추가 키워드: {keywords_line}"""
    else:
        user_prompt = f"""트랙: {track_label}
면접 분야: {domains_line}
사용자 추가 키워드: {keywords_line}

위 후보들 중 하나를 무작위로 골라 면접의 첫 질문을 한 문장 생성하세요.
어떤 분야 또는 키워드에서 골랐는지 domain_label 에 명시하세요."""

    if req.exclude_questions:
        recent_lines = "\n".join(f"- {q}" for q in req.exclude_questions[-10:])
        user_prompt += (
            "\n\n## 이미 물어본 질문 (반드시 피하기)\n"
            f"{recent_lines}\n\n"
            "위 질문들의 토픽을 다시 다루지 마세요. 표현만 바꾸는 것은 금지입니다."
        )

    # Topic-fidelity check: when we pre-picked a topic, the generated question
    # MUST share at least one content keyword with that topic. Catches Solar
    # ignoring our topic and reverting to the canonical question for the 분야.
    requested_topic_kw: set[str] | None = (
        _seed_keyword_set(suggested[0]) if suggested is not None else None
    )

    settings = get_settings()
    use_tools = settings.enable_llm_tool_calling and settings.use_web_search

    seed: SeedQuestion | None = None
    for _ in range(3):
        if use_tools:
            msgs = await tool_calling_chat(
                system=SEED_GENERATOR_SYSTEM,
                user=user_prompt,
                tools=[WEB_SEARCH_TOOL_SPEC],
                tool_dispatcher=dispatch_tool_call,
                temperature=0.7,
                max_iters=1,
            )
            seed = await structured_chat_after_tools(
                SeedQuestion,
                messages=msgs,
                temperature=0.3,
            )
        else:
            seed = await structured_chat(
                SeedQuestion,
                system=SEED_GENERATOR_SYSTEM,
                user=user_prompt,
                temperature=0.7,
            )
        if _seed_too_similar(seed.question, excluded_norm):
            continue  # collides with already-asked
        if requested_topic_kw and not (_seed_keyword_set(seed.question) & requested_topic_kw):
            continue  # Solar drifted to a different topic — retry
        return SeedResponse(question=seed.question, domain_label=seed.domain_label)

    # Final fallback: LLM keeps producing the same canonical question. Pull
    # from the deterministic mock template list, skipping anything similar to
    # what's already been asked.
    fallback = _seed_template_fallback(req, excluded_norm)
    if fallback is not None:
        return fallback
    assert seed is not None
    return SeedResponse(question=seed.question, domain_label=seed.domain_label)


async def _try_material_seed(
    req: SeedRequest,
    excluded_norm: list[set[str]],
    track_label: str,
) -> SeedResponse | None:
    """Pull diverse chunks from the user's uploaded materials, pick one
    randomly, and ask Solar to phrase a first interview question grounded
    in that chunk. Returns None if Chroma yields nothing usable (e.g. all
    candidates collide with already-asked questions, or no user-source
    chunks were retrieved) — caller falls back to the static pool path.
    """
    chunks = await _retrieve_seed_chunks(req, excluded_norm)
    if not chunks:
        return None

    chosen = random.choice(chunks)
    domain_label = _guess_seed_domain_label(chosen, req)

    domains_line = ", ".join(req.domains) if req.domains else "(없음)"
    keywords_line = ", ".join(req.keywords) if req.keywords else "(없음)"
    chunk_header = chosen.file_name + (f" — {chosen.heading}" if chosen.heading else "")
    chunk_excerpt = chosen.text[:800]  # cap prompt size

    user_prompt = f"""트랙: {track_label}
면접 분야: {domains_line}
사용자 추가 키워드: {keywords_line}

지원자가 첨부한 자료의 한 부분입니다. 이 부분에서 다루는 토픽을 식별해 첫 면접 질문을 만드세요.

자료 출처: {chunk_header}
자료 내용:
\"\"\"
{chunk_excerpt}
\"\"\"

규칙:
1. 자료의 본문을 그대로 베끼지 마세요. 자료가 다루는 핵심 토픽(개념·기법·차이·동작 원리 등) 중 하나를 골라 자연스러운 면접 질문 형태로 변형하세요.
2. 신입 ~ 1년차 면접의 첫 질문 난이도. 정의 / 큰 그림 / 두 개념 비교 수준 — 부담 없이 답할 수 있어야 합니다.
3. 한국어 존댓말, 회화체 면접관 톤 OK ('혹시 ~ 들어보셨어요?', '~ 한 번 설명해주실래요?').
4. 영어 기술 용어는 원문 그대로.
5. domain_label 에는 '{domain_label}' 을 그대로 넣으세요."""

    if req.exclude_questions:
        recent_lines = "\n".join(f"- {q}" for q in req.exclude_questions[-10:])
        user_prompt += (
            "\n\n## 이미 물어본 질문 (반드시 피하기)\n"
            f"{recent_lines}\n\n"
            "위 질문들의 토픽과 동일하거나 표현만 살짝 바꾼 질문은 만들지 마세요."
        )

    settings = get_settings()
    use_tools = settings.enable_llm_tool_calling and settings.use_web_search

    seed: SeedQuestion | None = None
    for _ in range(2):  # one retry on similarity collision
        if use_tools:
            msgs = await tool_calling_chat(
                system=SEED_GENERATOR_SYSTEM,
                user=user_prompt,
                tools=[WEB_SEARCH_TOOL_SPEC],
                tool_dispatcher=dispatch_tool_call,
                temperature=0.7,
                max_iters=1,
            )
            seed = await structured_chat_after_tools(
                SeedQuestion,
                messages=msgs,
                temperature=0.3,
            )
        else:
            seed = await structured_chat(
                SeedQuestion,
                system=SEED_GENERATOR_SYSTEM,
                user=user_prompt,
                temperature=0.7,
            )
        if not _seed_too_similar(seed.question, excluded_norm):
            # Only attach a citation when the LLM actually pulled topical
            # content from the chunk. Heuristic: ≥2 unique non-stopword
            # tokens shared between the chunk's heading + first 400 chars
            # and the generated question. Avoids the "Special Thanks"
            # false-citation where the LLM ignored the chunk and invented
            # a question from general knowledge.
            chunk_kws = _seed_keyword_set(
                (chosen.heading or "") + " " + chosen.text[:400]
            )
            question_kws = _seed_keyword_set(seed.question)
            citations: list[Citation] = []
            if len(chunk_kws & question_kws) >= 2:
                citations = [
                    Citation(
                        file_name=chosen.file_name,
                        heading=chosen.heading,
                        excerpt=_excerpt_for_citation(chosen.text),
                    )
                ]
            return SeedResponse(
                question=seed.question,
                domain_label=seed.domain_label or domain_label,
                citations=citations,
            )
    # Both attempts collided — let caller try the static pool.
    return None


async def _retrieve_seed_chunks(
    req: SeedRequest,
    excluded_norm: list[set[str]],
) -> list[Chunk]:
    """Query Chroma once per selected domain/keyword and aggregate chunks
    from the user's uploaded materials.

    Strategy: domain label as the query, top_k=8 per query, then dedup by
    (file_name, heading) to maximize topical spread. Filters to source='user'
    only — public corpus chunks are reserved for follow-up RAG, not seed.
    """
    if _search_chunks_impl is None:
        return []

    queries = [*req.domains, *req.keywords]
    if not queries:
        queries = ["기술 면접 핵심 개념"]

    seen: dict[tuple[str, str], Chunk] = {}
    for q in queries:
        try:
            raw = await _search_chunks_impl(  # type: ignore[misc]
                query=q,
                material_ids=req.material_ids,
                top_k=8,
            )
        except Exception:
            continue
        for c in raw or []:
            if (c.get("source") or "user") != "user":
                continue  # skip public chunks for seed
            text = _clean_html(c.get("text", ""))
            if len(text) < _USEFUL_CHUNK_MIN_CHARS:
                continue  # too thin to mine a topic from — fall through to static pool
            key = (c.get("file_name", ""), c.get("heading", ""))
            if key in seen:
                continue
            seen[key] = Chunk(
                text=text,
                source="user",
                file_name=c.get("file_name", ""),
                heading=_clean_html(c.get("heading", "")),
                score=float(c.get("score", 0.0)),
            )

    candidates = list(seen.values())
    if not candidates:
        return []
    if excluded_norm:
        fresh = [
            c for c in candidates
            if not _seed_too_similar((c.heading + " " + c.text[:200]), excluded_norm)
        ]
        if fresh:
            candidates = fresh
    return candidates


def _guess_seed_domain_label(chunk: Chunk, req: SeedRequest) -> str:
    """Pick the most plausible domain label for a retrieved chunk.

    Best-effort — checks if any selected domain or keyword appears as a
    substring in the chunk's heading or text. Falls back to the first
    domain (or keyword, or '일반') when no match is found.
    """
    haystack = (chunk.heading + " " + chunk.text[:300]).lower()
    for label in [*req.domains, *req.keywords]:
        if label.lower() in haystack:
            return label
    if req.domains:
        return req.domains[0]
    if req.keywords:
        return req.keywords[0]
    return "일반"


_CITATION_HTML_TAG_RE = re.compile(r"<[^<>]+>")


def _excerpt_for_citation(text: str, max_chars: int = 280) -> str:
    """Trim chunk text down to a 3-6 line excerpt for the citations card.

    Strips HTML tags defensively so chunks ingested before the pipeline's
    HTML cleanup (or any tag that slipped through) don't leak into the UI.
    """
    cleaned = _CITATION_HTML_TAG_RE.sub("", text).strip().replace("\r\n", "\n")
    if len(cleaned) <= max_chars:
        return cleaned
    cut = cleaned[:max_chars]
    # break at the last sentence-ish boundary if possible
    for sep in ["\n", ". ", "다.", "요.", "다 ", "요 "]:
        idx = cut.rfind(sep)
        if idx > max_chars * 0.6:
            return cut[: idx + len(sep)].rstrip() + " …"
    return cut.rstrip() + " …"


def _pick_seed_angle(
    req: SeedRequest,
    excluded_norm: list[set[str]],
) -> tuple[str, str] | None:
    """Randomly pick a (sample_question, domain_label) from the curated pool.

    Used to bias the seed prompt with a server-side random choice — LLMs do
    not actually randomize topic selection, so we pre-pick the topic and only
    let Solar phrase it. Filters out angles that overlap with already-asked
    questions; if all are excluded, falls back to the unfiltered pool so the
    user always gets *something*. Returns None only when both domains and
    keywords are empty (which the API layer already 400's on).
    """
    pool: list[tuple[str, str]] = []
    for label in req.domains:
        templates = _MOCK_SEED_TEMPLATES.get(label, [])
        for t in templates:
            pool.append((t, label))
        if not templates:
            pool.append(
                (f"{label}의 핵심 개념 중 자신 있는 부분 하나를 골라 설명해주세요.", label)
            )
    for kw in req.keywords:
        # Multiple concrete angles per custom keyword so LLM can pick a
        # specific topic and rephrase, instead of always falling back to
        # the generic "~에 대해 자유롭게 설명" template.
        for angle in _keyword_seed_angles(kw):
            pool.append((angle, kw))
    if not pool:
        return None
    if excluded_norm:
        fresh = [
            (q, label) for (q, label) in pool
            if not _seed_too_similar(q, excluded_norm)
        ]
        if fresh:
            pool = fresh
    return random.choice(pool)


def _keyword_seed_angles(kw: str) -> list[str]:
    """Concrete starter-question angles for a user-supplied keyword.

    The LLM picks one randomly and rephrases. Replaces the previous single
    "~에 대해 알고 계신 내용을 자유롭게 설명해주세요" template, which the LLM
    kept echoing verbatim because there was nothing to vary against.
    """
    return [
        f"{kw}가 어떤 기술이고 어떤 문제를 해결하기 위해 등장했는지 한 번 설명해주실래요?",
        f"{kw}의 핵심 개념을 본인이 이해하신 대로 한 줄로 정의해 주실 수 있을까요?",
        f"{kw}의 기본적인 작동 원리나 구조를 신입 입장에서 간단히 설명해주세요.",
        f"{kw}와 비교되는 비슷한 도구·기술이 있다면 어떤 차이가 있는지 말씀해주실 수 있나요?",
    ]


def _seed_template_fallback(
    req: SeedRequest,
    excluded_norm: list[set[str]],
) -> SeedResponse | None:
    candidates: list[tuple[str, str]] = []
    for label in req.domains:
        for t in _MOCK_SEED_TEMPLATES.get(label, []):
            candidates.append((t, label))
        if label not in _MOCK_SEED_TEMPLATES:
            candidates.append(
                (f"{label}의 핵심 개념 중 자신 있는 부분 하나를 골라 설명해주세요.", label)
            )
    for kw in req.keywords:
        for angle in _keyword_seed_angles(kw):
            candidates.append((angle, kw))
    fresh = [c for c in candidates if not _seed_too_similar(c[0], excluded_norm)]
    if not fresh:
        return None
    q, label = random.choice(fresh)
    return SeedResponse(question=q, domain_label=label)


_SEED_STOPWORDS: set[str] = {
    "설명", "해주세요", "주세요", "주실래요", "본인", "한번", "말로",
    "대해", "어떻게", "무엇", "무엇인가요", "무엇입니까", "왜",
    "그리고", "그것", "이것", "저것", "또한", "예를", "들어",
}


def _seed_keyword_set(text: str) -> set[str]:
    """Extract content keywords from a question for duplicate detection.

    Strips punctuation/stopwords; keeps Korean (length>=2) and English (length>=2)
    word-like tokens. Words are lowercased so 'TCP' / 'tcp' collide.
    """
    tokens = re.findall(r"[가-힣]{2,}|[A-Za-z]{2,}", text.lower())
    return {t for t in tokens if t not in _SEED_STOPWORDS}


# Common Korean particles that often suffix nouns in question form. Stripping
# them turns "프로세스와" → "프로세스" so the same noun across phrasings collapses.
_KO_PARTICLES = (
    "와의", "과의", "에서의", "에서는", "에서", "에는", "에서도",
    "와", "과", "은", "는", "이", "가", "을", "를", "의", "로", "으로",
    "에", "도", "만", "이나", "나", "야", "아", "께",
)


def _seed_topic_terms(questions: list[str]) -> set[str]:
    """Pull topical nouns out of already-asked questions to forbid in the prompt.

    Naive Korean lemmatization: strip the longest matching trailing particle,
    drop tokens that survive only as 1-char fragments. Also keeps English/ASCII
    technical terms verbatim. Stopwords are still excluded.
    """
    raw: set[str] = set()
    for q in questions:
        for tok in re.findall(r"[가-힣]+|[A-Za-z][A-Za-z0-9]*", q):
            t = tok.strip()
            if not t:
                continue
            if re.match(r"^[A-Za-z]", t):
                # Technical English term — keep as-is, lowercased.
                lt = t.lower()
                if len(lt) >= 2 and lt not in _SEED_STOPWORDS:
                    raw.add(lt)
                continue
            # Korean: peel off particle suffix
            stripped = t
            for p in _KO_PARTICLES:
                if stripped.endswith(p) and len(stripped) > len(p) + 1:
                    stripped = stripped[: -len(p)]
                    break
            if len(stripped) >= 2 and stripped not in _SEED_STOPWORDS:
                raw.add(stripped)
    return raw


def _seed_too_similar(
    new_question: str,
    excluded_keyword_sets: list[set[str]],
    threshold: float = 0.5,
) -> bool:
    new_set = _seed_keyword_set(new_question)
    if not new_set:
        return False
    for prev in excluded_keyword_sets:
        if not prev:
            continue
        denom = max(len(new_set), len(prev))
        overlap = len(new_set & prev) / denom
        if overlap >= threshold:
            return True
    return False


# Curated first-question pool per domain. Used both as the angle source for
# `generate_seed_question` (which biases the LLM with one randomly-picked
# entry) and as the deterministic mock/fallback. Keep entries at 신입 수준
# 난이도, natural Korean phrasing, and **broad topic coverage** within each
# domain so the user doesn't see the same opening question twice in a row.
_MOCK_SEED_TEMPLATES: dict[str, list[str]] = {
    "운영체제": [
        "프로세스와 스레드의 차이를 설명해주세요.",
        "컨텍스트 스위칭이 무엇이고 왜 비용이 발생하는지 설명해주세요.",
        "mutex 와 semaphore 의 차이를 설명해주세요.",
        "데드락이 발생하는 조건과 예방 방법 한 가지를 설명해주세요.",
        "가상 메모리가 무엇이고 왜 사용하는지 설명해주세요.",
        "사용자 모드와 커널 모드는 어떻게 다른지 설명해주세요.",
        "CPU 스케줄링 알고리즘 중 하나를 골라 동작 방식을 설명해주세요.",
    ],
    "데이터베이스": [
        "데이터베이스 인덱스가 검색 속도를 빠르게 하는 원리를 설명해주세요.",
        "트랜잭션의 ACID 속성을 간단히 설명해주세요.",
        "정규화가 왜 필요하고, 어떤 경우에 비정규화를 고려하는지 설명해주세요.",
        "INNER JOIN 과 LEFT JOIN 의 차이를 설명해주세요.",
        "RDBMS 와 NoSQL 을 어떤 기준으로 선택하시는지 설명해주세요.",
        "트랜잭션 격리 수준 중 하나를 골라 어떤 문제를 해결하는지 설명해주세요.",
        "B+Tree 인덱스가 다른 자료구조 대비 가지는 장점을 설명해주세요.",
    ],
    "네트워크": [
        "TCP 와 UDP 의 차이를 설명해주세요.",
        "HTTP 와 HTTPS 의 차이를 설명해주세요.",
        "TCP 의 3-way handshake 과정을 설명해주세요.",
        "DNS 가 도메인 이름을 IP 주소로 바꾸는 흐름을 설명해주세요.",
        "REST API 의 핵심 원칙 중 자신 있는 것 하나를 설명해주세요.",
        "쿠키, 세션, 토큰 인증의 차이를 설명해주세요.",
        "OSI 7 계층 중 본인이 이해한 만큼 큰 그림으로 설명해주세요.",
    ],
    "자료구조": [
        "해시 테이블의 충돌이 발생하는 이유와 해결 방법을 설명해주세요.",
        "스택과 큐의 차이를 설명해주세요.",
        "배열과 연결 리스트의 차이와 각각의 장단점을 설명해주세요.",
        "이진 탐색 트리에서 균형 트리(AVL, Red-Black)가 왜 필요한지 설명해주세요.",
        "힙 자료구조의 특징과 어떤 상황에 쓰는지 설명해주세요.",
        "그래프를 표현하는 두 가지 방식의 차이를 설명해주세요.",
    ],
    "알고리즘": [
        "동적 계획법이 분할 정복과 어떻게 다른지 설명해주세요.",
        "이진 탐색의 시간 복잡도와 동작 원리를 설명해주세요.",
        "정렬 알고리즘 중 두 개를 골라 시간 복잡도와 차이를 설명해주세요.",
        "그리디 알고리즘이 항상 최적해를 보장하지 않는 이유를 설명해주세요.",
        "BFS 와 DFS 는 어떤 상황에서 다르게 쓰이나요?",
        "Big-O 표기법이 무엇을 의미하는지 본인 말로 설명해주세요.",
    ],
    "컴퓨터구조": [
        "CPU 캐시가 성능에 어떻게 영향을 주는지 설명해주세요.",
        "파이프라이닝이 무엇이고 왜 사용하는지 설명해주세요.",
        "캐시 적중률을 높이려면 어떤 접근 패턴이 유리한지 설명해주세요.",
        "가상 메모리가 물리 메모리와 어떻게 매핑되는지 큰 그림으로 설명해주세요.",
        "메모리 계층 구조(레지스터-캐시-메모리-디스크)가 존재하는 이유를 설명해주세요.",
    ],
    "Spring": [
        "Spring 의 Dependency Injection 이 왜 필요한지, 일반적인 객체 생성과 비교해 설명해주세요.",
        "Spring AOP 의 동작 방식을 간단히 설명해주세요.",
        "Spring Bean 의 생명주기를 큰 그림으로 설명해주세요.",
        "@Transactional 어노테이션이 어떻게 동작하는지 본인 말로 설명해주세요.",
        "Spring MVC 의 요청 처리 흐름을 간단히 설명해주세요.",
        "IoC 컨테이너가 개발자에게 무엇을 해주는지 설명해주세요.",
        "JPA 의 영속성 컨텍스트가 무엇이고 왜 필요한지 설명해주세요.",
    ],
    "React": [
        "React 의 useState 와 useReducer 는 언제 다르게 사용하시나요?",
        "React 의 가상 DOM 이 무엇이고 왜 사용하는지 설명해주세요.",
        "useEffect 의 의존성 배열이 왜 중요한지 설명해주세요.",
        "React 컴포넌트가 리렌더링 되는 조건을 설명해주세요.",
        "Props 와 State 의 차이와 각각 언제 쓰는지 설명해주세요.",
        "Controlled 컴포넌트와 Uncontrolled 컴포넌트의 차이를 설명해주세요.",
        "React Key prop 이 왜 필요한지 설명해주세요.",
    ],
    "Node.js": [
        "Node.js 의 이벤트 루프가 동시 요청을 처리하는 방식을 설명해주세요.",
        "Node.js 가 싱글 스레드라고 하는데 왜 그런지, 그리고 어떤 한계가 있는지 설명해주세요.",
        "Express 미들웨어가 어떻게 동작하는지 설명해주세요.",
        "스트림(Stream)이 무엇이고 어떤 상황에 쓰는지 설명해주세요.",
        "비동기 처리에서 Promise 와 async/await 의 차이를 설명해주세요.",
        "Node.js 에서 CPU 바운드 작업을 처리할 때 어떤 점을 고려해야 하나요?",
    ],
    "Django": [
        "Django ORM 의 N+1 문제와 해결 방법을 설명해주세요.",
        "Django 의 미들웨어가 어떻게 동작하는지 설명해주세요.",
        "Django 의 MVT 구조를 일반적인 MVC 와 비교해 설명해주세요.",
        "QuerySet 의 lazy evaluation 이 무엇이고 왜 그렇게 동작하는지 설명해주세요.",
        "Django REST Framework 의 Serializer 가 어떤 역할을 하는지 설명해주세요.",
        "Django 의 Signal 이 어떤 상황에 유용한지 설명해주세요.",
    ],
    "Vue": [
        "Vue 3 의 Composition API 가 Options API 와 어떻게 다르고 왜 도입되었는지 설명해주세요.",
        "Vue 의 반응성 시스템(reactivity)이 어떻게 동작하는지 설명해주세요.",
        "v-if 와 v-show 의 차이를 설명해주세요.",
        "Vue 의 computed 와 watch 는 언제 다르게 사용하나요?",
        "Vue Router 의 동작 방식을 큰 그림으로 설명해주세요.",
        "Pinia(또는 Vuex)가 어떤 문제를 해결해주는지 설명해주세요.",
    ],
    "FastAPI": [
        "FastAPI 의 Dependency Injection 시스템을 어떻게 활용하시나요?",
        "FastAPI 가 Pydantic 으로 검증을 처리하는 방식을 설명해주세요.",
        "async def 와 def 엔드포인트는 어떻게 다르게 동작하나요?",
        "FastAPI 가 자동 생성하는 OpenAPI 문서가 어떤 정보로부터 만들어지는지 설명해주세요.",
        "FastAPI 의 Background Tasks 가 어떤 상황에 유용한지 설명해주세요.",
        "FastAPI 에서 인증·인가를 보통 어떻게 구현하시나요?",
    ],
    "Kotlin": [
        "Kotlin 코루틴이 일반 스레드 모델과 비교해 갖는 장점을 설명해주세요.",
        "Sealed Class 가 일반 abstract class 와 어떻게 다르고 어떤 상황에 쓰는지 설명해주세요.",
        "Kotlin 의 null safety 가 어떻게 NPE 를 줄여주는지 설명해주세요.",
        "data class 가 일반 class 와 다른 점을 설명해주세요.",
        "Kotlin 의 확장 함수(extension function)가 어떤 문제를 해결해주는지 설명해주세요.",
        "Kotlin 의 lateinit 과 lazy 의 차이를 설명해주세요.",
    ],
    "iOS Swift": [
        "Swift 의 ARC(Automatic Reference Counting) 가 메모리를 어떻게 관리하는지 설명해주세요.",
        "강한 참조 순환(strong reference cycle)이 왜 발생하고 어떻게 해결하는지 설명해주세요.",
        "Swift 의 struct 와 class 의 차이를 설명해주세요.",
        "Optional 이 무엇이고 왜 도입되었는지 설명해주세요.",
        "MVVM 패턴이 MVC 와 어떻게 다르고 왜 iOS 에서 자주 쓰이는지 설명해주세요.",
        "SwiftUI 와 UIKit 은 화면을 그리는 방식이 어떻게 다른지 설명해주세요.",
    ],
    "Flutter": [
        "Flutter 의 StatefulWidget 과 StatelessWidget 의 차이와 선택 기준을 설명해주세요.",
        "Flutter 의 위젯 트리가 어떻게 화면을 그리는지 큰 그림으로 설명해주세요.",
        "BuildContext 가 무엇이고 왜 필요한지 설명해주세요.",
        "Flutter 의 setState 가 호출되면 내부적으로 어떤 일이 일어나는지 설명해주세요.",
        "Riverpod(또는 Provider)이 어떤 문제를 해결해주는지 설명해주세요.",
        "Hot Reload 와 Hot Restart 의 차이를 설명해주세요.",
    ],
}


def _mock_seed(req: SeedRequest) -> SeedResponse:
    candidates: list[tuple[str, str]] = []
    for label in req.domains:
        templates = _MOCK_SEED_TEMPLATES.get(label)
        if templates:
            for t in templates:
                candidates.append((t, label))
        else:
            candidates.append(
                (f"{label}의 핵심 개념 중 자신 있는 부분 하나를 골라 설명해주세요.", label)
            )
    for kw in req.keywords:
        candidates.append(
            (f"{kw}에 대해 알고 계신 내용을 자유롭게 설명해주세요.", kw)
        )
    if not candidates:
        return SeedResponse(
            question="자기소개와 함께 가장 자신 있는 기술 영역을 한 가지 말씀해주세요.",
            domain_label="일반",
        )
    excluded = set(req.exclude_questions or [])
    fresh = [c for c in candidates if c[0] not in excluded]
    pool = fresh if fresh else candidates
    question, label = random.choice(pool)
    return SeedResponse(question=question, domain_label=label)


async def human_review_node(state: GraphState) -> dict:
    """No-op pass-through node.

    interrupt_before causes the graph to pause *before* this node executes.
    When the BE resumes (after graph.aupdate_state + graph.ainvoke(None, config)),
    this node runs and increments feedback_count to guard against infinite feedback
    loops. iteration_count is reserved exclusively for evaluator retry counting.
    The actual routing decision happens in _route_after_feedback (workflow.py).
    """
    fb_in: UserFeedback | None = state.get("feedback")
    new_count = state.get("feedback_count", 0) + 1
    stage(
        "▶ [HUMAN_REVIEW] resume",
        feedback_action=fb_in.action if fb_in else None,
        feedback_count=new_count,
    )
    return {"feedback_count": new_count}


async def evaluator_node(state: GraphState) -> dict:
    stage(
        "▶ [EVALUATOR] start",
        candidates=len(state["follow_ups"].follow_ups) if state.get("follow_ups") else 0,
    )
    if get_settings().use_mock_llm:
        out_mock = _build_mock_eval()
        stage(
            "✓ [EVALUATOR] done",
            mode="mock",
            score=round(out_mock.score, 2),
            pass_threshold=out_mock.pass_threshold,
        )
        return {"evaluation": out_mock}
    fu_json = state["follow_ups"].model_dump_json(indent=2)
    user_prompt = f"""원래 질문: {state['question']}

지원자 답변:
{state['answer']}

생성된 꼬리 질문:
{fu_json}

위 꼬리 질문들의 품질을 평가하세요."""
    out = await structured_chat(
        EvaluationOutput,
        system=EVALUATOR_SYSTEM,
        user=user_prompt,
        temperature=0.0,
        reasoning_effort="low",
    )
    stage(
        "✓ [EVALUATOR] done",
        score=round(out.score, 2),
        pass_threshold=out.pass_threshold,
    )
    return {"evaluation": out}
