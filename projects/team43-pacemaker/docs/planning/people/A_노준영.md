# A — 노준영 (Flutter Web 프론트)

## 한 줄 책임

Flutter Web 대시보드 — 좌측 카드 3종(일정/컨디션/최근 운동) + 가운데 부위별 피로도 레이더. **Supabase SDK 직접 CRUD** + UI 조립.

## 주 디렉토리·파일

- `frontend/` 전체 (B의 `lib/chat/` 제외)
- `frontend/lib/main.dart` — 레이아웃, 라우팅
- `frontend/lib/cards/` — calendar / health / workouts / fatigue 위젯
- `frontend/lib/api/` — Supabase 클라이언트 래퍼
- `frontend/test/` — Dart 단위 테스트

## 합의 (이미 락)

- **D/E와**: Supabase 테이블 스키마 (`calendar_events`, `health_snapshots`, `workout_records`) = `schemas/models.py` Pydantic 모델 그대로. **변경 시 `[interface-change]` PR + 5명 react**.
- **B와**: `frontend/` 디렉토리 컨벤션 — B는 `lib/chat/` 안에서 작업, A는 그 외. 레이아웃 셸이 채팅 영역에 어떤 폭/위치를 줄지는 디자인 PR 코멘트로 합의.

## 일자별 to-do

| 날짜 | 할 일 | 합격 기준 |
|---|---|---|
| **5/4 (월)** | `cd frontend && flutter create .` 실행 / 빈 화면 1회 띄움 (`flutter run -d chrome`) / 첫 PR | 빈 Flutter Web 화면 떠 있음 |
| **5/5 (화)** | Supabase 프로젝트 생성 → **`SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY` 팀 채널에 공유 (전원이 .env에 채워야 함)** → `supabase_flutter` 초기화 + 좌측 카드 1종 더미 렌더 + `lib/api/getCalendar()` Supabase 쿼리 1개 | Supabase에서 조회한 데이터가 카드에 표시 |
| **5/6 (수)** | 좌측 카드 3종 + 가운데 피로도 레이더 모두 Supabase 실데이터 연동 | 좌·중앙 4종 위젯이 Supabase 실데이터로 갱신 |
| **5/7 (목)** | 카드 로딩/에러 상태, 색상 단계화 (피로도 0=초록 → 5=빨강) | 네트워크 지연/501 에러 시 UI 깨지지 않음 |
| **5/8 (금)** ★ | 화면 전체 조립, BE 실연결 검증 | 채팅에 "이번 주 운동 추천해줘" → 카드 3종 + 추천 슬롯 + 레이더 모두 출력 |
| **5/9 (토)** | 화면 폴리싱 (여백, 폰트, 색맹 친화), 로딩/에러 표시 | 디자인 톤이 `docs/design/*.png`와 일치 |
| **5/10 (일)** | 데모 화면 최종 점검 (해상도, 컬러, 로딩) | 데모 시나리오 무사고 시연 |

## KPI 시나리오 — 본인 영향

- **5번** (추천 부위와 FE 레이더 색상 일치) — 레이더 위젯이 `MuscleFatigueState.fatigue`를 색으로 정확히 변환하는지

## 자주 볼 문서·CLAUDE.md

- `frontend/CLAUDE.md` ← 본인 슬라이스
- `schemas/CLAUDE.md` ← Supabase 테이블 스키마 / 모델 정의
- `data/CLAUDE.md` ← Supabase 테이블명 + 시딩 방법
- `docs/spec/feature_spec.md` ← F1·F2·F3·F5 수용 기준
- `docs/design/ChatGPT Image *.png` ← 디자인 레퍼런스

## 흔한 함정

- Supabase 데이터가 없어도 UI 로딩 상태로 화면을 먼저 그릴 것 (mock-first)
- `flutter create .` 실행 시 기존 `CLAUDE.md`와 `.gitkeep`은 보존됨 (덮어쓰지 않음)
- UI 텍스트는 한국어, 식별자·로그는 영어
- Supabase anon key는 RLS 정책 전제 — 테이블 권한(SELECT/INSERT/UPDATE/DELETE) 설정 확인
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`는 `.env`에서 읽어야 함 (하드코딩 금지)
