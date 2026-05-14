# 토론 기능 설계

## 배경

토론 기능은 여러 도메인 페르소나가 하나의 주제에 대해 분석, 반론, 합성을 수행해 사용자에게 더 검증된 인사이트와 실행 계획을 제공하는 기능이다. 프로젝트 기획서의 멀티 에이전트 구조화 토론 흐름을 1차 MVP에서는 수동 트리거 기반 동기식 API로 구현한다.

기존 코드에는 `AgentDiscussion`, `AgentDiscussionMessage`, `DiscussionRound`, `DiscussionStatus` 엔티티가 이미 존재한다. 채팅 기능은 `SolarApiClient`, `Persona.systemPrompt`, `KnowledgeContextBuilder`를 조합해 Solar API를 호출하고 있으므로 토론 기능도 이 패턴을 확장한다.

## 목표

- 사용자가 직접 입력한 `topic`으로 토론을 시작할 수 있다.
- 선택적으로 `knowledgeNodeId`를 함께 전달해 특정 지식 노드를 토론 맥락에 포함할 수 있다.
- 선택적으로 `personaIds`를 전달해 참여 페르소나를 지정할 수 있다.
- `personaIds`가 없으면 활성화된 모든 페르소나가 토론에 참여한다.
- 하나의 요청 안에서 3라운드 토론을 순차적으로 실행하고 최종 결과를 반환한다.
- 라운드별 응답과 최종 요약, 실행 계획을 DB에 저장한다.

## 제외 범위

- 자동 패턴 감지 기반 토론 트리거
- 백그라운드 비동기 실행과 polling API
- HITL 사용자 추가 질문 흐름
- 토론 결과를 새 지식 노드로 자동 생성하는 기능
- 페르소나별 Solar 호출 병렬화

## API 설계

### 토론 생성 및 실행

`POST /api/discussions`

요청 본문:

```json
{
  "topic": "요즘 피곤한 이유를 건강과 학업 관점에서 분석해줘",
  "knowledgeNodeId": 1,
  "personaIds": [1, 2]
}
```

요청 규칙:

- `topic`은 필수이며 공백일 수 없다.
- `knowledgeNodeId`는 선택값이다.
- `personaIds`는 선택값이다.
- `personaIds`가 비어 있거나 `null`이면 `enabled = true`인 모든 페르소나가 참여한다.
- 참여 페르소나는 최소 2명 이상이어야 한다.

응답:

```json
{
  "id": 1,
  "triggerNodeId": 1,
  "status": "COMPLETED",
  "title": "요즘 피곤한 이유를 건강과 학업 관점에서 분석해줘",
  "summary": "최종 요약",
  "actionPlan": "실행 계획",
  "messages": [
    {
      "id": 1,
      "personaId": 1,
      "personaName": "건강 Persona",
      "round": "ANALYSIS",
      "content": "건강 관점 분석"
    }
  ]
}
```

주요 에러:

- `400`: `topic` 공백, 참여 페르소나 2명 미만
- `404`: 지식 노드 또는 페르소나를 찾을 수 없음
- `502`: Solar API 응답이 비어 있거나 호출 결과를 사용할 수 없음

### 토론 상세 조회

`GET /api/discussions/{discussionId}`

저장된 토론의 최종 결과와 라운드별 메시지를 반환한다.

### 토론 메시지 조회

`GET /api/discussions/{discussionId}/messages`

해당 토론의 라운드별 메시지를 생성 순서대로 반환한다.

## 서비스 흐름

1. `DiscussionController`가 `CreateDiscussionCommand`를 받는다.
2. `DiscussionService`가 `topic`을 검증한다.
3. `knowledgeNodeId`가 있으면 `KnowledgeNode`를 조회한다.
4. `personaIds`가 있으면 해당 페르소나를 조회하고, 없으면 활성 페르소나 전체를 조회한다.
5. 참여 페르소나가 2명 미만이면 `INVALID_REQUEST`를 반환한다.
6. `AgentDiscussion`을 `RUNNING` 상태로 저장한다.
7. Round 1 `ANALYSIS`를 페르소나별로 순차 실행하고 메시지를 저장한다.
8. Round 2 `REBUTTAL`을 페르소나별로 순차 실행하고 메시지를 저장한다.
9. Round 3 `SYNTHESIS`를 서버 합성 프롬프트로 실행하고 최종 합성 메시지를 저장한다.
10. 합성 결과에서 요약과 실행 계획을 분리해 `AgentDiscussion`에 저장하고 상태를 `COMPLETED`로 변경한다.
11. 저장된 토론 결과를 응답 DTO로 변환해 반환한다.

