# 02. Design System and Navigation

## Goal

제공된 디자인의 Mist & Indigo Foundation을 React Native 컴포넌트와 navigation 구조로 옮긴다.

## Design Tokens

`src/constants/theme.ts`에 고정한다.

```ts
export const colors = {
  cream: "#eef0f3",
  cream2: "#e6e9ee",
  paper: "#ffffff",
  mist: "#dde0e6",
  line: "#dde0e6",
  line2: "#e4e7ec",
  ink: "#181a22",
  ink2: "#262a35",
  muted: "#6a6e7a",
  muted2: "#9aa0a8",
  faint: "#c1c5cc",

  indigo: "#3d4ed8",
  indigoPressed: "#2f3eb8",
  indigo50: "#e6e9ff",
  indigo100: "#c8cffc",
  indigoTint: "#dde2ff",

  // Legacy aliases kept because the design prototype still maps --coral to Indigo.
  coral: "#3d4ed8",
  coralPressed: "#2f3eb8",
  coral50: "#e6e9ff",
  coral100: "#c8cffc",
  coralTint: "#dde2ff",

  pink: "#c45a8b",
  pink50: "#fbeaf1",
  pink100: "#f3cedd",
  pinkTint: "#f7dde7",

  mint: "#c8d9d2",
  mintTint: "#e2ece8",
  sage: "#c8d9d2",
  sageTint: "#e2ece8",
  sky: "#c8d4e8",
  skyTint: "#e0e7f0",
  lilac: "#d8d2e8",
  lilacTint: "#ebe7f3",
  butter: "#d8d2e8",
  butterTint: "#ebe7f3",

  success: "#2e8a5e",
  warn: "#b97d2c",
  danger: "#c4392e",
  deadline: "#c45a8b",
};

export const darkColors = {
  cream: "#14151a",
  cream2: "#1b1d24",
  paper: "#1e2028",
  mist: "#262833",
  line: "#262833",
  line2: "#2c2f3a",
  ink: "#eceef3",
  ink2: "#c8ccd5",
  muted: "#8f93a0",
  muted2: "#6a6e7a",
  faint: "#3c3f4a",
  indigo: "#6c7cff",
  indigoPressed: "#5566ee",
  indigo50: "#1f223a",
  indigo100: "#2a3056",
  indigoTint: "#232846",
  coral: "#6c7cff",
  coralPressed: "#5566ee",
  coral50: "#1f223a",
  coral100: "#2a3056",
  coralTint: "#232846",
  pink: "#d97aa6",
  pink50: "#341d2a",
  pink100: "#4d2a3c",
  pinkTint: "#3d2333",
  mint: "#2f4a40",
  mintTint: "#1f2c28",
  sage: "#2f4a40",
  sageTint: "#1f2c28",
  sky: "#2c3a52",
  skyTint: "#1d2535",
  lilac: "#382f4a",
  lilacTint: "#241e30",
  butter: "#382f4a",
  butterTint: "#241e30",
};
```

Token usage rules:

- New code should prefer `indigo*` names for primary actions, links, active tab states, focus rings, and Agent highlights.
- Keep `coral*` aliases available while porting design code because the prototype maps those variables to Indigo.
- Use `pink`/`deadline` for deadline, urgent, destructive-adjacent, or warm-contrast schedule emphasis.
- Use `mint`, `sky`, and `lilac` for category dots/chips.
- Do not reintroduce the old warm cream/coral palette.

Typography:

- 기본 폰트는 시스템 폰트를 사용한다.
- 한국어 시각 품질 개선을 위해 추후 Pretendard를 추가할 수 있으나 MVP 필수는 아니다.
- 숫자 시간 표시는 `fontVariant: ["tabular-nums"]`를 사용한다.

Spacing/radius:

- 화면 좌우 padding: 18 또는 20
- 카드 radius: 16-24
- 버튼 radius: pill 또는 16-22
- bottom tab height는 safe area를 포함해 플랫폼 기본 감각을 유지한다.
- shadow color는 cool deep slate tone을 사용한다: `rgba(24,26,34,...)`.

## Shared Components

`src/components`에 아래 컴포넌트를 만든다.

- `KLogo`
- `IconButton`
- `PrimaryButton`
- `Chip`
- `AgentBubble`
- `AgentTag`
- `ThinkingDots`
- `ScheduleSummaryCard`
- `ScheduleRow`
- `MiniMonthCalendar`
- `EmptyState`
- `ErrorNotice`

구현 기준:

- 컴포넌트는 데이터 표시와 touch event props만 받는다.
- API 호출이나 navigation을 컴포넌트 내부에 넣지 않는다.
- 버튼 disabled/loading 상태를 지원한다.
- 모든 touch target은 최소 44px 높이를 목표로 한다.
- deadline 또는 마감 tag는 primary Indigo가 아니라 `deadline`/`pink` 색상을 사용한다.

## Navigation

`src/navigation`에 구성한다.

```text
RootStack
  MainTabs
    HomeTab -> HomeScreen
    CalendarTab -> CalendarScreen
  ScheduleFlowScreen
  EventDetailScreen
```

라우트 파라미터:

```ts
type RootStackParamList = {
  MainTabs: undefined;
  ScheduleFlow: { initialText?: string } | undefined;
  EventDetail: { scheduleId: number };
};

type MainTabParamList = {
  Home: undefined;
  Calendar: { selectedDate?: string } | undefined;
};
```

Bottom Tabs:

- 홈
- 캘린더

디자인에는 일정 탭과 내 정보 탭이 있지만 MVP에서는 제외한다.

## Screen Layout Rules

Home:

- 상단에 날짜와 큰 헤드라인을 표시한다.
- 자연어 입력 카드를 첫 화면 핵심 액션으로 둔다.
- 추천 입력 chip 3개를 표시한다.
- 오늘 일정 섹션은 `GET /api/schedules` 결과 중 오늘 일정만 보여준다.

ScheduleFlow:

- 대화형 screen으로 구현한다.
- 분석 중, 추가 질문, 확인, 완료, 실패 상태는 같은 screen 내 state machine으로 전환한다.

Calendar:

- 월간 grid와 선택 날짜 일정 목록을 한 화면에 표시한다.
- 일정이 없는 날짜는 빈 상태를 표시한다.

EventDetail:

- `Kairos가 등록` badge, title, 날짜/시간, 장소, 알림, 원래 입력을 표시한다.
- 현재 백엔드 목록 응답에는 `original_text`가 없으므로, 상세 화면에서는 `original_text` 표시 영역을 optional로 둔다.

## Acceptance Criteria

- iOS와 Android에서 safe area가 깨지지 않는다.
- Home, Calendar, EventDetail, ScheduleFlow 간 navigation이 동작한다.
- 디자인 토큰이 한 파일에서 관리된다.
- 공통 컴포넌트가 screen에 중복 구현되지 않는다.
