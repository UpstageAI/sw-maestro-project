# 팩폭머니 — 기능 명세서 v3

> **이 문서는 코딩 에이전트가 자율 구현하기 위한 완전한 스펙이다.**
> UI_BRIEF.md는 프론트엔드 선행 개발 단계의 이전 지침이며, 충돌 시 본 문서가 우선한다.

## 1. 제품 요약

소비 데이터 기반 AI 재정 코칭 챗봇. 사용자의 거래 내역을 분석하고, 미래 자산을 시뮬레이션하며, 직설적인 "팩폭" 톤으로 행동 변화를 유도한다.

- **스택**: Next.js 16 (App Router) — 프론트 + API Routes 백엔드 일체형
- **LLM**: Gemini Flash (Google AI Studio 무료 티어, OpenAI 호환 API)
- **DB**: SQLite (better-sqlite3)
- **에이전트**: Analyzer → Simulator → Coach 순차 체이닝 (함수 파이프라인)

---

## 2. 사용자 시나리오

### 시나리오 A: 첫 진입 — 데이터 업로드
1. 사용자가 웹에 접속하면 빈 채팅 화면 + PendingOrb 표시
2. 파일 첨부 버튼으로 거래내역 CSV 업로드 후 전송 버튼 클릭
3. 프론트가 `POST /api/upload` 호출 → 성공 시 자동으로 `POST /api/chat { message: "", userId }` 호출
4. 서버가 빈 message를 감지하면 **초기 분석 모드**로 동작: 전체 소비 요약 + 첫 팩폭 메시지 생성
5. 미래 자산 시뮬레이션 차트가 메시지 하단에 표시

### 시나리오 B: 대화형 코칭
1. 사용자가 "나 이번 달 많이 쓴 거 맞아?" 같은 질문 입력
2. Analyzer가 거래 데이터에서 관련 수치 추출
3. Simulator가 현재 패턴 유지 시 자산 변화 계산
4. Coach가 수치 기반 팩폭 메시지 + 행동 미션 생성
5. 응답 타이핑 애니메이션으로 출력

### 시나리오 C: 미션 제시
1. 위험 소비 패턴 감지 시 Coach가 구체적 행동 미션 제시
2. 예: "오늘 배달앱 대신 편의점 도시락으로 바꾸세요. 절약분 12,000원."
3. 미션 수락/거절 버튼 표시
4. **수락/거절은 프론트 상태만 변경** (서버 저장 안 함, MVP 범위)

---

## 3. 세션 및 사용자 식별

- 세션 시작 시 클라이언트가 `crypto.randomUUID()`로 `userId`를 생성하여 Zustand store에 보관
- 이후 모든 API 호출에 해당 `userId`를 전달
- 시드 데이터(persona-a, persona-b)는 DB 초기화 시 미리 삽입됨
- 새 사용자는 `POST /api/upload` 시 users 테이블에 기본값으로 자동 INSERT
- 페이지 새로고침 시 userId는 새로 생성됨 (인메모리 전용, localStorage 미사용)

---

## 4. API 엔드포인트

모든 API Route 파일은 **App Router 규약**을 따른다: `app/api/{name}/route.ts`에 HTTP 메서드별 named export.

### POST /api/chat

**파일**: `app/api/chat/route.ts`

채팅 메시지 처리. 내부적으로 에이전트 파이프라인 실행.

**Request:**
```json
{
  "message": "이번 달 내가 얼마나 썼어?",
  "userId": "uuid-string"
}
```

- `message`가 빈 문자열(`""`)이면 **초기 분석 모드**: CSV 업로드 직후 전체 소비 요약 생성
- `message`가 있으면 **대화 모드**: 질문에 맞는 분석 + 코칭

