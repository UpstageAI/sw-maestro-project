# ADR-0011: AI Gateway 호스팅과 외부 노출 차단 — Railway us-east4 + 공유 비밀 헤더

- **상태**: Accepted
- **날짜**: 2026-05-03

## Context

ADR-0003에서 AI Gateway = FastAPI + LangGraph로 결정했지만 호스팅 위치·외부 노출 차단·빌드 방식은 미정. 데이터 흐름은 ADR-0008 결정에 따라 BFF가 INSERT 책임이고 Gateway는 stateless LLM 모듈이라 해당 책임에 맞는 호스팅 선택 필요.

## Decision

| 축 | 선택 |
|---|---|
| 호스팅 | **Railway** |
| 리전 | **us-east4 (Virginia)** |
| 외부 노출 차단 | **공유 비밀 헤더 `X-Internal-Secret`** |
| 빌드 방식 | **Dockerfile** 명시 작성 |
| 모노레포 처리 | Railway Root Directory `apps/ai-gateway` |

## Rationale

### Railway 선택
- 비영리 사이드 + 트래픽 작음 → 매월 $5 포함 크레딧이 자동 갱신되어 사실상 무료.
- GitHub repo connect 한 번이면 push마다 자동 배포 — Fly.io의 `flyctl` CLI 흐름보다 setup 빠름.
- Trial은 신용카드 등록 불필요. Hobby 도달 시점에만 카드 필요.
- `apps/ai-gateway/` Root Directory 지정으로 monorepo 자연 처리.

### us-east4 선택
- Vercel server function default region(iad1=Virginia)과 같은 권역 → BFF↔Gateway hop ~10ms.
- OpenAI(US) 가까움 → Gateway↔OpenAI ~30ms.
- 직관적으로 한국에서 가까운 Singapore가 BFF↔Gateway 250ms로 오히려 더 느림 — 사용자 직접 latency가 dominant 아닌 구조 때문.

### 공유 비밀 헤더 선택
- 호스팅 무관 / setup 가장 단순 (BFF·Gateway 각각 환경변수 1개 + 미들웨어 1개).
- BFF만 시크릿 보유 → 브라우저 노출 0.
- ADR-0006 β의 사용자 JWT와 직교 → defense in depth.
- Railway private networking은 Vercel BFF가 외부에 있어 사실상 사용 불가.

### Dockerfile 선택
- LangChain/LangGraph 등 무거운 의존성에서 Railpack 자동 감지보다 안정.
- 미래 호스팅 변경(Cloud Run, Fly.io) 시 그대로 재사용 — vendor lock-in 회피.

## Endpoint 시그니처

```
POST /diary/generate
  Headers: Authorization: Bearer <user-jwt>, X-Internal-Secret: <shared>
  Body: {
    session_id,         # BFF가 UUID 발급 후 forward (LangSmith trace metadata 사용)
    seq: 1,
    pet_id,
    photo_signed_url,   # BFF가 사용자 JWT로 발급한 signed URL (TTL 1h)
    keywords,
    honorific,          # BFF가 pets에서 fetch
    species,            # BFF가 pets에서 fetch
    gender,             # 'male' | 'female' | 'unknown'
    recent_diaries      # BFF가 diaries에서 fetch (최근 3개 diary_text)
  }
  Response: SSE (`text/event-stream`) — 이벤트 union은 ADR-0008 부록(2026-05-05) 및 packages/shared-types/src/stream.ts

POST /diary/regenerate
  Headers: 동일
  Body: {
    session_id,
    seq,                  # BFF 결정 (다음 seq, 2~4)
    pet_id,
    photo_signed_url,
    keywords,
    honorific,
    species,
    gender,
    recent_diaries,
    previous_diary_text,
    feedback?,            # 1~500자 자유 텍스트, NULL 허용
    vision_description?   # 직전 generation의 vision 결과 echo. 있으면 graph가 vision LLM skip (ADR-0005 부록 2026-05-05)
  }
  Response: SSE (`text/event-stream`) — ADR-0008 부록(2026-05-05) 참조

GET /health
  Headers: 없음 (X-Internal-Secret 미들웨어 제외 — Railway healthcheck용)
  Response: 200 { status: "ok" }
```

> Gateway는 stateless — 응답에 LLM 산출물(`diary_text`/`short_caption`/`mood_tag`)만 포함. `session_id`/`generation_id`/`regenerate_remaining` 등 메타·카운터는 BFF가 INSERT 후 합성해서 클라이언트에 전달 (ADR-0008 응답 페이로드 참조).

`adopt`/`feed`/`quota`는 BFF가 supabase 직접 호출 — Gateway에 없음.

