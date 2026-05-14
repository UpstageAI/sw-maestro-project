from __future__ import annotations

import os
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    upstage_api_key: str
    upstage_base_url: str
    upstage_chat_model: str
    upstage_document_embedding_model: str
    upstage_query_embedding_model: str
    chroma_path: str
    chroma_collection_name: str
    per_keyword_limit: int
    top_k: int
    request_timeout_seconds: int
    email_from: str
    email_to_default: str
    email_outbox_path: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_use_tls: bool
    smtp_use_ssl: bool
    naver_client_id: str
    naver_client_secret: str

    @classmethod
    def from_env(cls, load_env: bool = True) -> "Settings":
        if load_env:
            try:
                from dotenv import load_dotenv

                load_dotenv()
            except ImportError:
                pass

        api_key = os.getenv("UPSTAGE_API_KEY", "").strip()
        document_model = os.getenv(
            "UPSTAGE_DOCUMENT_EMBEDDING_MODEL",
            "solar-embedding-1-large-passage",
        )
        query_model = os.getenv(
            "UPSTAGE_QUERY_EMBEDDING_MODEL",
            "solar-embedding-1-large-query",
        )
        collection_name = os.getenv("CHROMA_COLLECTION_NAME", "").strip()
        if not collection_name:
            model_slug = _slugify(document_model if api_key else "demo-embedding")
            collection_name = f"daily_news_articles_{model_slug}"

        return cls(
            upstage_api_key=api_key,
            upstage_base_url=os.getenv("UPSTAGE_BASE_URL", "https://api.upstage.ai/v1"),
            upstage_chat_model=os.getenv("UPSTAGE_CHAT_MODEL", "solar-pro3"),
            upstage_document_embedding_model=document_model,
            upstage_query_embedding_model=query_model,
            chroma_path=os.getenv("CHROMA_PATH", "data/chroma"),
            chroma_collection_name=collection_name,
            per_keyword_limit=int(os.getenv("PER_KEYWORD_LIMIT", "3")),
            top_k=int(os.getenv("TOP_K", "5")),
            request_timeout_seconds=int(os.getenv("REQUEST_TIMEOUT_SECONDS", "10")),
            email_from=os.getenv("EMAIL_FROM", "").strip(),
            email_to_default=os.getenv("EMAIL_TO_DEFAULT", "").strip(),
            email_outbox_path=os.getenv("EMAIL_OUTBOX_PATH", "data/outbox").strip() or "data/outbox",
            smtp_host=os.getenv("SMTP_HOST", "").strip(),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_username=os.getenv("SMTP_USERNAME", "").strip(),
            smtp_password=os.getenv("SMTP_PASSWORD", ""),
            smtp_use_tls=_parse_bool(os.getenv("SMTP_USE_TLS", "true")),
            smtp_use_ssl=_parse_bool(os.getenv("SMTP_USE_SSL", "false")),
            naver_client_id=os.getenv("NAVER_CLIENT_ID", "").strip(),
            naver_client_secret=os.getenv("NAVER_CLIENT_SECRET", "").strip(),
        )

    def validate_mail_settings(self) -> None:
        if not self.email_from:
            raise ValueError("smtp 메일 전송에는 EMAIL_FROM 설정이 필요합니다.")
        if not self.smtp_host:
            raise ValueError("smtp 메일 전송에는 SMTP_HOST 설정이 필요합니다.")
        if not self.smtp_username:
            raise ValueError("smtp 메일 전송에는 SMTP_USERNAME 설정이 필요합니다.")
        if not self.smtp_password:
            raise ValueError("smtp 메일 전송에는 SMTP_PASSWORD 설정이 필요합니다.")
        if self.smtp_use_tls and self.smtp_use_ssl:
            raise ValueError("SMTP_USE_TLS와 SMTP_USE_SSL을 동시에 true로 설정할 수 없습니다.")

        if self.smtp_host.lower() == "smtp.gmail.com":
            self._validate_gmail_smtp_settings()

    def _validate_gmail_smtp_settings(self) -> None:
        if self.smtp_use_ssl:
            if self.smtp_port != 465:
                raise ValueError("Gmail SSL 사용 시 SMTP_PORT는 465를 권장합니다.")
            return

        if not self.smtp_use_tls:
            raise ValueError("Gmail SMTP는 SMTP_USE_TLS=true 또는 SMTP_USE_SSL=true 설정이 필요합니다.")
        if self.smtp_port != 587:
            raise ValueError("Gmail TLS 사용 시 SMTP_PORT는 587을 권장합니다.")


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", value).strip("_").lower()
    return slug or "default"


def _parse_bool(value: str) -> bool:
    return value.strip().lower() in {"1", "true", "yes", "on"}
