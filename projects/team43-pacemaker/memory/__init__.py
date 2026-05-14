"""LangGraph 체크포인터 셋업. 담당: C(이유준).

in-memory로 시작 → 필요 시 SQLite 체크포인터로 교체.
"""
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()
