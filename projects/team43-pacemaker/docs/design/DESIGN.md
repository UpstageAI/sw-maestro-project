# AI 운동 코치 디자인 시스템 (DESIGN.md)

본 문서는 AI 운동 코치 웹 서비스(Flutter Web)의 디자인 토큰, 컴포넌트, 레이아웃, 인터랙션 가이드를 정의한다. 모든 신규 화면 및 컴포넌트는 본 문서의 토큰을 기준으로 구현되어야 한다.

---

## 1. 디자인 철학

### 1.1 핵심 원칙
- **Data-First (데이터 우선)**: 차트와 수치를 가장 먼저 보이도록 시각적 위계를 구성
- **Calm Tech (차분한 기술감)**: 다크 테마 + 시안(Cyan) 글로우로 미래지향적이면서 눈이 편안한 인상
- **Glanceable (한눈에 파악)**: 중요한 정보는 카드 단위로 분리하여 즉시 인지 가능
- **Conversational AI (대화형 AI)**: 챗봇 영역은 대화의 흐름을 방해하지 않도록 군더더기 없는 구성

### 1.2 무드보드 키워드
`다크 모드` `네온 시안 글로우` `유리 카드(Glassmorphism)` `정밀한 데이터 시각화` `미니멀`

---

## 2. 컬러 시스템

### 2.1 기본 팔레트

#### Background
| 토큰 | HEX | 용도 |
|------|-----|------|
| `--bg-base` | `#0A0F1E` | 페이지 최하단 배경 (가장 어두운 네이비) |
| `--bg-elevated-1` | `#101730` | 카드 배경 (1단계) |
| `--bg-elevated-2` | `#162041` | 카드 내부 보조 배경 (2단계, 차트 배경 등) |
| `--bg-overlay` | `#0A0F1ECC` | 모달 오버레이 (80% 투명) |

#### Brand / Accent
| 토큰 | HEX | 용도 |
|------|-----|------|
| `--accent-primary` | `#4FC3F7` | 주요 강조 (오늘 카드 테두리, 차트 라인, CTA 보조) |
| `--accent-primary-glow` | `#4FC3F766` | 글로우/그림자 효과 (40% 투명) |
| `--accent-secondary` | `#7B61FF` | 보조 강조 (캘린더 등록 버튼, 사용자 챗 버블 강조) |
| `--accent-secondary-glow` | `#7B61FF66` | 보조 글로우 |

#### Text
| 토큰 | HEX | 용도 |
|------|-----|------|
| `--text-primary` | `#FFFFFF` | 본문/제목 |
| `--text-secondary` | `#B8C2D9` | 보조 텍스트 |
| `--text-tertiary` | `#6B7794` | 비활성 / 캡션 |
| `--text-on-accent` | `#0A0F1E` | 액센트 배경 위 텍스트 |

#### Border / Divider
| 토큰 | HEX | 용도 |
|------|-----|------|
| `--border-subtle` | `#1F2A4A` | 카드 외곽선 (기본) |
| `--border-emphasis` | `#4FC3F7` | 강조 외곽선 (오늘 카드, 포커스 상태) |
| `--divider` | `#1A2240` | 영역 구분선 |

### 2.2 시맨틱 컬러 (상태)

| 토큰 | HEX | 용도 |
|------|-----|------|
| `--status-success` | `#4ADE80` | 양호 |
| `--status-success-bg` | `#4ADE801F` | 양호 배지 배경 |
| `--status-warning` | `#FBBF24` | 주의 |
| `--status-warning-bg` | `#FBBF241F` | 주의 배지 배경 |
| `--status-danger` | `#F87171` | 위험/높음 |
| `--status-danger-bg` | `#F871711F` | 위험 배지 배경 |
| `--status-info` | `#4FC3F7` | 정보 |

### 2.3 카테고리 컬러 (운동 부위)

운동 이력 아이콘 배경, 일정 카드 강조에 사용:

| 카테고리 | 토큰 | HEX |
|---------|------|-----|
| 상체 (푸쉬/풀) | `--cat-upper` | `#4FC3F7` |
| 하체 | `--cat-lower` | `#A78BFA` |
| 코어 | `--cat-core` | `#F472B6` |
| 유산소 | `--cat-cardio` | `#4ADE80` |
| 휴식 | `--cat-rest` | `#6B7794` |

### 2.4 그라디언트

