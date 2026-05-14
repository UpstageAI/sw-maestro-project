import json
from typing import Optional, Annotated
from operator import add

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, START, END
from typing_extensions import TypedDict

from mise.config import GOOGLE_API_KEY, MODEL_NAME, MAX_INPUT_LENGTH, API_TIMEOUT
from mise.models.scene_schema import (
    ExtractionResult, FillResult, PromptResult, SceneSchema, SceneElements, VerifyResult,
)
from mise.prompts.extraction_prompt import _prompt_template as extraction_template
from mise.prompts.prompt_generator import _prompt_template as prompt_template
from mise.prompts.focused_prompt_generator import _focused_prompt_template as focused_prompt_template
from mise.prompts.fill_prompt import _prompt_template as fill_template
from mise.prompts.verify_prompt import _prompt_template as verify_template


def _create_llm() -> ChatGoogleGenerativeAI:
    return ChatGoogleGenerativeAI(
        model=MODEL_NAME,
        google_api_key=GOOGLE_API_KEY,
        temperature=0.3,
        request_timeout=API_TIMEOUT,
    )


def _validate_input(novel_text: str, mode: str, prev_scene: Optional[dict]) -> None:
    if not novel_text or not novel_text.strip():
        raise ValueError("입력 텍스트가 비어있습니다.")
    if len(novel_text) > MAX_INPUT_LENGTH:
        raise ValueError(f"입력 텍스트가 {MAX_INPUT_LENGTH}자를 초과합니다. (현재: {len(novel_text)}자)")
    if mode not in ("generate", "regenerate"):
        raise ValueError(f"잘못된 mode: '{mode}'. 'generate' 또는 'regenerate'만 허용됩니다.")
    if mode == "regenerate" and prev_scene is None:
        raise ValueError("regenerate 모드에서는 prev_scene이 필요합니다.")


# ── LangGraph State ─────────────────────────────────────────────────
class PipelineState(TypedDict, total=False):
    novel_text: str
    mode: str
    prev_scene: Optional[dict]
    changed_values: dict[str, object]
    elements: SceneElements
    source_type: dict[str, str]
    style: str
    missing_fields: list[str]


# ── Node 1: 장면 추출 ───────────────────────────────────────────────
def extract_node(state: PipelineState) -> dict:
    if state["mode"] == "generate":
        llm = _create_llm()
        chain = extraction_template | llm.with_structured_output(ExtractionResult)
        result = chain.invoke({"novel_text": state["novel_text"]})
        return {
            "elements": result.elements,
            "source_type": result.source_type,
            "style": "cinematic",
        }
    else:
        prev = state["prev_scene"]
        return {
            "elements": SceneElements.model_validate(prev["elements"]),
            "source_type": prev.get("source_type", {}),
            "style": prev.get("prompt", {}).get("style", "cinematic"),
        }


# ── Node 2: 누락 검사 ───────────────────────────────────────────────
def check_missing_node(state: PipelineState) -> dict:
    missing = []
    for field_name in SceneElements.model_fields:
        if field_name == "objects":
            continue
        if getattr(state["elements"], field_name) == "":
            missing.append(field_name)
    return {"missing_fields": missing}


# ── Node 3: 보완 생성 ───────────────────────────────────────────────
def fill_node(state: PipelineState) -> dict:
    missing = state["missing_fields"]

    llm = _create_llm()
    elements_json = json.dumps(state["elements"].model_dump(), ensure_ascii=False)
    chain = fill_template | llm.with_structured_output(FillResult)
    result = chain.invoke({
        "novel_text": state["novel_text"],
        "elements_json": elements_json,
    })

    updated_source = dict(state["source_type"])
    for field in missing:
        updated_source[field] = "inferred"

    return {
        "elements": result.elements,
        "source_type": updated_source,
    }


# ── Node 4: 일관성 검증 ─────────────────────────────────────────────
def verify_node(state: PipelineState) -> dict:
    llm = _create_llm()
    elements_json = json.dumps(state["elements"].model_dump(), ensure_ascii=False)
    chain = verify_template | llm.with_structured_output(VerifyResult)
    result = chain.invoke({
        "novel_text": state["novel_text"],
        "elements_json": elements_json,
    })
    return {"elements": result.elements}


# ── Node 5: 프롬프트 생성 ───────────────────────────────────────────
def prompt_node(state: PipelineState) -> dict:
    llm = _create_llm()
    elements_json = json.dumps(state["elements"].model_dump(), ensure_ascii=False)
    changed_values = state.get("changed_values") or {}

    if changed_values:
        changed_json = json.dumps(changed_values, ensure_ascii=False)
        chain = focused_prompt_template | llm.with_structured_output(PromptResult)
        result = chain.invoke({
            "elements_json": elements_json,
            "changed_json": changed_json,
            "style": state["style"],
        })
    else:
        chain = prompt_template | llm.with_structured_output(PromptResult)
        result = chain.invoke({
            "elements_json": elements_json,
            "style": state["style"],
        })
    return {"prompt_result": result}


# ── Graph 빌드 ───────────────────────────────────────────────────────
class _SceneState(TypedDict, total=False):
    novel_text: str
    mode: str
    prev_scene: Optional[dict]
    changed_values: dict[str, object]
    elements: SceneElements
    source_type: dict[str, str]
    style: str
    missing_fields: list[str]
    prompt_result: PromptResult


def _route_after_check(state: PipelineState) -> str:
    """check_missing 이후 분기: 누락이 있으면 fill, 없으면 prompt로 바로 이동"""
    if state["missing_fields"]:
        return "fill"
    return "prompt"


def _build_graph() -> StateGraph:
    graph = StateGraph(_SceneState)

    # 노드 등록
    graph.add_node("extract", extract_node)
    graph.add_node("check_missing", check_missing_node)
    graph.add_node("fill", fill_node)
    graph.add_node("verify", verify_node)
    graph.add_node("prompt", prompt_node)

    # 엣지 연결
    graph.add_edge(START, "extract")
    graph.add_edge("extract", "check_missing")

    # 조건부 엣지: 누락 여부에 따라 경로 분기
    graph.add_conditional_edges(
        "check_missing",
        _route_after_check,
        {"fill": "fill", "prompt": "prompt"},
    )

    graph.add_edge("fill", "verify")
    graph.add_edge("verify", "prompt")
    graph.add_edge("prompt", END)

    return graph.compile()


_GRAPH = _build_graph()


# ── 공개 API ─────────────────────────────────────────────────────────
def extract_scene(
    novel_text: str,
    mode: str = "generate",
    prev_scene: Optional[dict] = None,
    changed_values: Optional[dict] = None,
) -> SceneSchema:
    _validate_input(novel_text, mode, prev_scene)

    result = _GRAPH.invoke({
        "novel_text": novel_text,
        "mode": mode,
        "prev_scene": prev_scene,
        "changed_values": changed_values or {},
    })

    return SceneSchema(
        elements=result["elements"],
        source_type=result["source_type"],
        prompt=result["prompt_result"],
    )
