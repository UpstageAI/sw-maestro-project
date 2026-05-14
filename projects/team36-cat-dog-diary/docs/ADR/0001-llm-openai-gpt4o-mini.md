# ADR-0001: LLM으로 OpenAI GPT-4o-mini 채택

- **상태**: Accepted
- **날짜**: 2026-05-01

## Context

냥멍일기는 사진 + 키워드를 입력받아 한국어 일기를 생성한다. 다음 요구사항을 만족하는 LLM이 필요:

- **Vision 멀티모달** 지원 (사진 분석 → 일기 톤에 반영)
- **한국어** 자연스러움
- **LangChain/LangGraph 1급 통합** (선택된 워크플로우 프레임워크)
- 사용자당 일 8회 호출 가정 시 **합리적인 비용**
- 보호자 호칭과 페르소나 톤을 안정적으로 반영하는 **지시 따름 능력**

또한 사용자는 **로컬 모델 운영을 원하지 않음** (vLLM 등 자체 호스팅 배제).

## Decision

**OpenAI GPT-4o-mini를 메인 LLM으로 채택한다.** (`gpt-4o-mini`)

- 일기 생성, 사진 분석을 단일 모델로 통합 (Vision + structured outputs 1회 호출)
- 안전성 검증은 ADR-0005 부록의 deterministic check (호칭 substring + 길이)으로 처리. **OpenAI Moderation API는 MVP 미사용** — 미래 PII/abuse Reflection 또는 Validation Agent 단계에서 통합

## Rationale

- Vision 지원 (이미지 직접 입력 가능)
- 4o-mini는 입력 $0.15 / 출력 $0.60 per 1M tokens — 사용자당 일 8회 호출도 ~10원/일 수준
- LangChain `langchain-openai` 1급 통합, LangGraph 노드 어디서든 자연스럽게 사용
- 한국어 품질이 일기/감성 톤에는 충분

## Alternatives Considered

### Anthropic Claude (claude-sonnet-4-6 / haiku-4-5)
- 한국어 자연스러움과 캐릭터 톤 일관성은 더 우수했음
- **탈락 이유**: 사용자가 Claude Pro 구독 중이지만 **API는 별도 종량제 청구**. Pro 구독 비용을 또 지불하는 구조 부담. (참고: Anthropic ToS상 Pro 구독을 제3자 백엔드에서 재사용 불가)

### Google Gemini 2.5 Flash
- 비전 가성비는 가장 좋음
- **탈락 이유**: 한국어/감성 톤 안정성에서 OpenAI/Anthropic 대비 떨어짐. 단, 비용 압박 시 재고려 가능

### Provider 추상화 (다중 LLM)
- LangChain `init_chat_model`로 가능
- **탈락 이유**: MVP에 불필요한 복잡도. 단일 모델로 시작 후 필요 시 도입

### vLLM 셀프호스팅
- 사용자가 명시적으로 배제

## Consequences

### Pros
- 단일 모델로 시작해 운영 단순
- LangGraph 노드 모두 동일 모델로 비용 모델링 쉬움
- Vision + JSON mode 모두 안정 지원

### Cons
- 한국어 캐릭터 톤이 Claude만 못할 수 있음 — 프롬프트 튜닝으로 보완 필요
- OpenAI 단일 의존 — 장애 시 폴백 없음

### 후속 조치
- 프롬프트 평가 셋 구축 (`apps/ai-gateway/tests/prompt_eval/`) — 톤 회귀 감지
- LangSmith 트레이스로 응답 품질 지속 모니터링
- 6개월 후 GPT-4o(상위 모델)와 A/B 비교 검토
