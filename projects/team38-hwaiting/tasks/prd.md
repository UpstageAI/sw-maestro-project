# PRD: 노트북 추천 챗봇 (LangGraph 기반 순환형 대화 에이전트)

> **저장 경로:** `tasks/prd-laptop-recommendation-chatbot.md`
> **문서 버전:** v1.2 (2026-05-07) — Minor 이슈(m-1~m-10) 추가 보강: US-001 CI 헬스체크화 · langchain-upstage 결정 · 카드 wrap & 썸네일 fallback · Solar JSON 모드 OQ-9 · dev deps 분리 · markdownlint-cli2 명시 · LLM 비용 SM-11·SM-12 · LangGraph cycle 패턴 §7.7 · TypedDict reducer
> **대상 독자:** 주니어 개발자 / 코드 생성 에이전트(Ralph, Claude Code 등)

---

## 0. 사전 질문 답변 요약 (Decisions)

| # | 항목 | 선택 | 결정 사항 |
|---|------|------|-----------|
| 1 | LLM 공급자 | **D. 기타** | **Upstage Solar LLM** (`solar-pro` 또는 `solar-1-mini-chat`) — OpenAI 호환 엔드포인트 `https://api.upstage.ai/v1/solar` 사용. API Key는 `UPSTAGE_API_KEY` 환경변수. |
| 2 | 크롤링 방식 | **B. 동적** (검증 후 보완) | 다나와 노트북 카테고리(`cate=112758`)는 **1페이지는 정적 HTML**, **2페이지 이후 및 필터 적용은 AJAX POST(`productListAjax.php`)** 로 작동함을 사전 검증. → **하이브리드 전략**: ① 1차로 `httpx.AsyncClient` 로 AJAX POST 병렬 호출, ② 응답 파싱 실패 시 Playwright(async) 비동기 컨텍스트로 폴백. **유효 적재 ≥ 300건**(필수 4컬럼 결측 0). 손실 보전을 위해 **raw fetch ≥ 350건**(약 14% 버퍼). 페이지 단위 동시성으로 크롤 시간 단축. |
| 3 | 데이터 저장소 | **A. SQLite 파일** | `db/laptops.db` 단일 파일에 영속 저장. 스키마는 `db/schema.sql`. |
| 4 | 9개 조건 충족 기준 | **A. 9개 모두 필수** | Node B는 9개 조건이 **모두 채워졌을 때만** Node D로 진행. 누락 시 Node C 루프. |
| 5 | 결과 표시 | **D. Streamlit 풀세트** | `st.columns` + `st.image` + `st.expander` + 비교표(`st.dataframe`) + 외부 링크(`st.link_button`) 조합. |

---

## 1. Introduction / Overview

본 프로젝트는 **사용자와 한국어로 자연스럽게 대화하면서 9가지 노트북 스펙 조건(화면 인치 / 무게 / OS / 해상도 / 밝기 / CPU / 램 / 저장 용량 / 가격)을 순차·반복적으로 수집**하고, 9개 조건이 모두 채워지면 **사전에 다나와에서 크롤링한 SQLite 데이터베이스**를 조회하여 사용자에게 **노트북 후보를 자연어 + 시각 컴포넌트(이미지·표·링크 포함)로 추천**하는, **LangGraph StateGraph 기반의 순환형(Cyclic) 챗봇**이다. 사용자는 Streamlit 웹 UI에서 질의하고, 모델은 Upstage Solar LLM을 호출하며, 상태는 `st.session_state` 와 동기화된다.

---

## 2. Goals (측정 가능한 목표)

- **G-1.** 9가지 스펙 조건을 평균 **6턴 이내**에 모두 수집 완료한다(랜덤 페르소나 10명 시뮬레이션 기준).
- **G-2.** 9개 조건 충족 후 SQL 변환·DB 조회·응답 생성까지 **단일 사용자 응답 기준 5초 이내** (LLM 응답 제외 시 1초 이내).
- **G-3.** 다나와 노트북 카테고리에서 **유효 적재 ≥ 300건**(가격·CPU·램·저장 4컬럼 결측 0)을 확보한다. 손실 보전을 위해 **raw fetch ≥ 350건**, **DB 적재 ≥ 300건**을 **5분 이내**에 완료한다.
- **G-4.** 9개 조건 모두 충족된 사용자의 **추천 1건 이상 반환율 ≥ 90%** (조건이 너무 좁으면 자동 완화 옵션은 본 범위 외, Open Question 참조).
- **G-5.** `pip install -r requirements.txt && streamlit run app/main.py` **단일 명령**으로 신규 환경에서 즉시 기동 (단, `.env` 에 `UPSTAGE_API_KEY` 가 채워져 있다는 전제).
- **G-6.** 모든 노드 전환 시 콘솔에 9개 조건 채움 현황을 **JSON 한 줄**로 로그 출력하여 디버깅을 용이하게 한다.

---

## 3. User Stories

> 각 스토리는 한 세션(약 1~2시간) 내에 구현 가능한 단위로 분해됨. 모든 스토리는 `Typecheck/lint passes` 를 공통 Acceptance Criteria 로 포함.

### US-001: 다나와 사이트 구조 변화 감지 헬스체크 (CI 연동)
**Description:** As a 운영자, I want 다나와 노트북 카테고리 URL의 정적/AJAX 응답 구조가 §0 의 사전 검증 결과와 일치하는지 **주기적으로** 확인하는 헬스체크 스크립트를 갖고 싶다, so that 사이트 구조 변경 시 즉시 알림을 받아 크롤러를 선제 대응할 수 있다. (구현 전 1회성 진단이 아니라 **운영 중 회귀 감지** 용도)

**Acceptance Criteria:**
- [ ] `python -m crawler.probe` 실행 시 `cate=112758` 의 1·2·3·5페이지 각각에 대해 다음을 콘솔/JSON으로 출력: HTTP 메서드, 응답 Content-Type, 응답 본문에 상품명·가격이 포함되어 있는지(boolean), 응답 크기(byte)
- [ ] 출력 JSON 에 `"recommended_strategy"` 키가 있고 값은 `"static_only" | "ajax_post" | "playwright_required"` 중 하나
- [ ] **§0 의 결정값(`ajax_post`)과 다른 strategy 가 감지되면 비-0 종료 코드** (CI 회귀 알림용)
- [ ] GitHub Actions(또는 cron) 에서 **주 1회** 실행 가능한 형태 — 외부 의존성은 인터넷 + Python 표준 라이브러리 + `httpx` 만 (Playwright 없이 동작)
- [ ] Typecheck/lint passes

### US-002: 다나와 크롤러 — 비동기 AJAX POST 우선 전략 구현
**Description:** As a 개발자, I want `httpx.AsyncClient` 로 다나와의 `productListAjax.php` 엔드포인트에 페이지 단위 POST 요청을 **병렬**로 보내 노트북 목록을 수집하는 모듈을 구현하고 싶다, so that ≥350건(DB 적재 ≥300건 확보용 버퍼)을 수 초 내에 가져올 수 있다.

