# Kairos Schedule Agent Backend

자연어로 입력한 일정을 AI가 JSON 형태로 정리하고, 사용자가 확인한 일정을 로컬 SQLite에 저장하는 FastAPI 백엔드 초안입니다.

현재 목표는 프론트엔드에서 확인 카드/폼과 달력 화면을 붙일 수 있는 최소 API를 제공하는 것입니다.

## 구현된 범위

- FastAPI 서버 기본 구성
- Upstage `solar-pro3` API를 이용한 자연어 일정 분석
- LangGraph를 이용한 얇은 분석 흐름 구성
- 분석 결과를 프론트 폼에서 쓰기 쉬운 JSON으로 반환
- 부족한 정보 재질문을 위한 분석 컨텍스트 반환
- 사용자가 승인한 일정 SQLite 저장 / 수정 / 삭제 / 목록 조회
- **Google OAuth 2.0 인증** (Calendar 연동용 토큰 발급 및 저장)
- **Google Calendar 자동 동기화** (일정 생성/수정/삭제)
- **Google Calendar 알람** 연동 (`reminder_minutes` → Google reminders)
- **FreeBusy 조회** (공유 그리드에서 막힌 시간 자동 불가 처리)
- Swagger 문서 제공

## 아직 제외한 범위

- 로그인/회원 관리
- Apple Calendar 연동
- 모바일 푸시 알림
- 반복 일정
- 그룹 가용시간 그리드 (FreeBusy 데이터는 준비됨)
- WebSocket 실시간 동기화
- 복수 알람
- 이벤트 타입별 스마트 알림 기본값

## 폴더 구조

```text
backend/
  app/
    main.py                      # FastAPI 앱 진입점
    db.py                        # SQLite 연결
    models.py                    # DB 모델 (Schedule, GoogleCredential)
    schemas.py                   # 요청/응답 스키마
    routes/
      schedules.py               # 일정 API 라우터
      auth.py                    # Google OAuth 라우터
      availability.py            # FreeBusy 조회 라우터
    services/
      ai_parser.py               # Upstage API 호출
      schedule_graph.py          # LangGraph 분석 흐름
      schedule_service.py        # 일정 저장/조회 로직
      google_calendar.py         # Google Calendar API 연동
  requirements.txt
  .env.example
```

## 실행 방법

```bash
cd backend
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp .env.example .env
```

`.env`에 API 키를 입력합니다.

```env
UPSTAGE_API_KEY=여기에_키_입력
GOOGLE_CLIENT_ID=여기에_입력
GOOGLE_CLIENT_SECRET=여기에_입력
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
OAUTHLIB_INSECURE_TRANSPORT=1   # 로컬 개발 시에만
```

서버 실행:

```bash
.venv/bin/uvicorn app.main:app --reload
```

Swagger 문서: `http://127.0.0.1:8000/docs`

---

## API 요약

### `GET /health`

서버 상태 확인.

---

### Google OAuth (`/auth`)

#### `GET /auth/google?session_id=<uuid>`

Google 로그인 페이지로 redirect합니다. `session_id`는 클라이언트가 생성한 임의 UUID입니다.

#### `GET /auth/google/callback`

Google에서 돌아오는 콜백. 토큰을 DB에 저장합니다. 직접 호출하지 않아도 됩니다.

#### `GET /auth/status?session_id=<uuid>`

해당 세션의 Google Calendar 연동 여부를 반환합니다.

```json
{ "connected": true }
```

---

### 일정 (`/api/schedules`)

#### `POST /api/schedules/analyze`

자연어 입력을 AI가 일정 JSON으로 변환합니다.

요청:

```json
{
  "text": "내일 오후 3시에 치과 예약, 30분 전에 알려줘",
  "timezone": "Asia/Seoul",
  "analysis_context": null
}
```

응답:

```json
{
  "original_text": "내일 오후 3시에 치과 예약, 30분 전에 알려줘",
  "schedule": {
    "title": "치과 예약",
    "start_at": "2026-05-10T15:00:00+09:00",
    "end_at": null,
    "location": "치과",
    "reminder_minutes": 30,
    "schedule_type": "appointment"
  },
  "missing_fields": [],
  "needs_confirmation": true,
  "analysis_context": { "..." },
  "message": "아래 일정으로 등록할까요?"
}
```

