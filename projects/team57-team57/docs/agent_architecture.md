# Agent Architecture

## 목표

이 프로젝트는 소상공인 리뷰 운영 보조를 위한 Agent MVP입니다.

## Node

구현된 node 구성은 아래와 같습니다.

1. `InputParserNode`
2. `ContextLoaderNode`
3. `ClassifierAgentNode`
4. `ReplyDrafterAgentNode`
5. `PersistenceToolNode`
6. `PatternAgentNode`
7. `ChecklistAgentNode`

## Edge

기본 edge 흐름:

`InputParserNode -> ContextLoaderNode -> ClassifierAgentNode -> ReplyDrafterAgentNode -> PersistenceToolNode -> PatternAgentNode -> ChecklistAgentNode -> END`

조건부 edge:

- 파싱 결과가 없으면 종료
- 누적 리뷰가 부족하면 `PatternAgentNode`가 데이터 부족 상태를 반환

## Tool Calling

tool-like function은 DB 저장/조회와 데모 초기화에 적용됩니다.

- `load_store_context_tool`
- `load_recent_feedback_tool`
- `save_reviews_tool`
- `load_negative_review_patterns_tool`
- `initialize_demo_store_tool`

## Memory

SQLite가 장기 기억 저장소 역할을 합니다.

- `stores`: 매장 컨텍스트
- `review_sessions`: 실행 단위 기록
- `reviews`: 분석 결과와 답글 초안
- `feedback_events`: 사용자의 수정 이력

## Feedback Loop

수정 답글은 `feedback_events`와 `reviews.edited_reply`에 저장되고, 다음 실행 시 `ContextLoaderNode`가 최근 수정 답글을 다시 읽어 `ReplyDrafterAgentNode`의 예시 컨텍스트로 전달합니다.

## 이 프로젝트에서 백엔드라고 볼 수 있는 부분

- LangGraph Agent flow
- SQLite Repository
- LLM Provider Adapter
- tool-like DB functions
- safety / masking functions

## 이 프로젝트에서 프론트엔드라고 볼 수 있는 부분

- Streamlit UI
- 매장 컨텍스트 입력 화면
- 리뷰 입력 화면
- 결과 카드 / 리뷰 결과 영역
- 답글 수정 UI
- 실행 로그 / DB 상태 패널

## 데모 영상에서 백엔드와 프론트엔드가 함께 드러나는 지점

- 사용자가 버튼 클릭
- 프론트엔드가 graph 실행
- 백엔드 node들이 state를 갱신
- DB tool이 저장 수행
- 결과가 다시 UI에 표시

## 데모 설명 예시

1. 사용자가 `샘플 리뷰 A 불러오기` 또는 텍스트 입력
2. 사용자가 `분석 시작` 클릭
3. Streamlit UI가 `ReviewAgentState`를 생성
4. LangGraph Agent flow가 node 순서대로 실행
5. `PersistenceToolNode`가 SQLite에 저장
6. `PatternAgentNode`가 누적 리뷰를 조회
7. 결과 카드, 리뷰별 답글, 반복 불만, 백엔드 실행 로그가 화면에 렌더링

