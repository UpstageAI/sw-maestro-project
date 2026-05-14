# ADR-0003: AI Gateway에 FastAPI + LangGraph 채택

- **상태**: Accepted
- **날짜**: 2026-05-01

## Context

일기 생성은 다단계 파이프라인 (입력 검증 → 사진 분석 → 컨텍스트 빌드 → 생성 → 안전성 검증)이며, 각 단계에서:
- 분기/루프가 발생할 수 있음 (안전성 위반 시 자동 재시도)
- 노드별 비용/토큰 측정이 필요
- 트레이싱이 중요 (어느 노드에서 실패했는지)

또한 AI 호출은 응답 시간이 길고 외부 의존성이 크므로 **Next.js BFF에서 분리**하는 편이 좋음 (배포 주기 분리, 장애 격리, 동시성 튜닝 독립).

## Decision

**별도의 Python AI Gateway 서비스를 두고, FastAPI + LangChain + LangGraph로 구성한다.**

- 프레임워크: FastAPI (async)
- LLM 추상화: LangChain (`langchain-openai`)
- 워크플로우: LangGraph (StateGraph)
- 의존성 관리: `uv`
- 트레이싱: LangSmith
- 배포: Fly.io 또는 Railway (확정은 트래픽 패턴 보고)

Next.js BFF가 HMAC 서명으로 Gateway를 호출.

## Rationale

- LangGraph는 분기/루프/조건부 엣지를 1급 지원 — 안전성 재시도 같은 흐름이 자연스럽게 표현됨
- LangChain의 retriever/memory 추상화가 RAG 확장에 그대로 활용 가능 (`DiaryRetriever`와 결합)
- LangSmith는 LangChain/LangGraph 1급 트레이싱 — 노드별 비용·지연 자동 수집
- AI Gateway 분리로 OpenAI rate limit 튜닝, 동시성 제어를 Vercel 함수와 독립적으로 관리
- FastAPI는 Pydantic 기반 검증 + async가 자연스럽고 LangGraph와 잘 어울림

## Alternatives Considered

### Next.js Route Handler에 직접 LLM 호출 통합
- 컴포넌트 1개로 단순
- **탈락 이유**: Vercel 함수의 30초 제한, 동시성 제어 한계. 다단계 파이프라인 트레이싱 어려움

### LangChain만 (LangGraph 없이)
- 단순 sequential chain으로 가능
- **탈락 이유**: 안전성 위반 시 자동 재시도 같은 분기를 chain만으로는 깔끔히 표현 못함. 추가로 RAG 확장 시 분기 더 복잡해짐

### TypeScript LangChain.js (Node 게이트웨이)
- 풀 스택을 TS로 통일
- **탈락 이유**: 사용자가 FastAPI + Python을 명시적으로 선택. LangGraph Python이 JS보다 더 성숙

### Vercel AI SDK
- Next.js 친화적
- **탈락 이유**: 다단계 워크플로우 + 트레이싱 측면에서 LangGraph 대체로 부족

## Consequences

### Pros
- 분기/루프가 그래프로 명시적
- 노드별 모델 swap 쉬움 (`generate_diary`만 4o로, 나머지는 4o-mini)
- LangSmith 트레이싱으로 운영 가시성 확보
- AI Gateway 독립 배포

### Cons
- 서비스 수 +1 (운영 부담)
- BFF↔Gateway HMAC 인증 구현 필요
- LangChain/LangGraph 학습 곡선
- Python + TS 두 런타임 유지

### 후속 조치
- BFF↔Gateway 인증: HMAC + IP allowlist (가능 시) — `apps/ai-gateway/app/auth.py`
- LangSmith 워크스페이스 + API 키 시크릿 관리
- 그래프 노드 추가 시 `add-langgraph-node` 스킬 정의 (반복 절차)

---

## 부록 — 후속 ADR로 갱신 (2026-05-03)

본 ADR의 다음 결정은 후속 ADR로 정합 갱신됨. 본문은 결정 변천사로 보존:

- **BFF↔Gateway 인증 (HMAC)** → ADR-0006(β: 사용자 JWT forward + RLS 자동) + ADR-0011(`X-Internal-Secret` 공유 비밀 헤더)으로 superseded. HMAC 방식은 채택되지 않음 (ADR-0006 Alternative α 탈락).
- **호스팅 미정 (Fly.io 또는 Railway, 트래픽 패턴 보고)** → ADR-0011(Railway us-east4)로 확정.
- **LangSmith 워크스페이스 시크릿 관리** → ADR-0012에서 정식 결정 (Developer Free, 카드 미등록).
- **`add-langgraph-node` 스킬 정의** → MVP 외, 미래 작업.