**Response:**
```json
{
  "id": "uuid",
  "role": "ai",
  "content": "이번 달 총 지출 **187만 3천원**이에요. ...",
  "createdAt": 1715000000000,
  "simulation": {
    "currentPattern": {
      "monthlySaving": 127000,
      "projections": [
        { "year": 1, "assets": 6524000 },
        { "year": 3, "assets": 9572000 },
        { "year": 5, "assets": 12620000 }
      ]
    },
    "optimizedPattern": {
      "monthlySaving": 580000,
      "projections": [
        { "year": 1, "assets": 11960000 },
        { "year": 3, "assets": 25880000 },
        { "year": 5, "assets": 41800000 }
      ]
    }
  },
  "mission": {
    "id": "uuid",
    "text": "이번 주 배달앱 3회 이하로 줄이기",
    "savingAmount": 45000
  },
  "categoryBreakdown": {
    "배달": 342000,
    "카페": 118000,
    "팝업스토어": 235000,
    "화장품": 261000,
    "쇼핑": 285000
  }
}
```

- `simulation`: 초기 분석 모드에서만 포함. 일반 대화에서는 생략 가능 (Coach 판단)
- `mission`: Coach가 미션을 생성한 경우에만 포함
- `categoryBreakdown`: 초기 분석 모드에서만 포함 (상위 5개 카테고리)

**내부 처리 흐름 (초기 분석 모드 & 대화 모드 공통):**

매 요청마다 Analyzer → Simulator → Coach 파이프라인을 전체 실행한다. SQLite 로컬 쿼리는 충분히 빠르므로 캐싱 불필요.

1. `userId`로 DB에서 거래 데이터 로드. **거래 데이터가 없으면** (CSV 미업로드 상태) Coach에게 "사용자가 아직 CSV를 업로드하지 않았다"는 컨텍스트를 전달하고, Coach가 업로드를 유도하는 메시지를 생성하도록 한다. 이 경우 Analyzer/Simulator는 스킵하고 Coach만 호출.
2. user 메시지를 `chat_history` 테이블에 저장. 초기 분석 모드(빈 message)일 때는 content를 `"[CSV 업로드 후 자동 분석 요청]"`으로 대체하여 저장.
3. Analyzer: 거래 데이터 분석 결과 생성 (순수 JS, LLM 호출 없음)
4. Simulator: 자산 시뮬레이션 계산 (순수 JS, LLM 호출 없음)
5. Coach: 분석 + 시뮬 결과 + 최근 대화 히스토리를 프롬프트에 넣고 Gemini Flash 호출
6. Coach 응답 파싱 (content + mission 분리)
7. **categoryBreakdown 조립** (API route에서): 초기 분석 모드일 때만, Analyzer의 `byCategory`에서 total 기준 상위 5개 추출: `Object.fromEntries(Object.entries(byCategory).sort((a,b) => b[1].total - a[1].total).slice(0,5).map(([k,v]) => [k, v.total]))`
8. mission이 있으면 `crypto.randomUUID()`로 id 생성, missions 테이블에 INSERT
9. ai 메시지를 `chat_history` 테이블에 저장 (role: 'ai', content: 텍스트만. simulation/mission/categoryBreakdown은 저장하지 않음)
10. 응답 조립 후 반환

### POST /api/upload

**파일**: `app/api/upload/route.ts`

CSV 파일 업로드 및 파싱.

**Request:** multipart/form-data
- `file`: CSV 파일
- `userId`: string (form field)

**Response:**
```json
{
  "userId": "uuid-string",
  "transactionCount": 80,
  "summary": {
    "totalSpending": 1873000,
    "topCategory": "배달",
    "period": "2025-04-01 ~ 2025-04-30"
  }
}
```

**처리:**
1. CSV 파싱 (date, category, merchant, amount) — papaparse 사용
2. users 테이블에 해당 userId가 없으면 기본값으로 INSERT (`monthly_income: 2800000, current_savings: 5000000`)
3. 동일 userId의 기존 transactions를 DELETE 후 새 CSV 데이터로 교체 (재업로드 = 덮어쓰기)
4. 요약 통계 반환

**CSV 규칙:**
- UTF-8 only
- 첫 행은 반드시 헤더: `date,category,merchant,amount`
- 헤더 불일치 시 400 에러 반환: `{ "error": "CSV 헤더가 올바르지 않습니다. date,category,merchant,amount 형식이어야 합니다." }`
- amount는 양수만 허용 (음수 행은 무시)
- 빈 행은 스킵

### GET /api/transactions

**파일**: `app/api/transactions/route.ts`

거래 내역 조회. 디버깅/확장용 — MVP에서 프론트 호출은 없으나 API는 구현한다.