**Acceptance Criteria:**
- [ ] `python -m crawler.fetch --limit 350` 실행 시 **≥ 350건의 raw HTML 조각**을 메모리/임시 디렉터리에 보관 (DB 적재 후 ≥300건 확보를 위한 ~14% 버퍼). 350건 미달 시 비-0 종료 코드
- [ ] 동시 요청 수는 환경변수 `CRAWL_CONCURRENCY` 로 제어 (기본값 5)
- [ ] 요청 간 지연(jitter) 200~600ms 랜덤 적용 (서버 부하 방지)
- [ ] HTTP 4xx/5xx/네트워크 오류 발생 시 지수 백오프(최대 3회) 재시도
- [ ] User-Agent 헤더에 일반 브라우저 문자열 포함
- [ ] AJAX 응답 파싱 실패율(0건 응답)이 5%를 넘으면 비-0 종료 코드로 종료
- [ ] Typecheck/lint passes

### US-003: 다나와 크롤러 — Playwright 폴백 경로
**Description:** As a 개발자, I want US-002 의 AJAX 경로가 실패할 때 자동으로 Playwright(async, headless, chromium)로 폴백하여 동일 페이지를 렌더링·추출하도록 하고 싶다, so that 사이트 구조 변경에도 크롤러가 견고하게 동작한다.

**Acceptance Criteria:**
- [ ] 환경변수 `CRAWL_FORCE_PLAYWRIGHT=1` 시 폴백 경로만 실행
- [ ] 한 번에 최대 3개의 비동기 브라우저 컨텍스트로 페이지 병렬 처리
- [ ] AJAX 응답 0건이 연속 2회 발생하면 자동으로 Playwright 폴백 활성화
- [ ] 폴백 경로로도 동일하게 **≥ 350건 raw HTML** 산출
- [ ] Typecheck/lint passes

### US-004: 노트북 스펙 파서 (HTML → 구조화 dict)
**Description:** As a 개발자, I want raw HTML 조각에서 9가지 스펙(화면 인치 / 무게 / OS / 해상도 / 밝기 / CPU / 램 / 저장 용량 / 가격) + 제품명 + 썸네일 URL + 다나와 상세 링크를 정규화하여 추출하는 파서를 만들고 싶다, so that DB 적재 직전의 표준화된 dict 리스트를 얻는다.

**Acceptance Criteria:**
- [ ] 입력: HTML 조각 1개. 출력: `LaptopSpec` Pydantic 모델 1개 또는 `None`(파싱 실패)
- [ ] 단위 정규화: 무게는 `kg`(float), 화면은 `inch`(float), 램·저장은 `GB`(int), 가격은 `KRW`(int), 밝기는 `nits`(int 또는 None)
- [ ] 해상도는 `"1920x1080"` 형태 문자열, OS는 enum 문자열 (`"Windows 11"`, `"macOS"`, `"FreeDOS"`, `"Linux"`, `"None"` 중 하나)
- [ ] CPU는 `"Intel Core i5-1340P"` 같은 정규화 문자열
- [ ] 9개 필드 중 **가격·CPU·램·저장 용량 4개가 결측이면 행을 폐기**(`None` 반환)
- [ ] Typecheck/lint passes 및 단위 테스트 5건(샘플 HTML로) 통과

### US-005: SQLite 스키마 정의 및 적재 스크립트
**Description:** As a 개발자, I want 9가지 스펙 + 메타데이터(URL, 썸네일, 크롤링 시각)를 저장할 SQLite 스키마를 정의하고, 파싱 결과를 일괄 적재(≥300건 보장)하는 명령을 만들고 싶다, so that 챗봇이 즉시 DB 조회를 수행할 수 있다.

**Acceptance Criteria:**
- [ ] `db/schema.sql` 에 `laptops` 테이블 DDL 정의: 컬럼은 `id`, `product_name`, `screen_inch`, `weight_kg`, `os`, `resolution`, `brightness_nits`, `cpu`, `ram_gb`, `storage_gb`, `price_krw`, `thumbnail_url`, `detail_url`, `crawled_at`
- [ ] `price_krw`, `weight_kg`, `screen_inch`, `ram_gb`, `storage_gb` 에 인덱스 부여
- [ ] `python -m crawler.load --db db/laptops.db` 실행 시 콘솔에 **`INSERTED=N, SKIPPED=M`** 출력. **`N ≥ 300`** 이 아니면 비-0 종료 코드 (FR-1 보장)
- [ ] 동일 `detail_url` 중복은 UPSERT 처리
- [ ] Typecheck/lint passes

### US-006: LangGraph State 스키마 정의
**Description:** As a 개발자, I want LangGraph 워크플로우 전체에서 공유될 `LaptopChatState` Pydantic 스키마를 정의하고 싶다, so that 모든 노드가 동일한 타입을 입출력하고 디버깅이 용이하다.

**Acceptance Criteria:**
- [ ] `LaptopChatState` 에 다음 필드 포함: `messages` (LLM 메시지 이력), `slots` (9개 조건 dict, 미충족 시 `None`), `last_assistant_question` (Node C 산출물), `sql_clause` (Node D 산출물), `candidates` (Node E 산출물 리스트), `final_answer` (Node F 산출물), `turn_count` (int), `is_complete` (bool)
- [ ] `slots` 의 9개 키는 정확히 다음 이름: `screen_inch`, `weight_kg`, `os`, `resolution`, `brightness_nits`, `cpu`, `ram_gb`, `storage_gb`, `price_krw`
- [ ] `slots.values()` 중 `None` 이 없으면 `is_complete=True` 가 자동 계산되는 헬퍼 메서드 제공
- [ ] **State 구현 방식**: `TypedDict` 채택(LangGraph 표준). `messages` 필드는 `Annotated[list[dict], add_messages]` reducer 로 **자동 누적 병합**, `slots` 는 dict 단순 덮어쓰기 정책. `LaptopChatState` 의 모든 필드별 reducer 명시(누적인지 덮어쓰기인지) — Pydantic 기반은 NG (LangGraph 표준 패턴 우선)
- [ ] Typecheck/lint passes

### US-007: Node A — Streamlit 사용자 입력 진입점
**Description:** As a 사용자, I want Streamlit 채팅 UI에서 자연어로 발화할 수 있고, my 입력이 LangGraph State 의 `messages` 에 추가되도록 하고 싶다, so that 대화가 시작·진행된다.

**Acceptance Criteria:**
- [ ] `st.chat_input("어떤 노트북을 찾으세요?")` 렌더링
- [ ] 사용자 입력이 비어있지 않을 때만 그래프 invoke
- [ ] 입력 즉시 `st.chat_message("user")` 로 화면에 에코 표시
- [ ] State 의 `messages` 가 누적됨(이전 대화 보존)
- [ ] Typecheck/lint passes
- [ ] 브라우저에서 동작 확인 (`streamlit run app/main.py` 후 채팅창에 텍스트 입력 → 화면에 즉시 반영)

### US-008: Node B — 9개 조건 충족 평가 (LLM, Conditional Edge)
**Description:** As a 시스템, I want 누적된 사용자 발화에서 9개 슬롯 값을 추출·갱신하고 모두 채워졌는지 판정하는 LLM 노드를 만들고 싶다, so that 다음 분기를 결정할 수 있다.

