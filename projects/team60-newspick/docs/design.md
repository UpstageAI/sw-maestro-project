# NewPick Design — UI/UX 단일 진실원천

`prototype/` 의 모든 디자인 자산을 손실·왜곡 없이 옮긴 단일 명세서. Spring+Next 구현 단계에서 이 문서를 기준으로 디자인을 재현한다. 원본 파일들은 `prototype/` 에 그대로 보존되며, 본 문서는 그것을 정규화한 사본이다.

`docs/_archive/` 의 원본 두 MD가 텍스트 백업이라면, 이 문서는 디자인 백업이다. 본문 내 모든 색상값·치수·클래스명·화면 텍스트는 prototype 원본에서 발췌한 것이며 임의로 단순화하지 않았다.

---

## 1. 개요

- **모바일 우선 + iOS 프레임 메타포**. 모든 화면은 `.phone-frame`(390×820, 라운드 32px) 안에서 렌더링된다.
- **컬러 모드**: light only (`color-scheme: light`). 다크 토큰 미정의.
- **브랜드 컬러**: 오렌지 `#FF8A3D` (`--blue` 변수명, 의미는 브랜드 액션 컬러). 같은 변수를 모든 CTA·강조·진행률에 사용한다.
- **타이포**: Pretendard Variable (45 920 weight range). fallback은 Inter → ui-sans-serif → system stack.
- **데일리 리포트**는 C+ 보강형(타임라인 메타포)으로 확정. 변형 A/B/C/C+ 의 비교 시안은 `prototype/report-variations.jsx` 에 보존되어 있다.

---

## 2. 스타일 토큰

### 2.1 색상 (CSS 변수, `prototype/styles.css:10-24`)

| 변수 | 값 | 용도 |
|---|---|---|
| `--bg` | `#f2f4f6` | 페이지 배경 (모바일 외부) |
| `--surface` | `#ffffff` | 카드/시트/네비/챗 헤더 배경 |
| `--ink` | `#191f28` | 본문 텍스트, 강조 |
| `--muted` | `#6b7684` | 보조 텍스트, 요약 본문 |
| `--hint` | `#8b95a1` | 힌트, 메타 시간, 출처 |
| `--line` | `#e5e8eb` | 디바이더, 카드 테두리 |
| `--chip` | `#f2f4f6` | 칩 배경, 키워드 배경 (= `--bg`) |
| `--blue` | `#ff8a3d` | 브랜드 액션 (오렌지로 재정의된 별칭) |
| `--blue-pressed` | `#f97821` | 액티브/프레스드 상태 |
| `--blue-soft` | `#fff0e7` | 브랜드 소프트 배경 |

> 변수명은 `--blue` 지만 실제 컬러는 오렌지(`#ff8a3d`)다. Tailwind 매핑 시 `brand` 또는 `accent` 같은 의미 토큰명으로 재명명을 권장하지만, 본 prototype 의 클래스/변수와 1대1 일치를 위해 변수명은 그대로 유지한다.

### 2.2 추가 hex 값 (변수에 잡히지 않은 inline 색상)

| 위치 | 값 | 용도 |
|---|---|---|
| `loading-card` | `var(--blue-soft)` 그라디언트 + `rgba(255, 138, 61, 0.22)` (orbit border) | 로딩 카드 |
| `category-icon` 기본 배경 | `#ffffff` | 카테고리 카드 아이콘 박스 |
| `quiz-feedback` | `#f8fafb` | 퀴즈 피드백 박스 배경 |
| `quiz-result-item` | `#f8fafb` | 결과 항목 배경 |
| `report-briefing` 그라디언트 | `linear-gradient(135deg, #fff7f2 0%, #ffeedd 100%)` | 데일리 리포트 브리핑 카드 |
| `inline-quiz` 그라디언트 | `linear-gradient(180deg, #fff7f1 0%, #ffffff 72%)` | 인라인 퀴즈 카드 |
| `report-bg` | `#f6f7f9` (report-variations.html) | 리포트 변형 페이지 배경 |
| `issue-card--economy` | `#4f9cf9` (border-left), `#eef4ff` (badge bg), `#4f9cf9` (badge text) | 경제 카테고리 |
| `issue-card--social` | `#9b7cf8` (border-left), `#f3eeff` (badge bg), `#9b7cf8` (badge text) | 사회 카테고리 |
| 타임라인 노드 컬러 (인라인 `--c`) | `#ff8a3d` (테크), `#4f9cf9` (경제), `#9b7cf8` (이슈) | 카테고리 컬러 매핑 |
| `news-skeleton` 그라디언트 | `linear-gradient(90deg, #eceff2 0%, #f8fafb 48%, #eceff2 100%)` | 스켈레톤 shimmer |
| `quiz-dots` 비활성 | `#d1d6db` | 퀴즈 진행 도트 |
| `primary-button:disabled` | `#d1d6db` | 비활성 버튼 |
| 버튼 variant (확정 안된 시안) | `#ff6b5c` (soft-emerald), `#ff8a3d` (mint-green), `#34d399` (calm-green), `#5eead4` + 텍스트 `#0f3b35` (fresh-mint), pressed: `#f25445`/`#f97821`/`#10b981`/`#2dd4bf` | `prototype/styles.css:1444-1475` button-variants 비교용. 실제 채택은 `mint-green`(=`#ff8a3d`) |
| `chat-bubble--ai` shadow | `0 1px 4px rgba(25,31,40,0.07)` | AI 챗 버블 |
| `report-keywords` (구버전) | `#ff8a3d` 등 | (사용 안 함) |
| 카테고리 컬러 (`prototype/report-variations.jsx:NEWS`) | 예: 동일하게 `#ff8a3d`, `#4f9cf9`, `#9b7cf8` | 변형 시안에서 동일하게 재사용 |

