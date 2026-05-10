# 팩폭머니 구현 플랜

## 개요

SPEC.md v3 기준, 코딩 에이전트가 자율 구현한다. 사람 개입 없음.

## 실행 구조

```
메인 스레드 (선행 작업)
├── .env.local 확인 + npm install + next.config.ts + lib/types.ts
│
├── 트랙 B (worktree) ──── 코더 → 셀프체크 → 리뷰어 → 커밋/재수정
│   에이전트 파이프라인 (먼저 머지)
│
├── 트랙 A (worktree) ──── 코더 → 셀프체크 → 리뷰어 → 커밋/재수정
│   DB + 시드 + API Routes (B 머지 후 머지)
│
└── 트랙 C (메인 스레드)
    프론트 연동 + 컴포넌트 + 정리 → 셀프체크 → 리뷰어 → 커밋
```

## 수정 금지 규약

트랙 A/B worktree에서 아래 파일은 **절대 수정 금지** (충돌 방지):
- `lib/types.ts` — 0단계에서 확정. 추가 타입은 각 모듈 내부에 로컬 정의
- `package.json` / `package-lock.json` — 0단계에서 모든 의존성 설치 완료
- `next.config.ts` — 0단계에서 수정 완료

---

## 0단계: 선행 작업 (메인 스레드)

트랙 A/B가 공통으로 필요로 하는 의존성과 타입을 먼저 세팅한다.

1. **환경 변수 확인**
   - `.env.local`에 `GEMINI_API_KEY` 설정 확인

2. **의존성 설치**
   ```bash
   npm install better-sqlite3 openai papaparse recharts
   npm install -D @types/better-sqlite3 @types/papaparse tsx
   ```
   recharts peer dep 에러 시 `--legacy-peer-deps` 추가.

3. **next.config.ts 수정**
   - `serverExternalPackages: ['better-sqlite3']` 추가

4. **lib/types.ts 확장**
   - `SimulationResult` 타입 추가
   - `ChatMessage`에 `simulation?`, `mission?`, `categoryBreakdown?` 필드 추가
   - 에이전트 전용 타입도 여기서 정의 (트랙 A/B에서 types.ts를 수정하지 않도록):
     - `AnalysisResult`, `RiskPattern` (Analyzer 입출력)
     - `CoachInput`, `CoachOutput` (Coach 입출력)

완료 후 커밋: `"chore: 의존성 설치 + 타입 확장"`

---

## 트랙 A: DB + 시드 + API Routes (worktree)

### 코더 작업 목록

| # | 파일 | 설명 |
|---|------|------|
| A1 | `lib/db.ts` | SQLite 싱글톤 연결 (`globalThis.__db` 캐싱), 4개 테이블 auto-create |
| A2 | `scripts/seed.ts` | 페르소나 A (`path.join(process.cwd(), 'sample-data', 'persona_A_transactions.csv')` 읽기) + 페르소나 B (SPEC 9절 분포표 기준 코드 생성) |
| A3 | `app/api/upload/route.ts` | CSV 업로드 → papaparse 파싱 → 헤더 검증 (불일치 시 400) → 음수 행 무시 → 빈 행 스킵 → 기존 transactions DELETE → INSERT |
| A4 | `app/api/chat/route.ts` | SPEC 4절 10단계 처리 흐름 전체 구현: ① 거래 데이터 로드 (없으면 Coach만 호출하여 업로드 유도) ② chat_history에 user 메시지 저장 (빈 message는 `"[CSV 업로드 후 자동 분석 요청]"`으로 대체) ③ Analyzer ④ Simulator ⑤ Coach ⑥ Coach 응답 파싱 ⑦ categoryBreakdown 조립 (초기 분석 모드 시) ⑧ mission INSERT ⑨ chat_history에 ai 메시지 저장 (텍스트만) ⑩ 응답 조립 |
| A5 | `app/api/transactions/route.ts` | 거래 내역 조회 (디버깅/확장용). `byCategory`는 SQL `GROUP BY category`로 독립 집계 (`SUM(amount)`) |
| A6 | `app/api/simulation/route.ts` | 자산 시뮬레이션 조회 (디버깅/확장용) |

### 셀프 체크