**Query params:**
- `userId` (필수): 사용자 ID
- `category` (optional): 카테고리 필터
- `from`, `to` (optional): 날짜 범위 (YYYY-MM-DD)

**Response:**
```json
{
  "transactions": [
    { "date": "2025-04-01", "category": "카페", "merchant": "스타벅스 강남R점", "amount": 5800 }
  ],
  "stats": {
    "total": 1873000,
    "byCategory": { "배달": 342000, "카페": 118000 }
  }
}
```

### GET /api/simulation

**파일**: `app/api/simulation/route.ts`

자산 시뮬레이션 결과. 디버깅/확장용 — MVP에서 프론트 호출은 없으나 API는 구현한다.

**Query params:**
- `userId` (필수): 사용자 ID
- `monthlyIncome` (optional): 월 소득 (기본값: users 테이블의 monthly_income)
- `currentSavings` (optional): 현재 저축액 (기본값: users 테이블의 current_savings)

**Response:** POST /api/chat의 `simulation` 필드와 동일한 구조.

---

## 5. 에이전트 파이프라인

### 5.1. Analyzer

거래 데이터를 읽고 소비 패턴을 분석한다. **순수 JS만 사용. LLM 호출 없음.**

**입력:** 거래 내역 배열 + 사용자 질문
**출력:** 분석 결과 JSON
**파일:** `lib/agents/analyzer.ts`

```typescript
type AnalysisResult = {
  totalSpending: number;
  byCategory: Record<string, { count: number; total: number }>;
  riskPatterns: RiskPattern[];
  topMerchants: { name: string; count: number; total: number }[]; // total 기준 내림차순, 상위 5개
  period: { from: string; to: string };
};

type RiskPattern = {
  type: 'recurring_excess' | 'impulse' | 'unused_subscription' | 'lifestyle_creep';
  description: string;
  amount: number;
  frequency: number;
};
```

**위험 패턴 탐지 규칙 (룰 기반):**
- `recurring_excess`: 배달 주 4회+, 카페 일 2회+
- `impulse`: 팝업스토어/쇼핑 단건 3만원+ 이면서 월 3회+
- `unused_subscription`: 구독료 카테고리의 모든 거래를 후보로 플래그 (1개월치 데이터에서는 "미사용" 여부 판단 불가이므로 전부 경고)
- `lifestyle_creep`: 데이터가 2개월 이상일 때만 탐지. 동일 카테고리에서 최근 월 지출이 이전 월 대비 30%+ 증가. **1개월 이하 데이터일 경우 이 규칙은 스킵.**

### 5.2. Simulator

현재 소비 패턴 유지 시 vs 개선 시 미래 자산을 계산한다. **순수 JS만 사용. LLM 호출 없음.**

**파일:** `lib/agents/simulator.ts`

**입력:** 월 소득, 월 지출, 현재 저축액, 연 수익률 (기본 3.5%)
**출력:** SimulationResult

```typescript
type SimulationResult = {
  currentPattern: {
    monthlySaving: number;
    projections: { year: number; assets: number }[];
  };
  optimizedPattern: {
    monthlySaving: number;
    projections: { year: number; assets: number }[];
  };
};
```

**계산식:**
- 월 저축 = 소득 - 지출
- n년 후 자산 = 현재저축 × (1+r)^n + 월저축 × ((1+r/12)^(12n) - 1) / (r/12)
- 최적화 시나리오: riskPatterns의 amount 합산을 절감액으로 보고 저축으로 전환
- years: [1, 3, 5]

### 5.3. Coach

분석 + 시뮬레이션 결과를 받아 팩폭 메시지와 행동 미션을 생성한다. **Gemini Flash 호출.**

**파일:** `lib/agents/coach.ts`

**입력:** AnalysisResult + SimulationResult + 사용자 메시지 + 대화 히스토리 (최근 10턴)
**출력:** 코칭 메시지 텍스트 + 행동 미션 (optional)

