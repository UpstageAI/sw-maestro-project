"""f0_parse — raw_input 자유 텍스트를 ServicePlanInput으로 구조화."""

from dotenv import load_dotenv
from langchain_core.prompts import ChatPromptTemplate
from langchain_upstage import ChatUpstage

from schemas import ServicePlanInput
from state import ProjectState

load_dotenv()

# with_structured_output(ServicePlanInput):
#   LLM 응답을 자유 텍스트가 아니라 ServicePlanInput Pydantic 모델로 바로 파싱해서 반환.
#   내부적으로 function calling / tool use를 사용해 JSON을 강제한다.
_llm = ChatUpstage(model="solar-pro3").with_structured_output(ServicePlanInput)

_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "당신은 IT 서비스 기획 분석가입니다. "
        "사용자가 입력한 자유 형식의 서비스 아이디어를 구조화된 기획안으로 파싱하세요. "
        "- raw_text는 원문 전체를 그대로 담으세요. "
        "- 입력에 명시되지 않은 정보는 None으로 두세요. "
        "- key_features는 3~5개로 정리하세요.",
    ),
    ("human", "{raw_input}"),
])


def f0_parse(state: ProjectState) -> dict:
    # state["raw_input"]: 사용자가 graph.invoke({"raw_input": "..."})로 넘긴 자유 텍스트
    chain = _PROMPT | _llm
    brief: ServicePlanInput = chain.invoke({"raw_input": state["raw_input"]})

    # LangGraph 노드는 반드시 dict를 반환해야 한다.
    # {"brief": brief} → LangGraph가 state["brief"] 필드를 이 값으로 덮어쓴다.
    return {"brief": brief}