### 2.3 타이포그래피

| 토큰 | 패밀리 | weight | size | 비고 |
|---|---|---|---|---|
| 헤드라인 (`h1`) | Pretendard | 800 | 42px / line-height 1.12 | 스플래시 NewPick 로고 옆 |
| 카테고리 H2 (`category-header h2`) | Pretendard | 800 | 28px / 1.25 | "관심 있는 뉴스를 골라주세요" |
| 앱 페이지 H2 (`app-page h2`) | Pretendard | 850 | 30px / 1.22 | "오늘의 뉴스" 등 |
| 디테일 H2 (`detail-article h2`) | Pretendard | 900 | 26px / 1.28 | 기사 상세 제목 |
| 뉴스 카드 H3 (`news-card h3`) | Pretendard | 850 | 18px / 1.38 | 홈 카드 제목 |
| 본문 / 요약 (`news-summary`, `summary-list p`) | Pretendard | 600~700 | 13~14px / 1.55 | |
| `intro` (스플래시 부제) | Pretendard | 500 | 17px / 1.55 | "AI가 오늘의 뉴스를…" |
| 뉴스 메타 (`news-source`, `time`) | Pretendard | 700~750 | 12px | hint 색 |
| 칩·키워드 (`news-keywords span`) | Pretendard | 750 | 11px | chip 배경 |
| 리포트 헤더 (`report-date`) | Pretendard | 800 | 30px / letter-spacing -0.6px | "5월 10일" |
| 키워드 클라우드 (`kw-cloud-v2`) | Pretendard | 600 | `data-w` 9→17px / 7→15px / 6→14px / 5→13px / 4→12px / 3→12px / 2→11px (불투명도 1 → 0.62 단계) | |
| 리포트 변형 시안 헤더 (Variant C+) | Noto Serif KR (Google Fonts) | 700~900 | 변형별 다름 | report-variations 전용 |

### 2.4 간격 / 반경 / 그림자

| 항목 | 값 | 위치 |
|---|---|---|
| 폰 프레임 라운드 | `border-radius: 32px` | `.phone-frame` |
| 폰 프레임 그림자 | `0 18px 50px rgba(25, 31, 40, 0.12)` | |
| 폰 프레임 크기 | `width: min(100%, 390px)`, `height: min(820px, calc(100vh - 40px))` | |
| 카드 라운드 (뉴스/디테일) | 18~20px | |
| 라운드 — 칩 / pill | `999px` | |
| 라운드 — 인라인 퀴즈 | `24px` | |
| 라운드 — 데일리 리포트 헤드라인 카드 | `20px` | |
| 라운드 — 챗 버블 | `18px` (꼬리 쪽 `4px`) | |
| 그림자 — 뉴스 카드 | `0 10px 24px rgba(25, 31, 40, 0.05)` | |
| 그림자 — primary-button (디테일 퀴즈) | `0 12px 24px rgba(255, 138, 61, 0.22)` | |
| 그림자 — 인라인 퀴즈 | `0 12px 30px rgba(25, 31, 40, 0.06)` | |
| 그림자 — 챗 fab (`.nav-item--chat`) | `0 4px 14px rgba(255, 138, 61, 0.38)` | |
| 패딩 — 컨테이너 | `28px 28px 40px` (welcome), `64px 22px 24px` (category), `26px 22px 18px` (app) | |
| 하단 네비 | `padding: 10px 18px 18px`, `border-top: 1px solid var(--line)`, `background: rgba(255,255,255,0.94)` | |
| 미디어 쿼리 | `@media (max-width: 430px)`: 풀화면 모드 (라운드 0). `@media (max-height: 720px)`: 컴팩트 패딩 + brand 폰트 축소 | |

### 2.5 애니메이션 (`@keyframes`)

| 이름 | 용도 | 정의 위치 |
|---|---|---|
| `spin` | 로딩 orbit 회전 | `styles.css:1377` |
| `pulse` | (미사용 잔존) | `styles.css:1383` |
| `dots` | 타이핑 인디케이터 점 3단 | `styles.css:1389` |
| `shimmer` | 뉴스 스켈레톤 | `styles.css:1405` |
| `pageEnterSoft` | 일반 페이지 전환 (180ms ease-out) | `styles.css:1414` |
| `pageEnterDetail` | 상세 진입 (220ms cubic-bezier) | `styles.css:1425` |
| `msgEnter` | 챗 메시지 등장 (200ms ease-out) | `styles.css:2481` |
| `typingBounce` | 챗 타이핑 점 점프 | `styles.css:2490` |

