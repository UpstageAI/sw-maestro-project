# LangGraph

## LangGraph를 사용하는 이유

NewPick의 AI 처리는 다음처럼 단계가 나뉜다.

```text
RSS 수집
-> 본문 추출
-> 요약 생성
-> 요약 검증
-> 검증 실패 시 재요약
-> 퀴즈 생성
-> 저장
-> 리포트 생성
```

이 흐름은 단순 함수 하나보다 그래프 구조로 관리하는 것이 좋다.

LangGraph를 사용하면 다음을 명확하게 표현할 수 있다.

- 각 처리 단계를 노드로 분리
- 노드 간 상태 전달
- 검증 결과에 따른 조건부 분기
- 실패 시 재시도 횟수 관리
- 최종 저장 전 품질 검증
- 기사 단위 처리와 리포트 단위 처리 분리

## LangGraph와 LangSmith의 관계

두 도구의 관계를 간단히 정리하면 다음과 같다.

```text
LangGraph = 일을 진행하는 흐름 설계자
LangSmith = 그 일이 어떻게 진행됐는지 기록하고 분석하는 관찰자
```

NewPick에서는:

```text
LangGraph가 RSS 기사 처리 그래프를 실행한다.
LangSmith가 각 노드 실행 기록을 남긴다.
문제가 생기면 LangSmith trace를 보고 프롬프트나 노드 로직을 수정한다.
```

## 본 프로젝트의 노드/State/라우팅 설계

NewPick에서 LangGraph로 구성한 기사 처리 파이프라인 노드 정의, State 스키마, 조건부 라우팅, 리포트 파이프라인 등 프로젝트 고유 설계는 [architecture/pipeline-design.md](../architecture/pipeline-design.md) 에 정리한다. SSE 스트리밍 연동은 [architecture/realtime-ui-states.md](../architecture/realtime-ui-states.md) 의 `astream_events` 섹션 참조.
