#!/usr/bin/env python3
"""하루 1회 뉴스 수집 및 브리핑 생성 CLI 스크립트.

cron 등록 예시 (매일 오전 8시):
  crontab -e
  0 8 * * * cd /path/to/daily-news-agent && .venv/bin/python run_daily.py \
    --interest "AI 산업 동향" --keywords "AI, 반도체, 스타트업" >> data/cron.log 2>&1
"""
from __future__ import annotations

import argparse
import logging
import sys

from daily_news_agent.ai_client import DemoAIClient, UpstageAIClient
from daily_news_agent.config import Settings
from daily_news_agent.mail_sender import SMTPMailClient, build_briefing_email_payload
from daily_news_agent.news_source import GoogleNewsRssClient
from daily_news_agent.vector_store import ChromaArticleStore
from daily_news_agent.workflow import DailyNewsWorkflow


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        stream=sys.stdout,
    )


def _create_workflow(settings: Settings) -> DailyNewsWorkflow:
    if settings.upstage_api_key:
        ai_client: DemoAIClient | UpstageAIClient = UpstageAIClient(
            api_key=settings.upstage_api_key,
            base_url=settings.upstage_base_url,
            chat_model=settings.upstage_chat_model,
            document_embedding_model=settings.upstage_document_embedding_model,
            query_embedding_model=settings.upstage_query_embedding_model,
        )
    else:
        ai_client = DemoAIClient()

    return DailyNewsWorkflow(
        news_source=GoogleNewsRssClient(timeout_seconds=settings.request_timeout_seconds),
        vector_store=ChromaArticleStore(
            path=settings.chroma_path,
            collection_name=settings.chroma_collection_name,
        ),
        ai_client=ai_client,
    )


def main() -> int:
    _setup_logging()
    logger = logging.getLogger(__name__)

    parser = argparse.ArgumentParser(
        description="하루 1회 뉴스 수집 및 브리핑 생성 스크립트",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
예시:
  python run_daily.py --interest "AI 산업 동향" --keywords "AI, 반도체, 스타트업"
  python run_daily.py --interest "AI 산업" --keywords "AI, 반도체" --recipient me@gmail.com
  python run_daily.py --interest "AI 산업" --keywords "AI" --no-mail
        """,
    )
    parser.add_argument("--interest", required=True, help="관심 분야 (예: 'AI 산업 동향')")
    parser.add_argument("--keywords", required=True, help="검색 키워드, 쉼표 구분 (예: 'AI, 반도체')")
    parser.add_argument(
        "--recipient",
        default="",
        help="브리핑 수신 이메일 (미지정 시 .env의 EMAIL_TO_DEFAULT 사용)",
    )
    parser.add_argument("--no-mail", action="store_true", help="이메일 전송 생략")
    args = parser.parse_args()

    settings = Settings.from_env()
    logger.info("=== Daily News Agent 자동 실행 시작 ===")
    logger.info("관심 분야: %s", args.interest)
    logger.info("검색 키워드: %s", args.keywords)

    try:
        workflow = _create_workflow(settings)

        logger.info("--- 뉴스 수집 및 저장 ---")
        collection_result = workflow.collect_and_store(
            interest=args.interest,
            keyword_text=args.keywords,
            per_keyword_limit=settings.per_keyword_limit,
            progress=logger.info,
        )
        logger.info(
            "수집 완료 — 정제: %d건, 신규 저장: %d건, 기존: %d건",
            collection_result.collected_count,
            collection_result.stored_count,
            collection_result.skipped_existing_count,
        )
        for error in collection_result.errors:
            logger.warning("수집 오류: %s", error)

        logger.info("--- 브리핑 생성 ---")
        briefing_result = workflow.generate_briefing(
            interest=collection_result.interest,
            keywords=collection_result.keywords,
            top_k=settings.top_k,
            fallback_articles=collection_result.collected_articles,
            collected_count=collection_result.collected_count,
            stored_count=collection_result.stored_count,
            skipped_existing_count=collection_result.skipped_existing_count,
            errors=collection_result.errors,
            progress=logger.info,
        )
        logger.info("브리핑 생성 완료 — 선별 기사: %d건", len(briefing_result.selected_articles))

        recipient = args.recipient.strip() or settings.email_to_default
        if args.no_mail:
            logger.info("--no-mail 옵션으로 이메일 전송을 건너뜁니다.")
        elif recipient:
            try:
                settings.validate_mail_settings()
                payload = build_briefing_email_payload(
                    briefing_result=briefing_result,
                    sender=settings.email_from,
                    recipient=recipient,
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
                logger.info("브리핑 메일 전송 완료 → %s", recipient)
            except Exception as exc:
                logger.warning("메일 전송 실패 (브리핑 결과는 정상 생성됨): %s", exc)
        else:
            logger.info("수신자 이메일 미설정 — 이메일 전송을 건너뜁니다.")

        logger.info("=== 자동 실행 완료 ===")
        return 0

    except Exception as exc:
        logger.error("실행 실패: %s", exc)
        return 1


if __name__ == "__main__":
    sys.exit(main())