---

## 3. 레이아웃 시스템

### 3.1 phone-frame (모바일 셸)

`prototype/index.html` 의 `<section class="phone-frame">` 가 모든 화면의 컨테이너. 데스크톱 viewport 에서는 라운드된 폰 미리보기, ≤430px 에서는 풀스크린.

```
.phone-frame
├── .component-link            # "UI" 칩, 컴포넌트 시안 페이지 링크
├── .status-area               # 상태바: "9:41" + "5G 100%"
├── .content.screen.screen-welcome   # 스플래시
├── .content.screen.screen-category  # 카테고리 선택
├── .content.screen.screen-app       # 본 앱 (홈/상세/리포트/챗 페이지 컨테이너)
├── .welcome-actions           # 하단 CTA 영역 (서비스 시작하기 버튼)
└── .bottom-nav                # 홈 / 챗(중앙 FAB) / 리포트
```

상태바 `.status-area` 는 페이크다 (실제 OS 상태바가 아니라 디자인용 텍스트 "9:41" + "5G 100%"). 폰트 크기 13px, 굵기 700.

### 3.2 iOS 26 디바이스 프레임 (`prototype/ios-frame.jsx`)

별도 레퍼런스 컴포넌트. 디자인 캔버스(`design-canvas.jsx`)에서 시안 비교용으로 사용한다. 본 앱 구현에는 가벼운 `.phone-frame` 을 사용하고, iOS-frame 의 dynamic island / liquid glass / home indicator 는 시각 레퍼런스로만 본다.

| 부품 | 규격 |
|---|---|
| Device | 402×874, border-radius 48, 배경 `#F2F2F7` (light) / `#000` (dark) |
| Dynamic island | 126×37, top 11, 라운드 24, `#000` |
| Status bar | padding `21px 24px 19px`, 시간 표시 `9:41`, weight 590, 17px |
| Home indicator | 139×5, bottom 8, 라운드 100, `rgba(0,0,0,0.25)` (light) |
| Glass pill | 라운드 9999, blur 12px saturate 180%, inset 1.5px shine |
| List row | 52px min-height, 라운드 26 (그룹), 디바이더 0.5px |

### 3.3 안전영역 / 반응형

- 데스크톱: `.app-shell { padding: 20px }` 로 폰 프레임을 가운데 두고 외곽 여백.
- ≤430px: 폰 프레임이 전체 viewport를 차지 (라운드 0, shadow 0).
- ≤720px height: brand block transform `translateY(-34px)`, brand-mark 76px → 66px 축소, h1 38px, intro 16px.

---

## 4. 화면 인벤토리

prototype 에 존재하는 모든 화면을 빠짐없이 나열한다. 각 화면의 **원문 텍스트는 발췌 그대로** 보존한다.

### 4.1 스플래시 (`#welcomeScreen`, `prototype/index.html:21-33`)

- **요소**: NewPick 로고 이미지 (`assets/newspick.png`, 76×76, 라운드 24, 그림자 `0 16px 32px rgba(255,138,61,0.24)`) + h1 "NewPick" + intro 텍스트 + 하단 CTA "서비스 시작하기"
- **본문 그대로**:
  - h1: `NewPick`
  - intro: `AI가 오늘의 뉴스를 골라 짧게 요약하고 퀴즈로 정리해요.`
  - CTA: `서비스 시작하기`
- **상태바**: `9:41` / `5G 100%`
- **인터랙션**: CTA 클릭 → `screen-category` 로 전환

### 4.2 카테고리 선택 (`#categoryScreen`, `prototype/index.html:35-112`)

- **헤더 텍스트 그대로**:
  - step-label: `맞춤 설정`
  - h2: `관심 있는 뉴스를 골라주세요`
  - sub: `선택한 분야를 중심으로 요약, 퀴즈, 데일리 리포트를 준비할게요.`
- **카테고리 4종** (각 카드: 44px 아이콘 + 제목 + 설명 + 체크):
  | data-category | 제목 | 설명 |
  |---|---|---|
  | 테크 | 테크 | AI와 기술 흐름을 한눈에 |
  | 경제 | 경제 | 돈과 시장의 움직임을 쉽게 |
  | 정책 | 정책 | 정책 변화와 사회 방향을 이해해요 |
  | 이슈 | 이슈 | 지금 사람들이 주목하는 이야기 |
- **선택 상태**: `is-selected` 클래스 — 카드 배경 `--blue-soft`, 아이콘 박스 `--blue` + 흰 글자, `check-mark` 표시
- **뒤로가기**: 좌상단 `‹` 버튼 (back-button, 38×38, 라운드 14)

### 4.3 홈 — 로딩 (`.app-page[data-page="home"].is-loading`, `prototype/index.html:120-162`)

- **헤더**: step-label "Home" / h2 "오늘의 뉴스" / "AI가 관심 분야의 주요 뉴스를 정리하고 있어요."
- **로딩 카드** (`.loading-card`): orbit 스피너 + h3 `오늘의 뉴스를 정리 중이에요...` (typing-dots 3단) + 보조 문구 `잠시만 기다리면 오늘의 핵심을 정리해드릴게요.`
- **2단계 진행 카운터** (`.loading-steps`):
  - `data-step="collect"` — 라벨 `주요 뉴스 수집`, 카운트 `0 / 12 매체`
  - `data-step="summarize"` — 라벨 `AI 요약 생성`, 카운트 `0 / 8 기사`