- [ ] `npx tsx scripts/seed.ts` 실행 성공
- [ ] DB 파일(`data/factpokmoney.db`) 생성 확인
- [ ] persona-a, persona-b 데이터가 DB에 들어갔는지 쿼리 확인
- [ ] upload route: 정상 CSV → 200, 헤더 불일치 CSV → 400 확인
- [ ] chat route: 거래 데이터 없는 userId → 업로드 유도 메시지 반환 확인
- [ ] chat route: chat_history 저장/조회 동작 확인
- [ ] transactions, simulation route: GET 200 응답 확인
- [ ] TypeScript 컴파일 에러 없음 (`npx tsc --noEmit` — 단, 트랙 B 에이전트 import는 stub이므로 에러 허용)
- [ ] API route import 경로 정상
- [ ] 모든 SQL이 parameterized query 사용 (injection 방지)

### 참고

- A4(chat route)는 트랙 B의 에이전트 함수를 import한다. 트랙 B가 아직 완료 전이면 **import만 작성하고 함수 시그니처는 SPEC 5절 + `lib/types.ts` 기준으로 맞춘다.** 머지 후 실제 연결된다.

---

## 트랙 B: 에이전트 파이프라인 (worktree)

### 코더 작업 목록

| # | 파일 | 설명 |
|---|------|------|
| B1 | `lib/agents/analyzer.ts` | 거래 데이터 → 카테고리 합산, topMerchants (total 기준 내림차순 상위 5개), period, 위험 패턴 탐지 (순수 JS). 타입은 `lib/types.ts`에서 import |
| B2 | `lib/agents/simulator.ts` | 현재 vs 개선 시나리오 자산 예측 (순수 JS) |
| B3 | `lib/agents/coach.ts` | Gemini Flash 호출 (OpenAI SDK + baseURL 오버라이드), SPEC 5.3절 messages 배열 구조 준수, `---MISSION_JSON---` 마커 파싱 (try-catch로 파싱 실패 시 mission=null), 429 시 exponential backoff (1s→2s→4s, 최대 3회) |

### 셀프 체크

- [ ] analyzer: 페르소나 A CSV 기준 — totalSpending, byCategory 상위 항목, topMerchants 5개, period, riskPatterns 타입/개수 확인
- [ ] simulator: 수동 계산 비교 (소득 280만, 지출 187만, 저축 500만, 수익률 3.5% → 1/3/5년 자산)
- [ ] coach: messages 배열 구조 확인 — system(프롬프트+분석+시뮬), history(role 매핑 ai→assistant), user 메시지
- [ ] coach: MISSION_JSON 마커 있는 응답 → mission 파싱 성공
- [ ] coach: MISSION_JSON 마커 없는 응답 → mission=null
- [ ] coach: 429 재시도 로직 존재 확인
- [ ] TypeScript 컴파일 에러 없음 (`npx tsc --noEmit`)
- [ ] 모든 함수의 입출력 타입이 `lib/types.ts` 정의와 일치

---

## 리뷰 프로세스 (트랙 A, B, C 공통)

### 흐름

```
코더 완료
  → 셀프 체크 통과
  → git add -A && git diff --cached 으로 diff 준비
  → code-reviewer 서브에이전트 호출 (diff 전달)
       ↓
  diff 기반 리뷰
       ↓
  Approved? ─── Yes → 커밋
             └── No  → 코더에게 피드백 전달
                         ↓
                    코더 수정 → 다시 리뷰어
```

### 리뷰 루프 제한

**최대 3회.** 3회 리뷰 후에도 미통과 시 현재 상태로 커밋하고, 미해결 이슈를 커밋 메시지에 기록한다.

### 리뷰어 검사 항목

1. **로직 에러** — off-by-one, null 접근, 잘못된 조건문
2. **보안** — SQL injection (parameterized query 사용 여부), 입력 검증
3. **SPEC 정합성** — 타입, API request/response, 에이전트 입출력이 SPEC과 일치하는지
4. **에러 핸들링** — 429 재시도, CSV 파싱 실패, DB 에러 시 적절한 응답
5. **코드 품질** — 불필요한 코드, 하드코딩된 매직 넘버, 미사용 import

### 커밋 컨벤션

- 트랙 B: `"feat: 에이전트 파이프라인 (analyzer/simulator/coach)"`
- 트랙 A: `"feat: DB 모듈 + 시드 + API Routes"`
- 트랙 C: `"feat: 프론트 연동 + 차트/미션 컴포넌트"`

---

## 트랙 C: 프론트 연동 + 컴포넌트 (메인 스레드)

트랙 B, A 순서로 머지 후 시작.

### 작업 목록

