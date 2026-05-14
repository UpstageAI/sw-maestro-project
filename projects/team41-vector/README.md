# 팩폭머니 (FactPokMoney)

**Fact + 팩폭(팩트로 폭행) + Money**

소비 데이터를 기반으로 직설적이고 단호한 톤으로 금융 코칭을 제공하는 AI 챗봇입니다.
두루뭉술한 위로 대신 **숫자와 사실 근거의 팩트 지적**으로 소비 습관 개선을 유도합니다.

> 기존 금융 앱: "이번 달 지출이 조금 많네요 😊"  
> 팩폭머니: "이번달에 카페에만 **47회, 총 186,000원** 쓰셨습니다. 바쁘신 건 알겠는데, 그 와중에 이 정도면 카페 주주 하셔도 되겠습니다."

---

## 데모 시나리오

샘플 데이터: `sample-data/transactions_2026_mar_jun.csv` (2026년 3~6월, 319건)

**흐름:** CSV 업로드 → 자동 분석 팩폭 → 사용자 변명 → 코치 반박 → 그래프 요청 → 비교 분석 → 미션 수락 → 미션 완료

### ① CSV 업로드
입력창 왼쪽 클립 아이콘 → `transactions_2026_mar_jun.csv` 첨부 → 전송. 업로드 즉시 자동 분석 시작.

### ② 자동 분석 응답 (예상)
```
4개월 데이터 분석했습니다. 총 지출이 3월 181만원에서 6월 212만원으로 4개월 만에 17% 증가했습니다.
쇼핑에만 3월 359,000원 → 5월 479,000원으로 33% 급증했고,
무신사와 29CM에서만 4개월 합산 1,109,000원 나갔습니다.
```
카테고리 차트 + 자산 시뮬레이션 차트 자동 표시.

### ③ 변명 → 반박
사용자: `그래도 요즘 많이 줄이고 있어요`

코치 (예상):
```
줄이고 계신다고 하셨는데, 5월 지출이 4월 대비 8% 증가했습니다.
카페는 스타벅스 강남R점 혼자서 24회, 139,200원이고요. 이 정도면 주주 하셔도 되겠습니다.
```

### ④ 일별 그래프
사용자: `5월 소비 그래프 보여줘`

→ `get_daily_spending("2026-05")` 툴 호출 → 꺾은선 그래프 렌더링 (카테고리별 선 + 총합 굵은 선)

### ⑤ 3개월 비교
사용자: `저번달이랑 그 전달이랑 비교해줘`

→ `get_spending_comparison()` 툴 호출 → 카테고리·가맹점별 월별 증감 분석

### ⑥ 미션 수락 → 완료
코치가 쇼핑 관련 미션 카드 제안 → **수락** 클릭

사용자: `미션 완료했어요` → `complete_mission()` 호출 → 카드 "🎉 완료!" + 폭죽 효과

---

## 빠른 시작

```bash
npm install
```

`.env.local` 파일을 프로젝트 루트에 생성:

```env
OPENAI_API_KEY=sk-proj-...
```

```bash
npm run dev
```

