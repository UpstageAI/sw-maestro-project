# Demo Scenarios

## 시나리오 1. 마감 후 리뷰 정리

- 목표:
프론트엔드에서 리뷰를 붙여넣고, 백엔드 Agent가 분석/답글/저장을 수행하는 흐름을 보여준다.

- 영상 흐름:
1. Streamlit 화면 접속
2. 사이드바에서 매장 정보 확인
3. 리뷰 8건 붙여넣기
4. 분석 시작 클릭
5. 요약 카드 확인
6. 리뷰별 감정/카테고리/답글 초안 확인
7. 답글 하나를 수정하고 저장
8. 백엔드 실행 로그에서 node 실행 순서 확인
9. DB 상태 패널에서 `reviews` / `feedback_events` 저장 확인

- 보여줘야 할 Agent 요소:
- `InputParserNode`
- `ContextLoaderNode`
- `ClassifierAgentNode`
- `ReplyDrafterAgentNode`
- `PersistenceToolNode`
- tool-like DB save
- state 흐름

## 시나리오 2. 누적 리뷰 기반 반복 불만 분석

- 목표:
SQLite에 저장된 과거 리뷰 memory를 활용해 반복 불만 TOP 3와 개선 체크리스트가 생성되는 흐름을 보여준다.

- 영상 흐름:
1. `데모 모드 초기화` 버튼 클릭
2. 과거 리뷰 15~20건 seed 확인
3. 새 리뷰 5~8건 추가 입력
4. 분석 시작 클릭
5. 반복 불만 TOP 3 확인
6. 개선 체크리스트 확인
7. 백엔드 실행 로그에서 `PatternAgentNode`가 누적 데이터를 조회한 것을 확인
8. DB 상태 패널에서 누적 리뷰 개수 확인

- 보여줘야 할 Agent 요소:
- SQLite memory
- ContextLoader
- PatternAgentNode
- ChecklistAgentNode
- 누적 데이터 기반 분석
- 다세션 memory

## 빠른 데모 순서

1. `데모 모드 초기화` 클릭
2. `샘플 리뷰 A 불러오기`
3. `분석 시작`
4. 답글 하나 수정 후 저장
5. `샘플 리뷰 B 불러오기`
6. 다시 `분석 시작`
7. 반복 불만 TOP 3, 체크리스트, 백엔드 실행 로그, DB 상태 패널 확인

