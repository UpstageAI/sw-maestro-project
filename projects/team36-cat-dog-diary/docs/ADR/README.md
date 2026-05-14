# Architecture Decision Records

중요한 기술 결정을 **결정 단위로** 기록. 결정의 맥락과 트레이드오프를 보존하기 위함.

## 인덱스

| # | 제목 | 상태 | 날짜 |
|---|---|---|---|
| [0001](0001-llm-openai-gpt4o-mini.md) | LLM으로 OpenAI GPT-4o-mini 채택 | Accepted | 2026-05-01 |
| [0002](0002-baas-supabase.md) | BaaS로 Supabase 채택 | Accepted | 2026-05-01 |
| [0003](0003-ai-gateway-fastapi-langgraph.md) | AI Gateway에 FastAPI + LangGraph 채택 | Accepted | 2026-05-01 |
| [0004](0004-pluggable-diary-retriever.md) | DiaryRetriever 인터페이스 추상화 | Deprecated (2026-05-03) | 2026-05-01 |
| [0005](0005-langgraph-workflow-topology.md) | LangGraph 워크플로우 토폴로지 — 가벼운 그래프 + Reflection 보류 | Accepted | 2026-05-03 |
| [0006](0006-trust-boundary-and-auth.md) | 시스템 신뢰 경계와 BFF↔AI Gateway 인증 모델 | Accepted | 2026-05-03 |
| [0007](0007-persistence-model.md) | 일기 영속화 모델 — 즉시 영속 + 두 테이블 분리 | Accepted | 2026-05-03 |
| [0008](0008-bff-api-surface-and-session-model.md) | BFF API 표면과 일기 세션 모델 | Accepted | 2026-05-03 |
| [0009](0009-photo-upload-flow.md) | 사진 업로드 흐름 — 클라이언트 직접 업로드 + Storage RLS | Accepted | 2026-05-03 |
| [0010](0010-data-model-and-rls.md) | 데이터 모델과 RLS 정책 — 5 테이블 + β 단일 패턴 | Accepted | 2026-05-03 |
| [0011](0011-ai-gateway-hosting.md) | AI Gateway 호스팅과 외부 노출 차단 — Railway us-east4 + 공유 비밀 헤더 | Accepted | 2026-05-03 |
| [0012](0012-observability.md) | 관측성 — LangSmith trace + 호스팅 기본 로그 | Accepted | 2026-05-03 |
| [0013](0013-ui-routing-and-design-system.md) | UI 라우팅 + 메인 구조 + 디자인 시스템 — 4 라우트 + 펫별 row + shadcn/ui | Accepted | 2026-05-03 |

## 작성 규칙

- 파일명: `NNNN-kebab-case-title.md` (4자리 zero-pad)
- **결정을 뒤집을 때**: 새 ADR 생성 (예: `0005-llm-claude-switch.md`), 기존 ADR 상태를 `Superseded by 0005`로 변경. 기존 파일 삭제 금지.
- **마이너 변경**: ADR 안 만들고 기존 ADR에 부록 추가.
- 길이는 **1페이지 (~150줄)** 이하로 유지.

## 템플릿

```markdown
# ADR-NNNN: 제목

- **상태**: Proposed / Accepted / Superseded by NNNN / Deprecated
- **날짜**: YYYY-MM-DD
- **결정자**: 이름 또는 역할

## Context (왜 결정이 필요한가)

## Decision (무엇을 결정했나 — 한 문장)

## Rationale (근거)

## Alternatives Considered (검토한 다른 옵션 + 탈락 이유)

## Consequences (Pros / Cons / 후속 조치)
```
