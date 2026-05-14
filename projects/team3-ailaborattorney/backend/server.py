"""
AI 노무사 LangGraph Agent 서버
================================

docs/labor_law_rag.ipynb 의 qa_graph / analyze_graph 를 FastAPI 로 래핑한
프로덕션 진입점입니다. Next.js 클라이언트의 LANGGRAPH_URL 로 사용합니다.

빠른 실행:
    cd backend
    unzip -o chroma_db.zip -d .                   # ./chroma_db/ 생성
    python -m venv .venv && source .venv/bin/activate
    pip install -r requirements.txt
    export UPSTAGE_API_KEY=up_xxxxx
    uvicorn server:app --port 8000 --reload

확인:
    curl -s http://localhost:8000/ | jq
    curl -s -X POST http://localhost:8000/qa \
      -H 'content-type: application/json' \
      -d '{"question":"해고 예고는 며칠 전에 해야 하나요?"}' | jq
"""
from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, TypedDict

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from langgraph.graph import StateGraph, END
from langchain_upstage import ChatUpstage, UpstageEmbeddings
from langchain_chroma import Chroma


# ---------------------------------------------------------------------------
# 환경 변수 / 외부 리소스
# ---------------------------------------------------------------------------

load_dotenv()

UPSTAGE_API_KEY = os.environ.get("UPSTAGE_API_KEY", "").strip()
if not UPSTAGE_API_KEY:
    raise RuntimeError(
        "UPSTAGE_API_KEY 환경변수가 설정되지 않았습니다. "
        ".env 파일에 추가하거나 export 하세요."
    )

CHROMA_DIR = os.environ.get("CHROMA_DIR", "./chroma_db")
COLLECTION_NAME = os.environ.get("COLLECTION_NAME", "labor_law")
UPSTAGE_MODEL = os.environ.get("UPSTAGE_MODEL", "solar-pro")

if not os.path.isdir(CHROMA_DIR):
    raise RuntimeError(
        f"CHROMA_DIR='{CHROMA_DIR}' 디렉토리를 찾지 못했습니다. "
        "backend/chroma_db.zip 을 먼저 'unzip -o chroma_db.zip' 으로 풀어주세요."
    )

embeddings = UpstageEmbeddings(model="solar-embedding-1-large-query")
db = Chroma(
    persist_directory=CHROMA_DIR,
    collection_name=COLLECTION_NAME,
    embedding_function=embeddings,
)
llm = ChatUpstage(model=UPSTAGE_MODEL)


# ---------------------------------------------------------------------------
# QA Graph (노트북 cell 9 기반)
# ---------------------------------------------------------------------------

class QAState(TypedDict):
    question: str
    context: Optional[Dict[str, Any]]
    retrieved_docs: List[str]
    answer: str
    references: List[str]


def _format_contract_context(ctx: Optional[Dict[str, Any]]) -> str:
    """Next.js가 보낸 {parsed, rule, ai} 를 LLM 프롬프트용 텍스트로 직렬화."""
    if not ctx:
        return ""
    sections: List[str] = []
    for label, key in (
        ("계약서에서 추출된 데이터", "parsed"),
        ("룰 엔진 검사 결과", "rule"),
        ("이전 AI 분석 결과", "ai"),
    ):
        value = ctx.get(key)
        if value:
            sections.append(
                f"[{label}]\n{json.dumps(value, ensure_ascii=False, indent=2)}"
            )
    return "\n\n".join(sections)


def qa_retrieve(state: QAState) -> QAState:
    docs = db.similarity_search(state["question"], k=4)
    retrieved: List[str] = []
    refs: List[str] = []
    for d in docs:
        retrieved.append(d.page_content)
        article = d.metadata.get("article", "")
        title = d.metadata.get("title", "")
        ref = f"{article} {title}".strip()
        if ref:
            refs.append(ref)
    if not refs:
        refs = ["근로기준법"]
    return {
        **state,
        "retrieved_docs": retrieved,
        "references": list(dict.fromkeys(refs)),  # dedupe, keep order
    }


def qa_generate(state: QAState) -> QAState:
    law_context = "\n\n".join(state["retrieved_docs"])
    contract_context = _format_contract_context(state.get("context"))

    contract_block = (
        f"\n[사용자가 업로드한 근로계약서 정보]\n{contract_context}\n"
        if contract_context
        else "\n[사용자가 업로드한 근로계약서 정보]\n(업로드된 계약서 정보 없음)\n"
    )

    prompt = f"""당신은 AI 노무사입니다.

반드시 아래 규칙을 지키세요.
- 법적 판단·확정적 의견을 내지 말 것 ("위법입니다" 대신 "위반 가능성이 있습니다" 사용)
- 근거 조항(법률·시행령)을 가능한 한 명시할 것
- 추측·상상 금지. 데이터 없는 항목은 "정보 부족"으로 표시할 것
- 불확실하면 노동청 1350 또는 공인노무사 상담을 권유할 것
- 2025년 기준 최저임금: 10,030원/시간
- 한국어 존댓말 사용
- 사용자가 "내 계약서", "제 시급" 등 본인 계약 관련 질문을 하면 아래 [사용자가 업로드한 근로계약서 정보] 를 1순위 근거로 답변할 것
{contract_block}
[관련 법령]
{law_context}

[질문]
{state["question"]}
"""
    res = llm.invoke(prompt)
    answer = getattr(res, "content", str(res))
    return {**state, "answer": answer}


