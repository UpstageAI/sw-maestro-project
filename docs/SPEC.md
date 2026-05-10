# autocoin-ai 제품/기능 명세

## 문서 목적

이 문서는 `autocoin-ai` 서브프로젝트의 최소 요구사항을 정의한다. Coin Agent 전체 문맥은 유지하되, 이 문서는 AI 계층이 무엇을 판단하고 무엇을 판단하지 않는지에 집중한다.

## 관련 문서

- 진입점과 배경 요약: `README.md`
- 이 문서: `SPEC.md`
- 책임 경계: `ARCHITECTURE.md`
- FE boundary 계약: `FE.md`
- BE boundary 계약: `BE.md`
- AI 계층 상세: `AI.md`
- 데이터 계약: `DATA.md`
- 테스트 기준: `TEST_AND_DEMO.md`

## 1. 목표

`autocoin-ai`의 목표는 Binance Spot Testnet 전용 Coin Agent에서 주문 테스트 요청을 정책 기준으로 해석하고, 리스크 게이트와 설명 가능한 결과를 제공하며, 같은 `run_id` 기준 resume 가능한 AI run을 보장하는 것이다.

## 2. 배경과 범위 압축

실거래 전 단계의 개인 사용자는 안전한 환경에서 현물 주문 흐름을 검증하고 싶어한다. 이 서브프로젝트는 그중 AI 계층만 분리해 다룬다. 따라서 전체 Coin Agent의 FE/BE 기능 명세를 다시 풀지 않고, AI가 받아야 할 입력, 남겨야 할 판단 근거, 지켜야 할 경계만 최소 범위로 정의한다.

## 3. 포함 범위

- 정책 기반 주문 테스트 해석
- `policy_context` grounding
- 리스크 게이트 판단
- evaluator 또는 reflection 성격의 재평가
- `decision_trace` 중심 설명 가능성
- `PASS`와 `READY_FOR_BE` 의미 분리
- `HOLD_REVIEW_REQUIRED`, `HOLD_DATA_INSUFFICIENT` 구분
- 동일 `run_id` 기준 checkpoint / resume 흐름
- 최종 상태와 리포트 생성 기준 정리

## 4. 제외 범위

- FE 화면 상세 명세
- BE REST API 전체 명세
- Binance 직접 서명, 제출, 취소 실행 로직
- 실거래, 선물, 마진, 출금, 레버리지
- Production host

## 5. 책임 경계 요약

| 계층 | 책임 | 하지 않는 일 |
|---|---|---|
| FE | 사용자 입력 수집, 상태 표시 | Binance 직접 호출, 서명, 실행 판단 |
| BE | 정책 retrieval, Binance Testnet 연동, deterministic 재검증, 최종 제출 | AI 판단을 실행 권한으로 간주 |
| AI | 정책 해석, 리스크 게이트, trace 생성, 결과 설명 | Binance 직접 호출, 최종 제출, 실거래 전환 |

## 6. 핵심 요구사항