```css
/* 페이지 배경 */
--gradient-page: radial-gradient(
  ellipse at top,
  #131B36 0%,
  #0A0F1E 70%
);

/* 강조 카드 (오늘) */
--gradient-today: linear-gradient(
  180deg,
  #4FC3F71A 0%,
  #4FC3F708 100%
);

/* 챗봇 추천 카드 */
--gradient-recommend: linear-gradient(
  135deg,
  #162041 0%,
  #1F2A4A 100%
);
```

---

## 3. 타이포그래피

### 3.1 폰트 패밀리
- **기본**: `Pretendard`, `Noto Sans KR`, `-apple-system`, `BlinkMacSystemFont`, `sans-serif`
- **숫자/데이터 강조**: `Pretendard` (tabular-nums 옵션 사용)

### 3.2 타입 스케일

| 토큰 | size / line-height | weight | 용도 |
|------|---------------------|--------|------|
| `--type-display` | 32px / 40px | 700 | 페이지 메인 타이틀 ("이번 주 운동 코치") |
| `--type-h1` | 24px / 32px | 700 | 카드 헤더 |
| `--type-h2` | 20px / 28px | 600 | 섹션 제목 |
| `--type-h3` | 18px / 26px | 600 | 카드 내 강조 텍스트 |
| `--type-body-lg` | 16px / 24px | 400 | 본문 (대) |
| `--type-body` | 14px / 22px | 400 | 본문 (기본) |
| `--type-caption` | 12px / 18px | 400 | 캡션, 메타 정보 |
| `--type-overline` | 11px / 16px | 600 | 라벨 (uppercase 가능) |
| `--type-data-xl` | 48px / 56px | 700 | 컨디션 점수(78) 등 핵심 수치 |
| `--type-data-md` | 18px / 24px | 600 | 차트 라벨 수치 |

### 3.3 사용 규칙
- 제목 위계는 항상 페이지당 1개의 Display, 카드당 1개의 H1을 따른다
- 숫자가 강조되는 영역(`78/100`)은 `tabular-nums`를 적용해 자릿수 흔들림 방지
- 한국어 본문에서는 `letter-spacing: -0.01em` 정도의 미세 자간 조정 적용 가능

---

## 4. 간격 / 레이아웃 시스템

### 4.1 Spacing Scale (4px 기반)

| 토큰 | 값 | 용도 |
|------|-----|------|
| `--space-1` | 4px | 아이콘과 텍스트 사이 |
| `--space-2` | 8px | 작은 컴포넌트 내부 |
| `--space-3` | 12px | 카드 내부 요소 사이 |
| `--space-4` | 16px | 기본 간격 |
| `--space-5` | 24px | 카드 내부 패딩 |
| `--space-6` | 32px | 섹션 간 여백 |
| `--space-7` | 48px | 큰 섹션 분리 |
| `--space-8` | 64px | 페이지 상하 여백 |

### 4.2 Radius

| 토큰 | 값 | 용도 |
|------|-----|------|
| `--radius-sm` | 6px | 배지, 작은 버튼 |
| `--radius-md` | 10px | 입력창, 일반 버튼 |
| `--radius-lg` | 14px | 일정 카드, 채팅 버블 |
| `--radius-xl` | 20px | 메인 카드 패널 |
| `--radius-full` | 9999px | 둥근 버튼, 아바타 |

### 4.3 Elevation / Shadow

```css
--shadow-card: 0 1px 0 0 #FFFFFF08 inset, 
                0 8px 24px 0 #00000040;

--shadow-glow-cyan: 0 0 0 1px #4FC3F740,
                    0 0 24px 0 #4FC3F733;

--shadow-glow-violet: 0 0 0 1px #7B61FF40,
                      0 0 24px 0 #7B61FF33;
```

### 4.4 그리드 / 브레이크포인트

| 디바이스 | 브레이크포인트 | 컬럼 / 거터 |
|---------|----------------|-------------|
| Desktop (Wide) | ≥ 1440px | 12 / 24px |
| Desktop | 1280–1439px | 12 / 20px |
| Tablet | 768–1279px | 8 / 16px |
| Mobile | ≤ 767px | 4 / 12px |

#### 메인 대시보드 컬럼 구성 (Desktop ≥ 1280px)
- 좌측 데이터 영역: 7컬럼
- 우측 챗봇 영역: 5컬럼
- 영역 간 거터: 24px

---

## 5. 컴포넌트 가이드

### 5.1 카드 (Panel)

