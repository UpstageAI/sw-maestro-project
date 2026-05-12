# AI 문서 리뷰 업데이트 — 최신 Coin Agent 문서 기준

> 검토 대상: `README.md`, `PROPOSAL.md`, `SPEC.md`, `ARCHITECTURE.md`, `AI.md`, `DATA.md`, `FE.md`, `BE.md`, `TEST_AND_DEMO.md`
> 검토 기준: 현재 저장소의 **Binance Spot Testnet 전용 Coin Agent** 범위와 문서 간 정합성
> 한 줄 결론: **기존 `feedback-ai.md`의 "agentic이 아니다"라는 비판은 현재 문서 세트 기준으로는 그대로 유지되기 어렵다.** 최신 문서는 이미 상태 기반 오케스트레이션, 권한 경계, fail-closed, BE 재검증, 구조화 trace 방향을 명시하고 있으며, 현재의 핵심 이슈는 "agentic 부재"보다 **구현 계약의 구체성 부족**에 가깝다.

---

## 문서 목적

이 문서는 과거 루트에 있던 `feedback-ai.md`를 최신 문서 기준으로 다시 정리한 버전이다.
기존 문서는 Upbit 중심 예시와 과거 설계 전제를 포함하고 있어, 현재 저장소의 Binance Spot Testnet 문맥 및 최신 `AI.md`와 직접 맞지 않는 부분이 있었다.

따라서 이 문서는 다음 두 가지를 분리해 기록한다.

1. **이미 최신 문서에서 해소된 비판**
2. **여전히 남아 있는 명세 수준의 부족점**

---

## 관련 문서

- 상위 기획: `PROPOSAL.md`
- 요구사항: `SPEC.md`
- 시스템 구조: `ARCHITECTURE.md`
- AI 구현 기준: `AI.md`

---

## 1. 기존 피드백에서 현재 기준으로 수정해야 하는 점

기존 `feedback-ai.md`는 다음 전제를 깔고 있었다.

- 설계가 Upbit 시세 조회 중심이다.
- LLM이 단순 직렬 파이프라인에서만 동작한다.
- shared state, 상태 전이, trace 계약이 거의 없다.
- AI는 설명만 하고 구조적 판단 책임이 없다.

하지만 현재 루트 문서 세트는 이미 이 전제에서 벗어나 있다.

### 1.1 거래소/도메인 전제가 바뀌었다

현재 저장소 전체의 기준은 **Binance Spot Testnet only**다.
기존 피드백 문서에 남아 있던 Upbit 예시, Upbit tool naming, Upbit 기준 실행 논의는 최신 기준 문서와 맞지 않는다.

따라서 앞으로 feedback 문서는 반드시 다음 기준을 유지해야 한다.

- Binance Spot Testnet 문맥을 기준으로 검토한다.
- 실거래, 선물, 마진, 출금 같은 범위 외 기능을 비판 축으로 삼지 않는다.
- "왜 이 문서가 현재 문서 세트와 어긋나는지"를 저장소 기준 용어로 설명한다.

### 1.2 "단순 일직선 파이프라인" 비판은 현재 문서에 그대로 적용되지 않는다

현재 `AI.md`와 `ARCHITECTURE.md`는 다음 요소를 이미 명시한다.

- `AI Orchestrator`가 상태 전이를 관리한다.
- `Policy / Planning Agent`, `Market / Risk Agent`, `Execution / Report Agent`로 역할이 나뉜다.
- `Shared State` 계약과 상태 전이 집합(`RECEIVED`, `RISK_REVIEW`, `READY_FOR_BE`, `BE_REJECTED`, `REPORT_READY` 등)이 존재한다.
- AI의 `PASS`는 실행 완료가 아니라 **BE 재검증 이전 제안**으로 제한된다.

즉, 현재 문서는 최소한 **상태 기반 오케스트레이션 문서**로는 정리되어 있다.
따라서 지금의 정확한 평가는 "agentic이 0이다"가 아니라, **agentic 방향을 선언했지만 세부 실행 계약이 덜 닫혀 있다**에 가깝다.

