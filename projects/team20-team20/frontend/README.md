# 학교공지 AI — 프론트엔드

20팀 백엔드 ([asm-ai-team20](https://github.com/soma17th-ai20/asm-ai-team20))의
공지 알림 서비스용 사용자 화면. Next.js 16 + React 19 + Tailwind v4 + framer-motion.

## 페이지

| 경로 | 역할 | 호출하는 백엔드 |
|---|---|---|
| `/` | 랜딩 (소개·CTA, mock 미리보기) | — |
| `/signup` | 회원가입 4단계 폼 (이름·이메일·학과·학년) | localStorage 저장만 |
| `/login` | 이메일로 로그인 (비밀번호 X) | `POST /api/users/login` |
| `/interests` | 카테고리 태그 다중선택 + 직접입력 | `POST /api/users` (가입+첫 관심사) → `POST /api/users/{uid}/interests` × N |
| `/settings` | 알림 이메일 + 빈도 (realtime/daily/weekly) | `GET·PATCH /api/users/{uid}/settings` |
| `/keywords` | 내 키워드 CRUD | `GET·POST /api/users/{uid}/interests`, `DELETE .../{kw}` |
| `/feed` | 매칭된 공지 카드 + 👍/👎 | `GET /api/users/{uid}/notifications`, `POST /api/notifications/{nid}/feedback` |

## 인증 모델

비밀번호 없는 **이메일 1개로 식별** (newsletter-style).

- 가입: `/signup` → `/interests` 끝낼 때 `POST /api/users`로 user_id 받아 localStorage에 저장
- 재방문: `/login`에서 이메일 입력 → `POST /api/users/login` → user_id 회수
- 세션은 localStorage의 `user_id` + `user_email` 두 개로 표현
- Navbar가 세션 감지해서 `[로그인][시작하기]` ↔ `[이메일 칩][로그아웃]` 자동 전환

## 빠른 시작

```bash
npm install
echo "NEXT_PUBLIC_API_BASE=http://localhost:8000" > .env.local
npm run dev
```

브라우저: http://localhost:3000

백엔드가 다른 호스트면 `.env.local`의 `NEXT_PUBLIC_API_BASE`만 바꾸면 됨.
백엔드는 `:3000` CORS 허용해 둠.

## API 클라이언트

`app/_lib/api.ts` — 타입드 fetch 래퍼 + localStorage 세션 헬퍼.

```ts
import { registerUser, login, listInterests, addInterest,
         removeInterest, getSettings, updateSettings,
         listMyNotifications, setFeedback,
         saveSession, clearSession, getUserId, getEmail } from './_lib/api'

// 가입
const r = await registerUser('alice@khu.ac.kr', '장학금')
saveSession(r.user_id, r.email)

// 로그인 (재방문)
const u = await login('alice@khu.ac.kr')
saveSession(u.user_id, u.email)

// 키워드 추가
await addInterest(getUserId()!, '인턴십')
```

에러는 `ApiError` (status, detail). 404 등은 `instanceof ApiError`로 구분.

## 디렉토리

```
app/
├── _lib/api.ts                 # 백엔드 API 클라이언트 + 세션 헬퍼
├── _components/Navbar.tsx      # 세션 인식 네비게이션
├── layout.tsx                  # 루트 레이아웃 (Navbar + main)
├── page.tsx                    # / 랜딩
├── signup/page.tsx             # /signup (LS 저장만)
├── login/page.tsx              # /login → POST /api/users/login
├── interests/page.tsx          # /interests → POST /api/users 가입
├── settings/page.tsx           # /settings → PATCH 설정
├── keywords/page.tsx           # /keywords → 키워드 CRUD
└── feed/page.tsx               # /feed → 알림 + 피드백
```

## 환경변수

| 변수 | 기본값 | 설명 |
|---|---|---|
| `NEXT_PUBLIC_API_BASE` | `http://localhost:8000` | 백엔드 호스트 |

## 의존성 메모

- **Next.js 16** — 마이너 버전 차이로 일부 API가 변동 가능. `AGENTS.md` 참고.
- **framer-motion ^12** — 페이지 트랜지션, 카드 인 애니메이션
- **Tailwind v4** — `@tailwindcss/postcss` 사용. `app/globals.css`에 토큰 정의.
- **react 19** + **react-dom 19**

## 백엔드 함께 띄우기

자세한 건 백엔드 저장소 README 참조. 요약:

```bash
# 백엔드 저장소 루트에서
docker compose up -d                # postgres + redis + backend (port 8000)
cd backend && python -m scheduler.main &     # 30분 주기 인제스천
cd backend && python -m notifier.worker &    # 메일 발송 워커

# FE
cd ../soma17th-ai20-FE && npm run dev        # http://localhost:3000
```

가입 → 관심사 등록 후 백엔드의 다음 사이클(또는 `python -m cli rematch`)이 돌면 매칭된
공지가 이메일과 `/feed` 페이지로 도착.

## 빌드 / 배포

```bash
npm run build && npm start
```

Vercel, Railway, Fly.io 등 Next.js 호환 플랫폼 어디든. 운영 시 `NEXT_PUBLIC_API_BASE`를
실 백엔드 도메인으로 설정.
