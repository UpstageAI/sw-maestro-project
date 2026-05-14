# 03. Agent Schedule Flow

## Goal

사용자가 자연어로 입력한 일정을 Agent 흐름으로 분석하고, 등록 전 확인을 거친 뒤 FastAPI에 저장한다.

## State Machine

`ScheduleFlowScreen`은 다음 상태만 가진다.

```ts
type FlowStatus =
  | "idle"
  | "analyzing"
  | "needsInput"
  | "confirming"
  | "saving"
  | "done"
  | "failed";
```

상태 전환:

- `idle` -> 사용자가 텍스트 제출 -> `analyzing`
- `analyzing` -> 필수값 충분 -> `confirming`
- `analyzing` -> `title` 또는 `start_at` 부족 -> `needsInput`
- `analyzing` -> API 실패 또는 해석 불가 -> `failed`
- `needsInput` -> 사용자 답변 제출 -> 기존 입력과 답변을 합쳐 다시 `analyzing`
- `confirming` -> 등록하기 -> `saving`
- `saving` -> 저장 성공 -> `done`
- `saving` -> 저장 실패 -> `failed`
- 취소 -> `MainTabs/Home`

## Required Field Rules

등록 확인으로 넘어가기 위한 최소 조건:

- `title`이 비어 있지 않다.
- `start_at`이 ISO datetime으로 존재한다.

추가 질문 규칙:

- `start_at`이 없으면 “몇 월 며칠, 몇 시 일정인가요?”를 묻는다.
- 날짜는 있으나 시간이 없다고 판단되는 경우 “몇 시 일정인가요?”를 묻는다.
- `title`이 없으면 “일정 이름을 어떻게 적을까요?”를 묻는다.

현재 백엔드는 missing field 배열을 내려주지 않으므로 앱은 `schedule`의 null 필드를 기준으로 판정한다.

## Input Composition

추가 답변을 다시 분석할 때는 원문과 답변을 합쳐 보낸다.

예:

```text
원래 입력: 내일 병원 가는 거 알림 맞춰줘.
추가 답변: 오후 3시
```

재분석 요청 text:

```text
내일 병원 가는 거 알림 맞춰줘. 추가 정보: 오후 3시
```

## Screens and UI

Home에서 시작:

- 자연어 입력 카드에 multiline input을 둔다.
- 입력이 비어 있으면 제출 버튼 disabled.
- 추천 chip을 누르면 해당 문구를 입력값에 채운다.
- 제출 시 `ScheduleFlow`로 이동하면서 `initialText`를 넘긴다.

ScheduleFlow:

- 사용자 입력 bubble을 먼저 표시한다.
- `analyzing`: `Kairos · 입력 분석 중`, thinking dots, 추출 정보 preview를 표시한다.
- `needsInput`: Agent 질문, quick reply chip, 답변 input을 표시한다.
- `confirming`: Agent 문구 “아래 내용으로 등록할까요?”, `ScheduleSummaryCard`, 수정/등록 버튼을 표시한다.
- `saving`: 등록 버튼 loading, 중복 submit 방지.
- `done`: “등록했어요”, 저장된 일정 요약, “캘린더에서 보기”, “일정 하나 더 만들기” 버튼.
- `failed`: 실패 사유, 다시 입력 action, 홈으로 돌아가기 action.

## Confirm Payload

`confirming`에서 저장 payload를 만든다.

```ts
const payload = {
  title: candidate.title.trim(),
  start_at: candidate.start_at,
  end_at: candidate.end_at,
  location: candidate.location,
  reminder_minutes: candidate.reminder_minutes ?? 30,
  original_text: originalText,
};
```

사용자가 `수정`을 누르면 inline edit form을 표시한다.

MVP 수정 가능 필드:

- 제목
- 시작 일시
- 장소
- 알림 분

수정 form은 저장 전 확인 카드 안에서만 제공한다. 저장된 일정 수정은 MVP 제외다.

## Error Handling

분석 실패:

- 문구: “일정 분석 중 문제가 발생했어요. 잠시 후 다시 시도해주세요.”
- action: 다시 시도, 홈으로

필수값 누락:

- 실패가 아니라 `needsInput`으로 처리한다.

저장 실패:

- 문구: “일정을 저장하지 못했어요. 네트워크 상태를 확인하고 다시 시도해주세요.”
- action: 다시 등록, 홈으로

## Acceptance Criteria

- “이번 주 토요일 오후 6시에 홍대에서 친구 만나. 1시간 전에 알려줘.” 입력 시 확인 카드까지 이동한다.
- “내일 병원 가는 거 알림 맞춰줘.” 입력 시 추가 질문 상태가 표시된다.
- 추가 답변 “오후 3시” 입력 후 확인 카드까지 이동한다.
- 등록하기 전에는 저장 API가 호출되지 않는다.
- 등록 성공 후 완료 화면이 표시된다.
- 완료 화면의 “캘린더에서 보기”는 Calendar 탭으로 이동하고 해당 날짜를 선택한다.

