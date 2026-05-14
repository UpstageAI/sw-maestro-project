# ADR-0006: 시스템 신뢰 경계와 BFF↔AI Gateway 인증 모델

- **상태**: Accepted
- **날짜**: 2026-05-03

## Context

ADR-0002(Supabase BaaS), ADR-0003(FastAPI + LangGraph) 위에서 **Gateway가 Supabase에 직접 접근할지**, **BFF↔Gateway 채널을 어떻게 인증할지**가 다른 모든 결정의 토대다.

## Decision

### B안 — Gateway가 Supabase에 직접 read 접근

- BFF(Next.js): 사용자 권한 검증 1차 게이트(세션·소유권 검증), 일일 한도 enforce.
- AI Gateway: 받은 요청으로 Supabase에서 직접 데이터 조회 (예: 최근 일기 N개, 미래 RAG 임베딩).

### β — 사용자 JWT forward + RLS 자동 적용

- BFF는 Supabase Auth `access_token`을 추출, 매 Gateway 요청마다 `Authorization: Bearer <token>` 헤더로 forward.
- Gateway는 동일 토큰을 PostgREST 호출에 사용 → **Supabase RLS가 Gateway 안에서도 자동 강제**.
- Gateway는 **`anon` 키만** 보유 (공개 가능 키). `service_role` 키는 Gateway에 두지 않는다.
- Gateway는 시작 시 Supabase JWKS를 캐시, 토큰 sub/aud/exp를 자체 검증.

## Rationale

1. **이중 가드.** BFF가 권한을 한 번, Gateway에서도 RLS가 자동 강제 → Gateway 코드 버그가 다른 사용자 데이터 노출로 이어지지 않음.
2. **service-role 분산 제거.** Gateway에 service-role 키를 두지 않으므로 키 노출 시 폭발 반경이 작음.
3. **MVP에 비용 거의 0.** 사용자 토큰 1h TTL은 일기 생성 P95 8초에 충분.
4. **AI 스택 정합성.** Gateway 안의 LangChain/LangGraph 자산이 retrieval 흐름에서도 활용됨. RAG 전환 시 임베딩 + pgvector 호출이 자연스럽게 LangGraph 노드 안에서 처리.

## Alternatives Considered

### A — Gateway는 stateless 변환기 (BFF가 모든 데이터 페이로드 동봉)
- Gateway 단순 + 테스트 쉬움.
- **탈락 이유**: RAG 전환 시 BFF가 OpenAI 임베딩 + pgvector 쿼리를 해야 함 → ADR-0003 정신과 어긋남, Python LangChain 자산 못 씀.

### α — HMAC 서명 + service-role 키
- 멘탈 모델 단순.
- **탈락 이유**: service-role 분산. Gateway 버그 시 다른 사용자 데이터 노출 위험. RLS가 Gateway에 미치지 못함.

### γ — mTLS
- 가장 견고.
- **탈락 이유**: 인증서 관리 복잡, 사이드 프로젝트 운영 부담 ↑.

## Consequences

### Pros
- Gateway 코드 버그가 RLS로 막힘 (이중 가드).
- 키 분산 최소화 (anon만).
- LangChain/LangGraph 자산 활용.

### Cons
- 사용자 JWT를 내부 서비스에 forward — HTTPS 필수, Gateway 자체 신뢰성 ↑ 필요.
- 백그라운드 작업(임베딩 백필 등)은 사용자 컨텍스트 없으므로 미래에 service-role 트랙이 별도로 필요해질 수 있음 → RAG 도입 시 별도 ADR.

### 후속 조치
- Gateway 시작 시 Supabase JWKS 캐시 검증 로직.
- BFF가 사용자 access_token을 헤더로 forward하는 미들웨어/유틸.
- Gateway 외부 노출 금지: BFF만 호출자. 호스팅 결정 시 IP allowlist 또는 동등한 보호.