- **스켈레톤 카드** 2개 (shimmer 애니메이션)
- **상태 클래스**: `is-active`(현재 단계), `is-done`(완료, 바 100% + 불투명도 0.55)
- **백엔드 연동 매핑**: [architecture/realtime-ui-states.md](architecture/realtime-ui-states.md) 의 SSE 스키마 참조.

### 4.4 홈 — 피드 (`.app-page[data-page="home"].is-loaded`, `prototype/index.html:164-227`)

3개 예시 뉴스 카드. 각 카드 구조: meta(카테고리 칩 + 출처 + 시간) → h3 → 요약 텍스트 → 키워드 칩 → "상세 보기" 버튼.

| 카드 | 카테고리 | 출처 | 시간 | 제목 |
|---|---|---|---|---|
| 1 | 테크 | ZDNet Korea | 09:20 | 오픈AI·앤트로픽, AI 에이전트 경쟁 본격화... 작업 자동화 시대 가시화 |
| 2 | 경제 | 한국경제 | 08:45 | 미국 관세 인상 여파... 반도체·자동차 수출 기업 비용 부담 가중 |
| 3 | 이슈 | 연합뉴스 | 08:10 | 합계출산율 0.75명 역대 최저... 정부, 인구전략기획부 신설 추진 |

각 카드의 요약 본문·키워드 3개는 `prototype/index.html:172-225` 에 그대로 보존되어 있으며, 본 문서 외 인용은 카드 1만 발췌:

> 카드1 요약: "오픈AI와 앤트로픽이 잇따라 에이전트 기능을 공개하며 단순 대화를 넘어 업무 자동화 시장에 진입하고 있어요. 이메일 작성, 코드 실행, 파일 관리 등 실제 작업을 AI가 직접 처리하는 서비스가 빠르게 확산되고 있습니다."
> 카드1 키워드: `AI 에이전트` / `오픈AI` / `자동화`

### 4.5 기사 상세 (`.app-page[data-page="detail"]`, `prototype/index.html:230-336`)

- **상단**: `‹` back 버튼 (38×38, 라운드 14, chip 배경)
- **hero**: meta(카테고리/출처/`오늘 09:20`) → h2 → 키워드 → source-strip(`원문 기반 AI 정리` / `원문 보기` 링크)
- **3섹션**:
  1. **핵심만 보기** (`.summary-section`) — 번호 매겨진 ol (`.summary-list`), 각 항목은 28×28 라운드 999 번호 배지 + 14px/1.55 본문
  2. **왜 중요해?** (`.insight-block`) — 좌측 3px `--blue` 보더 + 그라디언트 배경
  3. **조금 더 알기** (`.context-section`) — `<strong>배경/영향</strong>` + 설명 row 리스트
- **퀴즈 진입 버튼** (`.detail-quiz-button`): 라운드 999, primary 컬러, 그림자 `0 12px 24px rgba(255,138,61,0.22)`, 텍스트 `퀴즈로 이해도 확인하기`

### 4.6 인라인 O/X 퀴즈 (`.inline-quiz#inlineQuiz`, `prototype/index.html:299-334`)

- **헤더**: `읽은 내용 확인하기` 라벨 + 보조 `기사 핵심을 가볍게 체크해볼게요.` + `quiz-dots` 진행 표시 (3개 점, `is-active` 는 폭 18px+컬러)
- **문항 블록**: `Q1` 라벨(blue, 12px, 900) + strong 본문(15px/1.6, 750)
- **OX 버튼** (`.ox-actions`): 2분할 그리드, 58px min-height, 22px 굵은 글씨. 선택 시 `is-selected` → `--blue-soft` 배경 + `--blue` 텍스트
- **피드백 카드** (`.quiz-feedback`): 14px padding, 라운드 16, 배경 `#f8fafb`, "맞았어요/틀렸어요" 타이틀 + 해설 본문
- **다음 문제** 버튼 (`.quiz-next-button`): ink 배경 + 흰 글씨
- **결과 요약** (`.quiz-result-summary`): 정/오답 색 구분 항목 리스트. 정답 `is-correct` (blue-soft + blue), 오답 `is-wrong` (chip + muted)

### 4.7 데일리 리포트 (`.app-page[data-page="report"]`, `prototype/index.html:338-424`)

C+ 보강형(타임라인 메타포). 6 섹션 순서:

1. **헤더** (`.report-top` + `.report-day`):
   - `report-date`: `5월 10일` (30px/800, letter-spacing -0.6)
   - `report-update`: `09:30 업데이트` (12px hint)
   - `report-day`: `화요일 · 데일리 리포트` (13px muted)
2. **AI 브리핑** (`.report-briefing-v2`):
   - 좌측 28×28 `--blue-soft` 박스에 `AI` 배지
   - briefing-label: `BRIEFING` (10px hint, letter-spacing 1.2)
   - 본문: `AI 자동화와 통상 압박, 인구 위기가 동시에 부상한 하루였습니다.`