`missing_fields`에 필드가 있으면 추가 질문 필요. 후속 답변 시 `analysis_context`를 그대로 다시 보냅니다.

#### `POST /api/schedules`

사용자가 확인한 일정을 저장합니다. `session_id`를 넣으면 Google Calendar에도 등록됩니다.

요청:

```json
{
  "title": "치과 예약",
  "start_at": "2026-05-10T15:00:00+09:00",
  "reminder_minutes": 30,
  "session_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

응답:

```json
{
  "id": 1,
  "title": "치과 예약",
  "start_at": "2026-05-10T15:00:00+09:00",
  "end_at": "2026-05-10T16:00:00+09:00",
  "location": null,
  "reminder_minutes": 30,
  "schedule_type": null,
  "google_event_id": "abc123xyz",
  "status": "confirmed"
}
```

`google_event_id`가 있으면 Google Calendar 등록 성공입니다. Google 실패 시에도 로컬 저장은 유지됩니다.

#### `GET /api/schedules`

저장된 일정 목록을 시작 시간 오름차순으로 반환합니다.

#### `PATCH /api/schedules/{id}`

일정을 부분 수정합니다. `session_id`를 포함하면 Google Calendar도 업데이트됩니다.

#### `DELETE /api/schedules/{id}?session_id=<uuid>`

일정을 삭제합니다. `session_id`가 있으면 Google Calendar에서도 삭제됩니다.

---

### 가용시간 (`/api/availability`)

#### `GET /api/availability`

Google Calendar FreeBusy API로 막힌 시간대를 조회합니다. 이벤트 내용은 반환하지 않으며 시간 범위만 반환합니다.

```
GET /api/availability
  ?session_id=<uuid>
  &time_min=2026-05-10T00:00:00%2B09:00
  &time_max=2026-05-17T00:00:00%2B09:00
```

응답:

```json
{
  "time_min": "2026-05-10T00:00:00+09:00",
  "time_max": "2026-05-17T00:00:00+09:00",
  "busy": [
    {
      "start": "2026-05-12T10:00:00+09:00",
      "end": "2026-05-12T11:00:00+09:00"
    },
    { "start": "2026-05-14T14:00:00+09:00", "end": "2026-05-14T15:30:00+09:00" }
  ]
}
```

---

## Google Calendar 연동 설정

1. [Google Cloud Console](https://console.cloud.google.com)에서 프로젝트 생성
2. **Google Calendar API** 활성화
3. **사용자 인증 정보** → OAuth 2.0 클라이언트 ID 생성 (웹 애플리케이션)
4. 승인된 리디렉션 URI에 `http://localhost:8000/auth/google/callback` 추가
5. `client_id`, `client_secret`을 `.env`에 입력
6. OAuth 동의 화면에서 테스트 사용자로 본인 Google 계정 추가

---

## 프론트엔드 연동 흐름

```text
[최초 1회] Google 연동
1. 클라이언트에서 UUID session_id 생성 후 저장
2. GET /auth/google?session_id=<uuid> → 브라우저로 열기
3. 로그인 완료 후 GET /auth/status 로 연동 확인

[일정 등록]
1. 자연어 입력
2. POST /api/schedules/analyze
3. 응답의 schedule로 확인 카드 표시, missing_fields 있으면 추가 질문
4. 사용자 확인 후 POST /api/schedules (session_id 포함)
5. GET /api/schedules 로 달력에 표시

[공유 그리드]
1. GET /api/availability 로 바쁜 시간대 조회
2. 해당 슬롯을 자동 '불가' 처리 (내용 비공개)
```

---

## 변경 이력

- 2026-05-09: Google OAuth, Calendar 동기화, FreeBusy 조회 추가
- 2026-05-08: 분석 응답에 `missing_fields`, `needs_confirmation`, `schedule_type` 추가
- 2026-05-08: 재질문 멀티턴용 `analysis_context` 추가
- 2026-05-08: 일정 수정/삭제 API 추가
- 2026-05-08: 일정 저장/수정 예외 검증 추가

---

## 알려진 한계

- 같은 시간에 중복 일정이 들어가도 막지 않음 (충돌 감지 미구현)
- 반복 일정 생성 미지원
- 현재 DB는 로컬 `schedules.db`. `.env`와 `schedules.db`는 Git에 올리지 않음