| ID | 요구사항 |
|---|---|
| AI-FR-01 | 모든 AI run은 `run_id` 기준으로 추적 가능해야 한다. |
| AI-FR-01A | 최초 요청은 `request_context`와 주문 테스트 intent를 포함한 최소 FE→BE→AI 요청 계약으로 정규화되어야 한다. |
| AI-FR-02 | 정책 입력은 자유 문장만이 아니라 retrieval 가능한 artifact 집합으로 다루고 `policy_context`로 정리해야 한다. |
| AI-FR-03 | AI는 `decision_trace`에 최소한 `reason_codes`, `evidence_refs`, `final_action`을 남겨야 한다. |
| AI-FR-03A | 각 단계는 자신의 검증 결과를 `verification_checks`에 남겨 다음 단계와 FE/BE가 같은 기준으로 해석할 수 있어야 한다. |
| AI-FR-03B | `decision_trace`는 stage-keyed canonical container(`policy`, `risk`, `evaluator`, `execution`, `run_summary`)를 사용해야 한다. |
| AI-FR-04 | 보류 상태는 `hold_reason`으로 세분화해야 하며 최소 집합은 `HOLD_REVIEW_REQUIRED`, `HOLD_DATA_INSUFFICIENT`다. |
| AI-FR-05 | `PASS`는 최종 실행 승인 의미가 아니며, BE 재검증 전 proposal 상태로만 해석해야 한다. |
| AI-FR-05A | `READY_FOR_BE`는 AI-side proposal이 BE deterministic revalidation으로 handoff 되는 lifecycle 상태로 정의되어야 한다. |
| AI-FR-06 | BE 재검증 차단은 `BE_REJECTED`로 구분 기록해야 한다. |
| AI-FR-07 | 최종 사용자용 결과는 `REPORT_READY`, `NO_ORDER`, `BE_REJECTED`, `FAILED`, `HOLD` 흐름과 모순되면 안 된다. |
| AI-FR-08 | FE와 BE가 같은 필드명과 상태명을 쓸 수 있도록 `DATA.md` 기준 계약을 따라야 한다. |
| AI-FR-09 | FE 입력 boundary와 BE 실행 boundary는 각각 `FE.md`, `BE.md`에서 정의한 로컬 계약과 충돌하면 안 된다. |
| AI-FR-10 | BE가 AI에 되돌려 주는 completion payload는 `execution_result` 또는 `be_rejection_evidence`를 포함한 최소 계약으로 정의되어야 한다. |
| AI-FR-11 | AI는 사용자의 자연어 입력(`user_input.raw_text`)을 구조화된 주문 의도(`normalized_order_intent`)로 파싱하는 `intake` 노드를 가져야 한다. |
| AI-FR-12 | AI는 `trader_id` × `persona` 결정 행렬을 통해 트레이더 스타일과 페르소나를 결정해야 하며, 발화에서 명시 단어가 감지되면 `persona_override_reason`을 기록해야 한다. |
| AI-FR-13 | AI는 `knowledge/{trader_id}/principles.md`를 키워드 매칭 방식으로 검색해 관련 트레이더 원칙(`trader_principles`)을 `policy` 노드에서 retrieval해야 한다. |
| AI-FR-14 | AI는 `trader_principles`와 `persona_bounds`를 참고해 `llm_proposal`을 생성하는 `strategy` 노드를 가져야 한다. |
| AI-FR-15 | `risk_gate` 노드는 결정론 7단계 검증(conviction, size, symbol, balance, volatility, concentration)을 위→아래 단락 방식으로 수행해야 하며, 각 도구 호출을 `risk_tool_calls`에 기록해야 한다. |
| AI-FR-16 | `evaluator` 노드는 `FAILED`를 제외한 모든 lifecycle에서 항상 실행되어야 하며, `evaluator_review.user_message`와 `schema_warnings`를 포함한 최종 사용자 리포트를 생성해야 한다. |
| AI-FR-17 | `hold_reason` 최소 집합은 기존 `HOLD_REVIEW_REQUIRED`, `HOLD_DATA_INSUFFICIENT`에 더해 `HOLD_INPUT_AMBIGUOUS`, `HOLD_LOW_CONVICTION`, `HOLD_RISK_AGENT_FLAGGED`를 포함해야 한다. |

## 7. 비기능 요구사항

- Korean-first 문서와 설명을 유지한다.
- Testnet-only 엔드포인트만 사용한다.
- FE->BE->AI 경계와 BE의 최종 실행 권한을 흐리지 않는다.
- 루트 문서와 같은 canonical 상태명과 필드명을 유지한다.
- AI 중심 저장소이므로 FE/BE는 boundary context 수준에서만 언급한다.
- schema mismatch나 기술 실패는 조용히 흡수하지 않고 `FAILED` 또는 문서화된 보류 상태로 구분해야 한다.
- human QA와 정책별 rehearsal이 같은 상태명과 기대 결과로 반복 가능해야 한다.

## 8. 완료 기준

- `README.md`, `SPEC.md`, `ARCHITECTURE.md`, `AI.md`, `DATA.md`, `TEST_AND_DEMO.md`가 서로 교차 참조된다.
- `run_id`, `policy_context`, `decision_trace`, `hold_reason`가 같은 의미로 유지된다.
- `verification_checks`의 의미와 소유자가 문서 간 충돌 없이 유지된다.
- `request_context`, `execution_result`, `be_rejection_evidence`의 최소 shape가 문서 간 충돌 없이 유지된다.
- `decision_trace`가 stage-keyed canonical container로 일관되게 해석된다.
- `PASS`와 `READY_FOR_BE`의 역할이 문서 간 충돌 없이 유지된다.
- `HOLD_REVIEW_REQUIRED`, `HOLD_DATA_INSUFFICIENT`, `HOLD_INPUT_AMBIGUOUS`, `HOLD_LOW_CONVICTION`, `HOLD_RISK_AGENT_FLAGGED`, `BE_REJECTED`, `FAILED`, `REPORT_READY`, `NO_ORDER`가 문서 간 충돌 없이 사용된다.
- `trader_id`, `inferred_persona`, `trader_principles`, `llm_proposal`, `evaluator_review`가 같은 의미로 유지된다.
- `user_input.raw_text` 모드와 기존 dict 모드가 회귀 호환을 유지하며 공존한다.
- Testnet 전용 범위와 FE->BE->AI 경계가 모든 문서에서 유지된다.

## 9. 문서 세트 완료 조건

- 새 구현자는 root `.docs`를 보지 않아도 이 로컬 문서 세트만으로 FE, BE, AI 구현 순서와 handoff 계약을 해석할 수 있어야 한다.
- FE와 BE는 product scope 확장 없이 boundary-only 문서로 유지되어야 한다.