3. **타임라인 헤드** (`.tl-head`): `가장 많이 다뤄진 순` + 디바이더 라인 + `3건` 카운트
4. **타임라인** (`.timeline`):
   - `tl-rail`: 좌측 2px 그라디언트 라일
   - **헤드라인 노드** (`.tl-item--big` + `.tl-node.tl-node--big`): 16×16 큰 노드, 외곽 6px tint shadow, 카드는 `--blue-soft` 배경 + `--blue` 보더, 17px h3 + 13px 본문 + `src-tag` (4×5px dot 묶음 + `4개 매체가 동시에 보도`)
   - **서브 노드 1** (경제, `--c:#4f9cf9`): 작은 카드, `미국 관세 인상 여파... 반도체·자동차 수출 기업 부담 가중` + `3개 매체 보도`
   - **서브 노드 2** (이슈, `--c:#9b7cf8`): `합계출산율 0.75명 역대 최저... 인구전략기획부 신설 추진` + `2개 매체 보도`
5. **오늘의 흐름** (`.flow-list-v2`): 3개 row, 각 row 는 44px 카테고리 라벨 + 1줄 본문
   - 테크: `AI 에이전트 경쟁이 업무 자동화 시장으로 본격 확산`
   - 경제: `미국 관세 여파로 반도체·자동차 수출 기업 부담 가중`
   - 이슈: `합계출산율 역대 최저, 정부 전담 부처 신설로 대응`
6. **오늘의 키워드** (`.kw-cloud-v2`): `data-w` 단계별 사이즈/불투명도. 8개 키워드 — `AI 에이전트(9)`, `미국 관세(7)`, `오픈AI(6)`, `출산율(5)`, `자동화(4)`, `수출(3)`, `저출생(3)`, `반도체(2)`
7. **마침표** (`.report-footer-mark`): 점선 디바이더 + 16×16 체크 배지 + `오늘 따라잡기 끝 — 내일 09:30에 다시 만나요`

### 4.8 AI 챗 (`.app-page.chat-page`, `prototype/index.html:427-481`)

- **헤더** (`.chat-header`): 36×36 `--blue-soft` 아이콘 박스(핀+점 SVG) + 제목 `AI 어시스턴트` (15px/700) + 보조 `기사·리포트 검색` (11px hint) + 우측 `chat-reset-btn` (34×34 라운드 50, 1px 보더)
- **초기 상태** (`.chat-intro`):
  - 56×56 일러스트 (반원 + 점, fill `#fff0e7` + stroke `#ff8a3d`)
  - 타이틀: `뉴스가 궁금하면 물어보세요`
  - 설명: `수집된 기사와 리포트를 바탕으로\n답변해 드릴게요.`
  - 제안 칩 4종 (`chat-suggestion-chip`):
    - `어제 테크 뉴스 뭐 있었어?`
    - `AI 관련 기사 찾아줘`
    - `이번주 경제 흐름은?`
    - `오픈AI가 최근에 뭐 발표했어?`
- **대화 상태** (`.chat-messages`): 사용자/AI 버블 (max-width 82%, 라운드 18, 꼬리 4px). AI 버블 안에는 기사 카드(`chat-article-card`) 와 출처 라벨(`chat-source-label`) 노출 가능.
- **타이핑 인디케이터** (`.chat-typing`): 3개 7×7 점, 0/0.18/0.36s 딜레이로 `typingBounce` 애니메이션
- **입력바** (`.chat-input-bar`): 42px 라운드 21 텍스트 인풋 + 42×42 라운드 50 send 버튼 (`--blue` 배경, 흰 종이비행기 SVG)
- **placeholder**: `궁금한 뉴스를 물어보세요`

### 4.9 하단 네비게이션 (`.bottom-nav`, `prototype/index.html:491-520`)

- 3 슬롯 (1fr / 64px / 1fr): 홈, 챗 FAB, 리포트
- **홈/리포트 nav-item**: 22×22 SVG 아이콘 + 12px 라벨, 활성 시 `--blue-soft` 배경 + `--blue` 텍스트
- **챗 FAB** (`.nav-item--chat`): 52×52 라운드 50, `--blue` 배경, 흰 말풍선 SVG, 그림자 `0 4px 14px rgba(255,138,61,0.38)`. margin-top -6px 로 살짝 떠 있음.

### 4.10 컴포넌트 시안 페이지 (`prototype/button-variants.html`)

`.components-shell` 안에 헤더 + `component-section` 들. CTA 버튼(메인 컬러 `#FF8A3D` 명시) + 카테고리 아이콘 4종(테크/경제/정치·정책/사회 이슈) 미리보기.

### 4.11 디자인 캔버스 + 리포트 변형 (`prototype/preview.html`, `report-variations.html`)

`design-canvas.jsx` 가 zoom/pan 가능한 캔버스에 시안 다 펼쳐 보여주는 dev 도구. `report-variations.jsx` 에 `VariantA / VariantB / VariantC / VariantCPlus` 4개 변형 + 공통 `phoneShell / StatusBar / BottomNav` 정의. **확정 시안은 VariantCPlus** = `prototype/index.html` 의 리포트 페이지가 그것의 정적 포팅이다.