## 프롬프트 설계

`DiscussionPromptTemplates`를 추가해 라운드별 프롬프트를 분리한다.

Round 1 분석:

- 각 페르소나의 `systemPrompt`를 system 메시지로 사용한다.
- 사용자 `topic`, 선택된 지식 노드, 해당 도메인 지식 그래프 컨텍스트를 함께 제공한다.
- 자신의 도메인 관점에서 원인, 근거, 확인할 점, 제안을 작성하도록 요청한다.

Round 2 반론:

- 각 페르소나의 `systemPrompt`를 system 메시지로 사용한다.
- Round 1의 전체 분석을 제공한다.
- 다른 페르소나 주장 중 과도한 추론, 빠진 변수, 충돌하는 해석을 짚도록 요청한다.

Round 3 합성:

- 서버 측 합성 system 메시지를 사용한다.
- Round 1과 Round 2 전체 내용을 제공한다.
- 최종 응답은 `요약`과 `실행 계획` 섹션을 명확히 나누도록 요청한다.

## 데이터 모델 변경

기존 엔티티를 활용하되, 상태 변경 메서드가 필요하다.

- `AgentDiscussion`
  - `markCompleted(String summary, String actionPlan)`
  - `markFailed(String summary)`
- `AgentDiscussionMessage`
  - 기존 구조 유지

추가 저장소:

- `AgentDiscussionRepository`
- `AgentDiscussionMessageRepository`

필요한 페르소나 조회:

- `PersonaRepository.findByEnabledTrue()`
- `PersonaRepository.findAllById(...)` 사용 또는 지정 ID 전체 존재 검증 로직 추가

## DTO

요청 DTO:

- `CreateDiscussionCommand`
  - `String topic`
  - `Long knowledgeNodeId`
  - `List<Long> personaIds`

응답 DTO:

- `DiscussionResult`
  - 토론 기본 정보
  - 최종 요약
  - 실행 계획
  - 메시지 목록
- `DiscussionMessageResult`
  - 메시지 ID
  - 페르소나 ID
  - 페르소나 이름
  - 라운드
  - 내용
  - 생성 시각

## 예외 처리

- Solar API 호출 중 비어 있는 응답이 오면 `SOLAR_RESPONSE_EMPTY`를 사용한다.
- 토론 실행 중 예외가 발생하면 가능한 경우 `AgentDiscussion` 상태를 `FAILED`로 변경한다.
- 생성 전 검증 실패는 토론 엔티티를 만들지 않고 즉시 예외를 반환한다.
- 지정한 `personaIds` 중 일부만 존재하는 경우 전체 요청을 실패시킨다.

## 테스트 전략

서비스 테스트:

- `topic`, `knowledgeNodeId`, `personaIds`로 토론을 생성하면 3라운드 메시지와 최종 결과가 저장된다.
- `personaIds`가 없으면 활성 페르소나 전체가 참여한다.
- 참여 페르소나가 2명 미만이면 실패한다.
- 존재하지 않는 지식 노드 또는 페르소나 ID는 실패한다.
- Solar API 빈 응답은 `SOLAR_RESPONSE_EMPTY`로 실패한다.

컨트롤러 테스트:

- `POST /api/discussions` 성공 응답과 Swagger에 명시된 주요 에러 응답을 검증한다.
- `GET /api/discussions/{discussionId}`와 `GET /api/discussions/{discussionId}/messages` 조회 응답을 검증한다.

## 확장 방향

- 동기식 실행이 안정화되면 상태 모델을 그대로 사용해 비동기 실행으로 전환한다.
- 교차 도메인 패턴 감지 기능이 준비되면 내부 서비스에서 `topic`과 `knowledgeNodeId`를 만들어 같은 토론 실행 서비스를 호출한다.
- 합의 미달 판단 로직을 추가하면 `NEEDS_USER_INPUT` 상태와 사용자 추가 입력 API를 연결한다.
- 토론 결과를 `KnowledgeNode`와 `KnowledgeEdge`로 자동 저장해 지식 그래프에 반영한다.