기본 카드 스타일:
```css
background: var(--bg-elevated-1);
border: 1px solid var(--border-subtle);
border-radius: var(--radius-xl);
padding: var(--space-5);
box-shadow: var(--shadow-card);
```

#### 변형
- **Default**: 위 기본 스타일
- **Highlighted (오늘 카드)**: `border-color: var(--accent-primary)` + `box-shadow: var(--shadow-glow-cyan)`
- **Compact**: `padding: var(--space-4)`, 작은 위젯용

### 5.2 일정 카드 (Day Card)

크기: 너비 가변(7등분), 높이 약 168px

구성 (위에서 아래로):
1. 요일 (예: "월") — `--type-body`, `--text-secondary`
2. 날짜 (예: "5/27") — `--type-body`, `--text-primary`
3. 카테고리 아이콘 — 24px
4. 카테고리 라벨 (예: "상체 (푸쉬)") — `--type-caption`, `--text-secondary`

상태:
- **Default**: 기본 카드 스타일
- **Today**: `border: 1px solid var(--accent-primary)`, `box-shadow: var(--shadow-glow-cyan)`, 라벨 색상 `--accent-primary`
- **Rest**: 카테고리 아이콘은 `--cat-rest`, 텍스트는 `--text-tertiary`
- **Hover**: `background: var(--bg-elevated-2)`, transition 150ms

### 5.3 버튼

#### Primary Button
```css
background: var(--accent-secondary);
color: #FFFFFF;
border-radius: var(--radius-md);
padding: 10px 16px;
font: var(--type-body) / weight 600;
box-shadow: var(--shadow-glow-violet);
```
- Hover: brightness 1.1
- Active: brightness 0.95
- Disabled: opacity 0.4

#### Secondary Button (Outlined)
```css
background: transparent;
border: 1px solid var(--border-subtle);
color: var(--text-primary);
border-radius: var(--radius-md);
padding: 8px 14px;
```

#### Ghost Button (지난주 / 다음주)
- 아이콘 + 텍스트
- 배경 없음, hover 시 `background: var(--bg-elevated-2)`
- 비활성(미래 주차 제한 등) 시 `color: var(--text-tertiary)`, `cursor: not-allowed`

#### Icon Button (전송, 새 대화 등)
- 36x36, `border-radius: var(--radius-md)`
- 활성 상태: `background: var(--accent-secondary)`, 아이콘 흰색

### 5.4 배지 (Status Badge)

```css
border-radius: var(--radius-sm);
padding: 2px 8px;
font: var(--type-caption) / weight 600;
```
- 양호: `background: var(--status-success-bg)`, `color: var(--status-success)`
- 주의: `background: var(--status-warning-bg)`, `color: var(--status-warning)`
- 위험: `background: var(--status-danger-bg)`, `color: var(--status-danger)`

### 5.5 도넛 차트 (Condition)

- 외경 144px, 두께 12px
- 진행 호: `--accent-primary` + glow
- 미진행 호: `var(--bg-elevated-2)`
- 중앙 텍스트: `--type-data-xl` (점수), `--type-caption` (`/100`), `--type-body` (라벨)

### 5.6 레이더 차트 (부위별 피로도)

- 6각형, 내부 격자 4단계 (`var(--border-subtle)`)
- 라인: `--accent-primary`, 굵기 2px
- 채움: `--accent-primary` 20% 투명도
- 데이터 포인트: 4px 원, `--accent-primary`
- 축 라벨: `--type-body`, `--text-secondary`
- 수치 라벨: `--type-caption`, `--text-tertiary`

### 5.7 채팅 버블

#### 사용자 메시지 (오른쪽)
```css
background: linear-gradient(135deg, #4FC3F71F, #7B61FF1F);
border: 1px solid #4FC3F740;
color: var(--text-primary);
border-radius: 14px 14px 4px 14px;
padding: 12px 16px;
max-width: 75%;
```

#### AI 응답 (왼쪽)
```css
background: var(--bg-elevated-2);
border: 1px solid var(--border-subtle);
border-radius: 14px 14px 14px 4px;
padding: 12px 16px;
max-width: 75%;
```

#### 메타 정보
- 보낸 시각: `--type-caption`, `--text-tertiary`, 버블 외부에 표시
- AI 아바타: 36x36 원형, `var(--bg-elevated-2)` 배경 + 로봇 아이콘

### 5.8 추천 운동 슬롯 카드

