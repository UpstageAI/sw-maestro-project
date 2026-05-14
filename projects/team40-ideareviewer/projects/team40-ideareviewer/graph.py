"""LangGraph 노드 연결 및 빌드. nodes/* 모듈을 import해서 StateGraph를 컴파일."""

from langgraph.graph import END, START, StateGraph

from nodes.f0_parse import f0_parse
from nodes.f1_select import route_opinions, select_personas
from nodes.f2_opinion import generate_opinion, route_reviews
from nodes.f3_review import generate_review
from nodes.f4_supervisor import supervisor_finalize
from state import ProjectState


def _noop(state: ProjectState) -> dict:
    # 병렬 fan-out 결과가 모두 state에 반영된 뒤 다음 라우팅/종합 노드로 넘어가기 위한 join 포인트.
    # 실제 데이터 변환은 하지 않는다.
    return {}


builder = StateGraph(ProjectState)

# ── 노드 등록 ──────────────────────────────────────────────────────────────────
# add_node("이름", 함수): 이름은 Send()와 add_edge()에서 참조하는 키.
builder.add_node("f0_parse", f0_parse)
builder.add_node("select_personas", select_personas)
builder.add_node("generate_opinion", generate_opinion)
builder.add_node("collect_opinions", _noop)   # opinions fan-out join 포인트
builder.add_node("generate_review", generate_review)
builder.add_node("collect_reviews", _noop)  # reviews fan-out join 포인트
builder.add_node("supervisor_finalize", supervisor_finalize)

# ── 엣지 연결 ──────────────────────────────────────────────────────────────────
builder.add_edge(START, "f0_parse")
builder.add_edge("f0_parse", "select_personas")

# add_conditional_edges(source, router_fn, destinations):
#   router_fn이 list[Send]를 반환하면 각 Send를 독립 실행 단위로 병렬 파견.
#   destinations는 router_fn이 파견할 수 있는 노드 이름 목록 (LangGraph 타입 검증용).
builder.add_conditional_edges("select_personas", route_opinions, ["generate_opinion"])

# generate_opinion이 N번 병렬 실행된 뒤 모두 완료되면 collect_opinions 한 번 실행.
# LangGraph는 같은 노드로 향하는 모든 엣지가 완료될 때까지 다음 노드 실행을 기다린다.
builder.add_edge("generate_opinion", "collect_opinions")

# opinions가 모두 쌓인 상태에서 route_reviews 실행 → generate_review×N 병렬 파견.
builder.add_conditional_edges("collect_opinions", route_reviews, ["generate_review"])

# generate_review가 N번 병렬 실행 완료 → collect_reviews에서 fan-in 후 supervisor가 최종 리뷰 생성.
builder.add_edge("generate_review", "collect_reviews")
builder.add_edge("collect_reviews", "supervisor_finalize")
builder.add_edge("supervisor_finalize", END)

# compile(): 엣지·노드 연결을 검증하고 실행 가능한 Runnable 객체로 반환.
# 이후 graph.invoke({"raw_input": "..."}) 또는 graph.stream(...)으로 실행.
graph = builder.compile()