---

## 5. 컴포넌트 인벤토리

본 인벤토리에 등장하는 모든 클래스명은 `prototype/styles.css` 와 `prototype/index.html` 에 정의된 그대로다.

### 5.1 버튼

| 클래스 | 용도 | 시각 스펙 |
|---|---|---|
| `.primary-button` | 스플래시 / 컴포넌트 시안 메인 CTA | 100% width, 54px 또는 46px (variants 안에서), 라운드 16, `--blue` 배경, 17px/750 흰 글씨, pressed `--blue-pressed`, disabled `#d1d6db` |
| `.detail-quiz-button` | 디테일 퀴즈 진입 | 52px min-height, 라운드 999, 그림자 `0 12px 24px rgba(255,138,61,0.22)` |
| `.quiz-next-button` | 다음 문제 | 44px min-height, 라운드 14, ink 배경 + 흰 글씨 |
| `.detail-back`, `.back-button`, `.components-back` | 38×38 back chevron `‹` | 라운드 14, chip 배경(detail-back) / 투명(back-button) |
| `.news-actions button` | 카드 내 액션 (`상세 보기`) | 38px min-height, 1px line 보더, 라운드 12 (마지막 child 는 blue-soft 배경 + blue 텍스트) |
| `.ox-actions button` | OX 선택 | 58px min-height, 라운드 18, 22px/850 |
| `.chat-suggestion-chip` | 챗 제안 칩 | 라운드 20, 1px line 보더, 13px/500 |
| `.chat-send-btn` | 챗 전송 | 42×42 라운드 50, `--blue` 배경 |
| `.chat-reset-btn` | 챗 초기화 | 34×34 라운드 50, 1px line 보더 |
| `.nav-item` / `.nav-item--chat` | 하단 네비 | nav-item: 52px min-height, 라운드 16 / chat: 52×52 FAB |
| `.component-link` | 우측 상단 "UI" 칩 | 30×24, 라운드 999, chip 배경 |

#### 5.1.1 button-variants 시안 (`styles.css:1444-1475`)

리포트 시안과 별개로 **버튼 컬러 변형** 4종이 정의되어 있다. 실제 채택은 `.variant-mint-green` (= `#ff8a3d`).

| 클래스 | 배경 | 텍스트 | pressed |
|---|---|---|---|
| `.variant-soft-emerald` | `#ff6b5c` | `#fff` | `#f25445` |
| `.variant-mint-green` (✅채택) | `#ff8a3d` | `#fff` | `#f97821` |
| `.variant-calm-green` | `#34d399` | `#fff` | `#10b981` |
| `.variant-fresh-mint` | `#5eead4` | `#0f3b35` | `#2dd4bf` |

### 5.2 카드

| 클래스 | 용도 |
|---|---|
| `.news-card` | 홈 피드 기사 카드 (1px line 보더, 라운드 20, 그림자 약함) |
| `.detail-article` | 기사 상세 컨테이너 (gap 18px, padding-bottom 28px) |
| `.insight-block` | "왜 중요해?" 강조 박스 (좌측 3px blue 보더 + 그라디언트) |
| `.inline-quiz` | 인라인 OX 퀴즈 (1px blue-translucent 보더, 라운드 24, 부드러운 그라디언트) |
| `.quiz-result-item` | 퀴즈 결과 한 줄 (28×28 ●○ 배지 + 본문) |
| `.report-briefing-v2` | 데일리 리포트 AI 브리핑 (1px line 보더, 라운드 14) |
| `.tl-card` / `.tl-card--big` | 타임라인 카드 (작은 / 큰) |
| `.flow-list-v2` | 카테고리별 한 줄 정리 |
| `.headline-card` (구버전) | (기존 변형 시안 잔존, 현재 미사용) |
| `.sub-article-card` (구버전) | (기존 변형 시안 잔존) |
| `.issue-card` / `.issue-card--economy` / `.issue-card--social` | 변형 시안용 색상 분기 |
| `.stat-card` / `.stat-card--quiz` | 변형 시안용 통계 카드 (`.report-stats`) |
| `.chat-bubble--user` / `.chat-bubble--ai` | 챗 버블 |
| `.chat-article-card` | 챗 안 기사 카드 |
| `.icon-preview-card` (button-variants.html) | 카테고리 아이콘 미리보기 |
| `.loading-card` | 홈 로딩 안내 카드 |
| `.news-skeleton` | shimmer 스켈레톤 |
| `.category-card` / `.category-card.is-selected` | 온보딩 카테고리 선택 카드 |

### 5.3 칩 / 배지

| 클래스 | 용도 |
|---|---|
| `.news-category` | 카테고리 칩 (24px height, blue-soft 배경, blue 텍스트) |
| `.news-keywords span` | 키워드 칩 (24px, chip 배경, muted 텍스트) |
| `.briefing-label` | "BRIEFING" 라벨 (hint 컬러, letter-spacing 1.2) |
| `.cluster-badge` / `.cluster-badge--muted` | "N개 매체 보도" 배지 (변형 시안용) |
| `.tl-cat`, `.flow-cat` | 타임라인/플로우 카테고리 라벨 (인라인 `--c` 컬러) |
| `.detail-label` | 섹션 라벨 (blue, 13px, 900) |
| `.step-label` | 온보딩 step 라벨 |
| `.check-mark` | 카테고리 선택 ✓ |
| `.footer-check` | 리포트 마침표 ✓ |
| `.chat-source-label` | 챗 출처 라벨 |

