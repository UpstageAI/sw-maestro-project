# 데모 영상 대본 (5막 · 약 4:00)

> Upstage Solar API (~1-2s/call) 기준 시간축. 영상 4분 권장.
> 막마다 시간 / 화면 액션 / narration / 자막을 한 표로 정리.

화면 캡처 영역: Streamlit 브라우저 (1920×1080). 자막은 영상 하단에 burn-in.

---

## 1막 — 인트로 (0:00 – 0:25)

| 시간 | 화면 | Narration / 자막 |
|---|---|---|
| 0:00 – 0:08 | README 상단 + Mermaid main_graph PNG | "안녕하세요. 소상공인 리뷰 응대 멀티 Agent 시스템입니다." |
| 0:08 – 0:16 | Mermaid 다이어그램 강조 | "LangGraph 위에 Router · Memory Store · Streaming · Tool use 네 가지 surface가 동작합니다." |
| 0:16 – 0:25 | 화면 전환 → Streamlit `localhost:8501` | "데모 매장은 카페 A 와 식당 B, 두 매장으로 구성. 시연 시작합니다." |

---

## 2막 — 시나리오 1: 마감 후 5건 처리 (0:25 – 1:50)

| 시간 | 화면 | Narration / 자막 |
|---|---|---|
| 0:25 – 0:35 | 사이드바 PLACE_001 라디오 + `🍽️ 메뉴 7개`·`🎭 톤 샘플 3개` expander 펼침 | "사이드바에서 매장 메뉴 7개와 과거 톤 샘플 3개를 미리 확인합니다." |
| 0:35 – 0:42 | `🔁 새 리뷰 5건 가져오기` 클릭 → 진행 패널 등장 | "5건 가져오기 클릭. 진행 패널이 등장합니다." |
| 0:42 – 1:05 | 노드 단계 로그 expander 펼친 상태에서 진행률 차오름 | "Solar API 라 진행률이 빠르게 차오릅니다. load_context, pii_mask, classifier, router, drafter, memory_save 6단계가 한 review 당 약 5초 소요." |
| 1:05 – 1:18 | 첫 카드의 graph trace 표 강조 | "graph trace 표를 보면 classifier 가 약 2초 걸려 negative, 신뢰도 0.95, 카테고리 대기시간으로 분류했습니다." |
| 1:18 – 1:30 | classifier 행 `📜 prompt/응답` toggle ON | "LLM 노드의 prompt 미리보기로 system + user prompt 가 그대로 보이고, response_format 이 JSON schema 로 검증됐습니다." |
| 1:30 – 1:40 | `🔀 route_by_sentiment` toggle ON | "Router 분기 결정도 trace 에 남습니다. 신뢰도 0.95 가 임계값 0.7 을 넘으니 apology_drafter 로 갔어요." |
| 1:40 – 1:50 | 부정 카드 `✏️ 수정` → 일부 다듬기 → `💾 저장 + 톤 학습` | "사장님이 답글을 살짝 다듬어 저장하면 백그라운드로 Solar 가 AI 원본과 사장 수정본 차이를 한 줄로 요약. 사이드바 톤 샘플이 4개로 갱신됐습니다." |

---

## 3막 — 시나리오 2: 누적 분석 + Tool use (1:50 – 2:35)

| 시간 | 화면 | Narration / 자막 |
|---|---|---|
| 1:50 – 1:58 | `📊 TOP 3 + 체크리스트 새로고침` 클릭 → batch graph 진행 | "이번엔 TOP 3 + 체크리스트 새로고침 버튼. 별도 batch graph 가 약 10초 만에 끝납니다." |
| 1:58 – 2:08 | 결과 카드 등장: TOP 3 + 체크리스트 | "최근 4주 부정 카테고리 TOP 3 — 대기시간 7회, 위생 5회, 가격 3회. 매장 메뉴까지 반영한 체크리스트 5개." |
| 2:08 – 2:25 | `🔍 batch graph trace` 펼침 → `pattern.llm_decide` + `pattern.sql_tool` toggle ON | "trace 를 보면 LLM 이 먼저 query_review_stats tool 을 호출하기로 *결정* 했고, args = {place_id, group_by: category, days: 28} 도 LLM 이 직접 정했어요. 그 결과를 받아 자연어로 정리한 게 두 번째 LLM 호출입니다." |
| 2:25 – 2:35 | `pattern.llm_summarize` toggle ON → 응답 미리보기 | "LangGraph Tool use 패턴 — LLM 이 데이터 직접 안 보고 도구를 우회 호출하는 구조죠. ChatUpstage.bind_tools 로 OpenAI 호환 tool calling 그대로 동작." |

