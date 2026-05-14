# 05. Notifications and Permissions

## Goal

사용자 승인 후 저장된 일정에 대해 로컬 알림을 예약한다.

## Library

Expo 기준으로 `expo-notifications`를 사용한다.

초기 설정 위치:

- `App.tsx`: notification handler 설정
- `src/utils/notifications.ts`: 권한 요청, 알림 예약 함수

## Permission Flow

권한 요청 시점:

- 사용자가 첫 일정 등록을 승인하고 저장에 성공한 직후

동작:

- 이미 권한이 있으면 바로 알림 예약
- 권한이 없으면 permission prompt 요청
- 거부되면 완료 화면에 “일정은 저장됐지만 알림 권한이 꺼져 있어요.”를 표시

홈 진입 시 권한을 선요청하지 않는다.

## Scheduling Rule

저장 성공 후 `Schedule` 응답으로 알림 trigger를 계산한다.

```ts
triggerAt = new Date(schedule.start_at) - schedule.reminder_minutes * 60 * 1000
```

규칙:

- `reminder_minutes`가 null/undefined이면 30으로 처리한다.
- `triggerAt`이 현재 시각보다 과거이면 알림을 예약하지 않는다.
- 알림 예약 실패는 일정 저장 성공을 되돌리지 않는다.
- 예약 성공 여부를 완료 화면 상태에 반영한다.

알림 내용:

- title: `Kairos 일정 알림`
- body: `${schedule.title} 일정이 곧 시작돼요.`
- data: `{ scheduleId: schedule.id }`

## User Feedback

완료 화면 메시지:

- 예약 성공: “일정과 알림이 예약됐어요.”
- 권한 거부: “일정은 저장됐지만 알림 권한이 꺼져 있어요.”
- 예약 생략: “일정은 저장됐어요. 알림 시간이 지나 알림은 예약하지 않았어요.”
- 예약 실패: “일정은 저장됐지만 알림 예약에 실패했어요.”

## Platform Notes

iOS:

- 실제 알림은 simulator 제한이 있을 수 있으므로 실기기 테스트를 우선한다.

Android:

- Android 13 이상에서는 notification permission이 필요하다.
- Expo 개발 빌드/Expo Go 환경 차이를 문서화한다.

## Acceptance Criteria

- 저장 성공 후 알림 권한 요청이 발생한다.
- 권한 허용 시 미래 trigger 알림이 예약된다.
- 권한 거부 시 일정 저장은 유지되고 완료 화면에 알림 권한 안내가 표시된다.
- 과거 trigger는 예약하지 않고 완료 화면에서 알림 생략 상태를 표시한다.