**Acceptance Criteria:**
- [ ] Upstage Solar LLM에 시스템 프롬프트 + 현재 `slots` + 신규 사용자 메시지를 입력하여 **JSON 모드** 응답을 받음
- [ ] 응답 JSON은 `slots` 와 동일한 9개 키를 가지며, 추출된 값 또는 `null`
- [ ] State.slots 갱신 시 **이미 채워진 값은 다음 휴리스틱을 모두 만족할 때만 덮어쓴다**: ① 사용자 발화에 변경 의도 토큰(`바꿔/바꿀게/올려/낮춰/수정/변경/대신/말고/아니라`) 또는 비교 부사(`더/덜/까지`) 중 하나 이상 포함, ② 동일 슬롯에 대해 새 수치/값이 명확히 추출됨, ③ 새 값이 기존 값과 다름. 셋 중 하나라도 미충족이면 기존 값 유지
- [ ] **변경 의도 단위 테스트 5건 통과**: ⓐ 기존 가격 150만원 + "예산을 200만원으로 올릴게요" → 200만원으로 갱신, ⓑ 기존 가격 150만원 + "150만원도 좋아요" → 유지, ⓒ 기존 OS Windows + "맥으로 바꿀게요" → macOS 갱신, ⓓ 기존 램 16GB + "16GB면 충분해요" → 변경 없음, ⓔ 기존 무게 1.3kg + "더 가벼운 거" → 유지(수치 미추출, Node C 가 후속 질문)
- [ ] 9개가 모두 non-null 이면 Conditional Edge가 Node D로, 아니면 Node C로 라우팅
- [ ] Node 진입 시 `[Node B] slots=…` 로 콘솔에 한 줄 JSON 로그 출력
- [ ] Typecheck/lint passes

### US-009: Node C — 부족한 조건을 묻는 추가 질문 생성
**Description:** As a 시스템, I want 미충족 슬롯 중 하나(또는 자연스럽게 묶을 수 있는 두 개)에 대해 한국어로 친근한 후속 질문을 생성해 사용자에게 되묻고 싶다, so that 9개가 채워질 때까지 루프가 진행된다.

**Acceptance Criteria:**
- [ ] 미충족 슬롯이 1개 이상일 때만 노드 동작
- [ ] LLM 출력은 1~2 문장의 자연어 질문, 한국어, "?" 로 종결
- [ ] 동일 사용자 발화에 대해 동일 질문을 연속 3회 반복하지 않음(중복 방지: 마지막 N개 질문을 컨텍스트에 포함)
- [ ] State.last_assistant_question 에 저장 후 `messages` 에 assistant 턴으로 추가
- [ ] Node B 로 돌아가지 않고 **Node A(사용자 입력 대기)** 로 흐름이 끝남(Cycle)
- [ ] Typecheck/lint passes

### US-010: Node D — 9개 슬롯 → SQL WHERE 절 변환
**Description:** As a 시스템, I want 9개 슬롯 값을 SQLite WHERE 절(파라미터 바인딩 형식)로 변환하는 노드를 만들고 싶다, so that DB 조회를 안전하게 수행할 수 있다.

**Acceptance Criteria:**
- [ ] 출력은 `(where_sql: str, params: list)` 튜플
- [ ] **비교 연산자 (결정론적)**: 가격 `price_krw <= ?`, 무게 `weight_kg <= ?`, 화면 `screen_inch BETWEEN ?-1 AND ?+1`, 램·저장 `>= ?`, 밝기 `(brightness_nits IS NULL OR brightness_nits >= ?)`, OS `os LIKE ?`(파라미터 양옆 `%` 자동 부착), CPU `cpu LIKE ?`(아래 정규화 룰로 추출한 키워드에 `%` 자동 부착), 해상도 `resolution = ?`(canonical `WxH` 문자열 — Node B 가 사전 매핑, 부록 A.1)
- [ ] **CPU 키워드 추출 정규화 룰** (우선순위 순): ① `Apple M[1-4]( Pro| Max| Ultra)?`, ② `Intel Core (Ultra )?(i[3579]|Ultra [579])-?\d{3,5}[A-Z]?`, ③ `Ryzen [3579] \d{4,5}[A-Z]?`, ④ 위 3개 미매칭 시 입력 원문 그대로. 추출된 키워드를 `%키워드%` 로 감싸 LIKE 인자로 바인딩
- [ ] **OS 정규화 룰**: 슬롯 값을 `Windows | macOS | FreeDOS | Linux` 4개 카테고리 중 하나로 매핑한 뒤 `%카테고리%` 로 LIKE. 버전 정보(11/10 등)는 매칭에서 무시
- [ ] **해상도 매핑은 Node B 책임**(부록 A.1). Node D 는 이미 canonical 인 슬롯 값을 `=` 비교만 수행
- [ ] 모든 값은 **반드시 `?` 파라미터 바인딩**으로 전달, SQL 인젝션 방지
- [ ] LLM 호출 시 응답이 JSON 스키마를 따르지 않으면 1회 재시도, 2회 실패 시 결정론적 룰베이스 폴백 함수 사용
- [ ] Typecheck/lint passes 및 단위 테스트 3건 통과

### US-011: Node E — DB 조회 (Hard-coded Tool, LLM 미사용)
**Description:** As a 시스템, I want Node D 가 만든 WHERE 절·params 로 SQLite 를 조회하여 후보 리스트를 반환하는 결정론적 도구를 만들고 싶다, so that 추천의 사실성(factuality)을 보장한다.

**Acceptance Criteria:**
- [ ] `SELECT * FROM laptops WHERE … ORDER BY price_krw ASC LIMIT 5` 형태로 최대 5건 조회
- [ ] 결과 0건이면 `candidates=[]` 를 State 에 저장(빈 결과 처리는 Node F가 담당)
- [ ] LLM 호출 없음, 순수 sqlite3
- [ ] 콘솔에 `[Node E] matched=N` 로그 출력
- [ ] Typecheck/lint passes

### US-012: Node F — 자연어 추천 응답 + 빈 결과 메시지 생성
**Description:** As a 사용자, I want 후보 노트북 0~5건에 대한 한국어 자연어 요약 + 추천 사유를 LLM이 생성해주길 원한다, so that 단순 표 나열이 아닌 친근한 추천을 받는다.

**Acceptance Criteria:**
- [ ] 후보 ≥1건: 각 후보별 1~2 문장 요약 + 사용자 조건과의 매칭 포인트 명시
- [ ] 후보 0건: "조건을 만족하는 노트북이 없습니다. 다음 항목을 완화해보세요: …" 형식의 안내 메시지 (어떤 슬롯을 완화할지 LLM이 추천)
- [ ] 응답은 마크다운 형식, Streamlit `st.chat_message("assistant")` 가 그대로 렌더 가능
- [ ] State.final_answer 에 저장
- [ ] Typecheck/lint passes

### US-013: 순환 루프 제어 — Conditional Edges 와 종료 조건
**Description:** As a 개발자, I want LangGraph StateGraph 에 Node A→B→(C→A | D→E→F→END) 흐름을 정의하고 싶다, so that 9개 조건 미충족 시 무한 루프, 충족 시 1회 추천 후 종료가 보장된다.

**Acceptance Criteria:**
- [ ] StateGraph DSL 또는 SDK로 그래프 빌드 → `graph.compile()` 성공
- [ ] Conditional edge 분기 함수가 `state.is_complete` 만으로 결정
- [ ] **`turn_count > 20`** 안전장치 도달 시 강제 종료하며 사용자에게 "조건 수집이 길어져 추천을 진행합니다"는 알림 + 부분 슬롯으로 Node D 진행
- [ ] Typecheck/lint passes

### US-014: Streamlit UI — 결과 카드(컴포넌트 풀세트)
**Description:** As a 사용자, I want 추천 결과를 이미지·요약·비교표·외부 링크가 포함된 카드 형태로 보고 싶다, so that 빠르게 비교·이동할 수 있다.