---

## 4막 — 시나리오 3: 매장 톤 학습 비교 (2:35 – 3:35)

| 시간 | 화면 | Narration / 자막 |
|---|---|---|
| 2:35 – 2:43 | 사이드바 라디오 → 식당 B 전환 | "이번엔 매장을 식당 B 로 전환. 신규 매장이라 메뉴도 톤 샘플도 0개입니다." |
| 2:43 – 3:00 | `➕ 사장님 답글 직접 추가` expander → form 입력 | "사장님이 과거 작성하셨던 답글을 form 으로 시드합니다. 리뷰와 답글, 카테고리, drafter 종류 입력." |
| 3:00 – 3:10 | `➕ 톤 샘플 추가` 클릭 → 사이드바 갱신 (출처 `✍️ 수동 추가`) | "톤 샘플 1개로 갱신, 출처가 '수동 추가' 로 표시됩니다." |
| 3:10 – 3:25 | (선택) 식당 B 새 리뷰 1건 fetch → 답글이 새 톤 반영 | "이제 새 리뷰를 처리하면 Drafter prompt 에 이 톤 샘플이 자동 주입돼서 답글이 사장 톤에 맞게 나옵니다." |
| 3:25 – 3:35 | 사이드바 라디오 → 카페 A 로 다시 전환 → 톤 샘플 4개 확인 | "다시 카페 A 로 돌아가도 톤 샘플 4개 그대로. Memory Store 가 (place_id, kind) namespace 라 매장끼리 자동 격리됩니다." |

---

## 5막 — 회고 (3:35 – 4:00)

| 시간 | 화면 | Narration / 자막 |
|---|---|---|
| 3:35 – 3:43 | `src/graph/build.py` 코드 일부 (`graph = build_graph()` 강조) | "이 프로젝트는 노드 7개, conditional edge 1개, tool 1개로 구성됩니다." |
| 3:43 – 3:55 | README "Agent 주요 요소" 표 강조 | "Upstage Solar API 와 langchain-upstage 로 한국어 답글이 자연스럽고, 16만원 free credit 으로 비용 부담 없이 학습·발표 모두 처리. Router · Memory Store · Streaming · Tool use 네 가지 surface 가 모두 살아 있습니다." |
| 3:55 – 4:00 | 검은 화면 + 팀 크레딧 (소마 17기 57조) | "감사합니다." |

---

## 영상 편집 권장

- LLM 응답 (~2s/call) 은 *컷 없이 그대로* — 진행 패널이 매끄럽게 차오르는 모습이 streaming surface 의 핵심.
- 마우스 hover 시 1초 정지 — 시청자가 클릭 위치 인식할 시간.
- 자막 위치: 영상 하단 중앙, 80px 높이 검은 띠 + 흰색 텍스트.
- 한국어 폰트: Pretendard 또는 Noto Sans KR.

## 시간 합산

| 막 | 시작 | 종료 | 길이 |
|---|---|---|---|
| 1 인트로 | 0:00 | 0:25 | 0:25 |
| 2 시나리오 1 | 0:25 | 1:50 | 1:25 |
| 3 시나리오 2 | 1:50 | 2:35 | 0:45 |
| 4 시나리오 3 | 2:35 | 3:35 | 1:00 |
| 5 회고 | 3:35 | 4:00 | 0:25 |
| **총** | | | **4:00** |

Upstage Solar API 속도 (~1-2s/call) + 컷 편집 최소화로 자연스러운 흐름.