| # | 파일 | 설명 | 의존 |
|---|------|------|------|
| C1 | `lib/store/chat-store.ts` | `userId` 상태 추가 (`initialState`에서 `crypto.randomUUID()`), `sendMessage` 내부에서 `apiSendMessage({ message: text, userId: get().userId, attachment })` 호출로 변경 | — |
| C2 | `lib/api/chat.ts` | Mock import 제거 → `fetch('/api/upload')` + `fetch('/api/chat')` 실제 호출. `res.ok` 체크. CSV 첨부 시 텍스트 무시 | C1 |
| C3 | `lib/api/transactions.ts` | Mock import 제거 → `fetch('/api/transactions?userId=')` 호출. 시그니처: `getTransactions(userId: string)` | — |
| C4 | `components/chat/simulation-chart.tsx` | `'use client'`, Recharts LineChart, hex 색상 (`#a5a2b6`, `#5b21b6`), 200px | — |
| C5 | `components/chat/mission-card.tsx` | `'use client'`, 수락/거절 버튼, `useState`로 상태 관리 | — |
| C6 | `components/chat/category-breakdown.tsx` | `'use client'`, 순수 div 수평 바 차트, 최대 금액 기준 width 비례 | — |
| C7 | `components/chat/message-list.tsx` | GraphSlot import + `lastAiIndex` 로직 삭제 → SimulationChart, MissionCard, CategoryBreakdown import 추가 → 각 AI 메시지 하단에 조건부 렌더링 | C4,C5,C6 |
| C8 | `app/layout.tsx` | title `"팩폭머니 — AI 재정 코치"`, description, `lang="ko"`, `class="light"` 추가 (dark 모드 방지) | — |
| C9 | 삭제 | `lib/mock/messages.ts`, `lib/mock/transactions.ts`, `components/chat/graph-slot.tsx` | **C2, C3 완료 후** |

### 셀프 체크

- [ ] `GEMINI_API_KEY` 환경 변수 존재 확인
- [ ] mock import 잔존 없음 (`grep -r "lib/mock" lib/ components/` 결과 0건)
- [ ] graph-slot import 잔존 없음 (`grep -r "graph-slot" components/` 결과 0건)
- [ ] `npm run dev` 정상 기동
- [ ] CSV 업로드 → 첫 팩폭 메시지 + SimulationChart + CategoryBreakdown 표시
- [ ] 텍스트 메시지 전송 → 코칭 응답 + MissionCard 표시
- [ ] 미션 수락/거절 버튼 동작
- [ ] 타이핑 애니메이션 정상
- [ ] TypeScript 컴파일 에러 없음 (`npx tsc --noEmit`)
- [ ] 빌드 성공 (`npm run build`)

### 리뷰 후 커밋

트랙 A/B와 동일한 리뷰 프로세스 적용 (최대 3회).

---

## 머지 전략

```
1. 트랙 B worktree 완료 (리뷰 통과) → main에 머지 (먼저)
   └ B는 lib/agents/ 신규 파일만 추가 — 충돌 없음
2. 트랙 A worktree 완료 (리뷰 통과) → main에 머지
   └ A의 chat route가 B의 에이전트를 import → B가 이미 main에 있으므로 해소
3. 메인에서 트랙 C 시작 → 완료 → 리뷰 → 커밋
4. 최종 통합 테스트: npm run dev로 전체 플로우 확인
```

**머지 순서 B→A는 강제.** B가 먼저 끝나지 않아도, A가 먼저 끝나면 B 머지를 기다린다.

---

## 실패 시 대응

| 상황 | 대응 |
|------|------|
| npm install 실패 (recharts peer dep) | `--legacy-peer-deps` 플래그 추가 |
| better-sqlite3 빌드 실패 | `npm rebuild better-sqlite3` |
| Gemini API 429 | exponential backoff (SPEC 6절) |
| GEMINI_API_KEY 미설정 | 0단계에서 `.env.local` 확인. 없으면 중단 |
| CSV 파싱 실패 (인코딩/포맷) | 400 에러 + 사용자 친화적 메시지 반환 |
| 시드 스크립트 실패 | 에러 로그 확인 후 수정. DB 파일 삭제 후 재실행 |
| worktree 머지 충돌 | `lib/types.ts` — 0단계에서 확장 완료이므로 가능성 낮음. 발생 시 수동 해결 |
| MISSION_JSON 파싱 실패 | try-catch로 mission=null 처리. LLM 출력 비결정성은 허용 |
| 리뷰 3회 미통과 | 현재 상태로 커밋, 미해결 이슈를 커밋 메시지에 기록 |