### 5.4 입력 / 진행

| 클래스 | 용도 |
|---|---|
| `.chat-input` | 42px 라운드 21 텍스트 인풋. focus 시 blue 1px 보더 + surface 배경 |
| `.loading-step-bar` | 4px 라운드 2 진행 바, 채움색 `--blue` |
| `.quiz-dots span` | 6×6 도트, 활성 18px+blue, 완료 alpha 0.42 |
| `.src-dots` | 5×5 도트 묶음 (`--c` 컬러) |

### 5.5 변형(Variants) 컴포넌트 (`prototype/report-variations.jsx`)

리포트 변형 4종이 React 컴포넌트로 정의되어 있다. **현 채택은 VariantCPlus**, 나머지는 비교/탐색 시안.

| 함수 | 시각 컨셉 |
|---|---|
| `VariantA` | `prototype/report-variations.jsx:168` — 미니멀 카드형 |
| `VariantB` | `prototype/report-variations.jsx:355` — 통계 강조 |
| `VariantC` | `prototype/report-variations.jsx:528` — 리스트 강조 |
| `VariantCPlus` (✅채택) | `prototype/report-variations.jsx:649` — 타임라인 메타포 |

각 variant 는 공통으로 `phoneShell`, `StatusBar`, `BottomNav` 를 import 하고 `NEWS` 상수의 데모 데이터를 사용한다. `BottomNav` 의 `activeColor` 기본값은 `#ff8a3d`.

### 5.6 카테고리 아이콘 SVG (4종)

`prototype/index.html:53-110` 와 `button-variants.html:35-82` 에 동일한 SVG 정의가 있다. 모두 24×24 viewBox, `stroke=currentColor`, `stroke-width=2`, `stroke-linecap/linejoin=round`, `fill=none`.

| 카테고리 | 이미지 컨셉 |
|---|---|
| 테크 | 가운데 사각형 + 8방향 핀 (AI 칩) |
| 경제 | 상승 그래프 + 동전 (좌하 원) |
| 정책 | 라운드 사각형 안 체크 (문서 + 체크) |
| 이슈 | 말풍선 + 우상단 원 (말풍선 + 알림점) |

button-variants.html 에서는 카테고리 라벨이 `정치·정책`, `사회 이슈` 로 표시되는데, 본 앱(`index.html`)에서는 `정책`, `이슈` 로 축약해 사용한다. **공식 라벨은 `정책` / `이슈`**.

---

## 6. 인터랙션 / 모션

`prototype/script.js` 의 동적 동작을 항목별로 정리. 함수 위치는 `prototype/script.js:LINE` 으로 표기.

| 동작 | 함수 / 위치 | 설명 |
|---|---|---|
| 화면 단계 전환 (`welcome → category → app`) | `showOnly` (`script.js:83`), `showWelcomeStep` (`108`), `showCategoryStep` (`118`) | `is-active` 클래스 토글 + back-button 표시 |
| 페이지 진입 애니메이션 | `animatePage`, `showAppPage` (`script.js:126, 136`) | `page-enter-soft`(180ms ease-out) 또는 `page-enter-detail`(220ms cubic) 적용 |
| 카테고리 선택 토글 | `script.js:89-106` 영역 | 카드 클릭 → `is-selected` 토글 + CTA 텍스트 동적 변경 |
| 홈 로딩 진행률 mock | `startHomeLoading` (`script.js:180`), `clearHomeLoading` (`172`) | ease-out cubic 으로 카운터/바 애니메이션. 실제 SSE 연동 시 [architecture/realtime-ui-states.md](architecture/realtime-ui-states.md) 의 EventSource 코드로 교체 |
| 인라인 퀴즈 출제 | `renderQuizQuestion` (`script.js:243`), `showQuizResult` (`269`), `resetInlineQuiz` (`56`) | 3문항 순차 진행, OX 선택 → 피드백 → 다음 문제 → 결과 요약 |
| 챗 페이지 메시지 입출력 | `sendMessage` 등 (`script.js:351~`) | 캔드 응답 매핑 (`CHAT_RESPONSES`) → 실제 SSE 연동 시 [ai/rag-chat.md](ai/rag-chat.md) 의 `EventSource` 코드로 교체 |
| 챗 인트로 ↔ 메시지 전환 | `chatIntro[hidden]` / `chatMessages[hidden]` 토글 | 첫 메시지 전송 시 `chatIntro` 숨김, `chatMessages` 노출 |
| 타이핑 인디케이터 | `.chat-typing` 노드 동적 삽입 | 응답 시 추가, 응답 완료 시 제거 |

---

## 7. 자산

