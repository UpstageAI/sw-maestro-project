# Kairos MVP Implementation Specs

## Purpose

이 폴더는 Kairos MVP를 Expo React Native 앱과 기존 FastAPI 백엔드로 구현하기 위한 단계별 작업 spec을 정의한다.

기준 자료:

- PRD: `frontend/docs/product/PRD.md`
- 기획서: `frontend/docs/product/project-plan.md`
- 백엔드 API: `backend/README.md`
- 디자인 참고: Claude 디자인 URL의 Kairos 모바일 앱 화면, Foundation Palette B `Mist & Indigo`

## Implementation Order

1. `01-expo-app-foundation.md`
   - Expo 앱 스캐폴딩, 앱 실행 구조, API base URL, 기본 타입을 만든다.
2. `02-design-system-navigation.md`
   - 디자인 토큰, 공통 UI 컴포넌트, Bottom Tabs와 Stack 흐름을 만든다.
3. `03-agent-schedule-flow.md`
   - 홈 입력부터 분석, 추가 질문, 등록 확인, 저장, 완료/실패까지 Agent 흐름을 구현한다.
4. `04-calendar-event-detail.md`
   - 저장된 일정을 월간 캘린더, 선택 날짜 목록, 상세 화면에 표시한다.
5. `05-notifications-permissions.md`
   - 로컬 알림 권한 요청과 일정 등록 후 알림 예약을 연결한다.
6. `06-mvp-verification.md`
   - 데모 입력과 수동 QA 기준으로 MVP 완성도를 검증한다.

## MVP Scope

포함:

- Expo 기반 React Native 모바일 앱
- 홈 화면의 자연어 일정 입력
- Agent 상호작용 상태: 분석 중, 추가 질문, 등록 확인, 완료, 실패
- FastAPI 연동: 일정 분석, 저장, 목록 조회
- 월간 캘린더와 선택 날짜 일정 목록
- 일정 상세 화면
- 로컬 알림 권한 요청과 알림 예약

제외:

- 로그인/회원 관리
- 일정 수정/삭제
- 반복 일정
- Google Calendar, Apple Calendar 실제 계정 연동
- 음성 입력
- 장기 메모리 기반 개인화
- 설정 화면 전체 구현
- 별도 일정 탭 전체 구현

## Shared Product Rules

- UI foundation은 Mist & Indigo를 기준으로 한다. Primary accent는 Indigo, deadline/urgent emphasis는 Pink를 사용한다.
- 사용자 승인 전에는 `POST /api/schedules`를 호출하지 않는다.
- `start_at`이 없거나 사용자가 이해하기 어려운 날짜 표현이면 등록 확인으로 넘기지 않는다.
- `reminder_minutes`가 없으면 앱에서 기본값 30분을 적용하되, 등록 확인 카드에 기본 알림임을 표시한다.
- `end_at`이 없으면 백엔드가 1시간 기본 duration으로 저장한다.
- 모든 날짜/시간 표시 기준 timezone은 `Asia/Seoul`이다.
- Agent 문구는 간결하게 유지하고, 애매한 정보는 추측해서 저장하지 않는다.

## Backend Contract

Base URL은 Expo 환경 변수로 관리한다.

- 로컬 iOS simulator: `http://127.0.0.1:8000`
- Android emulator: `http://10.0.2.2:8000`
- 실기기 테스트: 개발 머신의 LAN IP 사용

API:

- `GET /health`
- `POST /api/schedules/analyze`
- `POST /api/schedules`
- `GET /api/schedules`

클라이언트는 API 실패를 사용자에게 실패 상태로 표시하고, 콘솔에 원본 error를 남긴다.