**Acceptance Criteria:**
- [ ] **카드 그리드 wrap 정책**: 최대 **3 컬럼 × 2 행**. `len(candidates) ≤ 3` → 단일 행(`st.columns(len)`); `4~5` → `st.columns(3)` 두 번 호출하여 **첫 행 3개 + 둘째 행 나머지** 배치(둘째 행 빈 컬럼은 `st.empty()`); 6건 이상은 FR-14 의 `LIMIT 5` 로 발생 불가
- [ ] 각 카드: `st.image(thumbnail_url or PLACEHOLDER_IMG)` + 제품명(`st.subheader`) + 가격(`st.metric`) + `st.expander("스펙 자세히")` 안에 9개 스펙 표 + `st.link_button("다나와에서 보기", detail_url)`. `PLACEHOLDER_IMG` 는 **로컬 파일 경로** `app/static/no_image.png` (외부 URL 의존 금지, 오프라인에서도 렌더 보장)
- [ ] 카드 아래에 9개 스펙 비교용 `st.dataframe` (행=후보, 열=9개 스펙) 표시
- [ ] 후보 0건일 때는 카드/표 영역 대신 Node F 안내 메시지만 렌더
- [ ] Typecheck/lint passes
- [ ] 브라우저에서 동작 확인 (썸네일 표시, 링크 클릭 시 다나와 새 탭 열림)

### US-015: `st.session_state` ↔ LangGraph State 동기화
**Description:** As a 사용자, I want 페이지 위젯 상호작용(예: 사이드바 클릭, 다른 입력)이 발생해도 대화 이력과 슬롯이 유지되길 원한다, so that 같은 세션 내에서는 진행이 끊기지 않는다.

**Acceptance Criteria:**
- [ ] `st.session_state["chat_state"]` 에 `LaptopChatState` 인스턴스 보관
- [ ] 매 입력 처리 후 그래프 결과를 다시 `st.session_state` 에 직렬화 저장
- [ ] 사이드바에 "대화 초기화" 버튼 → 클릭 시 `st.session_state.clear()` + `st.rerun()`
- [ ] 페이지 새로고침 시에만 손실(이는 본 범위에서 허용)
- [ ] Typecheck/lint passes
- [ ] 브라우저에서 동작 확인

### US-016: 사이드바 디버그 패널 — 슬롯 채움 현황 시각화
**Description:** As a 개발자/QA, I want 사이드바에 9개 슬롯의 현재 값과 진행 상태(채움/미채움)를 실시간으로 보고 싶다, so that 디버깅·시연이 쉽다.

**Acceptance Criteria:**
- [ ] `st.sidebar` 에 9개 슬롯 라벨 + 현재 값(미채움이면 "—") 표시
- [ ] 채워진 슬롯 개수 진행 바 (`st.progress(filled_count / 9)`)
- [ ] `st.sidebar.expander("Raw State JSON")` 안에 전체 State JSON 표시
- [ ] Typecheck/lint passes
- [ ] 브라우저에서 동작 확인

### US-017: 콘솔 로깅 — 노드 전환 시 State 한 줄 JSON
**Description:** As a 개발자, I want 모든 노드(A~F)가 진입·이탈 시 `[Node X] event=enter|exit, slots=…` 형식으로 한 줄 JSON 로그를 stdout에 남기길 원한다, so that 비-UI 환경에서도 흐름을 추적할 수 있다.

**Acceptance Criteria:**
- [ ] Python 표준 `logging` 모듈 사용, 포매터는 한 줄 JSON
- [ ] 환경변수 `LOG_LEVEL` (기본 `INFO`) 로 레벨 제어
- [ ] 민감정보(API Key) 가 로그에 절대 포함되지 않음 (단위 테스트로 검증)
- [ ] Typecheck/lint passes

### US-018: 환경설정 — `.env`, `.env.example`, `requirements.txt`
**Description:** As a 신규 개발자, I want 저장소 클론 후 1분 안에 의존성 설치와 환경 설정을 끝내고 싶다, so that 빠르게 실행을 시작할 수 있다.

**Acceptance Criteria:**
- [ ] `.env.example` 에 `UPSTAGE_API_KEY=`, `LOG_LEVEL=INFO`, `CRAWL_CONCURRENCY=5`, `CRAWL_FORCE_PLAYWRIGHT=0`, `DB_PATH=db/laptops.db` 키 모두 존재
- [ ] `requirements.txt` 에 **운영 의존성**만 명시: `langgraph`, `langchain`, **`langchain-upstage`**(Upstage 공식 SDK — `ChatUpstage` 클래스. OpenAI 호환 백업 경로는 §7.3 참조), `streamlit`, `httpx`, `beautifulsoup4`, `playwright`, `pydantic`, `python-dotenv`
- [ ] **`requirements-dev.txt`** 로 테스트·린트 의존성 분리: `pytest`, `pytest-asyncio`, `ruff`, `mypy`. (마크다운 린트는 npm 도구 `markdownlint-cli2` — README 에 별도 설치 안내) 운영 환경에서는 `requirements-dev.txt` 를 설치하지 않음
- [ ] `.env` 는 `.gitignore` 에 포함
- [ ] `python-dotenv` 로딩이 `app/main.py` 최상단에서 수행
- [ ] Typecheck/lint passes

### US-019: README 와 실행 문서
**Description:** As a 신규 개발자, I want README 만 따라 하면 즉시 챗봇을 띄울 수 있는 문서를 원한다, so that 진입 장벽이 낮다.

**Acceptance Criteria:**
- [ ] `README.md` 에 다음 섹션 포함: 프로젝트 개요, 요구사항(Python 3.11+), 설치 단계, 크롤링 단계(`python -m crawler.fetch && python -m crawler.load`), 실행 단계(`streamlit run app/main.py`), 9개 조건 표, 트러블슈팅 (Playwright 브라우저 설치 명령 `playwright install chromium` 명시)
- [ ] 예시 대화 스크립트(사용자 6턴 → 추천)가 README에 포함
- [ ] Typecheck/lint passes — 마크다운 린트는 **`markdownlint-cli2`**(npm) 사용. 저장소 루트에 `.markdownlint.json` 동봉(기본 룰셋 + `MD013`[line-length] 와 `MD033`[inline-html] 비활성, 한국어 문서 특성 반영)

### US-020: 페르소나 시뮬레이션 하니스 (SM-1 / SM-2 측정용)
**Description:** As a 개발자/QA, I want 10명의 가상 사용자 페르소나가 챗봇과 자동 대화하여 9개 슬롯 수집 턴 수와 추천 반환율을 측정하는 스크립트를 갖고 싶다, so that SM-1·SM-2 의 수치 목표를 객관적으로 검증할 수 있다.

**Acceptance Criteria:**
- [ ] `tests/sim/personas.yaml` 에 10개 페르소나 정의 (각자 9개 스펙 선호값 + 발화 톤·축약 정도 지정. 예: 학생/디자이너/개발자/시니어 사용자)
- [ ] `python -m tests.sim.run --n 10 --max-turns 20` 실행 시 각 페르소나당 1회 대화 시뮬레이션 — **페르소나 측은 LLM 미사용 룰베이스 응답기**(챗봇 질문에서 슬롯 키를 식별 → 자기 선호값을 자연어로 답변), **챗봇 측은 실제 그래프 invoke**
- [ ] 출력: `tests/sim/report.json` — 페르소나별 턴 수, 9개 슬롯 충족 여부, 추천 ≥1건 반환 여부, LLM 포함/제외 응답 지연
- [ ] 콘솔 요약: `SM-1=X턴 (목표≤6), SM-2=Y% (목표≥90%), SM-4=Zs (목표≤5s)` 한 줄 출력
- [ ] 9개 슬롯 모두 수집한 페르소나가 **7명 미만**이거나 추천 반환율 < 90% 시 비-0 종료 코드 (회귀 방지)
- [ ] CI 에서 `--n 3 --smoke` 모드를 호출할 수 있도록 인자 분리 (전체 10개는 로컬·릴리스 시 실행)
- [ ] Typecheck/lint passes

