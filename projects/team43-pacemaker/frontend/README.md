# frontend — AI 운동 코치 (Flutter Web)

> 43조 맞춤형 운동 스케줄링 에이전트의 웹 클라이언트.
> 슬라이스 분담·전체 컨텍스트는 루트 [`CLAUDE.md`](../CLAUDE.md)와 [`frontend/CLAUDE.md`](CLAUDE.md) 참고.

## 화면 구성

좌측 데이터 영역 (이번 주 일정 / 컨디션 점수 / 최근 운동 / 부위별 피로도) + 우측 AI 코치 채팅. 디자인 토큰·컴포넌트는 [`docs/design/DESIGN.md`](../docs/design/DESIGN.md) 단일 진실 소스.

## 빠른 시작

```bash
cd frontend
flutter pub get

flutter run -d chrome \
  --dart-define=SUPABASE_URL=https://<project>.supabase.co \
  --dart-define=SUPABASE_ANON_KEY=<anon-key>
```

`SUPABASE_URL`, `SUPABASE_ANON_KEY`는 팀 채널에서 공유. 코드/`.env`/셸 스크립트에 하드코딩 금지 — 컴파일 타임 `--dart-define`만 사용.

키 없이 실행하면 안내 화면(`_ConfigMissingPage`)으로 폴백한다.

## 디렉토리

```
frontend/
├── lib/
│   ├── main.dart                레이아웃 셸 (헤더 + 7:5 컬럼)
│   ├── env.dart                 --dart-define 주입
│   ├── api/
│   │   ├── calendar_api.dart    Supabase calendar_events 조회
│   │   ├── health_api.dart      Supabase health_snapshots 조회
│   │   └── workouts_api.dart    Supabase workout_records 조회
│   ├── models/                  schemas/models.py 와 1:1 매핑
│   │   ├── calendar_event.dart
│   │   ├── health_snapshot.dart
│   │   ├── workout_record.dart
│   │   └── muscle_fatigue_state.dart
│   ├── cards/
│   │   ├── card_panel.dart      공통 카드 패널 + Placeholder
│   │   ├── calendar_card.dart   이번 주 일정
│   │   ├── health_card.dart     컨디션 점수
│   │   ├── workouts_card.dart   최근 운동 이력
│   │   └── fatigue_radar_card.dart 부위별 피로도 레이더
│   ├── design/
│   │   ├── app_theme.dart       ThemeData + Pretendard
│   │   └── tokens/              colors/typography/spacing/radius/shadows
│   └── chat/                    ★ B 슬라이스 (박장우)
├── test/
│   ├── calendar_event_test.dart
│   ├── health_snapshot_test.dart
│   └── workout_record_test.dart
└── web/index.html               Pretendard CDN preconnect
```

## 데이터 계약

- **Supabase 직접 CRUD** — REST `/data/*` 없음. `supabase_flutter` SDK가 RLS·anon key로 직접 read.
- 테이블: `calendar_events`, `health_snapshots`, `workout_records` (스키마는 [`schemas/models.py`](../schemas/models.py)와 1:1)
- 컬럼명: Postgres 예약어 충돌 회피로 `start_at`/`end_at` 사용 (`schemas/models.py`도 동일). Dart 모델은 `startAt`/`endAt`로 카멜케이스 매핑.
- 도메인 모델은 `id: int?` 보유 — Supabase가 발급, 클라이언트 생성 시 `null`.
- SSE 채팅(`POST /agent/chat`)은 B 슬라이스(`lib/chat/`).

## 개발 워크플로

```bash
dart format --set-exit-if-changed .   # 포매팅
flutter analyze                        # 정적 분석 (0 issue 유지)
flutter test                           # 단위 테스트
flutter build web --no-tree-shake-icons \
  --dart-define=SUPABASE_URL=... --dart-define=SUPABASE_ANON_KEY=...
```

PR 단위는 디렉토리/카드 단위로 작게. 같은 파일을 여럿이 만질 때는 PR 코멘트로 머지 순서 합의.

## 디자인 가드

- 모든 색·타이포·간격은 `lib/design/tokens/`만 import — 하드코딩 금지
- `prefers-reduced-motion`, 키보드 포커스, 다크 콘트라스트 AA — DESIGN.md §8/§11 체크리스트 따름
- UI 텍스트는 한국어, 식별자·로그·주석은 영어

## 의존성

- `supabase_flutter` ^2.5 — Supabase SDK
- `intl` ^0.19 — 한국어 날짜·요일 포맷
- `lucide_icons` ^0.257 — 아이콘 시스템

## 인터페이스 변경 시

`schemas/models.py` · Supabase 테이블 컬럼 · SSE 청크 포맷을 바꿔야 하면 PR 제목에 `[interface-change]` 태그 + 5명 모두 react 후 머지.
