# 01. Expo App Foundation

## Goal

Expo React Native 앱을 새로 만들고, FastAPI와 통신할 수 있는 최소 구조를 준비한다.

## Project Setup

`frontend` 아래에 Expo 앱을 둔다. 현재 `frontend`에는 구현 파일이 없으므로 다음 형태를 기준으로 생성한다.

```text
frontend/
  app/
    App.tsx
    src/
      api/
      components/
      constants/
      navigation/
      screens/
      types/
      utils/
  docs/
```

권장 생성 명령:

```bash
cd frontend
npx create-expo-app@latest app --template blank-typescript
```

필수 패키지:

- `@react-navigation/native`
- `@react-navigation/bottom-tabs`
- `@react-navigation/native-stack`
- `react-native-safe-area-context`
- `react-native-screens`
- `expo-notifications`
- `expo-status-bar`

아이콘은 Expo 기본 흐름에 맞춰 `lucide-react-native` 또는 `@expo/vector-icons` 중 하나를 사용한다. MVP에서는 `lucide-react-native`를 우선 사용한다.

## Environment

`frontend/app/.env.example`을 둔다.

```env
EXPO_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
EXPO_PUBLIC_TIMEZONE=Asia/Seoul
```

API base URL 선택 규칙:

- `EXPO_PUBLIC_API_BASE_URL`이 있으면 그대로 사용한다.
- 없으면 개발 기본값 `http://127.0.0.1:8000`을 사용한다.
- Android emulator에서 테스트할 때는 `.env`를 `http://10.0.2.2:8000`으로 바꾼다.

## Types

`src/types/schedule.ts`에 백엔드 계약과 동일한 타입을 둔다.

```ts
export type ScheduleCandidate = {
  title: string | null;
  start_at: string | null;
  end_at: string | null;
  location: string | null;
  reminder_minutes: number | null;
};

export type AnalyzeScheduleResponse = {
  original_text: string;
  schedule: ScheduleCandidate;
  message: string;
};

export type ScheduleCreatePayload = {
  title: string;
  start_at: string;
  end_at?: string | null;
  location?: string | null;
  reminder_minutes: number;
  original_text?: string | null;
};

export type Schedule = {
  id: number;
  title: string;
  start_at: string;
  end_at: string | null;
  location: string | null;
  reminder_minutes: number;
  status: string;
};
```

## API Client

`src/api/schedules.ts`에 세 함수만 만든다.

- `analyzeSchedule(text: string): Promise<AnalyzeScheduleResponse>`
- `createSchedule(payload: ScheduleCreatePayload): Promise<Schedule>`
- `listSchedules(): Promise<Schedule[]>`

요구사항:

- 모든 요청은 JSON으로 통신한다.
- non-2xx 응답은 `Error`를 throw한다.
- 사용자에게 보여줄 문구는 screen layer에서 결정한다.
- API layer는 백엔드 `detail`이 있으면 error message에 포함한다.

## App Entry

`App.tsx`는 다음만 담당한다.

- navigation container 렌더링
- theme/provider 연결
- notification handler 초기화는 `05` spec에서 추가

비즈니스 상태는 `App.tsx`에 두지 않는다.

## Acceptance Criteria

- `npx expo start`로 앱이 실행된다.
- TypeScript compile error가 없다.
- `/health` 또는 `GET /api/schedules` 호출이 개발 환경에서 성공한다.
- API base URL을 `.env`에서 바꿀 수 있다.