**시스템 프롬프트:**
```
너는 '팩폭머니'의 AI 재정 코치다.

규칙:
- 존댓말, 직설적, 돌려 말하지 않음
- 모든 피드백은 반드시 실제 거래 데이터 수치를 인용
- 핵심 기법: 구체적 수치 제시 / 사용자 발언과의 모순 짚기 / 평균 비교
- 3~5문장으로 제한
- 마크다운 **강조**는 숫자/금액/기간/횟수에만 사용
- 금지: 인종·성별·외모 비하, 자학 유도, 도덕적 비난, 투자 추천

아래 분석 데이터를 근거로 사용자에게 팩트 기반 피드백을 제공하라.

위험 패턴이 있으면 실행 가능한 행동 미션 1개를 제시하라:
- 구체적 행동 1개
- 절약 예상 금액 명시 (원 단위)
- 기한 명시 (이번 주, 오늘 등)

미션을 제시할 경우 반드시 아래 JSON을 응답 마지막에 포함:
---MISSION_JSON---
{"text": "미션 내용", "savingAmount": 45000}
---END_MISSION_JSON---
```

**Coach 응답 파싱:**
1. `---MISSION_JSON---` 마커가 있으면 해당 JSON을 파싱하여 `mission` 필드로 분리
2. 마커 이전 텍스트가 `content`
3. 마커가 없으면 `mission`은 null

**대화 히스토리:**
- DB의 `chat_history` 테이블에서 해당 userId의 최근 10턴(user+ai 쌍 = 20행)을 가져옴:
  `SELECT * FROM chat_history WHERE user_id = ? ORDER BY created_at DESC LIMIT 20` 후 `.reverse()`로 시간순 정렬
- DB의 `role: 'ai'`는 OpenAI API의 `role: 'assistant'`로 매핑

**Coach messages 배열 구조:**
```typescript
const messages = [
  {
    role: 'system' as const,
    content: systemPrompt
      + '\n\n[분석 데이터]\n' + JSON.stringify(analysisResult)
      + '\n\n[시뮬레이션]\n' + JSON.stringify(simulationResult),
  },
  ...chatHistory.map(h => ({
    role: (h.role === 'ai' ? 'assistant' : 'user') as 'assistant' | 'user',
    content: h.content,
  })),
  {
    role: 'user' as const,
    content: userMessage || '처음 방문한 사용자입니다. 전체 소비 요약을 해주세요.',
  },
];
```

---

## 6. LLM 설정 (Gemini Flash)

**SDK:** openai 패키지 사용 (baseURL 오버라이드)

```typescript
import OpenAI from 'openai';

const client = new OpenAI({
  apiKey: process.env.GEMINI_API_KEY,
  baseURL: 'https://generativelanguage.googleapis.com/v1beta/openai',
});

const response = await client.chat.completions.create({
  model: 'gemini-2.0-flash',
  messages: [...],
});
```

**Rate limit 대응 (무료 티어: 15 RPM, 1500 RPD):**
- LLM 호출은 Coach에서만 (Analyzer, Simulator는 순수 JS)
- 429 에러 시 exponential backoff: 1초 → 2초 → 4초, 최대 3회 재시도
- 3회 초과 시 사용자에게 에러 메시지 반환: "요청이 많아 잠시 후 다시 시도해주세요."

---

## 7. 데이터 모델 (SQLite)

### DB 설정

**파일:** `lib/db.ts`

- `better-sqlite3` 싱글톤 연결 (`globalThis.__db ??= new Database(...)` 패턴으로 hot reload 시 중복 커넥션 방지)
- `next.config.ts`에 `serverExternalPackages: ['better-sqlite3']` 추가 필수
- DB 파일 경로: `path.join(process.cwd(), 'data', 'factpokmoney.db')` (절대 경로로 해석)
- `data/` 디렉터리는 없으면 `fs.mkdirSync`로 자동 생성
- 테이블은 DB 연결 시 `CREATE TABLE IF NOT EXISTS`로 auto-create

### users
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | TEXT PK | crypto.randomUUID() 또는 persona-a 등 |
| name | TEXT | 표시명 (기본값: '사용자') |
| monthly_income | INTEGER | 월 소득 (원, 기본값: 2800000) |
| current_savings | INTEGER | 현재 저축액 (원, 기본값: 5000000) |
| created_at | INTEGER | epoch ms |

### transactions
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | INTEGER PK | autoincrement |
| user_id | TEXT FK | users.id |
| date | TEXT | YYYY-MM-DD |
| category | TEXT | 카페, 배달, 교통 등 |
| merchant | TEXT | 가맹점명 |
| amount | INTEGER | 금액 (원, 양수) |

