# Coin Agent BE 문서 세트

> Binance Spot Testnet 전용 FastAPI 백엔드의 현재 구현 기준 문서 모음

## 문서 목적

이 문서 세트는 `autocoin-api` 저장소의 실제 구현 상태를 기준으로 공개 API, AI 연동, run/report 계약, 자연어 자동매매 세션 제어를 설명한다. 미래 계획이 아니라 **현재 동작하는 것만** 기준으로 유지한다.

## 현재 구현 범위 요약

- 수동 주문 run 시작 / resume / report 조회
- 자연어 auto order 1회 실행
- 연속 자동매매 세션 start / stop / status
- 잔고 / 현재가 / 호가 / 캔들 / stream 상태 조회
- 주문 상태 조회 / 취소
- AI 서비스와의 `/runs/start`, `/runs/agentic/start`, `/runs/resume`, `/runs/complete` 연동
- Binance Testnet deterministic 재검증 및 최종 제출

## 문서 읽는 순서

1. `README.md`
2. `api-spec.md`
3. `ARCHITECTURE.md`
4. `BE.md`
5. `AI.md`
6. `DATA.md`
7. `TEST_AND_DEMO.md`

## 문서별 역할

| 문서 | 역할 |
|---|---|
| `README.md` | 저장소 문서 진입점과 현재 구현 범위 |
| `api-spec.md` | 공개 HTTP API 계약 |
| `ARCHITECTURE.md` | FE/BE/AI/Binance 책임 경계 |
| `BE.md` | Backend 실행 권한, 재검증, submit 원칙 |
| `AI.md` | BE가 AI를 어떻게 호출하는지와 current constraints |
| `DATA.md` | 응답/상태/모델 명세 |
| `TEST_AND_DEMO.md` | 테스트와 데모 시나리오 |

## 구현 시 꼭 유지할 사실

- BE만 Binance를 직접 호출한다.
- `POST /orders` 와 `POST /orders/auto` 는 Binance 원본 응답이 아니라 run 중심 응답을 반환한다.
- 연속 자동매매 세션 loop 는 FE가 아니라 BE가 소유한다.
- auto-trading tick 은 live account/market snapshot 을 수집한 뒤 AI에 주입한다.
- agentic run resume 는 현재 지원되지 않는다.
