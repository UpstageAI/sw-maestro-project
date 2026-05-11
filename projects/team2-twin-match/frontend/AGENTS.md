<!-- BEGIN:nextjs-agent-rules -->
# This is NOT the Next.js you know

This version (16.x) has breaking changes — APIs, conventions, and file structure may all differ from your training data. Read the relevant guide in `node_modules/next/dist/docs/` before writing any code. Heed deprecation notices.
<!-- END:nextjs-agent-rules -->

---

# AGENTS.md (Frontend)

`llm-blind-date` 프로젝트의 프론트엔드 레포. 백엔드는 형제 디렉토리 `../llm-blind-date/` (FastAPI + Solar LLM). 두 레포가 동일한 협업 원칙을 따른다.

## 1. Think Before Coding
- 추측 금지. 모르면 묻거나 가정을 명시한다.
- 더 단순한 길이 있으면 먼저 제시한다.
- **백엔드 인터페이스를 임의로 가정하지 않는다.** `pnpm typegen` 으로 실제 OpenAPI에서 타입을 생성하고 그것을 신뢰한다.

## 2. Simplicity First
- 요청되지 않은 기능, 추상화, "유연성"은 추가하지 않는다.
- 단일 사용처 hook/컴포넌트는 페이지 안에 둔다. 두 곳 이상에서 쓰일 때 옮긴다.
- 불가능한 시나리오를 위한 에러 처리는 넣지 않는다 (입력은 백엔드에서 한 번 더 검증됨).

## 3. Surgical Changes
- 요청한 영역만 손댄다. 인접 코드 "개선"은 별도 PR.
- 기존 스타일/네이밍을 따른다.
- 우리 변경으로 떠버린 import/변수만 정리한다.

## 4. Goal-Driven Execution
- "동작한다"가 아니라 검증 가능한 기준을 정의한다.
  - "Agent 생성 폼" → "valid input 시 POST /api/agents 호출되고, 4xx 응답의 detail이 사용자에게 보인다"
- 멀티스텝 작업은 1줄 단위 plan을 먼저 적는다.

---

## 아키텍처

```
src/
├── app/                  # Next.js App Router (페이지/레이아웃)
├── lib/
│   ├── api/
│   │   ├── client.ts     # 단일 API 진입점 (openapi-fetch + unwrap)
│   │   └── types.ts      # 자동 생성 (pnpm typegen) — 손대지 말 것
│   └── queries/
│       ├── QueryProvider.tsx
│       └── *.ts          # 도메인별 useQuery / useMutation 훅
└── components/           # 재사용 UI
```

### 3-layer 대응 (백엔드와 짝)
| 백엔드 | 프론트엔드 | 책임 |
|---|---|---|
| Router | `app/**/page.tsx` | 사용자 입력 받고 결과 렌더 |
| Service | `lib/queries/*.ts` (TanStack Query 훅) | 캐시·폴링·재시도 정책 |
| Repository | `lib/api/client.ts` | 단일 fetch 진입점 + 에러 변환 |

### 절대 규칙
1. **단일 API 진입점**: 모든 백엔드 호출은 `lib/api/client.ts` 의 `api` 인스턴스를 거친다. 컴포넌트에서 `fetch` / `axios` 직접 호출 금지.
2. **타입 자동 생성**: `lib/api/types.ts` 는 손으로 고치지 마라. 백엔드 인터페이스가 바뀌면 `pnpm typegen`.
3. **에러 포맷**: 백엔드는 모든 에러를 `{detail: string}` 으로 보낸다. UI는 `ApiError.detail` 만 보면 된다.
4. **폴링은 TanStack Query**: `/api/jobs/{id}` 같은 폴링은 `refetchInterval`. `setInterval` 직접 사용 금지.
5. **CORS**: 백엔드는 `http://localhost:3000` 만 허용한다. 다른 포트로 띄우지 마라.

---

## 백엔드 명세 위치 (단일 진실)
- API 명세: `../llm-blind-date/docs/backend-specs/02-api-specification.md`
- 에러 코드 표: 같은 문서 §5
- DB 스키마: `../llm-blind-date/docs/backend-specs/03-database-schema.md`
- FR / 비즈니스 규칙: `../llm-blind-date/docs/backend-specs/01-functional-requirements.md`

코드로 옮길 때는 **먼저 `pnpm typegen` 으로 타입 동기화**, 명세는 "왜 이 필드가 필요한지" 맥락 참고용으로만.

---

## 실행

```bash
pnpm install
cp .env.example .env.local            # NEXT_PUBLIC_API_BASE_URL 확인
# (백엔드를 ../llm-blind-date 에서 ./start.sh 로 띄운 뒤)
pnpm typegen                           # OpenAPI → src/lib/api/types.ts
pnpm dev                               # http://localhost:3000
```
