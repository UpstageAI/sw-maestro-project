from __future__ import annotations

import math
from hashlib import sha256
from typing import Protocol

from daily_news_agent.models import NewsArticle
from daily_news_agent.summarizer import build_briefing_messages
from daily_news_agent.tagger import build_tagging_messages, parse_tags_response


class AIClient(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError

    def embed_query(self, text: str) -> list[float]:
        raise NotImplementedError

    def generate_briefing(self, interest: str, articles: list[NewsArticle]) -> str:
        raise NotImplementedError

    def generate_tags_batch(self, articles: list[NewsArticle]) -> list[list[str]]:
        raise NotImplementedError


class DemoAIClient:
    """API key 없이 로컬 출력물을 확인하기 위한 결정적 demo client."""

    def __init__(self, dimensions: int = 64) -> None:
        self.dimensions = dimensions

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)

    def generate_tags_batch(self, articles: list[NewsArticle]) -> list[list[str]]:
        return [article.keyword.split() for article in articles]

    def generate_briefing(self, interest: str, articles: list[NewsArticle]) -> str:
        if not articles:
            return "## 오늘의 핵심 요약\n- 관련 뉴스를 찾지 못했습니다.\n"

        article_lines = []
        for article in articles:
            summary = article.summary or "요약 정보가 제공되지 않았습니다."
            article_lines.append(
                f"- **{article.title}**\n"
                f"  - 핵심 내용: {summary}\n"
                f"  - 출처: {article.source}\n"
                f"  - [원문 보기]({article.link})"
            )

        return (
            "## 오늘의 핵심 요약\n"
            f"- `{interest}`와 관련해 총 {len(articles)}개의 주요 뉴스를 선별했습니다.\n"
            "- 현재는 Upstage API key 없이 실행되는 demo 요약입니다.\n\n"
            "## 주요 뉴스\n"
            + "\n".join(article_lines)
            + "\n\n## 확인할 만한 흐름\n"
            "- 실제 Upstage API key를 연결하면 기사 목록을 바탕으로 더 자연스러운 종합 브리핑을 생성합니다.\n"
        )

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dimensions
        tokens = [token for token in text.lower().split() if token]
        for token in tokens or [text.lower()]:
            digest = sha256(token.encode("utf-8")).digest()
            index = int.from_bytes(digest[:2], "big") % self.dimensions
            sign = 1.0 if digest[2] % 2 == 0 else -1.0
            vector[index] += sign

        norm = math.sqrt(sum(value * value for value in vector))
        if norm == 0:
            return vector
        return [value / norm for value in vector]


class UpstageAIClient:
    def __init__(
        self,
        api_key: str,
        base_url: str,
        chat_model: str,
        document_embedding_model: str,
        query_embedding_model: str,
    ) -> None:
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("openai 패키지가 설치되어 있지 않습니다.") from exc

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.chat_model = chat_model
        self.document_embedding_model = document_embedding_model
        self.query_embedding_model = query_embedding_model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        response = self.client.embeddings.create(
            model=self.document_embedding_model,
            input=texts,
        )
        return [item.embedding for item in response.data]

    def embed_query(self, text: str) -> list[float]:
        response = self.client.embeddings.create(
            model=self.query_embedding_model,
            input=[text],
        )
        return response.data[0].embedding

    def generate_tags_batch(self, articles: list[NewsArticle]) -> list[list[str]]:
        result = []
        for article in articles:
            messages = build_tagging_messages(article)
            resp = self.client.chat.completions.create(
                model=self.chat_model,
                messages=messages,
                temperature=0.1,
                max_tokens=60,
            )
            result.append(parse_tags_response(resp.choices[0].message.content or ""))
        return result

    def generate_briefing(self, interest: str, articles: list[NewsArticle]) -> str:
        if not articles:
            return "## 오늘의 핵심 요약\n- 관련 뉴스를 찾지 못했습니다.\n"

        messages = build_briefing_messages(interest, articles)
        response = self.client.chat.completions.create(
            model=self.chat_model,
            messages=messages,
            temperature=0.2,
            max_tokens=1400,
        )
        return response.choices[0].message.content or ""