_qa_b = StateGraph(QAState)
_qa_b.add_node("retrieve", qa_retrieve)
_qa_b.add_node("generate", qa_generate)
_qa_b.set_entry_point("retrieve")
_qa_b.add_edge("retrieve", "generate")
_qa_b.add_edge("generate", END)
qa_graph = _qa_b.compile()


# ---------------------------------------------------------------------------
# Analyze Graph (노트북 cell 11 기반)
# ---------------------------------------------------------------------------

class AnalyzeState(TypedDict):
    contract_data: Dict[str, Any]
    rule_result: Dict[str, Any]
    user_info: Optional[Dict[str, Any]]
    summary: str
    items: List[Dict[str, Any]]


def analyze_node(state: AnalyzeState) -> AnalyzeState:
    rule = state.get("rule_result") or {}
    violations = rule.get("violations") or []

    if not violations:
        return {
            **state,
            "summary": "현재 입력 정보 기준 특이사항은 발견되지 않았습니다.",
            "items": [],
        }

    items: List[Dict[str, Any]] = []
    for v in violations:
        title = v.get("title", "")
        msg = v.get("message", "")
        law = v.get("lawReference") or v.get("law_reference") or ""
        prompt = f"""당신은 AI 노무사입니다.

다음 위반 가능성을 사용자가 이해하기 쉽게 설명하세요.

규칙:
- 법적 판단·확정적 의견 금지 ("위법입니다" X)
- "위반 가능성이 있습니다" 같은 표현 사용
- 근거 조항 명시
- 추측 금지. 정보 부족 시 "정보 부족"이라고 설명
- 불확실하면 노동청 1350 또는 공인노무사 상담 권유
- 2025년 최저임금: 10,030원/시간
- 한국어 존댓말 사용

제목: {title}
설명: {msg}
법 조항: {law}
"""
        res = llm.invoke(prompt)
        issue = getattr(res, "content", str(res))
        items.append({
            "title": title,
            "risk_level": v.get("risk", "medium"),
            "issue": issue,
            "law_reference": law,
            "action": "노동청 1350 또는 공인노무사 상담을 권장합니다.",
        })

    return {
        **state,
        "summary": f"{len(items)}건의 검토 항목이 발견되었습니다.",
        "items": items,
    }


_an_b = StateGraph(AnalyzeState)
_an_b.add_node("analyze", analyze_node)
_an_b.set_entry_point("analyze")
_an_b.add_edge("analyze", END)
analyze_graph = _an_b.compile()


# ---------------------------------------------------------------------------
# FastAPI
# ---------------------------------------------------------------------------

app = FastAPI(title="AI 노무사 LangGraph Agent", version="1.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class QaReq(BaseModel):
    question: str
    context: Optional[Dict[str, Any]] = None


class QaRes(BaseModel):
    answer: str
    references: List[str] = Field(default_factory=list)


class AnalyzeReq(BaseModel):
    contract_data: Dict[str, Any] = Field(default_factory=dict)
    rule_result: Dict[str, Any] = Field(default_factory=dict)
    user_info: Optional[Dict[str, Any]] = None


class AnalyzeItem(BaseModel):
    title: str
    risk_level: str
    issue: str
    law_reference: Optional[str] = None
    action: Optional[str] = None


class AnalyzeRes(BaseModel):
    summary: str
    items: List[AnalyzeItem]


@app.get("/")
def root() -> Dict[str, Any]:
    return {
        "name": "AI 노무사 LangGraph Agent",
        "version": app.version,
        "endpoints": ["/qa", "/analyze"],
        "model": UPSTAGE_MODEL,
        "collection": COLLECTION_NAME,
    }


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/qa", response_model=QaRes)
def qa_endpoint(req: QaReq) -> QaRes:
    if not req.question.strip():
        raise HTTPException(status_code=400, detail="question is required")
    out = qa_graph.invoke({
        "question": req.question,
        "context": req.context,
        "retrieved_docs": [],
        "answer": "",
        "references": [],
    })
    return QaRes(
        answer=out.get("answer", ""),
        references=out.get("references", []),
    )


@app.post("/analyze", response_model=AnalyzeRes)
def analyze_endpoint(req: AnalyzeReq) -> AnalyzeRes:
    out = analyze_graph.invoke({
        "contract_data": req.contract_data,
        "rule_result": req.rule_result,
        "user_info": req.user_info or {},
        "summary": "",
        "items": [],
    })
    return AnalyzeRes(
        summary=out.get("summary", ""),
        items=[AnalyzeItem(**it) for it in out.get("items", [])],
    )
