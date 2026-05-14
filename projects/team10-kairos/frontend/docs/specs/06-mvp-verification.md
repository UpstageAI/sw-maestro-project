# 06. MVP Verification

## Goal

PRD의 데모 성공 기준을 기준으로 Expo 앱, FastAPI 연동, Agent 흐름, 캘린더 표시, 알림 예약을 검증한다.

## Prerequisites

Backend:

```bash
cd backend
.venv/bin/uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend/app
npx expo start
```

환경:

- `EXPO_PUBLIC_API_BASE_URL`이 실행 대상에 맞게 설정되어 있어야 한다.
- 백엔드 `.env`에 Upstage API key가 있어야 한다.
- 테스트 기기의 timezone은 `Asia/Seoul` 기준으로 본다.

## Demo Scenarios

### Scenario 1: 완전한 일정 입력

입력:

```text
이번 주 토요일 오후 6시에 홍대에서 친구 만나. 1시간 전에 알려줘.
```

기대 결과:

- 분석 중 상태가 보인다.
- 등록 확인 카드에 제목, 날짜, 시간, 장소, 알림이 표시된다.
- 등록하기 전까지 저장 API가 호출되지 않는다.
- 등록 후 완료 화면이 보인다.
- 캘린더에서 해당 날짜 일정으로 보인다.

### Scenario 2: 시간 누락 입력

입력:

```text
내일 병원 가는 거 알림 맞춰줘.
```

추가 답변:

```text
오후 3시
```

기대 결과:

- 추가 질문 상태가 보인다.
- 답변 후 다시 분석된다.
- 최종 확인 카드로 이동한다.
- 승인 후 저장된다.

### Scenario 3: 마감 일정

입력:

```text
금요일 자정까지 과제 제출
```

기대 결과:

- 제목은 과제 제출 의미로 표시된다.
- 날짜와 시간이 자정 기준으로 구조화된다.
- 알림이 없으면 기본 30분 전으로 표시된다.
- 승인 후 저장되고 캘린더에서 확인된다.

### Scenario 4: 일반 회의 일정

입력:

```text
다음 주 월요일 오전 10시 회의
```

기대 결과:

- 제목, 날짜, 시간 추출이 성공한다.
- 장소가 없어도 확인 카드로 이동한다.
- 알림은 기본 30분 전으로 표시된다.

## Manual QA Checklist

Home:

- 빈 입력은 제출되지 않는다.
- 추천 chip을 누르면 입력값이 채워진다.
- 오늘 일정 섹션이 API 목록과 맞는다.

Agent Flow:

- 분석 중에는 input이 중복 제출되지 않는다.
- 추가 질문 답변은 원문 맥락과 합쳐 재분석된다.
- 수정 form에서 필수값이 비면 등록 버튼이 disabled 된다.
- 취소하면 홈으로 돌아간다.

Calendar:

- 월 이동이 가능하다.
- 날짜 dot과 선택 날짜 목록이 일치한다.
- 빈 날짜는 빈 상태를 보여준다.
- 새로 등록된 일정은 다시 조회 후 표시된다.

Notifications:

- 권한 허용, 거부, 과거 trigger를 각각 확인한다.
- 알림 실패가 일정 저장 성공을 막지 않는다.

Error Cases:

- 백엔드 서버가 꺼져 있으면 실패 상태가 표시된다.
- 분석 API 502는 사용자 친화 문구로 표시된다.
- 저장 API 500은 다시 등록 action을 제공한다.

## Definition of Done

- 위 demo scenarios가 모두 통과한다.
- TypeScript error가 없다.
- Expo 앱이 iOS simulator 또는 Android emulator 중 하나 이상에서 실행된다.
- FastAPI Swagger의 API와 RN client payload가 일치한다.
- 사용자 승인 없는 저장 호출이 없다.
- 새 일정이 등록 완료 후 Calendar와 EventDetail에 표시된다.