### 1.3 Shared State와 trace 부재 비판도 일부 해소되었다

현재 `AI.md`에는 다음이 직접 정의되어 있다.

- shared state 필드 목록
- 필드별 작성자/소비자/불변 조건
- `decision_trace.policy`, `decision_trace.risk`, `decision_trace.execution`, `decision_trace.run_summary`
- `reason_codes`, `evidence_refs`, `verification_checks`, `final_action` 구조

기존 피드백의 "상태 누적이 없다"는 문장은 현재 문서에 그대로 쓰기 어렵다.
다만 아래 2장처럼 **merge 규칙과 persistence 계약이 빠져 있다**는 비판으로 바꾸는 편이 정확하다.

---

## 2. 현재 문서 기준에서도 여전히 남아 있는 핵심 부족점

## 2.1 Tool calling 계약이 아직 문서화되지 않았다

현재 `AI.md`는 LLM 사용 지점과 룰 엔진 사용 지점을 분리해 두었지만, 다음이 빠져 있다.

- 어떤 노드가 어떤 tool 집합을 사용할 수 있는지
- tool 입력/출력 schema가 무엇인지
- BE가 주입하는 데이터와 AI가 직접 호출하는 도구의 경계가 어디인지
- tool failure를 어떤 상태로 매핑하는지

즉, **"LLM이 무엇을 이해하고 무엇을 호출하는가"는 보이지만, "어떤 tool contract 위에서 작동하는가"는 아직 닫혀 있지 않다.**

현재 문서 범위에서는 최소한 다음 정도는 필요하다.

- Policy/Risk/Execution/Report 노드별 허용 도구 목록
- 각 도구의 입력/출력 예시
- AI 직접 호출 없음인지, 내부 tool 호출 허용인지에 대한 명시

## 2.2 Human-in-the-loop은 원칙 수준이고 resume 계약이 없다

현재 문서는 `HOLD` 상태를 통해 사람 승인 또는 추가 확인 필요성을 인정한다.
하지만 다음은 아직 문서화되지 않았다.

- 어떤 조건에서 `HOLD`가 사람 승인 대기인지
- 어떤 조건에서 단순 데이터 부족인지
- 승인 후 어떤 입력으로 재개하는지
- FE/BE/AI 사이 resume payload 형식이 무엇인지

즉, **사람 검토 가능성은 정의되어 있지만 실제 승인 루프는 아직 명세화되지 않았다.**

## 2.3 Persistence / Checkpoint / resume 규약이 없다

`ARCHITECTURE.md`와 `AI.md`는 "동일 run을 resume한다"는 방향은 설명한다.
하지만 아래 항목은 비어 있다.

- run state 저장 위치
- 저장 단위와 TTL
- resume 시 복원되는 필드
- 실패 run 재시도 기준
- 중간 상태 감사 로그 보존 정책

현재 문서에서 이 부분은 개념 수준에 머물고 있다.
따라서 기존 피드백의 "메모리/회복 없음" 비판은, 최신 기준에서는 **resume 개념은 생겼지만 persistence 계약이 없다**로 좁혀 쓰는 편이 맞다.

## 2.4 Shared State reducer / merge semantics가 없다

`AI.md`는 shared state 필드를 잘 나열했지만, LangGraph 수준에서 중요한 merge 규칙은 아직 없다.
예를 들어 아래 항목이 불분명하다.

- `errors`는 append인지 overwrite인지
- `verification_checks`는 단계별 병합인지 마지막 값 대체인지
- `decision_trace.run_summary`는 누가 언제 확정하는지
- BE resume 시 어떤 필드가 immutable인지

이 부분이 비어 있으면 구현 단계에서 상태 누락이나 덮어쓰기가 생기기 쉽다.

## 2.5 Structured output 강제 방식이 없다

현재 문서는 trace와 결과 구조를 잘 설명하지만, 다음이 빠져 있다.

- JSON schema 또는 Pydantic 모델 이름
- 노드별 출력 검증 실패 시 처리
- schema mismatch를 `FAILED`로 볼지 `HOLD`로 볼지 기준

즉, **구조화 결과를 요구하지만 강제 장치가 문서상 드러나지 않는다.**