| 파일 | 위치 | 사용처 | 비고 |
|---|---|---|---|
| `newspick.png` | `prototype/assets/newspick.png` | 스플래시 brand-mark (76×76, 라운드 24) | 라이선스: 프로젝트 자체 자산 |
| Pretendard Variable woff2 | CDN: `https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/woff2/PretendardVariable.woff2` | 본문 폰트 | OFL 라이선스 (Pretendard 공식) |
| Noto Serif KR | Google Fonts | report-variations 시안 일부 | OFL |
| 아이콘 SVG | inline (`prototype/index.html`, `button-variants.html`) | 카테고리/네비/챗/리포트 등 | 모두 inline, 외부 의존 없음. stroke 기반 (`width=2`, `linecap/linejoin=round`) |

> 추가 아이콘 세트(예: Lucide, Heroicons) 도입 여부는 Phase B 에서 frontend 결정.

---

## 8. 프로토타입 → 구현 매핑

| 프로토타입 자산 | Next.js 구현 시 매핑 (제안) |
|---|---|
| `prototype/index.html`의 `.phone-frame` | `app/(app)/layout.tsx` 안의 모바일 컨테이너 |
| `screen-welcome` 섹션 | `app/(app)/page.tsx` 또는 `app/onboarding/welcome/page.tsx` |
| `screen-category` 섹션 | `app/onboarding/category/page.tsx` |
| `app-page[data-page="home"]` | `app/feed/page.tsx` (로딩/피드 두 상태는 `isLoading` 으로 분기) |
| `app-page[data-page="detail"]` | `app/article/[id]/page.tsx` |
| `inline-quiz` | `app/article/[id]/_components/InlineQuiz.tsx` (서버 컴포넌트 + 클라이언트 인터랙션) |
| `app-page[data-page="report"]` | `app/report/page.tsx` |
| `app-page.chat-page` | `app/chat/page.tsx` |
| `bottom-nav` | `app/_components/BottomNav.tsx` (Server Component, 클라 active state 만 클라이언트) |
| `prototype/styles.css` 의 CSS 변수 | `tailwind.config.ts` 의 `theme.extend.colors` (또는 `:root` CSS 변수 그대로 + Tailwind plugin 으로 노출) |
| `prototype/styles.css` 의 컴포넌트 스타일 (`.news-card`, `.tl-card`, …) | Tailwind 유틸리티로 재작성 또는 CSS Modules 로 1대1 포팅 |
| `prototype/script.js`의 페이지 전환 로직 | Next.js App Router 의 `Link` + 페이지 전환 (대부분 자체 해결) |
| `prototype/script.js`의 SSE 연동 mock | `EventSource` (또는 `@microsoft/fetch-event-source`) 로 실제 연동, 코드 위치는 [ai/rag-chat.md](ai/rag-chat.md) / [architecture/realtime-ui-states.md](architecture/realtime-ui-states.md) 참조 |
| `prototype/ios-frame.jsx` | 본 앱 구현에 직접 사용 X (시각 레퍼런스). Storybook 등 디자인 시스템 도구에 살려두는 것 검토 |
| `prototype/design-canvas.jsx` | 본 앱 구현에 사용 X. 디자인 시안 비교 도구 — 별도 보존만 |
| `prototype/report-variations.jsx` | VariantCPlus 만 본 앱에 채택. 나머지는 보존만 |

> Tailwind 토큰 상세 매핑(`--blue` → `theme.colors.brand.500` 등)은 Phase B 의 [frontend/tailwind.md](frontend/tailwind.md) 에서 결정한다.

---

## 9. 변경 이력

| 날짜 | 변경 | 사유 |
|---|---|---|
| 2026-05-10 | 데일리 리포트를 VariantCPlus(타임라인 메타포)로 확정 | 헤드라인 + 매체 수 시각화의 정보 밀도가 가장 높음 |
| 2026-05-10 | 별도 퀴즈 탭 제거, 기사 상세 안에 인라인 퀴즈로 통합 | 퀴즈는 기사 종속 기능. 네비 단순화 |
| 2026-05-10 | 홈 로딩을 3단계 mock 텍스트 → 2단계 실제 카운터(SSE 연동 가능 구조)로 전환 | 백엔드 진행률과 일치 |
| 이후 변경 | Phase B 에서 Tailwind 토큰화 결정 시 추가 | |

---

## 보존 안전망

본 문서가 누락한 디테일이 의심되면 항상 원본 prototype 을 진실원천으로 본다. 본 문서의 어떤 항목도 prototype 자산을 대체하지 않는다 — prototype 은 **읽기 전용 보존**, 이 문서는 **현 시점 스냅샷**이다.

| 디자인 검증 시 | 1차 출처 | 2차 출처 |
|---|---|---|
| 색상값 | `prototype/styles.css:10-24` (변수) + 본문 검색 | 본 문서 §2 |
| 화면 텍스트 | `prototype/index.html` | 본 문서 §4 |
| 컴포넌트 클래스 | `prototype/styles.css` 본문 검색 | 본 문서 §5 |
| 인터랙션 | `prototype/script.js` 함수 | 본 문서 §6 |
| 변형 시안 | `prototype/report-variations.jsx`, `design-canvas.jsx` | 본 문서 §5.5 |