```css
background: var(--gradient-recommend);
border: 1px solid var(--border-subtle);
border-radius: var(--radius-lg);
padding: var(--space-5);
```
- 헤더: "추천 운동 슬롯" 라벨 + 일자 배지
- 본문: 운동명(`--type-h3`, `--accent-primary`) + 설명 + 종목 리스트(체크 아이콘 + 텍스트)
- 푸터: 예상 시간/칼로리 메타 + "캘린더에 등록" 버튼 (Primary)

### 5.9 입력창 (Chat Input)

```css
background: var(--bg-elevated-2);
border: 1px solid var(--border-subtle);
border-radius: var(--radius-full);
padding: 12px 16px;
height: 48px;
```
- 좌측: + 버튼 (첨부)
- 중앙: placeholder `메시지를 입력하세요...`
- 우측: 전송 버튼 (활성 시 `--accent-secondary`)
- Focus: `border-color: var(--accent-primary)`, `box-shadow: 0 0 0 3px var(--accent-primary-glow)`

### 5.10 운동 이력 카드

가로 레이아웃:
- 좌: 카테고리 아이콘 (40x40 원형, 카테고리 컬러 배경)
- 중: 운동명(`--type-body`, weight 600) + 종목 요약(`--type-caption`, `--text-tertiary`)
- 우: 날짜 + 시간/볼륨 메타 (오른쪽 정렬, `--type-caption`)

---

## 6. 아이코노그래피

### 6.1 아이콘 라이브러리
- **권장**: `lucide_icons` (Flutter 패키지)
- 기본 크기: 16 / 20 / 24px
- 기본 stroke-width: 1.75px
- 색상: 텍스트 토큰을 따름 (기본 `--text-secondary`)

### 6.2 주요 아이콘 매핑

| 용도 | 아이콘 |
|------|--------|
| 일정 | `calendar` |
| 컨디션 | `heart-pulse` |
| 부위별 피로도 | `sparkles` |
| 운동 이력 | `clock` |
| 챗봇 | `bot` |
| 새 대화 | `message-square-plus` |
| 첨부 | `plus-circle` |
| 전송 | `send` |
| 지난주/다음주 | `chevron-left` / `chevron-right` |
| 운동: 상체 | `dumbbell` |
| 운동: 유산소 | `footprints` |
| 운동: 휴식 | `moon` |

### 6.3 일러스트레이션 / 마스코트
- AI 코치 아바타: 둥근 픽토그램형 로봇 (단일 컬러, 라인 기반)
- 빈 상태(Empty State): 라인 일러스트 + 시안 액센트 사용

---

## 7. 모션 / 인터랙션

### 7.1 트랜지션 토큰

| 토큰 | 값 | 용도 |
|------|-----|------|
| `--motion-fast` | 120ms | 호버, 컬러 변경 |
| `--motion-base` | 200ms | 기본 트랜지션 |
| `--motion-slow` | 320ms | 모달, 패널 진입/퇴장 |
| `--motion-easing` | `cubic-bezier(0.2, 0.8, 0.2, 1)` | 기본 이징 |

### 7.2 주요 인터랙션

#### 주차 이동 (지난주/다음주)
- 일정 카드 영역 fade out → 새 데이터 fade in (200ms)
- 슬라이드 인 효과는 사용하지 않음 (혼란 방지)
- 좌측 위젯들도 동일 타이밍에 동기화

#### 챗봇 응답 스트리밍
- 토큰 단위로 한 글자씩 fade-in (10ms 간격)
- 답변 종료 후 추천 카드는 250ms scale-up (0.95 → 1) + opacity (0 → 1)

#### 호버 / 포커스
- 카드 호버: 1px border 색상 전환 + 상승감 없는 미세 lighten
- 버튼 호버: brightness 1.1, 120ms

#### 글로우 펄스 (오늘 카드)
- `box-shadow` 의 alpha 값을 0.2 → 0.4 → 0.2로 4초 주기 변화 (선택 효과, 배터리/성능 옵션으로 끌 수 있어야 함)

### 7.3 사용하지 말 것
- 과한 패럴랙스, 의미 없는 페이지 단위 슬라이드
- 글자 단위 회전/탄성 애니메이션
- 3초 이상 지속되는 로딩 스피너 → 스켈레톤으로 대체

---

## 8. 접근성 (A11y)

### 8.1 색 대비
- 본문 텍스트: WCAG AA 기준 4.5:1 이상 (다크 배경 대비 흰색 텍스트는 충족)
- 액센트 컬러 위 텍스트는 `--text-on-accent` 사용
- 시맨틱 컬러는 색상만으로 정보 전달하지 않고 항상 라벨/아이콘 동반 (예: "양호" 텍스트 + 색상)

