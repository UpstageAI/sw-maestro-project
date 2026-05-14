# CLAUDE.md

냥멍일기 — 반려동물 사진 + 키워드 → 1인칭 시점 일기를 자동 생성하는 아카이빙 서비스.

> **응답은 한국어로.** 사용자 글로벌 지침(~/.claude/CLAUDE.md) 우선.

## 바로 가기

- 기획: `docs/DESIGN.md` (§1 서비스 정의·범위만 — 아키텍처 재정의 중)
- 결정 기록: `docs/ADR/` (왜 그렇게 정했는지)
- 메모리 인덱스: `.claude/memory/INDEX.md`
- 도메인 규칙: `.claude/rules/` (프롬프트, RLS, 비용, 톤)

## 핵심 스택 (요약)

Next.js (Vercel) ↔ Supabase (Auth/PG/Storage) ↔ FastAPI + LangGraph ↔ OpenAI GPT-4o-mini (Vision).
상세 근거는 `docs/ADR/` 참조.

## 작업 시 지키는 4가지

1. **스코프 외 변경 금지** — 인접 리팩터링·추측성 추상화 X. 예외: ADR에 명시된 인터페이스.
2. **검증 가능한 목표 선언** — 작업 시작 전 성공 기준 1줄 ("X 호출 → Y 응답 확인").
3. **PII/보안** — 사진은 서명 URL, API 키는 게이트웨이만 보유, 로깅에 원문 금지.
4. **비용 가드레일** — 사용자당 일 8회(신규 5 + 재생성 3) 서버 enforcement.

## 디렉토리 (예정)

```
apps/{web,ai-gateway}/   packages/shared-types/   supabase/{migrations,seed.sql}   docs/   .claude/
```

각 `apps/*/CLAUDE.md`는 그 디렉토리 작업 시 자동 로드 (구현 시 채움).

## 명령어

### 모노레포 / 의존성
```bash
pnpm install                       # 모든 workspace 의존성 (root에서)
pnpm --filter web dev              # Next.js dev 서버
pnpm --filter web build            # Next.js prod build (TS check 포함)
```

### web (Next.js)

`apps/web/.env.local`은 Next.js가 cwd 기준으로 자동 로드 (root `.env.local`과 분리, 변경 시 둘 다 sync). 필요 env: `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY`, `INTERNAL_SHARED_SECRET`, `AI_GATEWAY_URL` (dev: `http://127.0.0.1:8765`, prod: Railway URL은 Vercel에 등록).

### ai-gateway (Python + uv)
```bash
uv sync --directory apps/ai-gateway                                        # venv + deps
uv run --directory apps/ai-gateway python -c "from ai_gateway.main import app"  # import sanity
uv run --directory apps/ai-gateway uvicorn ai_gateway.main:app --host 127.0.0.1 --port 8765  # dev 서버
```

`.env.local`은 root에 두고 ai-gateway가 자동 로드 (config.py가 monorepo root까지 탐색). 필요 env: `INTERNAL_SHARED_SECRET`, `OPENAI_API_KEY`, `SUPABASE_URL`(또는 `NEXT_PUBLIC_SUPABASE_URL`), `LANGSMITH_API_KEY` (PAT 권장 — `feedback_langsmith_pat.md` 참조), `LANGSMITH_TRACING=true`.

### Supabase (CLI는 `pnpm dlx supabase`로 호출, root에서)
```bash
pnpm dlx supabase start                          # 로컬 stack (Docker Desktop 실행 중이어야)
pnpm dlx supabase stop --no-backup               # 정리
pnpm dlx supabase db reset --local               # 마이그레이션만으로 DB 재구성
pnpm dlx supabase db advisors --local            # 로컬 advisor (보안/성능 lint)
pnpm dlx supabase db pull <name> --local --yes   # iterate 후 마이그레이션 파일 생성
```

### dev 환경 push (env 자동 로드)
```bash
set -a; source .env.local; set +a; pnpm dlx supabase db push --yes -p "$SUPABASE_DB_PASSWORD"
set -a; source .env.local; set +a; pnpm dlx supabase db advisors --linked
```

### Postgres 직접 접근 (로컬 컨테이너 안)
```bash
docker exec -i supabase_db_cat-dog-diary psql -U postgres -d postgres <<'EOF'
<SQL>
EOF
```

### Windows 환경 주의
- Docker Desktop 실행 중이어야 `supabase start` 동작
- `supabase/config.toml`에서 `[analytics] enabled = false` (Windows에서 storage health check 통과 위해)