---

## 4. Functional Requirements

### 크롤링 / 데이터 적재
- **FR-1.** 시스템은 다나와 노트북 카테고리(`https://prod.danawa.com/list/?cate=112758`) 에서 **raw HTML ≥ 350건**을 수집하고, 파싱·필터링(FR-6) 후 **DB 적재 ≥ 300건**을 보장해야 한다. 적재 < 300 인 경우 비-0 종료 코드로 실패시켜야 한다.
- **FR-2.** 시스템은 1차로 `httpx.AsyncClient` 기반의 AJAX POST 병렬 호출(`productListAjax.php`)을 사용해야 하며, 동시 요청 수는 환경변수 `CRAWL_CONCURRENCY`(기본 5)로 제어해야 한다.
- **FR-3.** AJAX 응답이 연속 2회 0건이면 시스템은 자동으로 **Playwright(async chromium, headless)** 폴백 경로로 전환해야 한다.
- **FR-4.** 시스템은 각 요청 사이에 **200~600ms 의 랜덤 jitter** 를 적용해야 한다.
- **FR-5.** 시스템은 9개 스펙 단위를 정규화해야 한다(무게 kg, 화면 inch, 램/저장 GB, 가격 KRW, 밝기 nits, 해상도 `WxH` 문자열).
- **FR-6.** 가격·CPU·램·저장 용량 중 하나라도 결측인 행은 **DB 적재 대상에서 제외**해야 한다.
- **FR-7.** SQLite 데이터베이스는 `db/laptops.db` 에 저장하며, `laptops` 테이블 하나만 둔다.
- **FR-8.** 동일 `detail_url` 의 중복 행은 **UPSERT 정책**으로 처리해야 한다.

### 챗봇 / LangGraph
- **FR-9.** 시스템은 LangGraph StateGraph 로 Node A(입력) → Node B(평가) → 분기 → Node C(질문, A로 복귀) 또는 Node D(SQL) → Node E(조회) → Node F(응답) → END 의 흐름을 구성해야 한다.
- **FR-10.** State 스키마는 9개 슬롯(`screen_inch`, `weight_kg`, `os`, `resolution`, `brightness_nits`, `cpu`, `ram_gb`, `storage_gb`, `price_krw`)을 모두 포함해야 한다.
- **FR-11.** Node B 는 9개 슬롯이 **모두 non-null** 일 때만 Node D 로 분기해야 한다(전부 필수 정책).
- **FR-12.** Node C 는 미충족 슬롯이 1개 이상 남아있는 동안만 동작하며, 매 호출마다 1~2 문장 한국어 질문을 생성해야 한다.
- **FR-13.** Node D 는 9개 슬롯을 **파라미터 바인딩(`?`) 방식 SQL** 로 변환해야 하며, 문자열 보간(SQL 인젝션 위험) 을 사용해서는 안 된다. **값이 `None` 인 슬롯은 WHERE 절에서 자동으로 생략**하여, 안전장치 경로(FR-16) 의 부분 슬롯 모드에서도 정상 동작해야 한다.
- **FR-14.** Node E 는 LLM 호출 없이 sqlite3 만 사용해야 하며, `ORDER BY price_krw ASC LIMIT 5` 로 최대 5건을 반환해야 한다.
- **FR-15.** Node F 는 후보 ≥1건이면 자연어 요약 + 매칭 포인트를, 0건이면 어떤 조건을 완화할지 안내하는 메시지를 생성해야 한다.
- **FR-16.** `turn_count > 20` 시 시스템은 강제 종료하며, 부분 슬롯으로라도 Node D 를 1회 시도해야 한다(안전장치).

### LLM (Upstage Solar)
- **FR-17.** 시스템은 Upstage Solar LLM(`solar-pro` 또는 `solar-1-mini-chat`)을 OpenAI 호환 클라이언트(`base_url="https://api.upstage.ai/v1/solar"`)로 호출해야 한다.
- **FR-18.** API Key 는 `UPSTAGE_API_KEY` 환경변수에서만 읽고, 코드에 하드코딩되어서는 안 된다.
- **FR-19.** Node B/C/D/F의 LLM 호출은 **JSON 모드**(가능 시) 또는 명시적 JSON 스키마 지시 + 응답 검증을 적용해야 하며, 검증 실패 시 1회 재시도해야 한다.
- **FR-20.** 시스템은 LLM 응답이 JSON 스키마를 2회 연속 위반하면 결정론적 룰베이스 폴백을 사용해야 한다(Node B/D 한정).

### Streamlit UI / 세션
- **FR-21.** 사용자 입력은 `st.chat_input` 으로 받아야 한다.
- **FR-22.** 대화 이력은 `st.chat_message("user"|"assistant")` 로 누적 렌더해야 한다.
- **FR-23.** 추천 결과는 `st.columns` + `st.image` + `st.expander` + `st.link_button` + `st.dataframe` 컴포넌트를 모두 사용해 렌더해야 한다.
- **FR-24.** LangGraph State 는 매 입력 처리 후 `st.session_state["chat_state"]` 에 동기화되어야 한다.
- **FR-25.** 사이드바는 9개 슬롯 채움 현황(라벨/값/진행 바) 과 Raw State JSON expander 를 표시해야 한다.
- **FR-26.** 사이드바의 "대화 초기화" 버튼은 `st.session_state` 를 비우고 `st.rerun()` 을 호출해야 한다.

### 로깅 / 운영
- **FR-27.** 모든 노드는 진입·이탈 시 한 줄 JSON 로그(`[Node X] event=…, slots=…`)를 stdout 에 출력해야 한다.
- **FR-28.** 로그에 API Key 를 포함하는 어떤 문자열도 출력되어서는 안 된다(테스트로 검증).
- **FR-29.** `pip install -r requirements.txt && playwright install chromium && streamlit run app/main.py` **세 명령**으로 시스템이 기동되어야 한다.

---

## 5. Non-Goals (Out of Scope)

- **NG-1.** 사용자 인증/계정 시스템 — 본 챗봇은 단일 세션 익명 사용을 가정한다.
- **NG-2.** 다중 세션·다중 사용자 동시성 — 단일 사용자 데모용. Streamlit 기본 세션 분리에 의존.
- **NG-3.** 추천 결과 0건일 때의 **자동 조건 완화 후 재조회** 루프 — 사용자에게 안내만 한다.
- **NG-4.** 다나와 외 다른 쇼핑몰(쿠팡, 11번가 등) 가격 비교.
- **NG-5.** 다나와 상품 상세 페이지 크롤링 — 목록 페이지의 요약 스펙만 사용.
- **NG-6.** 가격 시계열·할인 알림 기능.
- **NG-7.** 음성 입력/출력(STT/TTS).
- **NG-8.** 모바일 전용 반응형 UI 최적화 — 데스크톱 Streamlit 기본 레이아웃을 따른다.
- **NG-9.** 9개 외 다른 스펙(GPU, 배터리 시간, 단자 종류 등) 수집·필터링.
- **NG-10.** 챗봇 답변의 다국어 지원 — 한국어 전용.
- **NG-11.** LLM Fine-tuning, RAG 벡터 인덱스 — Solar LLM 의 zero-shot 추론에만 의존.
- **NG-12.** 페이지 새로고침 후 대화 복원(영속화) — `st.session_state` 휘발성 허용.
- **NG-13.** 다나와 robots.txt 위반 가능성이 있는 대량/장기 크롤링 — 본 범위는 300건 단발성.