## 환경변수

### AI Gateway (Railway)
```
OPENAI_API_KEY            # OpenAI
SUPABASE_URL              # https://<project>.supabase.co (NEXT_PUBLIC_SUPABASE_URL alias 수용).
                          # JWKS URL은 derive: f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
INTERNAL_SHARED_SECRET    # BFF↔Gateway 공유 비밀
LANGSMITH_API_KEY         # ADR-0012 (PAT 권장 — Service Key는 trace 쓰기 권한 X)
LANGSMITH_TRACING=true    # 자동 trace 활성화 토글 (ADR-0012)
LANGSMITH_PROJECT         # 환경별 trace 분리 (예: cat-dog-diary-prod)
PORT                      # Railway 자동 inject
```

> 본문은 SUPABASE_ANON_KEY / SUPABASE_JWKS_URL을 별도 env로 명시했으나 실제 미사용.
> ANON_KEY는 ai-gateway 코드 경로에서 미참조(supabase-js는 BFF만), JWKS_URL은 SUPABASE_URL에서 derive.

### BFF (Vercel)
```
AI_GATEWAY_URL            # https://<service>.up.railway.app
INTERNAL_SHARED_SECRET    # 같은 값
SUPABASE_URL / SUPABASE_ANON_KEY  # supabase-js init용
```

## Alternatives Considered

- **Fly.io** — 도쿄 리전 매력적이나 신규 가입자에게 free allowance 없음(PAYG only) + 신용카드 가입 필수. 설정 편의성도 GUI 부족.
- **Cloud Run (GCP)** — 서울 리전 있지만 cold start 1~3s + VPC connector setup 복잡.
- **Render** — sleep 깨우기 ~30s가 P95 8s 목표 위협.
- **Vercel Functions** — Python 컨테이너 실행 어려움.
- **Railway private networking** — BFF 옮기지 않는 한 사용 불가 (Vercel이 외부).
- **Singapore region** — 사용자 직접 latency 직관적으로 가깝지만 Vercel iad1과 250ms 떨어져 종합적으로 더 느림.
- **Railpack 자동 빌드** — LangChain·LangGraph 무거운 의존성에서 안정성 떨어짐.

## Consequences

### Pros
- 매월 $5 포함 크레딧 → MVP 트래픽 사실상 무료.
- GUI + GitHub push 자동 → 첫 배포 5분 안.
- BFF↔Gateway hop 가장 짧음.
- Dockerfile 재사용으로 호스팅 변경 시 비용 작음.

### Cons
- 한국 사용자 직접 RTT 우위는 없음 (도쿄·서울 리전 X) — 단, BFF가 중간에 있어 영향 작음.
- Trial $5 만료 시 카드 등록 필요 — 메모리 룰에 따라 사전 알림.

### 후속 조치 (사용자 액션, 배포 시점)
- Railway 가입 (GitHub OAuth) → New Project → Deploy from GitHub repo → Root Directory `apps/ai-gateway` 지정.
- GitHub App 권한 허가.
- 환경변수 입력 (dashboard 또는 CLI).
- Hobby 도달 시 카드 등록.

### 후속 조치 (코드)
- `apps/ai-gateway/Dockerfile` 작성 (Python 3.12 + uvicorn + LangChain/LangGraph 의존성).
- BFF 측 미들웨어 — 모든 Gateway 호출 시 `X-Internal-Secret` 헤더 추가.
- Gateway 측 미들웨어 — `X-Internal-Secret` 검증 (단, `/health`는 제외).
- Gateway 측 JWKS 캐싱 + `Authorization: Bearer` JWT 검증 (sub/aud/exp).

---

## 부록 — endpoint 갱신: SSE + vision_description forward (2026-05-05)

본문 §endpoint signature의 `Response: { diary_text, short_caption, mood_tag }`는 outdated. 실제는 SSE StreamingResponse로 전환됨 — 채택 이유와 mediator 패턴은 ADR-0008 부록(2026-05-05).

`/diary/regenerate` body에 `vision_description?: string` 추가 — seq≥2일 때 BFF가 직전 row에서 SELECT → forward → graph의 `_route_vision` conditional edge가 vision LLM skip (ADR-0005 부록 2026-05-05). NULL fallback 시 BFF mediator가 새로 emit된 `vision_done` 값으로 echo.

`SUPABASE_ANON_KEY`는 ai-gateway 미사용 → env 표에서 제거. `SUPABASE_JWKS_URL`은 `SUPABASE_URL`에서 derive하므로 별도 env var 아님. `LANGSMITH_PROJECT`는 환경별 trace 분리(ADR-0012)를 위해 추가.
