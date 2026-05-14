# Root Document Architecture Review Rubric

## 목적

이 평가표는 Coin Agent root 문서들이 **현재 확정된 아키텍처 방향성**을 유지하는지 채점하기 위한 기준이다. 이 평가표의 핵심은 일반적인 문서 품질보다 **권한 경계, 상태 의미, grounding, deterministic 재검증, run contract**를 강하게 검사하는 것이다.

## 선행 기준 문서

채점 전에 반드시 아래를 본다.

1. `.tools/root-doc-architecture-invariants.md`
2. `ARCHITECTURE.md`
3. `AI.md`
4. `BE.md`

## 채점 방식

- 각 항목은 `0`, `1`, `2`점으로 평가한다.
- `0점`: 불변식 위반, 명백한 모순, 또는 핵심 누락
- `1점`: 방향은 맞지만 약하거나 불완전함
- `2점`: 명확하고 모순 없이 유지됨

총점은 참고용이다. 아래 **즉시 실패 조건**이 하나라도 있으면 총점과 무관하게 최종 평가는 `FAIL`이다.

## 즉시 실패 조건

- AI, evaluator, PASS가 최종 실행 승인처럼 서술됨
- `READY_FOR_BE`가 execution approval 또는 execution complete처럼 서술됨
- `BE_REJECTED`가 AI 생성 상태처럼 서술됨
- BE의 deterministic revalidation 또는 signing 권한이 지워짐
- `policy_context`가 BE retrieval 기반 immutable grounding이 아니게 서술됨
- `run_id`, checkpoint, resume, cadence의 핵심 의미가 다른 root 문서와 충돌함
- Production Binance URL, 실거래 키, 실거래 전환, 선물/마진/출금/레버리지 허용 표현 존재

## 평가 항목

| 항목 | 0점 | 1점 | 2점 |
|---|---|---|---|
| Testnet 전용성 | 실거래/production 문맥이 섞임 | Testnet 중심이나 금지 범위가 약함 | Testnet 전용 범위와 금지 항목이 분명함 |
| BE 최종 권한 유지 | AI/FE가 final authority처럼 보임 | BE 권한이 있으나 강조가 약함 | BE만 deterministic verdict, signing, submit 권한을 가짐 |
| AI 역할 분리 | AI가 실행 권한까지 가진 것처럼 보임 | AI 역할은 보이나 proposal/explanation 경계가 약함 | AI는 proposal, gating, explanation에 한정됨 |
| READY_FOR_BE 의미 정확성 | 실행 승인/완료처럼 서술됨 | 대기 상태로 보이나 표현이 모호함 | BE 재검증 대기 상태로만 일관되게 서술됨 |
| BE_REJECTED 의미 정확성 | 다른 실패 상태와 혼동되거나 AI 생성처럼 보임 | BE 차단 의미는 있으나 경계가 약함 | BE 재검증 단계 전용 상태로 명확히 구분됨 |
| Deterministic 재검증 명시성 | 재검증 항목이 없거나 AI PASS에 종속됨 | 재검증은 있으나 구체 규칙이 약함 | `exchangeInfo`, 잔고, signed-request 제약 등과 연결됨 |
| policy_context grounding | AI 임의 정책처럼 보임 | grounding은 있으나 retrieval/immutable 의미가 약함 | BE retrieval 기반 immutable grounding으로 명확함 |
| Run contract 정확성 | `run_id`, checkpoint, resume 의미가 흔들림 | 일부만 명확함 | same-run resume, immutable/patch 필드 경계가 유지됨 |
| Cadence / audit 추적성 | 단계 보고가 불명확함 | cadence는 있으나 BE revalidation 단계가 약함 | request accepted~BE revalidation complete~final report ready가 유지됨 |
| Trace / schema 검증성 | trace, schema, verification evidence가 없음 | 일부만 있음 | `decision_trace`, `verification_checks`, schema 이름이 검증 가능하게 연결됨 |
| 테스트 / 데모 재현성 | `HOLD_*`, `BE_REJECTED`, `FAILED` 분리 검증이 없음 | 일부 분기만 검증됨 | 주요 상태와 분기가 실제 QA/데모로 검증 가능함 |

## 문서별 기대치 매트릭스

| 문서 | 반드시 직접 명시해야 하는 것 | 절대 뒤집으면 안 되는 것 |
|---|---|---|
| `README.md` | Testnet 전용성, 핵심 용어 일관성 | AI가 최종 실행 권한처럼 보이는 요약 |
| `PROPOSAL.md` | 프로젝트 목적, Agent 개념, 실거래 배제 | BE 최종 verdict 경계 약화 |
| `SPEC.md` | action proposal vs BE 실행 권한, 수용 기준 | AI PASS를 실행 승인처럼 표현 |
| `ARCHITECTURE.md` | 책임 경계, runtime contract, cadence | BE-only authority 붕괴 |
| `FE.md` | 사용자에게 보이는 상태 구분, BE_REJECTED 표시 | FE가 Binance 직접 호출 주체처럼 보이는 표현 |
| `BE.md` | 재검증, signing, checkpoint, cadence 저장 | BE를 transport-only처럼 서술 |
| `AI.md` | proposal/gate/trace/run contract | AI가 직접 실행 또는 최종 verdict를 가진다는 표현 |
| `DATA.md` | schema, serialized contract, lifecycle 상태 | 상태 이름/의미 충돌 |
| `TEST_AND_DEMO.md` | 분기별 QA/데모 검증 | `BE_REJECTED`, `HOLD_*`, `FAILED` 혼동 |

## Red / Green 예시

### Red

- “AI가 조건을 만족하면 주문을 최종 승인한다.”
- “READY_FOR_BE는 주문 실행 완료 상태다.”
- “BE는 LangGraph 결과를 JSON으로 전달만 한다.”
- “policy_context는 AI가 요청을 보고 만든 정책 요약이다.”

### Green

- “AI의 PASS는 proposal 상태이며, 최종 verdict는 BE deterministic revalidation 이후에만 확정된다.”
- “READY_FOR_BE는 BE 재검증 대기 상태다.”
- “BE_REJECTED는 BE 재검증 단계에서만 생성된다.”
- “policy_context는 BE가 retrieval한 immutable grounding 컨텍스트다.”

## 총점 해석

- `19-22점`: PASS
- `13-18점`: REVISION REQUIRED
- `0-12점`: FAIL

단, 즉시 실패 조건이 있으면 최종 평가는 무조건 `FAIL`이다.

## 리뷰 출력 템플릿

```md
# Root Doc Architecture Scorecard

## Verdict
- PASS | REVISION REQUIRED | FAIL

## Immediate Fail Check
- 없음 | 있음: [항목]

## Invariant Coverage
| Invariant ID | 상태 | 근거 |
|---|---|---|

## Score Breakdown
| 항목 | 점수 | 근거 |
|---|---:|---|

## Total Score
- XX / 22

## Required Fixes
- 우선순위가 높은 수정부터 기록
```