---

## 6. Design Considerations

### 6.1 챗 UI 와이어프레임 (텍스트 메모)

```
┌────────────────────────────────────────────────────────────────┐
│ [사이드바]                  │  [메인]                            │
│ 진행률 ▓▓▓▓▓░░░░ 5/9         │  💬 노트북 추천 챗봇                │
│                              │                                    │
│ ▸ 화면 인치     : 15"        │  🧑 "가벼운 노트북 찾아요"          │
│ ▸ 무게         : 1.2kg       │  🤖 "예산은 어느 정도 생각하세요?"   │
│ ▸ OS           : Windows 11  │  🧑 "150만원 이하요"                │
│ ▸ 해상도       : —           │  🤖 "OS는 윈도우/맥 중 어떤…"       │
│ ▸ 밝기         : —           │  …                                 │
│ ▸ CPU          : i5-1340P    │                                    │
│ ▸ 램           : 16GB        │  ─── 추천 결과 ──────────────       │
│ ▸ 저장         : —           │  ┌────┐ ┌────┐ ┌────┐               │
│ ▸ 가격         : 1,500,000   │  │ img│ │ img│ │ img│               │
│ ──────────────              │  │제품A│ │제품B│ │제품C│             │
│ [Raw State JSON ▼]          │  │1.49M│ │1.39M│ │1.45M│             │
│ [대화 초기화]                │  │[자세히▼] [다나와↗]                │
│                              │  └────┘ └────┘ └────┘               │
│                              │  [비교표 — st.dataframe ────────]   │
│ [st.chat_input: "메시지 입력……" ────────────────────────────────] │
└────────────────────────────────────────────────────────────────┘
```

### 6.2 재사용할 Streamlit 컴포넌트

- `st.chat_input`, `st.chat_message` — 채팅 표면 (Node A 입출력)
- `st.columns(N)` + `st.image` — 후보 카드 그리드 (Node F 출력)
- `st.expander` — 카드 내 9개 스펙 상세 펼침
- `st.metric` — 가격을 시각적으로 강조
- `st.link_button` — 다나와 외부 링크
- `st.dataframe` — 9개 스펙 비교표
- `st.sidebar`, `st.progress` — 슬롯 채움 진행률
- `st.spinner("생각 중…")` — LLM 호출 동안 로딩 표시
- `st.toast` — 노드 전환 시 짧은 알림 (옵션)
- `st.rerun` — "대화 초기화" 후 강제 리렌더

### 6.3 톤 앤 매너

- 챗봇 톤은 **친근한 존댓말**(예: "어떤 화면 크기가 편하세요?").
- 영어 약어는 한 번 풀어서 설명 (예: "RAM(메모리)").
- 추천 사유는 항상 사용자가 말한 조건을 인용 (예: "예산 150만원 이하 + 무게 1.3kg 이하 조건에 맞아요").

---

## 7. Technical Considerations

### 7.1 LangGraph State 스키마 초안

| 필드 | 타입 | 설명 |
|------|------|------|
| `messages` | `list[dict]` | `{"role": "user|assistant", "content": str}` 누적 이력 |
| `slots.screen_inch` | `float | None` | 인치 |
| `slots.weight_kg` | `float | None` | kg |
| `slots.os` | `str | None` | "Windows 11" / "macOS" / "FreeDOS" / "Linux" |
| `slots.resolution` | `str | None` | "1920x1080" 등 |
| `slots.brightness_nits` | `int | None` | nits |
| `slots.cpu` | `str | None` | "Intel Core i5-1340P" 등 |
| `slots.ram_gb` | `int | None` | GB |
| `slots.storage_gb` | `int | None` | GB |
| `slots.price_krw` | `int | None` | KRW(원) |
| `last_assistant_question` | `str | None` | Node C 산출물 |
| `sql_clause` | `tuple[str, list] | None` | Node D 산출물 (`where_sql`, `params`) |
| `candidates` | `list[dict]` | Node E 산출물 (DB 행 dict의 리스트, 최대 5) |
| `final_answer` | `str | None` | Node F 산출물 (마크다운) |
| `turn_count` | `int` | 안전장치용 카운터 |
| `is_complete` | `bool` | 9개 슬롯 모두 채워졌는지 |

### 7.2 크롤링 robots / 매너 정책

- **robots.txt 확인:** `https://prod.danawa.com/robots.txt` 를 크롤러 시작 시 1회 조회하여 카테고리 경로가 Disallow 인지 검증, Disallow 라면 비-0 종료.
- **요청 간 jitter:** 200~600ms 랜덤. `CRAWL_CONCURRENCY` 의 기본값 5 는 서버에 부담을 주지 않는 수준.
- **User-Agent:** 일반 브라우저 UA. 단, 스푸핑 의도가 아닌 명확한 식별을 위해 `+contact: <project repo url>` 같은 코멘트를 넣어도 무방.
- **총량 한도:** 본 PRD 범위에서는 **300건 단발성**. 정기 갱신/스케줄링은 Non-Goal.
- **에러 시 백오프:** 4xx/5xx/네트워크 오류 → 지수 백오프(1s, 2s, 4s) 최대 3회.

### 7.3 LLM 호출 비용·재시도

- **Upstage Solar 모델 선택 가이드:** Node C(자연어 질문 생성)·F(추천 응답)는 `solar-pro`(품질 우선), Node B(슬롯 추출)·D(SQL 변환)는 `solar-1-mini-chat`(저비용·구조화 출력 우선) 권장. 단, 본 PRD에서는 모델명은 환경변수 `UPSTAGE_MODEL_PRIMARY`, `UPSTAGE_MODEL_FAST` 로 외부화하여 변경 가능.
- **재시도:** JSON 스키마 위반 시 1회 재시도. 2회 연속 실패 시 결정론적 폴백(Node B는 키워드 매칭, Node D는 룰베이스).
- **타임아웃:** 단일 LLM 호출 60초 타임아웃. 초과 시 Node F는 "잠시 후 다시 시도해주세요" 메시지로 대체.
- **호출 횟수 가시성:** 사이드바 디버그에 누적 LLM 호출 수와 누적 토큰 사용량 표시(SM-11·SM-12 측정 근거).
- **SDK 선택 (m-2):** **1차로 `langchain-upstage`** 사용 — Upstage 공식 SDK 이며 `ChatUpstage` 클래스로 모델 라우팅·재시도가 표준화되어 있음. 미설치/버전 이슈 시 `langchain-openai` 의 `ChatOpenAI(base_url="https://api.upstage.ai/v1/solar", model="solar-pro")` 백업 경로로 즉시 전환 가능. 두 경로의 인터페이스 차이는 어댑터 함수 `make_llm()` 으로 캡슐화.
- **JSON 모드 가정 (m-5 / OQ-9):** OpenAI 호환 `response_format={"type":"json_object"}` 의 Solar 측 지원 여부는 **OQ-9 로 사전 검증** 필요. 미지원으로 판명될 경우 Node B/D/F 의 LLM 호출은 **명시적 JSON 스키마 시스템 프롬프트 + Pydantic `model_validate_json` 파싱 + 1회 재시도** 폴백을 사용한다 (현재 PRD: 폴백 적용을 기본 가정으로 둠).

