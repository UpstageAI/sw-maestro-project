# Coin Agent AI / Agent 개발 명세

## 문서 목적

이 문서는 LangGraph 기반 통합 AI 오케스트레이터 구조와 각 Agent의 역할, Shared State, 입력/출력, 리스크 게이트, 프롬프트 원칙을 정의한다.

## 관련 문서

- 요구사항: `SPEC.md`
- 시스템 구조: `ARCHITECTURE.md`
- 데이터 계약: `DATA.md`

## 1. AI 계층의 역할

AI 계층은 사용자 정책 해석, 시장 정보 해석, 리스크 게이트 판정 보조, 실행 결과 설명, 리포트 생성에 사용된다. 실제 실행 허용 여부는 룰 엔진과 정책 검증을 함께 통과해야 하며, 실패 시 기본값은 **무거래 또는 판단 보류**다.

## 2. 통합 Orchestrator 구조

AI는 다수의 독립 서비스가 아니라 **하나의 LangGraph 기반 통합 Orchestrator**로 구성한다.

```mermaid
flowchart LR
    IN[Request] --> S[Shared State]
    S --> P[Policy/Planning Agent]
    P --> R[Market/Risk Agent]
    R --> G{Risk Gate}
    G -->|Reject| H[Hold / No Trade]
    G -->|Pass| E[Execution/Report Agent]
    H --> OUT[Structured Result]
    E --> OUT
```

## 3. Agent 정의

### 3.1 Policy / Planning Agent

역할:

- 사용자 입력을 구조화된 정책 객체로 변환
- 정책 누락/이상치 검출
- 이후 분석에 필요한 실행 조건 구성

입력:

- 사용자 정책 초안
- 기존 활성 정책

출력:

- 정규화된 정책 객체
- 정책 검증 결과
- 실행 계획 초안

### 3.2 Market / Risk Agent

역할:

- 시장 데이터 해석
- 지표 계산 결과 해석
- 정책과 시장 상태 비교
- 리스크 게이트 판정 보조

입력:

- 정책 객체
- MarketSnapshot

출력:

- RiskAssessment
- ActionCandidate 초안

### 3.3 Execution / Report Agent

역할:

- 실행 후보 설명
- 페이퍼 실행 결과 요약
- 일간 리포트/최근 리포트 생성

입력:

- 리스크 게이트 통과 여부
- ActionCandidate
- PaperExecution 결과

출력:

- 사용자 표시용 설명
- DailyReport

## 4. Shared State 정의

Shared State는 최소 다음 항목을 포함해야 한다.

- `policy`
- `market_snapshot`
- `risk_assessment`
- `action_candidates`
- `paper_execution`
- `execution_logs`
- `report_draft`
- `errors`

세부 구조는 `DATA.md`를 따른다.

## 5. 노드 입력/출력 기준

| 노드 | 입력 | 출력 |
|---|---|---|
| Policy Node | 사용자 정책 초안 | 정규화 정책, 검증 결과 |
| Risk Node | 정규화 정책, 시장 데이터 | 리스크 판정, 후보 행동 |
| Gate Node | 리스크 판정, 후보 행동 | 실행 허용/보류 결정 |
| Execution Node | 실행 허용 후보 | 페이퍼 실행 결과 요약 |
| Report Node | 판정 결과, 실행 결과 | 사용자용 설명, 리포트 |

## 6. 리스크 게이트 기준

리스크 게이트는 다음 기준을 우선 적용한다.

- 정책 필수값 존재 여부
- 지원 코인 여부
- 손실 한도 접근 여부
- 허용 주문 크기 초과 여부
- 데이터 부족 여부
- 외부 API 실패 여부

하나라도 실패하면 기본값은 무거래 또는 판단 보류다.

## 7. LLM 사용 지점과 룰 엔진 사용 지점

### LLM 사용 지점

- 자연어 정책 보조 해석
- 자동 대응 근거 설명 생성
- 리포트 문장 구성

### 룰 엔진 사용 지점

- 정책 필수값 검증
- 수치 기반 손실 한도 판단
- 지원 코인/허용 주문 크기 판단
- 리스크 게이트 최종 통과 여부

원칙적으로 **행동 허용 결정은 LLM 단독으로 하지 않는다.**

## 8. 프롬프트 원칙

- 보수적 리스크 관리자 톤 유지
- 수익 보장 금지
- 확정적 급등/급락 예측 금지
- 정책 우선, 리스크 우선, 설명 분리
- 출력은 구조화 스키마를 우선
- 불확실하면 무거래 또는 판단 보류

## 9. 실패 처리 기본값

다음 경우 기본값은 무거래 또는 판단 보류다.

- 정책 파싱 실패
- 스키마 검증 실패
- 외부 API 실패
- 지표 계산 불가
- 리스크 게이트 불통과
- 실행 결과 저장 실패

## 10. 평가 기준

- 정책 보존 정확도
- 리스크 설명 일관성
- 보류 사유 명확성
- 출력 스키마 안정성
- 과도한 낙관 표현 억제 여부

## 11. 확정 구현 기준

- Orchestrator 내부 노드는 3개 Agent + 1개 Gate Node 구조로 시작한다.
- 멀티 에이전트 확장은 새 독립 서비스보다 서브그래프 추가를 우선한다.
- 프롬프트 템플릿은 역할별 1종으로 시작하고 점진적으로 세분화한다.
- AI 서비스 인터페이스는 HTTP만 사용한다.
- 자연어 정책 입력은 제외하고 폼 입력만 지원한다.
- AI 결과 캐시는 두지 않는다.
- Report Node는 요청 시 생성한다.