### missions
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | TEXT PK | UUID |
| user_id | TEXT FK | users.id |
| text | TEXT | 미션 내용 |
| saving_amount | INTEGER | 절약 예상 금액 |
| created_at | INTEGER | epoch ms |

> missions 테이블의 status 컬럼은 MVP에서 제거. 수락/거절은 프론트 상태에서만 관리.

### chat_history
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | TEXT PK | UUID |
| user_id | TEXT FK | users.id |
| role | TEXT | user / ai |
| content | TEXT | 메시지 내용 |
| created_at | INTEGER | epoch ms |

---

## 8. 프론트엔드 변경사항

### 8.1. 기존 유지
- Header, ChatInput, MessageBubble, TypingIndicator, PendingOrb
- Zustand 상태 관리 구조
- 타이핑 애니메이션 (useTypewriter)
- 디자인 시스템 (보라 그라데이션, CSS 변수)

### 8.2. Zustand store 변경 (`lib/store/chat-store.ts`)

**추가할 상태:**
```typescript
userId: string; // crypto.randomUUID()로 초기화 (initialState에서)
```

**sendMessage 내부 흐름 변경:**

기존 store의 `sendMessage(text: string)` 본문에서 `apiSendMessage` 호출부를 아래와 같이 변경:

```typescript
// 기존: const reply = await apiSendMessage({ text, attachment: sentAttachment ?? undefined });
// 변경:
const reply = await apiSendMessage({
  message: text,
  userId: get().userId,
  attachment: sentAttachment ?? undefined,
});
```

그 외 store 로직(placeholder 생성, fullContents 보관 등)은 기존과 동일하게 유지:
- 응답의 `simulation`, `mission`, `categoryBreakdown` 필드는 `{ ...reply, content: '' }` spread로 placeholder에 즉시 포함됨
- 따라서 **타이핑 애니메이션 중에도 SimulationChart, MissionCard, CategoryBreakdown이 즉시 표시된다** — 이것이 의도된 동작

### 8.3. 타입 변경 (`lib/types.ts`)

```typescript
export type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  createdAt: number;
  attachment?: { name: string; size: number };
  simulation?: SimulationResult;
  mission?: { id: string; text: string; savingAmount: number };
  categoryBreakdown?: Record<string, number>;
};

export type SimulationResult = {
  currentPattern: {
    monthlySaving: number;
    projections: { year: number; assets: number }[];
  };
  optimizedPattern: {
    monthlySaving: number;
    projections: { year: number; assets: number }[];
  };
};
```

### 8.4. API 연동 (`lib/api/chat.ts`)

Mock → 실제 API 전환:

```typescript
export type SendMessageInput = {
  message: string;
  userId: string;
  attachment?: File;
};

export async function sendMessage(input: SendMessageInput): Promise<ChatMessage> {
  if (input.attachment) {
    // 1) POST /api/upload (multipart: file + userId)
    const form = new FormData();
    form.append('file', input.attachment);
    form.append('userId', input.userId);
    const uploadRes = await fetch('/api/upload', { method: 'POST', body: form });
    if (!uploadRes.ok) {
      const err = await uploadRes.json().catch(() => ({ error: 'CSV 업로드에 실패했어요.' }));
      throw new Error(err.error);
    }
    // 2) POST /api/chat { message: "", userId } (초기 분석 모드)
    // CSV 첨부 시 텍스트 입력은 무시하고 초기 분석 모드로 진입한다.
    const res = await fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message: '', userId: input.userId }),
    });
    if (!res.ok) throw new Error('분석 요청에 실패했어요.');
    return res.json();
  }
  // attachment 없으면: POST /api/chat { message, userId } 직접 호출
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message: input.message, userId: input.userId }),
  });
  if (!res.ok) throw new Error('응답을 받지 못했어요.');
  return res.json();
}
```

### 8.4b. 거래 내역 조회 (`lib/api/transactions.ts`)

Mock → 실제 API 전환:

```typescript
export async function getTransactions(userId: string): Promise<{
  transactions: Transaction[];
  stats: { total: number; byCategory: Record<string, number> };
}> {
  const res = await fetch(`/api/transactions?userId=${userId}`);
  return res.json();
}
```