### 7.4 SQL 인젝션 방지

- Node D 의 모든 동적 값은 `?` 파라미터 바인딩으로만 전달.
- `LIKE` 패턴이라도 사용자 입력 그대로 보간 금지. 와일드카드 `%` 추가는 코드에서 수행하고 값 자체는 바인딩.
- 단위 테스트에 `"'); DROP TABLE laptops;--"` 같은 인젝션 페이로드를 슬롯 값으로 넣어도 테이블이 보존되는지 확인.

### 7.5 캐싱

- **DB 조회 캐싱:** `slots` 9개 값을 정규화한 튜플을 키로, Node E 결과를 `functools.lru_cache(maxsize=128)` 캐시. 동일 조건 재요청 시 DB I/O 절감.
- **LLM 응답 캐싱:** 동일 입력(messages 마지막 N개 + slots) 해시를 키로, Streamlit `@st.cache_data(ttl=600)` 적용 가능. 단, 사용자별 컨텍스트가 바뀌므로 보수적으로 적용.
- **크롤링 캐시:** 1차 raw HTML 을 임시 디렉터리에 보관하여 파싱 단계 분리·재실행 가능하도록.

### 7.6 모듈 구조 (재확인)

```
laptop-chatbot/
├─ crawler/
│   ├─ probe.py          # US-001: 렌더링 진단
│   ├─ fetch.py          # US-002, US-003: AJAX/Playwright 수집
│   ├─ parse.py          # US-004: HTML → LaptopSpec
│   └─ load.py           # US-005: SQLite 적재
├─ graph/
│   ├─ state.py          # US-006: LaptopChatState
│   ├─ nodes.py          # US-008~US-012: 노드 구현
│   ├─ edges.py          # US-013: Conditional edges
│   └─ build.py          # graph.compile()
├─ app/
│   ├─ main.py           # US-007, US-014~US-016: Streamlit 진입점
│   └─ ui_components.py  # 카드/사이드바 헬퍼
├─ db/
│   ├─ schema.sql
│   └─ laptops.db        # 적재 후 생성
├─ tests/                # 단위 테스트 (Node D, parser, state)
├─ .env.example
├─ requirements.txt
├─ requirements-dev.txt
├─ .markdownlint.json
└─ README.md
```

### 7.7 LangGraph 그래프 빌드 패턴 — Cycle 의 실제 의미 (m-9)

LangGraph 의 "Cycle" 은 **단일 invoke 안의 무한 루프가 아니라**, **세션 간 다중 invoke 의 반복**으로 구현한다. 사용자 발화 단위로 그래프가 한 번씩 invoke 되며, State 는 Streamlit 의 `st.session_state` 가 보관·재주입한다.

**그래프 토폴로지 (단일 invoke 기준)**

```
ENTRY → Node B (충분성 평가) ┬─ [is_complete=True]  → Node D → Node E → Node F → END
                              └─ [is_complete=False] → Node C → END
                                                                  ▲
                                                                  └── 사용자 다음 발화 시 새 invoke 가
                                                                       ENTRY 부터 다시 시작 (외부 Cycle)
```

- **Node A 는 그래프 외부**(Streamlit UI). LangGraph 노드가 아니므로 그래프 내 엣지로 연결하지 않음.
- **사이클의 실체**: 매 사용자 발화 시 `graph.invoke(state)` 가 호출되고 반환 State 가 다시 `st.session_state["chat_state"]` 에 저장된다 — 이로써 외관상 무한 사이클이 형성된다. LangGraph 자체는 매번 단방향(ENTRY→END) 으로만 실행된다.
- **분기 구현**: `add_conditional_edges("B", route_fn, {"complete": "D", "incomplete": "C"})`. C 와 F 는 둘 다 `END` 로 향한다.
- **`turn_count` 안전장치(FR-16)**: Node B 진입 시점에서 검사 — `turn_count > 20` 이면 `route_fn` 이 강제로 `"complete"` 분기를 반환하여 부분 슬롯 모드(FR-13) 로 Node D 진입.
- **체크포인터**: 본 PRD 범위에서는 `MemorySaver` 미사용 — Streamlit `session_state` 가 사실상 체크포인터 역할. 페이지 새로고침 시 손실(NG-12) 허용.

---

## 8. Success Metrics

| ID | 지표 | 목표값 | 측정 방법 |
|----|------|--------|-----------|
| **SM-1** | 9개 조건 평균 수집 턴 수 | **≤ 6턴** | 페르소나 시뮬레이션 10회 평균(scripted user) |
| **SM-2** | 9개 조건 충족 후 추천 1건 이상 반환율 | **≥ 90%** | 동일 시뮬레이션에서 `len(candidates) >= 1` 비율 |
| **SM-3** | 단일 사용자 응답 처리 시간 (LLM 제외) | **≤ 1초** | Node A 입력 ~ Node F 출력의 LLM 외 구간 합계 |
| **SM-4** | 단일 사용자 응답 처리 시간 (LLM 포함) | **≤ 5초** | 위와 동일하되 LLM 호출 시간 포함 |
| **SM-5** | 다나와 raw fetch ≥350건 → DB 적재 ≥300건까지 총 소요 시간 | **≤ 5분** | `python -m crawler.fetch --limit 350 && python -m crawler.load` 실측 |
| **SM-6** | DB 적재 데이터 품질 (가격·CPU·램·저장 결측 0%) | **결측 행 = 0** | `SELECT COUNT(*) WHERE price_krw IS NULL OR cpu IS NULL OR ram_gb IS NULL OR storage_gb IS NULL` |
| **SM-7** | LLM JSON 스키마 위반율 | **≤ 5%** | Node B/D LLM 응답 100회 중 위반 횟수 |
| **SM-8** | SQL 인젝션 페이로드 방어율 | **100%** | 인젝션 단위 테스트 10건 모두 통과 |
| **SM-9** | 1분 안에 신규 환경에서 기동 | **≤ 60초** | `pip install`(캐시된 휠 가정) + `streamlit run` 합산 |
| **SM-10** | 노드 전환 로그 누락율 | **0%** | 1회 대화당 진입·이탈 로그 쌍 누락 0 |
| **SM-11** | 1회 추천 사이클당 LLM 호출 횟수 | **≤ 8회** | Solar API 호출 카운터 (사이드바 디버그 패널에 누적 표시 — §7.3) |
| **SM-12** | 1회 추천 사이클당 LLM 토큰 사용량 (input + output) | **≤ 6,000 tokens** | LLM 응답 메타데이터의 `usage.total_tokens` 누적 합산 |

---

## 9. Open Questions

