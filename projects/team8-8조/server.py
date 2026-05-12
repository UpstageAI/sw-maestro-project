from __future__ import annotations

import dataclasses
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from daily_news_agent.ai_client import DemoAIClient, UpstageAIClient
from daily_news_agent.config import Settings
from daily_news_agent.mail_sender import SMTPMailClient, build_briefing_email_payload
from daily_news_agent.models import BriefingResult, CollectionResult, NewsArticle
from daily_news_agent.naver_news import NaverNewsClient
from daily_news_agent.news_source import GoogleNewsRssClient, NewsRouter
from daily_news_agent.vector_store import ChromaArticleStore
from daily_news_agent.workflow import DailyNewsWorkflow

app = FastAPI(title="Daily News Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_settings() -> Settings:
    return Settings.from_env()


def create_workflow(settings: Settings) -> DailyNewsWorkflow:
    ai_client = (
        UpstageAIClient(
            api_key=settings.upstage_api_key,
            base_url=settings.upstage_base_url,
            chat_model=settings.upstage_chat_model,
            document_embedding_model=settings.upstage_document_embedding_model,
            query_embedding_model=settings.upstage_query_embedding_model,
        )
        if settings.upstage_api_key
        else DemoAIClient()
    )
    naver_client = (
        NaverNewsClient(
            client_id=settings.naver_client_id,
            client_secret=settings.naver_client_secret,
            timeout_seconds=settings.request_timeout_seconds,
        )
        if settings.naver_client_id and settings.naver_client_secret
        else None
    )
    news_router = NewsRouter(
        google_client=GoogleNewsRssClient(timeout_seconds=settings.request_timeout_seconds),
        naver_client=naver_client,
    )
    return DailyNewsWorkflow(
        news_router=news_router,
        vector_store=ChromaArticleStore(
            path=settings.chroma_path,
            collection_name=settings.chroma_collection_name,
        ),
        ai_client=ai_client,
    )


def article_to_dict(article: NewsArticle) -> dict[str, Any]:
    return {
        "title": article.title,
        "summary": article.summary,
        "link": article.link,
        "source": article.source,
        "published_at": article.published_at,
        "keyword": article.keyword,
        "tags": article.tags,
    }


def collection_result_to_dict(result: CollectionResult) -> dict[str, Any]:
    return {
        "interest": result.interest,
        "keywords": result.keywords,
        "collected_articles": [article_to_dict(a) for a in result.collected_articles],
        "collected_count": result.collected_count,
        "stored_count": result.stored_count,
        "skipped_existing_count": result.skipped_existing_count,
        "errors": result.errors,
    }


def briefing_result_to_dict(result: BriefingResult) -> dict[str, Any]:
    return {
        "interest": result.interest,
        "keywords": result.keywords,
        "collected_count": result.collected_count,
        "stored_count": result.stored_count,
        "skipped_existing_count": result.skipped_existing_count,
        "selected_articles": [article_to_dict(a) for a in result.selected_articles],
        "briefing_markdown": result.briefing_markdown,
        "errors": result.errors,
    }


# --- Request Models ---

class CollectRequest(BaseModel):
    interest: str
    keyword_text: str
    per_keyword_limit: int = 3


class ArticleIn(BaseModel):
    title: str
    summary: str
    link: str
    source: str
    published_at: str
    keyword: str
    tags: list[str] = []


class BriefingRequest(BaseModel):
    interest: str
    keywords: list[str]
    top_k: int = 5
    collected_articles: list[ArticleIn]
    collected_count: int
    stored_count: int
    skipped_existing_count: int = 0
    errors: list[str] = []


class SendEmailRequest(BaseModel):
    recipient: str
    briefing_result: dict[str, Any]


# --- Endpoints ---

@app.get("/api/settings")
def api_settings() -> dict[str, Any]:
    settings = get_settings()
    naver_enabled = bool(settings.naver_client_id and settings.naver_client_secret)
    return {
        "ai_mode": "Upstage" if settings.upstage_api_key else "Demo",
        "news_source": "Naver(한글) + Google" if naver_enabled else "Google only",
        "chroma_path": settings.chroma_path,
        "collection_name": settings.chroma_collection_name,
        "per_keyword_limit": settings.per_keyword_limit,
        "top_k": settings.top_k,
        "email_to_default": settings.email_to_default,
    }


@app.post("/api/collect")
def api_collect(req: CollectRequest) -> dict[str, Any]:
    settings = get_settings()
    try:
        workflow = create_workflow(settings)
        result = workflow.collect_and_store(
            interest=req.interest,
            keyword_text=req.keyword_text,
            per_keyword_limit=req.per_keyword_limit,
        )
        return collection_result_to_dict(result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/briefing")
def api_briefing(req: BriefingRequest) -> dict[str, Any]:
    settings = get_settings()
    try:
        articles = [
            NewsArticle(
                title=a.title,
                summary=a.summary,
                link=a.link,
                source=a.source,
                published_at=a.published_at,
                keyword=a.keyword,
                tags=a.tags,
            )
            for a in req.collected_articles
        ]
        workflow = create_workflow(settings)
        result = workflow.generate_briefing(
            interest=req.interest,
            keywords=req.keywords,
            top_k=req.top_k,
            fallback_articles=articles,
            collected_count=req.collected_count,
            stored_count=req.stored_count,
            skipped_existing_count=req.skipped_existing_count,
            errors=req.errors,
        )
        return briefing_result_to_dict(result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/api/send-email")
def api_send_email(req: SendEmailRequest) -> dict[str, bool]:
    settings = get_settings()
    try:
        settings.validate_mail_settings()
        selected = [
            NewsArticle(
                title=a["title"],
                summary=a["summary"],
                link=a["link"],
                source=a["source"],
                published_at=a["published_at"],
                keyword=a["keyword"],
                tags=a.get("tags", []),
            )
            for a in req.briefing_result.get("selected_articles", [])
        ]
        briefing = BriefingResult(
            interest=req.briefing_result["interest"],
            keywords=req.briefing_result["keywords"],
            collected_count=req.briefing_result["collected_count"],
            stored_count=req.briefing_result["stored_count"],
            skipped_existing_count=req.briefing_result.get("skipped_existing_count", 0),
            selected_articles=selected,
            briefing_markdown=req.briefing_result["briefing_markdown"],
            errors=req.briefing_result.get("errors", []),
        )
        payload = build_briefing_email_payload(
            briefing_result=briefing,
            sender=settings.email_from,
            recipient=req.recipient,
        )
        SMTPMailClient(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password,
            use_tls=settings.smtp_use_tls,
            use_ssl=settings.smtp_use_ssl,
            timeout_seconds=settings.request_timeout_seconds,
        ).send(payload)
        return {"success": True}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
