# Root Document Architecture Invariants

## 목적

이 문서는 Coin Agent root 문서 리뷰의 **최상위 판정 기준**이다. 다른 `.tools` 문서는 이 문서의 불변식을 재서술하지 않고 참조해야 한다.

## 적용 범위

- `README.md`
- `PROPOSAL.md`
- `SPEC.md`
- `ARCHITECTURE.md`
- `FE.md`
- `BE.md`
- `AI.md`
- `DATA.md`
- `TEST_AND_DEMO.md`

## Invariants

### INV-01 Testnet Only

- 시스템은 Binance Spot Testnet 전용이어야 한다.
- 실거래 URL, 실거래 키, 선물, 마진, 출금, 레버리지, 실거래 전환은 범위 밖이다.

### INV-02 BE Final Authority

- 최종 deterministic verdict는 BE만 가진다.
- 주문 제출, 취소, 상태 조회, signing, `timestamp`, `signature`, `X-MBX-APIKEY` 처리는 BE만 수행한다.

### INV-03 AI Proposal-Only Execution Boundary

- AI는 요청 구조화, policy grounding, risk gate, evaluator/reflection, 설명 가능한 trace 생성을 담당한다.
- AI의 `PASS`는 실행 승인이나 실행 완료가 아니다.
- AI는 Binance를 직접 호출하지 않는다.

### INV-04 READY_FOR_BE Semantics

- `READY_FOR_BE`는 AI 측 proposal이 BE 재검증 대기로 넘어간 상태다.
- 이 상태를 execution complete 또는 approval로 서술하면 위반이다.

### INV-05 BE_REJECTED Ownership

- `BE_REJECTED`는 BE deterministic revalidation 단계에서만 생성된다.
- AI, evaluator, FE가 이 상태의 생성 주체처럼 보이면 위반이다.

### INV-06 policy_context Grounding

- `policy_context`는 BE가 retrieval한 정책 artifact를 묶은 immutable grounding 컨텍스트다.
- AI는 retrieval된 정책을 해석할 수 있지만 새 정책을 만들거나 완화하지 않는다.

### INV-07 Rule Engine Boundary

- LLM은 이해, 구조화, 설명, 보류 판단을 돕는다.
- 룰 엔진은 파라미터 검증, 심볼 형식, 주문 타입 필드, `exchangeInfo` 기반 제약, 실거래 차단, BE 제출 직전 재검증을 담당한다.
- 문서는 LLM과 deterministic rule의 경계를 섞어 서술하면 안 된다.

### INV-08 HOLD and hold_reason Semantics

- `HOLD`는 lifecycle 상태다.
- `hold_reason`은 최소 `HOLD_REVIEW_REQUIRED`, `HOLD_DATA_INSUFFICIENT`로 원인을 세분화한다.
- `HOLD`와 `hold_reason`을 같은 층위로 혼동하면 위반이다.

### INV-09 run_id / Checkpoint / Resume Contract

- 모든 주문 테스트 run은 `run_id`로 식별한다.
- resume는 같은 `run_id`에 대해서만 허용된다.
- `request_context`, `policy_context`, 최초 `normalized_order_intent`, 이전 trace 같은 immutable 필드는 resume에서 덮어쓰지 않는다.

### INV-10 Cadence and Auditability

- canonical cadence는 request accepted, policy retrieval complete, policy complete, risk gate complete, evaluator complete, BE revalidation complete, final report ready 순서를 따른다.
- `HOLD`가 발생하면 cadence는 다음 단계로 진행하지 않고 대기한다.

### INV-11 Schema and Trace Reviewability

- 문서는 `decision_trace`, `verification_checks`, 이름 있는 schema, `run_summary` 같은 검토 가능한 산출물을 요구해야 한다.
- 자유 서술형 설명만 있고 검증 산출물이 없으면 약한 문서로 본다.

### INV-12 Distinguishable End States

- 최소한 `NO_ORDER`, `HOLD`, `BE_REJECTED`, `FAILED`, `REPORT_READY`는 서로 다른 의미로 유지되어야 한다.
- 테스트/데모 문서는 이 상태들을 구분 검증해야 한다.

## 리뷰 적용 규칙

- 어떤 root 문서도 위 불변식을 뒤집어 요약하면 안 된다.
- 상위 요약 문서는 세부를 줄일 수 있지만 의미를 바꾸면 안 된다.
- 더 구체적인 문서가 우선이지만, 요약 문서의 잘못된 표현도 결함으로 기록한다.

## 즉시 실패 트리거

- “AI가 최종 승인한다”
- “READY_FOR_BE는 실행 완료다”
- “BE_REJECTED는 AI 판단 결과다”
- “BE는 JSON만 전달한다”
- “policy_context는 AI가 만든다”

## 리뷰 시 인용 우선순위

1. `ARCHITECTURE.md`
2. `AI.md`
3. `BE.md`
4. `DATA.md`
5. `SPEC.md`
6. 나머지 문서
