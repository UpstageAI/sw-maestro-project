from __future__ import annotations

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from .agents.chatbot import chat
from .agents.graph import generate_report
from .stocks import StockNotFoundError, get_stock_snapshot, is_live_mode, is_mock_mode, list_stock_snapshots, resolve_data_mode
from .config import settings

app = FastAPI(title="주식 리포트 생성 서비스", version="0.1.0")


class ReportRequest(BaseModel):
    symbol: str


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    question: str
    symbol: str | None = None
    history: list[ChatMessage] = Field(default_factory=list)


@app.get("/health")
def health() -> dict:
    data_mode = resolve_data_mode()
    kis_auth_ready = False
    kis_auth_mode = "mock"
    if is_live_mode():
        from .kis_client import KISClient

        kis_client = KISClient()
        kis_auth_ready = kis_client.has_live_auth
        kis_auth_mode = kis_client.auth_mode
    return {
        "ok": True,
        "data_mode": data_mode,
        "kis_configured": bool(settings.kis_app_key and settings.kis_app_secret),
        "kis_mock": is_mock_mode(),
        "kis_base_url": settings.kis_base_url,
        "kis_auth_mode": kis_auth_mode,
        "kis_auth_ready": kis_auth_ready,
        "llm_ready": bool(settings.upstage_api_key),
        "llm_base_url": settings.upstage_api_base,
        "model": settings.llm_model,
    }


@app.post("/report")
def report(req: ReportRequest) -> dict:
    symbol = (req.symbol or "").strip()
    if not symbol:
        raise HTTPException(400, "symbol is required")
    try:
        return generate_report(symbol)
    except StockNotFoundError:
        raise HTTPException(404, "symbol not found")


@app.get("/api/stocks")
def stocks() -> dict:
    return {
        "data_mode": resolve_data_mode(),
        "stocks": list_stock_snapshots(),
    }


@app.get("/api/stocks/{symbol}")
def stock(symbol: str) -> dict:
    try:
        return {
            "data_mode": resolve_data_mode(),
            "stock": get_stock_snapshot(symbol, include_bars=True),
        }
    except StockNotFoundError:
        raise HTTPException(404, "symbol not found")


@app.post("/chat")
def chat_endpoint(req: ChatRequest) -> dict:
    question = (req.question or "").strip()
    if not question:
        raise HTTPException(400, "question is required")
    sym = req.symbol.strip() if req.symbol else None
    history = [
        {"role": msg.role, "content": msg.content}
        for msg in req.history
    ]
    return chat(question, sym or None, history)