### 8.2 포커스 표시
```css
outline: 2px solid var(--accent-primary);
outline-offset: 2px;
border-radius: inherit;
```
- 모든 인터랙티브 요소에 가시적 포커스 링 제공
- 키보드 탭 순서: 헤더 → 일정 카드 → 위젯 → 챗봇 입력창

### 8.3 스크린 리더
- 차트는 동일한 정보를 텍스트로 제공 (`aria-label` 또는 인접한 데이터 테이블)
- 지난주/다음주 버튼: `aria-label="지난 주로 이동"` / `"다음 주로 이동"`
- 라이브 리전: 챗봇 응답 영역 `aria-live="polite"`

### 8.4 모션 감소 설정
- `prefers-reduced-motion: reduce` 환경에서 글로우 펄스, 스트리밍 fade를 즉시 표시로 대체

### 8.5 터치 영역
- 모바일에서 모든 탭 가능한 요소는 최소 44x44px 확보

---

## 9. 다크 / 라이트 테마

### 9.1 테마 전략
- 기본은 다크 모드 (서비스 정체성)
- 라이트 모드는 Phase 2에서 동일 토큰 명세를 light 변형으로 매핑

### 9.2 라이트 모드 매핑 (예시, Phase 2)

| 토큰 | Light HEX |
|------|-----------|
| `--bg-base` | `#F5F7FB` |
| `--bg-elevated-1` | `#FFFFFF` |
| `--bg-elevated-2` | `#EEF2F9` |
| `--text-primary` | `#0A0F1E` |
| `--text-secondary` | `#4A5468` |
| `--accent-primary` | `#0288D1` |
| `--border-subtle` | `#D9E0EE` |

---

## 10. 컴포넌트 매핑 (Flutter Web)

| 추상 컴포넌트 | Flutter 위젯 / 패키지 |
|---------------|----------------------|
| 페이지 레이아웃 | `Scaffold` + 커스텀 `Row`/`Column` |
| 카드 패널 | 커스텀 `Container` (`BoxDecoration`) |
| 도넛 차트 | `fl_chart` `PieChart` |
| 레이더 차트 | `fl_chart` `RadarChart` |
| 아이콘 | `lucide_icons` 패키지 |
| 글로우 효과 | `BoxDecoration.boxShadow` (다중 그림자) |
| 그라디언트 | `BoxDecoration.gradient` |
| 모션 | `AnimatedContainer`, `AnimatedOpacity` |
| 마크다운 채팅 메시지 | `flutter_markdown` |

### 10.1 토큰 적용 방법
- `lib/design/tokens/colors.dart`, `typography.dart`, `spacing.dart`, `radius.dart`, `shadows.dart` 로 분리 정의
- `ThemeData`의 `extensions`에 커스텀 테마 확장 등록
- 모든 위젯은 `Theme.of(context).extension<AppTokens>()`을 통해 토큰 접근

---

## 11. 디자인 QA 체크리스트

신규 화면/컴포넌트를 PR하기 전에 다음을 확인한다.

- [ ] 하드코딩된 색상값 없음 (모든 색상이 토큰 사용)
- [ ] 타이포 토큰 사용, 임의 font-size/weight 없음
- [ ] 간격 4px 그리드 준수
- [ ] 다크 모드 기준 콘트라스트 AA 충족
- [ ] 키보드 포커스 링 표시
- [ ] 모바일/태블릿/데스크톱 3개 브레이크포인트에서 확인
- [ ] 빈 상태 / 로딩 상태 / 에러 상태 디자인 포함
- [ ] `prefers-reduced-motion` 시 동작 확인
- [ ] 다국어 텍스트(한/영) 길이 차이로 깨지지 않음

---

## 12. 자산 및 배포

### 12.1 폰트
- Pretendard Variable: `https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.css`
- 로컬 폰트로 번들링하여 FOUT 최소화

### 12.2 아이콘
- `lucide_icons` Flutter 패키지 사용, 트리 셰이킹 적용

### 12.3 이미지
- 일러스트는 SVG 우선
- 라스터 이미지는 WebP, `1x/2x/3x` 변형 제공

---

## 13. 변경 이력

| 버전 | 일자 | 변경 |
|------|------|------|
| 0.1 | 2026.05.05 | 초기 디자인 시스템 정의 |

---

*문서 버전: 0.1*
*최종 수정일: 2026.05.05*
