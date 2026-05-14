import os
from dotenv import load_dotenv
from typing import TypedDict

load_dotenv()
from langgraph.graph import StateGraph, START, END
from openai import OpenAI
import json
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

client = OpenAI(
    api_key=os.environ.get("UPSTAGE_API_KEY"),
    base_url="https://api.upstage.ai/v1"
)

class MeetingState(TypedDict):
    transcript: str
    summary: str
    decision: str
    agenda: str

def summary_node(state: MeetingState) -> MeetingState:
    response = client.chat.completions.create(
        model="solar-pro",
        messages=[
            {"role": "system", "content": "당신은 회의 전사문을 분석하는 전문가입니다."},
            {"role": "user", "content": f"다음 회의 전사문의 핵심 내용을 3가지 bullet point로 요약해주세요.\n\n{state['transcript']}"}
        ]
    )
    return {"summary": response.choices[0].message.content}

def decision_node(state: MeetingState) -> MeetingState:
    response = client.chat.completions.create(
        model="solar-pro",
        messages=[
            {"role": "system", "content": "당신은 회의 전사문을 분석하는 전문가입니다."},
            {"role": "user", "content": f"다음 회의 전사문에서 결정된 사항을 3가지 bullet point로 정리해주세요.\n\n{state['transcript']}"}
        ]
    )
    return {"decision": response.choices[0].message.content}

def agenda_node(state: MeetingState) -> MeetingState:
    response = client.chat.completions.create(
        model="solar-pro",
        messages=[
            {"role": "system", "content": "당신은 회의 전사문을 분석하는 전문가입니다."},
            {"role": "user", "content": f"다음 회의 전사문을 바탕으로 다음 회의 안건을 3가지 bullet point로 제안해주세요.\n\n{state['transcript']}"}
        ]
    )
    return {"agenda": response.choices[0].message.content}

builder = StateGraph(MeetingState)
builder.add_node("summary", summary_node)
builder.add_node("decision", decision_node)
builder.add_node("agenda", agenda_node)
builder.add_edge(START, "summary")
builder.add_edge("summary", "decision")
builder.add_edge("decision", "agenda")
builder.add_edge("agenda", END)
graph = builder.compile()

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class AnalyzeRequest(BaseModel):
    transcript: str

class AnalyzeResponse(BaseModel):
    summary: str
    decision: str
    agenda: str

def parse_bullets(text: str) -> list[str]:
    items = []
    for line in text.strip().splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(("- ", "• ", "* ", "· ")):
            items.append(line[2:].strip())
        elif len(line) > 2 and line[0].isdigit() and line[1] in ".)":
            items.append(line[2:].strip())
        else:
            items.append(line)
    return [item for item in items if item]

def sse(payload: dict) -> str:
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(req: AnalyzeRequest):
    result = graph.invoke({
        "transcript": req.transcript,
        "summary": "",
        "decision": "",
        "agenda": ""
    })
    return AnalyzeResponse(
        summary=result["summary"],
        decision=result["decision"],
        agenda=result["agenda"]
    )

@app.post("/analyze/stream")
def analyze_stream(req: AnalyzeRequest):
    def event_stream():
        state: MeetingState = {"transcript": req.transcript, "summary": "", "decision": "", "agenda": ""}

        yield sse({"node": "input", "status": "active"})
        yield sse({"node": "input", "status": "done"})

        yield sse({"node": "summary", "status": "active"})
        state.update(summary_node(state))
        yield sse({"node": "summary", "status": "done", "content": parse_bullets(state["summary"])})

        yield sse({"node": "decision", "status": "active"})
        state.update(decision_node(state))
        yield sse({"node": "decision", "status": "done", "content": parse_bullets(state["decision"])})

        yield sse({"node": "agenda", "status": "active"})
        state.update(agenda_node(state))
        yield sse({"node": "agenda", "status": "done", "content": parse_bullets(state["agenda"]), "complete": True})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