> 현재 MVP에서 프론트가 이 함수를 호출하는 곳은 없지만, 확장을 위해 전환해둔다.

### 8.5. 신규 컴포넌트

아래 3개 컴포넌트는 모두 파일 상단에 **`'use client'`** 필수 (Recharts는 브라우저 전용).

**SimulationChart** (`components/chat/simulation-chart.tsx`):
- Recharts `LineChart` 사용
- 현재 패턴 vs 개선 패턴 2개 라인
- X축: 1, 3, 5년. Y축: 자산 (만원 단위 포맷)
- 현재 패턴 라인: `#a5a2b6` (회색, globals.css `--ink-300`에 대응)
- 개선 패턴 라인: `#5b21b6` (보라, globals.css `--accent`에 대응)
- 높이: 200px, 모서리: rounded-xl
- `message.simulation`이 존재하는 AI 메시지 하단에만 렌더링
- **Recharts에 CSS 변수를 직접 넣지 말 것** — SVG inline 속성은 CSS 변수를 해석 못함. 반드시 hex 값 사용.

**MissionCard** (`components/chat/mission-card.tsx`):
- 행동 미션 표시 + 수락/거절 버튼
- 수락 시 체크 아이콘 + "도전 중!" 텍스트로 전환 (프론트 상태만, `useState`로 관리)
- 거절 시 카드 dim 처리
- `message.mission`이 존재하는 AI 메시지 하단에만 렌더링

**CategoryBreakdown** (`components/chat/category-breakdown.tsx`):
- 수평 바 차트 (순수 div + Tailwind로 구현 — Recharts BarChart보다 가벼움)
- 상위 5개 카테고리만 표시
- 각 바에 카테고리명 + 금액 라벨
- 최대 금액 카테고리를 100% 기준으로 다른 바의 width를 비례 계산
- `message.categoryBreakdown`이 존재하는 AI 메시지 하단에만 렌더링

### 8.6. MessageList 변경

기존 `GraphSlot` import와 `lastAiIndex` 로직을 **삭제**하고, 각 메시지 `map` 내에서 데이터 유무에 따라 조건부 렌더링:

```tsx
{m.role === 'ai' && m.categoryBreakdown && <CategoryBreakdown data={m.categoryBreakdown} />}
{m.role === 'ai' && m.simulation && <SimulationChart data={m.simulation} />}
{m.role === 'ai' && m.mission && <MissionCard mission={m.mission} />}
```

### 8.7. 메타데이터 (`app/layout.tsx`)

```typescript
export const metadata: Metadata = {
  title: '팩폭머니 — AI 재정 코치',
  description: '소비 데이터 기반 AI 팩폭 재정 코칭',
};
```

`html lang="en"` → `lang="ko"` 변경.

### 8.8. Dark 모드

지원하지 않음. `globals.css`의 `.dark` 섹션은 shadcn 기본값이므로 삭제하지 않되, `html` 태그에 `class="light"`를 강제 적용하여 OS 설정에 의한 의도치 않은 dark 모드를 방지.

---

## 9. 가상 데이터 (시드)

**시드 스크립트:** `scripts/seed.ts` — `npx tsx scripts/seed.ts`로 실행

### 페르소나 A — 소확행 과잉형 (28세, 월 280만)
- 기존 CSV 사용: `sample-data/persona_A_transactions.csv` (1개월치, 80행)
- users 테이블: `{ id: 'persona-a', name: '소확행러', monthly_income: 2800000, current_savings: 5000000 }`
- CSV 컬럼: date, category, merchant, amount (UTF-8, 헤더 1행)

### 페르소나 B — 할부 잠식형 (33세, 월 350만)
- 시드 스크립트에서 직접 생성 (1개월치, 약 80행)
- users 테이블: `{ id: 'persona-b', name: '할부전사', monthly_income: 3500000, current_savings: 2000000 }`
- 특징: 전자기기 할부, 여행 할부, 구독 다수, 저축률 11%
- 할부 표현: category는 일반 카테고리 사용, merchant에 `'삼성 갤럭시 S25 (3/12회차)'` 형태로 기록
- 월 지출 약 310만원