- **OQ-1.** 추천 결과 0건일 때 **자동 조건 완화 후 재조회**(예: 가격 +10% 완화) 를 v2 로 추가할 것인가? 본 PRD는 안내만 한다.
- **OQ-2.** Solar LLM `solar-pro` 와 `solar-1-mini-chat` 의 비용·품질 차이를 실측한 후 노드별 모델 라우팅을 자동화할 것인가?
- **OQ-3.** 사용자가 같은 슬롯 값을 **수정**할 때(예: "예산을 200만원으로 올릴게요") 의도를 정확히 감지하는 임계값/룰을 어떻게 정할 것인가? 현재는 LLM 의 자체 판단에 위임.
- **OQ-4.** 다나와 1페이지 정적 + 2페이지 이후 AJAX 의 응답 구조가 다를 가능성 — 동일 파서로 모두 처리 가능한지 US-001 의 진단 결과로 확정 필요.
- **OQ-5.** 다나와 robots.txt 가 카테고리 페이지 크롤을 제한할 경우의 대안(공식 API 가 있는지, 또는 다른 정보원: 에누리, 쿠팡 등)을 어떻게 결정할 것인가?
- **OQ-6.** Playwright 폴백 시 브라우저 컨텍스트 동시성을 3 으로 둔 근거 — 측정 후 5~7 로 상향 가능 여부 확인 필요.
- **OQ-7.** 9개 조건 중 "밝기(nits)" 는 다나와 목록 페이지에 결측이 잦을 가능성 — 이 경우에도 "전부 필수" 정책을 고수할지, 또는 사용자 슬롯에는 받되 DB 필터링에서는 NULL 허용으로 완화할지 결정 필요. (현재 PRD: 슬롯 수집은 필수, DB 필터에서는 `(brightness_nits IS NULL OR brightness_nits >= ?)` 로 NULL 허용)
- **OQ-8.** 사이드바 "대화 초기화" 외에 "조건만 초기화"(이력은 유지) 버튼이 필요한가?
- **OQ-9.** Upstage Solar 의 OpenAI 호환 엔드포인트가 `response_format={"type":"json_object"}` (JSON 모드) 를 실제로 지원하는지 — 1차 스파이크 테스트 1건 실행 후 결정. 미지원 시 §7.3 의 명시적 JSON 스키마 + Pydantic 파싱 폴백을 기본 경로로 채택.
- **OQ-10.** `langchain-upstage` 패키지의 안정성·버전 호환성 — `ChatUpstage` API 가 `langchain-core` 최신과 충돌하지 않는지 확인. 충돌 시 §7.3 의 `langchain-openai` 백업 경로를 1차로 격상.

---

## 부록 A. 9가지 스펙 슬롯 정의 (PRD 자가 검증용)

| # | 슬롯 키 | 타입 | 단위/형식 | DB 컬럼 | Node D 비교 연산자 |
|---|---------|------|-----------|---------|---------------------|
| 1 | `screen_inch` | float | inch | `screen_inch` | `BETWEEN ?-1 AND ?+1` |
| 2 | `weight_kg` | float | kg | `weight_kg` | `<= ?` |
| 3 | `os` | str | enum 문자열 | `os` | `LIKE ?` |
| 4 | `resolution` | str | "WxH" | `resolution` | `= ?` |
| 5 | `brightness_nits` | int | nits | `brightness_nits` | `(NULL OR >= ?)` |
| 6 | `cpu` | str | 자유 문자열 | `cpu` | `LIKE ?` |
| 7 | `ram_gb` | int | GB | `ram_gb` | `>= ?` |
| 8 | `storage_gb` | int | GB | `storage_gb` | `>= ?` |
| 9 | `price_krw` | int | KRW | `price_krw` | `<= ?` |

---

## 부록 A.1. 사용자 표현 → Canonical 값 정규화 매핑 (Node B 책임)

> Node B 는 LLM 추출 결과에 다음 룰베이스 매핑을 **후처리로 적용**하여 슬롯 값을 canonical 형태로 저장한다. LLM 이 자유 형식으로 답해도 결정론적 매핑이 우선 적용되므로 Node D 의 SQL 변환이 단순해진다.

### A.1.1 해상도 매핑

| 사용자 표현 | Canonical `WxH` |
|---|---|
| FHD, 풀HD, 1080p | `1920x1080` |
| WUXGA | `1920x1200` |
| HD+ | `1600x900` |
| QHD, 2K, 1440p | `2560x1440` |
| WQXGA | `2560x1600` |
| UHD, 4K, 2160p | `3840x2160` |
| (그 외 `WxH` 형식 직접 입력) | 입력 원문 그대로 |

### A.1.2 OS 매핑

| 사용자 표현 | Canonical (DB 매칭 키워드) |
|---|---|
| 윈도우, Windows, 윈11, Win11, 윈10 | `Windows` |
| 맥, 맥OS, macOS, OSX | `macOS` |
| 프리도스, FreeDOS, 도스 | `FreeDOS` |
| 리눅스, Linux, 우분투, Ubuntu | `Linux` |

### A.1.3 CPU 키워드 추출 (Node D `LIKE %키워드%`)

| 사용자 표현 | 추출 키워드 |
|---|---|
| "i5", "코어 i5" | `i5-` |
| "i5-1340P" | `i5-1340P` |
| "M2", "애플 M2" | `Apple M2` |
| "라이젠 7", "Ryzen 7" | `Ryzen 7` |
| 미매칭 자유 문자열 | 입력 원문 |

### A.1.4 단위 추출 / 변환

| 슬롯 | 사용자 표현 → 값 |
|---|---|
| `weight_kg` | "1.3kg" / "1.3키로" / "1300g" → `1.3` |
| `screen_inch` | "15인치" / "15.6\"" / "15in" → `15.0` / `15.6` |
| `ram_gb` | "16GB" / "16기가" → `16` |
| `storage_gb` | "512GB" → `512` / "1TB" → `1024` |
| `price_krw` | "150만원" / "150만" / "1,500,000원" → `1500000` |
| `brightness_nits` | "300nit" / "300니트" → `300` |

---

## 부록 B. LangGraph 노드 ↔ FR / US 매트릭스 (자가 검증용)

| Node | 책임 | 관련 US | 관련 FR |
|------|------|---------|---------|
| **A. 사용자 입력** | Streamlit `st.chat_input` 수집 | US-007 | FR-21, FR-22 |
| **B. 충분성 평가** | LLM, 9개 슬롯 추출·갱신·분기 | US-006, US-008 | FR-10, FR-11, FR-19 |
| **C. 추가 질문 생성** | LLM, 자연어 후속 질문 → A로 복귀 | US-009, US-013 | FR-12 |
| **D. SQL 변환** | LLM(+폴백), 9개 슬롯 → WHERE | US-010 | FR-13, FR-19, FR-20 |
| **E. DB 조회** | sqlite3, 결정론적 도구 | US-011 | FR-14 |
| **F. 응답 생성** | LLM, 자연어 추천(+0건 안내) + UI 렌더 | US-012, US-014 | FR-15, FR-23 |
| **루프 제어** | Conditional Edge + 안전장치 | US-013 | FR-9, FR-16 |

---

## 자가 검증 체크리스트 (저장 직전)

- [x] 사전 질문(객관식)에 대한 사용자 답변(1D, 2B, 3A, 4A, 5D)을 PRD에 반영했는가? → §0
- [x] 9개 섹션이 모두 존재하는가? → §1~§9
- [x] 모든 User Story가 한 세션 내 구현 가능한 작은 단위인가? → US-001~US-020
- [x] Acceptance Criteria가 모두 검증 가능한 문장인가? (관찰 가능한 입출력으로 기술)
- [x] FR-1 ~ FR-29 가 중복·누락 없이 부여되었는가?
- [x] Non-Goals(NG-1 ~ NG-13)가 범위를 명확히 닫는가?
- [x] 9가지 스펙(화면 인치/무게/OS/해상도/밝기/CPU/램/저장/가격)이 모두 PRD에 등장하는가? → 부록 A
- [x] LangGraph 노드 A~F 와 순환 루프 흐름이 FR/US로 빠짐없이 표현되었는가? → 부록 B
- [x] 파일 경로 `tasks/prd-laptop-recommendation-chatbot.md` 로 저장되었는가? → 본 파일