## 2.6 평가 기준이 아직 구현 친화적으로 닫혀 있지 않다

현재 `AI.md`의 평가는 방향성은 맞지만 측정 규약이 부족하다.
다음이 추가되면 더 명확해진다.

- 샘플 시나리오 수
- 성공/실패 판정 데이터셋
- `PASS`, `HOLD`, `NO_ORDER`, `BE_REJECTED` 기대 결과 표
- 잘못된 입력에 대한 regression 케이스

지금 상태에서도 발표용 설명은 가능하지만, 구현 검증 문서로 쓰기에는 아직 추상적이다.

---

## 3. 최신 문서 세트 기준으로 다시 쓴 종합 평가

### 이미 잘 정리된 부분

- Binance Spot Testnet 전용 범위가 저장소 전체에서 일관된다.
- AI와 BE의 권한 경계가 분명하다.
- `PASS`와 실제 제출을 분리해 fail-closed 구조를 유지한다.
- 상태 전이, trace, 리포트 관점이 과거보다 훨씬 명확하다.

### 아직 보강이 필요한 부분

- tool contract
- HITL resume contract
- persistence/checkpoint contract
- shared state merge semantics
- structured output enforcement
- executable evaluation matrix

### 현재 기준 한 줄 평가

> **지금 문서는 더 이상 "agentic이 전혀 아닌 문서"는 아니다.**
> 다만 "상태 기반 agentic orchestration을 구현하기 위한 방향"은 갖췄고, 이를 실제 구현 가능한 수준으로 닫기 위해 필요한 세부 계약이 아직 덜 적혀 있다.

---

## 4. 우선순위 권장 수정안

### P0. 노드별 입출력 계약 표 추가

`AI.md`에 각 노드별로 아래를 붙이는 것이 가장 효과적이다.

- 입력 필드
- 출력 필드
- 허용 tool / 룰 엔진
- 실패 시 상태 전이

### P1. HOLD 세분화

현재 `HOLD`는 의미가 넓다.
최소한 아래 둘은 분리하는 편이 좋다.

- `HOLD_REVIEW_REQUIRED`
- `HOLD_DATA_INSUFFICIENT`

이렇게 해야 FE/BE가 재개 UI와 오류 안내를 다르게 줄 수 있다.

### P2. resume / persistence 최소 계약 추가

`run_id`, 저장 위치, 재개 payload, 만료 기준 정도만 추가해도 문서 완성도가 크게 오른다.

### P3. 평가 시나리오 표 명시

`TEST_AND_DEMO.md` 또는 `AI.md`에 아래 같은 표가 있으면 좋다.

| 시나리오 | 입력 | 기대 gate | 기대 최종 상태 |
|---|---|---|---|
| 잔고 부족 | 시장가 매수, quote 초과 | `REJECT` | `NO_ORDER` |
| 데이터 stale | snapshot 오래됨 | `HOLD` | `HOLD` |
| BE 재검증 실패 | AI `PASS`, BE 규칙 위반 | `PASS` | `BE_REJECTED` |

---

## 5. feedback 문서 관리 규칙

이 문서를 포함한 feedback 계열 문서는 앞으로 `feedback/` 디렉토리에서 관리한다.

운영 원칙은 다음과 같다.

- feedback 문서는 루트 기준 문서를 대체하지 않는다.
- feedback 문서는 반드시 **검토 시점의 대상 문서**를 상단에 명시한다.
- 이미 해결된 이슈와 미해결 이슈를 분리해서 쓴다.
- 현재 저장소 범위(Binance Spot Testnet only)를 벗어난 예시를 섞지 않는다.

---

## 확정 정리

- 기존 `feedback-ai.md`는 최신 문서 기준으로 내용이 낡아 있었다.
- 최신 문서 세트는 과거 비판에서 지적한 일부 핵심 문제를 이미 해소했다.
- 지금 시점의 올바른 피드백은 "agentic 부재"보다 **계약 구체성 부족**에 초점을 맞추는 것이다.
- feedback 문서는 앞으로 `feedback/` 아래에서 별도 관리한다.