[http://localhost:3000](http://localhost:3000) 접속 후 CSV 파일을 업로드하면 자동으로 분석이 시작됩니다.

> **요구사항:** Node.js 20 이상, OpenAI API 키 (GPT-4o-mini 사용)

---

## 아키텍처

### 전체 흐름

```
[사용자] CSV 업로드 or 채팅 메시지
    ↓
POST /api/chat
    ↓
[Analyzer] 거래 데이터 분석 (카테고리별 합산, 위험 패턴 탐지, 상위 가맹점)
    ↓
[Simulator] 자산 시뮬레이션 (현재 패턴 vs 최적화 패턴, 1/3/5년 예측)
    ↓
[Coach - GPT-4o-mini] 팩트 기반 피드백 생성
    │   ↕ Tool Calling (필요 시 DB 조회)
    ↓
응답 (텍스트 + 미션 카드 + 차트 데이터)
    ↓
[프론트] 타이핑 애니메이션 → 렌더링
```

### 에이전트 파이프라인 (`lib/agents/`)

| 에이전트 | 역할 | 특징 |
|---------|------|------|
| `analyzer.ts` | 거래 분석 | 순수 JS. 카테고리별 합산, 위험 패턴(반복과소비·충동구매·미사용구독·라이프스타일 상승) 탐지 |
| `simulator.ts` | 자산 시뮬레이션 | 순수 JS. 현재 저축률 vs 절약 후 저축률로 복리 계산 (1/3/5년) |
| `coach.ts` | AI 코치 (LLM) | GPT-4o-mini. Tool Calling 루프. 시스템 프롬프트에 분석·시뮬레이션 데이터 주입 |

### Tool Calling

Coach가 필요에 따라 스스로 호출하는 DB 조회 도구들:

| 툴 | 설명 |
|----|------|
| `get_mission_history` | 미션 이력 조회 (상태 필터 가능) |
| `complete_mission` | 최근 수락된 미션 완료 처리 |
| `update_user_profile` | 월수입/현재저축액 업데이트 → 시뮬레이션 재계산 트리거 |
| `get_spending_comparison` | 이번달·저번달·저저번달 카테고리별 + 가맹점별 지출 비교 |
| `get_daily_spending` | 특정 달 일별 카테고리 지출 조회 → 꺾은선 그래프로 렌더링 |

---

## 주요 기능

### CSV 업로드 & 자동 분석
채팅 입력창의 클립 아이콘으로 CSV를 첨부하면 `/api/upload`에서 SQLite에 저장 후 자동 분석이 시작됩니다.

CSV 포맷: `date(YYYY-MM-DD), category, merchant, amount(원 단위)` — 헤더 1행 포함.

### 팩폭 코칭
- 전달 대비 증감율, 월수입 대비 카테고리 비율 계산
- 사용자 발언의 허점을 데이터로 즉시 반박
- 비꼬기 허용 ("이 정도면 카페 주주 하셔도 되겠습니다")

### 미션 카드
Coach가 위험 패턴을 발견하면 절약 미션을 제안합니다. 사용자는 수락/거절할 수 있고, 나중에 채팅으로 "미션 완료했어요"라고 하면 완료 처리 + 폭죽 효과가 터집니다.

### 차트
- **자산 시뮬레이션**: CSV 업로드 직후 1회 표시. 현재 패턴 vs 개선 패턴 1/3/5년 예측.
- **카테고리 지출**: CSV 업로드 직후 상위 5개 카테고리 바 차트.
- **일별 소비 꺾은선**: 사용자가 요청하면 Coach가 `get_daily_spending`을 호출해 채팅 아래에 렌더링.

### 타이핑 애니메이션
AI 응답은 완성된 텍스트를 백엔드에서 한 번에 받아서, 프론트에서 24~28ms/자 속도로 타이핑 효과를 재현합니다.

---

## API Routes

| 경로 | 메서드 | 설명 |
|------|--------|------|
| `/api/chat` | POST | 채팅 메시지 처리, 에이전트 파이프라인 실행 |
| `/api/upload` | POST | CSV 파싱 후 transactions 테이블에 INSERT |
| `/api/missions` | PATCH | 미션 상태 업데이트 (accepted / rejected / completed) |

---

## DB 스키마 (SQLite, `data/factpokmoney.db`)

```sql
users         -- id, name, monthly_income, current_savings
transactions  -- id, user_id, date, category, merchant, amount
missions      -- id, user_id, text, saving_amount, status(pending/accepted/rejected/completed), created_at
chat_history  -- id, user_id, role(user/ai), content, created_at
```

WAL 모드, FK 제약 활성화. `getDb()` 싱글톤 패턴으로 HMR 중복 연결 방지.

---

## 폴더 구조

```
app/
├── page.tsx                    메인 페이지
├── globals.css                 디자인 토큰 + 커스텀 클래스
├── layout.tsx
└── api/
    ├── chat/route.ts           채팅 핸들러 (에이전트 파이프라인)
    ├── upload/route.ts         CSV 업로드
    └── missions/route.ts       미션 상태 변경

components/chat/
├── chat-input.tsx              텍스트 입력 + CSV 첨부
├── message-list.tsx            메시지 목록 + 카드/차트 렌더링
├── message-bubble.tsx          AI(좌) / User(우) / System 버블
├── mission-card.tsx            미션 수락·거절·완료 카드
├── daily-chart.tsx             일별 소비 꺾은선 그래프 (Recharts)
├── simulation-chart.tsx        자산 시뮬레이션 라인 차트
├── category-breakdown.tsx      카테고리별 지출 바 차트
├── typing-indicator.tsx        응답 대기 점 3개 애니메이션
└── pending-orb.tsx             빈 상태 돼지저금통 SVG

lib/
├── types.ts                    전체 타입 정의
├── db.ts                       SQLite 싱글톤 + 스키마 초기화
├── agents/
│   ├── analyzer.ts             거래 분석 (순수 JS)
│   ├── simulator.ts            자산 시뮬레이션 (순수 JS)
│   └── coach.ts                GPT-4o-mini + Tool Calling
├── api/chat.ts                 프론트→백엔드 fetch 래퍼
├── store/chat-store.ts         Zustand 상태 (messages, typing 등)
└── hooks/use-typewriter.ts     타이핑 애니메이션 훅
```

---

## 기술 스택

| 영역 | 기술 |
|------|------|
| 프레임워크 | Next.js 16 (App Router) + TypeScript |
| 스타일 | Tailwind CSS v4 + shadcn/ui |
| 상태 관리 | Zustand (인메모리) |
| DB | SQLite (better-sqlite3, WAL 모드) |
| AI | OpenAI GPT-4o-mini (Function Calling) |
| 차트 | Recharts |
| 기타 | canvas-confetti (미션 완료 효과), react-markdown |

---

## 디자인 토큰

보라 단일 액센트 (`#5b21b6` → `#8b5cf6`). 마크다운 `**강조**`는 숫자·금액·기간·횟수에만 사용 → `.fact-accent` 클래스로 보라 그라데이션 텍스트 자동 렌더링.

CommonMark 한글 강조 버그(닫는 `**` 직후 한글): `message-bubble.tsx`의 `fixHangulEmphasis()`가 자동 처리.

---

## 참고 문서

- [`SPEC.md`](./SPEC.md) — 기능 명세
- [`UI_BRIEF.md`](./UI_BRIEF.md) — UI 작업 브리프
- [`sample-data/`](./sample-data/) — 테스트용 CSV 샘플
