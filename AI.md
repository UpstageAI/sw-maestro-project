# Coin Agent AI 서비스 명세

## 문서 목적

이 문서는 AI 계층의 실제 구현 형태와 canonical 책임 경계를 정의한다. 기준은 stateful run orchestration, fail-closed, execution authority 분리다.

## 1. AI의 역할

AI는 주문 테스트 요청을 구조화하고, 정책과 리스크를 근거로 보류 또는 진행 제안을 만들고, 실행 후 결과 설명을 보강한다. 하지만 실제 주문 제출 권한은 없다.

## 2. 권한 경계

- AI는 Binance를 직접 호출하지 않는다.
- AI는 Binance 요청에 서명하지 않는다.
- AI는 API Key, Secret, signature를 다루지 않는다.
- AI는 실행 승인자가 아니다.
- BE만 실행 승인과 제출을 수행한다.

## 3. 현재 구현 형태

- AI는 standalone HTTP 서비스다.
- 공개 엔드포인트는 `/runs/start`, `/runs/resume`, `/runs/complete` 다.
- 현재 기본 run 저장소는 로컬 JSON 파일 기반이다.
- 같은 저장소 파일을 유지하는 한 프로세스 재시작 이후에도 non-agentic run 상태를 다시 읽을 수 있다.
- 현재 구현에는 `/runs/agentic/start` 엔드포인트도 존재한다.

## 4. AI HTTP 계약

### `POST /runs/start`

입력:

- `run_id`
- `request_context`
- `policy_context`

출력:

- 전체 agent state
- 최소 `lifecycle_status`, `decision_trace`, `verification_checks`, `hold_reason`, `report`

### `POST /runs/resume`

입력:

- `run_id`
- `resume_reason`
- `patch_fields`

출력:

- 같은 `run_id` 의 새 agent state

### `POST /runs/complete`

입력:

- `run_id`
- `completion_payload`

출력:

- completion 반영 후 agent state

## 5. `policy_context` 의 canonical 의미

`policy_context` 는 BE가 조합해 AI에 주입하는 grounding 입력이다. 현재 구현 기준에서 AI는 이 객체를 받아 해석한다. AI가 정책 아티팩트를 내부에서 직접 조회해 완성하는 구조로 문서화하면 안 된다.

즉, 현재 canonical 문장은 다음과 같다.

- 정책 retrieval과 조합 책임은 BE에 있다.
- AI는 주입된 `policy_context` 를 해석하고 trace에 반영한다.

## 6. 상태 모델 핵심 필드

- `run_id`
- `request_context`
- `policy_context`
- `normalized_order_intent`
- `lifecycle_status`
- `hold_reason`
- `decision_trace`
- `verification_checks`
- `completion_payload`
- `execution_result`
- `be_rejection_evidence`
- `report`
- `resume_history`
- `decision_trace_history`

## 7. canonical 상태 의미

| 상태 | 의미 |
|---|---|
| `RECEIVED` | run 수신 |
| `NORMALIZING` | 의도 정규화 중 |
| `RISK_REVIEW` | 리스크 판단 중 |
| `HOLD` | 승인 또는 추가 데이터 필요 |
| `READY_FOR_BE` | AI 기준 통과, BE 재검증 대기 |
| `BE_REJECTED` | BE가 최종 차단 |
| `REPORT_READY` | 결과 보고 준비 완료 |
| `NO_ORDER` | 주문 미생성 종료 |
| `FAILED` | 기술 실패 또는 복구 불가 |

## 8. resume의 실제 구현 의미

현재 구현에서 resume는 다음처럼 동작한다.

1. 기존 run 상태를 현재 run 저장소에서 읽는다.
2. 현재 상태가 `HOLD` 인지 확인한다.
3. `resume_history` 에 `resume_reason`, `patch_fields` 를 추가한다.
4. `decision_trace_history` 에 재개 직전 trace와 check 개수를 저장한다.
5. 그 상태를 다시 `start()` 경로로 실행한다.

이 동작에서 중요한 사실은 두 가지다.

- 이전 이력은 보존된다.
- 재개 후 현재 `decision_trace` 와 현재 `verification_checks` 는 재계산되어 overwrite될 수 있다.

따라서 현재 구현의 resume는 append-only current trace 모델이 아니다. 과거 상태는 history로 보존하고, 현재 상태는 새 계산 결과로 덮어쓴다.

추가 제약도 있다.

- 현재 MVP 구현에서 agentic run resume 는 지원하지 않는다.
- 현재 공개 BE 주문 흐름에서 사용하는 resume 는 non-agentic run 을 기준으로 동작한다.

## 9. completion의 실제 구현 의미

- `complete()` 는 `READY_FOR_BE` 상태에만 허용된다.
- BE가 주입한 `execution_result` 또는 `be_rejection_evidence` 를 기반으로 completion graph를 실행한다.
- 최종 상태는 보통 `REPORT_READY` 로 수렴한다.

## 10. 문서화 시 금지할 오해

- AI가 Binance 주문을 직접 넣는다고 쓰면 안 된다.
- AI가 Binance 서명을 생성한다고 쓰면 안 된다.
- AI가 정책 아티팩트를 내부 시스템에서 스스로 회수한다고 쓰면 안 된다.
- resume가 이전 trace를 그대로 누적 유지한다고 단순화하면 안 된다. 현재 trace는 재계산된다.

## 11. 현재 구현 메모

- AI 서비스는 public BE API가 아니라 내부 서비스 역할이지만, 별도 HTTP 프로세스다.
- 현재 risk/account/policy tool 호출은 로컬 mock 데이터 기반 평가를 포함한다.
- 오류는 HTTP 400 또는 404 성격으로 매핑될 수 있다.
- 같은 `run_id` 로 `FAILED` run 을 resume 할 수 없다.
- 같은 `run_id` 로 `HOLD` 가 아닌 run 을 resume 할 수 없다.
