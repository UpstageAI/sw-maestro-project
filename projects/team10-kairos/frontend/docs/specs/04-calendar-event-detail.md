# 04. Calendar and Event Detail

## Goal

FastAPI에 저장된 일정을 사용자가 날짜 기준으로 확인하고, 단일 일정 상세를 볼 수 있게 한다.

## Data Loading

Calendar screen 진입 시 `GET /api/schedules`를 호출한다.

갱신 시점:

- Calendar 탭 focus
- ScheduleFlow 완료 후 “캘린더에서 보기”로 이동
- 사용자가 pull-to-refresh 실행

클라이언트는 서버 결과를 메모리 state로 보관한다. MVP에서는 별도 로컬 캐시는 만들지 않는다.

## Date Grouping

`start_at`을 `Asia/Seoul` 기준 날짜 key로 변환한다.

```ts
type DateKey = `${number}-${number}-${number}`; // YYYY-MM-DD
```

월간 캘린더는 현재 선택 월의 날짜만 보여준다.

표시 규칙:

- 일정이 있는 날짜에는 최대 3개 dot을 표시한다.
- 선택 날짜는 ink 배경 원으로 강조한다.
- 오늘 날짜는 선택되지 않았을 때 indigo outline 또는 작은 dot으로 표시한다.
- 선택 날짜 일정 목록은 시작 시간 오름차순이다.

## Calendar Screen

구성:

- 상단: `2026`, `5월 May`, 이전/다음 월 이동 버튼
- 월간 grid: 일-토 7열
- 선택 날짜 summary: 요일, 날짜, 일정 개수
- 일정 목록
- 빈 상태
- FAB 또는 primary action: “일정 만들기”

일정 row 표시:

- 시작 시간
- 일정명
- 장소 optional
- 알림 여부
- 방금 등록된 일정이면 `방금 등록` badge optional

빈 상태 문구:

- “이 날은 등록된 일정이 없어요.”
- action: “일정 만들기”

## Event Detail Screen

진입:

- Calendar 일정 row tap
- 완료 화면의 저장된 일정 card tap optional

데이터 조회:

- 현재 백엔드에는 `GET /api/schedules/{id}`가 없으므로, navigation param의 `scheduleId`로 Calendar state의 목록에서 찾는다.
- 앱 cold start로 상세에 직접 들어온 경우 목록을 다시 조회한 뒤 id로 찾는다.
- 찾지 못하면 “일정을 찾을 수 없어요.” 빈 상태를 표시하고 Calendar로 돌아가는 버튼을 둔다.

표시 필드:

- `Kairos가 등록` badge
- title
- 날짜
- 시간 range
- 장소
- 알림 시간
- 원래 입력 optional

시간 range:

- `end_at`이 있으면 `오후 6:00 - 8:00`
- `end_at`이 없으면 시작 시간만 표시

알림:

- `reminder_minutes === 0`: “시작 시간”
- `reminder_minutes > 0`: “N분 전”
- 값이 없으면 “알림 없음”이 아니라 기본 30분 전으로 표시한다. 저장 payload에서 기본값이 들어가므로 일반적으로 null은 없다.

## Out of Scope

- 상세 화면에서 일정 수정
- 일정 삭제
- 지도 열기
- 알림 추가
- 외부 캘린더 deep link

디자인에 edit icon과 “지도 보기”, “알림 추가” 텍스트가 있어도 MVP에서는 disabled visual 또는 미표시로 처리한다.

## Acceptance Criteria

- 저장된 일정이 월간 캘린더 날짜 dot으로 보인다.
- 날짜 선택 시 해당 날짜 일정만 보인다.
- 일정이 없는 날짜는 빈 상태가 보인다.
- 일정 row를 누르면 상세 화면으로 이동한다.
- 상세 화면에 제목, 날짜, 시간, 장소, 알림이 올바르게 표시된다.
- ScheduleFlow 완료 후 Calendar로 이동하면 새 일정 날짜가 선택되어 있다.
