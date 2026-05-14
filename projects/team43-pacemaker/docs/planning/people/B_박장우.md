# B — 박장우 (Chat UI + Agent 통신 프로토콜)

## 한 줄 책임

Flutter Web 채팅 UI(SSE 스트림) + Agent 통신 프로토콜 정의. 메시지 디자인(폰트·이모티콘·말풍선) + `ChatChunk.type`별 payload 합의.

## 주 디렉토리·파일

- `frontend/lib/chat/` — 채팅 위젯, 입력창, SSE 클라이언트, 멀티턴 입력
- `backend/api/chat.py` — 스펙 합의(C와). 라우터는 C가 채움
- `schemas/models.py` — `ChatRequest`, `ChatChunk` 스키마 (C와 공동)

## 합의 (이미 락)

- **C와**: `ChatChunk.type` 5종(text/tool_call/proposal/done/error)별 payload 키 — `schemas/CLAUDE.md` 표에 박힘. 변경 시 `[interface-change]` PR.
- **A와**: 채팅 위젯이 차지하는 우측 폭/위치, 등록 버튼 노출 조건은 디자인 PR 코멘트로.

## 일자별 to-do

| 날짜 | 할 일 | 합격 기준 |
|---|---|---|
| **5/4 (월)** | `frontend/lib/chat/` 디렉토리 + 채팅 위젯 골격 PR / `ChatChunk` payload 표 초안 (`schemas/CLAUDE.md`에 적기) | 빈 채팅 위젯이 화면에 보임 |
| **5/5 (화)** | 채팅 입력→stub 응답 루프 / SSE 스트림 수신 골격 (`POST /agent/chat` 501 응답이라도 호출 흐름 검증) | 입력창에 친 메시지가 위젯에 거품으로 표시 |
| **5/6 (수)** | SSE `text` 청크 누적 표시 / `proposal` 청크 받으면 추천 슬롯 카드로 렌더 | C의 stub agent가 보낸 청크를 화면에 그려냄 |
| **5/7 (목)** | 멀티턴 입력창, `thread_id` 세션 보존 | 두 번째 메시지가 같은 thread로 전송 |
| **5/8 (금)** ★ | SSE 청크 5종 모두 화면 처리 / "캘린더에 등록" 버튼(F7) → D의 `POST /data/calendar` 호출 | 등록 버튼 클릭 시 일정 카드(F1)가 새 일정 표시 |
| **5/9 (토)** | 채팅 디자인 (말풍선, 이모티콘, 폰트), SSE 재연결 처리 | 데모 톤에 맞는 디자인, 네트워크 끊김 복구 |
| **5/10 (일)** | 데모 채팅 시나리오 5종 무사고 확인 | 데모 시나리오 1회 무사고 시연 |

## KPI 시나리오 — 본인 영향

- **4번** (멀티턴 재조정) — `thread_id` 보존, 응답 수신 흐름
- **5번** (추천 부위와 레이더 일치) — `proposal` 청크가 A의 레이더 위젯으로 잘 전달되는지

## 자주 볼 문서·CLAUDE.md

- `frontend/CLAUDE.md` ← `lib/chat/` 협업 영역
- `backend/CLAUDE.md` ← `/agent/chat` SSE 라우터 합의 포인트
- `agent/CLAUDE.md` ← `run_agent_stream`, `ChatChunk` 의미표
- `schemas/CLAUDE.md` ← `ChatRequest`/`ChatChunk` 스키마 (B 갱신 영역)
- `docs/spec/feature_spec.md` ← F4·F6·F7

## 흔한 함정

- SSE 스트림 파싱 — Flutter Web에서 `package:http`만으로는 부족. `package:dio` 또는 fetch로 byte stream 수신 후 `data:` 프레임 파싱
- `ChatChunk` 변경은 단독 결정 금지 — schemas/CLAUDE.md 갱신 + C와 합의
- 채팅 메시지 한국어, 코드/식별자 영어
- "stream까지 구현" — 토큰 단위 점진 표시 (text 청크 누적)가 핵심
