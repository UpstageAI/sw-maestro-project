# Presentation Script

## 서비스 한 줄 소개

소상공인이 리뷰를 붙여넣으면 AI Agent가 감정과 불만 유형을 분석하고, 답글 초안과 반복 불만 TOP 3, 개선 체크리스트까지 만들어주는 리뷰 운영 보조 서비스입니다.

## 사용자가 보는 화면 흐름

먼저 사이드바에서 매장 이름, 업종, 메뉴, 답글 톤, 답글 샘플을 저장합니다.  
그다음 메인 화면에서 샘플 리뷰를 불러오거나 직접 붙여넣고 `분석 시작` 버튼을 누릅니다.  
그러면 화면에 요약 카드, 리뷰별 감정과 카테고리, 메뉴 태그, 답글 초안, 반복 불만 TOP 3, 개선 체크리스트, 실행 로그가 순서대로 표시됩니다.

## 내부 Agent 흐름

버튼을 누르면 Streamlit 프론트엔드가 `ReviewAgentState`를 만들고 LangGraph Agent flow를 실행합니다.  
이후 입력 파싱, 매장 컨텍스트 로드, 리뷰 분류, 답글 생성, DB 저장, 누적 패턴 계산, 체크리스트 생성이 순차적으로 수행됩니다.

## node / edge 설명

- `InputParserNode`: 붙여넣은 리뷰를 나누고, 중복을 제거하고, 개인정보를 마스킹합니다.
- `ContextLoaderNode`: SQLite에서 매장 정보와 최근 수정 답글 샘플을 불러옵니다.
- `ClassifierAgentNode`: 감정, 카테고리, 메뉴 태그를 분석합니다.
- `ReplyDrafterAgentNode`: 매장 톤과 과거 답글 예시를 반영해 답글 초안을 생성합니다.
- `PersistenceToolNode`: 분석 결과와 답글 초안을 DB에 저장합니다.
- `PatternAgentNode`: 누적 리뷰를 조회해 반복 불만 TOP 3를 계산합니다.
- `ChecklistAgentNode`: 반복 불만을 바탕으로 점검 항목을 만듭니다.

edge는 `InputParserNode -> ContextLoaderNode -> ClassifierAgentNode -> ReplyDrafterAgentNode -> PersistenceToolNode -> PatternAgentNode -> ChecklistAgentNode -> END` 순서로 연결됩니다.

## tool calling 설명

DB 접근은 Agent node 내부에서 직접 SQL을 쓰지 않고 tool-like function으로 분리했습니다.  
예를 들어 `load_store_context_tool`, `load_recent_feedback_tool`, `save_reviews_tool`, `load_negative_review_patterns_tool`이 각각 조회와 저장을 담당합니다.

## memory 설명

memory는 SQLite가 담당합니다.

- `stores`: 매장 컨텍스트
- `review_sessions`: 실행 단위 기록
- `reviews`: 분석 결과와 답글 초안
- `feedback_events`: 사장님 수정 이력

이 구조 덕분에 단건 분석이 아니라 다세션 누적 분석과 feedback loop를 설명할 수 있습니다.

## 데모 시나리오 2개 설명

### 시나리오 1. 마감 후 리뷰 정리

샘플 리뷰 A를 불러와 분석 시작을 누릅니다.  
요약 카드와 리뷰별 결과를 확인한 뒤, 답글 하나를 수정 저장합니다.  
이 과정에서 실행 로그와 DB 상태 패널을 통해 어떤 node가 실행됐고 무엇이 저장됐는지 설명합니다.

### 시나리오 2. 누적 리뷰 기반 반복 불만 분석

`데모 모드 초기화`를 눌러 샘플 매장과 과거 리뷰 18건을 seed합니다.  
그다음 새 리뷰를 추가 분석하면 `PatternAgentNode`가 누적 리뷰를 이용해 반복 불만 TOP 3를 계산하고 `ChecklistAgentNode`가 개선 체크리스트를 생성합니다.

## 이번 MVP에서 구현한 것과 제외한 것

구현한 것:

- Streamlit 단일 페이지 UI
- LangGraph 기반 Agent flow
- Mock LLM 기반 전체 데모
- SQLite persistence와 memory
- 답글 수정 저장과 feedback loop
- 누적 리뷰 기반 반복 불만 분석

제외한 것:

- 외부 리뷰 플랫폼 API 연동
- 자동 답글 발행
- RAG / Web Search
- 관리자 권한 체계

이 항목들은 이번 범위에서는 제외했고, 필요하면 이후 확장 가능합니다.