**카테고리별 목표 분포:**

| 카테고리 | 목표 금액 | 행 수 | 비고 |
|----------|-----------|-------|------|
| 전자기기 | 약 80만 | 3행 | 할부 (갤럭시, 에어팟, 모니터 등) |
| 여행 | 약 60만 | 4행 | 할부 + 교통/숙박 |
| 구독료 | 약 12만 | 6행 | 넷플릭스, 유튜브, 스포티파이, 어도비, iCloud, 헬스장 |
| 카페 | 약 15만 | 15행 | |
| 배달 | 약 45만 | 15행 | |
| 식비 | 약 25만 | 15행 | 회사식당, 외식 |
| 교통 | 약 12만 | 10행 | 지하철, 택시 |
| 술자리 | 약 40만 | 5행 | |
| 쇼핑 | 약 20만 | 5행 | 의류 |
| **합계** | **~310만** | **~78행** | |

---

## 10. 환경 변수

```env
GEMINI_API_KEY=           # Google AI Studio API 키
```

코드에서 사용하는 상수 (환경변수 아닌 하드코딩):
- 모델명: `gemini-2.0-flash`
- Base URL: `https://generativelanguage.googleapis.com/v1beta/openai`
- DB 경로: `path.join(process.cwd(), 'data', 'factpokmoney.db')`

---

## 11. 의존성 추가

```bash
npm install better-sqlite3 openai papaparse recharts
npm install -D @types/better-sqlite3 @types/papaparse tsx
```

`next.config.ts`에 추가:
```typescript
const nextConfig: NextConfig = {
  serverExternalPackages: ['better-sqlite3'],
  // ... 기존 설정 유지
};
```

---

## 12. 파일 구조 (구현 후 예상)

```
app/
  api/
    chat/route.ts
    upload/route.ts
    transactions/route.ts
    simulation/route.ts
  globals.css
  layout.tsx
  page.tsx
components/
  chat/
    category-breakdown.tsx    ← 신규
    chat-input.tsx
    message-bubble.tsx
    message-list.tsx
    mission-card.tsx          ← 신규
    pending-orb.tsx
    simulation-chart.tsx      ← 신규
    typing-indicator.tsx
  header.tsx
  ui/
    button.tsx, card.tsx, input.tsx, scroll-area.tsx
lib/
  agents/
    analyzer.ts               ← 신규
    coach.ts                   ← 신규
    simulator.ts               ← 신규
  api/
    chat.ts                    ← Mock → 실 API 전환
    transactions.ts            ← Mock → 실 API 전환
  db.ts                        ← 신규
  hooks/
    use-typewriter.ts
  store/
    chat-store.ts              ← userId 추가
  types.ts                     ← simulation, mission 타입 추가
  utils.ts
scripts/
  seed.ts                      ← 신규
data/
  factpokmoney.db              ← 자동 생성
sample-data/
  persona_A_transactions.csv
```

---

## 13. 작업 순서

1. **의존성 설치 + 설정** — npm install, next.config.ts 수정
2. **타입 정의** — `lib/types.ts` 확장 (SimulationResult, mission 등)
3. **DB 모듈** — `lib/db.ts` (싱글톤 연결 + auto-create tables)
4. **시드 스크립트** — `scripts/seed.ts` (페르소나 A: CSV 읽기, 페르소나 B: 코드 생성)
5. **에이전트 함수** — analyzer.ts, simulator.ts, coach.ts
6. **API Routes** — /api/upload, /api/chat, /api/transactions, /api/simulation
7. **프론트 연동** — chat-store에 userId 추가, chat.ts Mock→실API, sendMessage 시그니처 변경
8. **신규 컴포넌트** — SimulationChart, MissionCard, CategoryBreakdown
9. **MessageList 변경** — GraphSlot 제거 → 조건부 차트/미션/카테고리 렌더링
10. **메타데이터 + 기타** — layout.tsx title/lang, dark 모드 방지

---

## 14. 삭제 대상

구현 완료 후 삭제할 파일:
- `lib/mock/messages.ts` — Mock 응답
- `lib/mock/transactions.ts` — Mock 거래 데이터
- `components/chat/graph-slot.tsx` — 빈 그래프 슬롯 (SimulationChart로 대체)
