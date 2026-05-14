# 발표 Q&A — review-ops-agent

평가위원·청중이 자주 물어볼 만한 질문과 미리 준비한 답변. 발표 후 Q&A 시간에 활용.

> **사용법**:
> - 발표 현장에서는 *짧은 답 (30초)* 위주로 대응
> - 시간 여유 시 *보충 답변* 추가
> - 모르는 질문 → "측정 안 했습니다. 발표 후 fact check 해서 메일로 답변드리겠습니다" — 추측 회피

---

## 카테고리 1 — 기술 결정

### Q1. 왜 Solar Pro 2 인가요? Claude/GPT 는 안 됐나요?

**짧은 답**:
한국어 작업이라 Ko-MT-Bench 81.0 점수를 보유한 Solar 를 선택했습니다. 초기 v1 은 Claude CLI subprocess 였는데 cold start 12초씩 들어 데모 흐름이 끊겼습니다. v2 에서 Solar API 로 옮기면서 건당 1~2초로 6배 빨라졌습니다.

**보충 답변**:
Solar 가 OpenAI 호환이라 `bind_tools`, `response_format=json_schema` 같은 LangChain 표준 surface 를 그대로 썼습니다. 모델 종속성을 낮춰서 추후 GPT/Claude 로 교체할 때 비용이 최소입니다. SOMA 16만원 크레딧으로 학습·평가·데모 모두 충분했습니다.

**근거**: `docs/LANGGRAPH-LEARNING.md` §11 (LLM backend 두 번의 마이그레이션), `src/llm/upstage.py`

---

### Q5. LangGraph 가 아니라 일반 Python state machine 이나 LangChain Expression Language (LCEL) 로 같은 걸 할 수 있지 않나요?

**짧은 답**:
기술적으로는 가능합니다. 다만 LangGraph 의 4 가지가 결정적이었습니다 — conditional edge 의 *그래프 시각화*, `Annotated[..., add]` reducer 자동 누적, cross-thread Memory Store 의 multi-tenant 기본값, `create_react_agent` prebuilt 의 5줄 챗 agent.

**보충 답변**:
직접 짰으면 *trace 인프라* 만 며칠 걸렸을 겁니다. 특히 평가·디버깅 측면에서 노드 단위 trace 가 자동으로 누적되는 게 학습·발표 양면에서 큰 이득입니다. LCEL 은 chain 표현엔 좋지만 *조건 분기·persistence* 가 약합니다.

**근거**: `docs/LANGGRAPH-LEARNING.md` Part 1 (LangGraph 6 surface), `src/graph/build.py`

---

### Q6. 왜 main / batch / chat 3 graph 로 분리했나요? 한 graph 로 다 할 수 없나요?

**짧은 답**:
한 graph 에 모든 트리거를 넣으면 *conditional edge 폭발* 합니다. "fetch 모드 vs batch 모드 vs chat 모드" 분기를 매번 따져야 해서 분기 함수가 복잡해집니다. 트리거·입력·출력이 다른 흐름은 *별개 graph* 가 자연스럽습니다.

**보충 답변**:
3 graph 분리로 각자 *학습 surface* 도 명확해졌습니다 — main 은 conditional Router·Memory Store, batch 는 Tool use·Streaming, chat 은 create_react_agent prebuilt. 공유 utility (Memory Store, SQLite) 는 graph 외부에 두면 중복 없습니다. 발표 시 *각 graph 가 어떤 surface 를 시연하는지* 가 깔끔하게 매핑됩니다.

**근거**: `docs/LANGGRAPH-LEARNING.md` §14 (3개의 graph 분리)

---

## 카테고리 2 — 아키텍처·안전성

### Q2. Memory Store JSON dump 가 atomic 하지 않으면 데이터 손실 위험 없나요?

**짧은 답**:
네 정확한 지적입니다. 현재는 매 write 후 전체 dump 라 *중간 종료 시 lost write* 가능성이 있습니다. 데모/MVP 범위에서는 받아들였고, 운영 단계에선 LangGraph 의 `PostgresStore` 같은 트랜잭션 backend 로 교체 예정입니다.

**보충 답변**:
*Primary 사실* (리뷰·답글·분류) 은 SQLite WAL 모드에 저장돼 손실 위험이 매우 낮습니다. Memory Store 에 저장되는 건 *톤 샘플·메타·feedback hint* 같은 *부가 컨텍스트* 라 dump 1회 lost 가 critical 하지 않습니다. 실제 운영 시점에는 namespace 별 atomic write 또는 SQLite-backed Store 로 교체합니다.

**근거**: `src/store/memory.py:save_dump`, `migrations/001_init.sql` (WAL), `docs/spec/02-data-model.md`

---

### Q3. 매장 간 데이터가 섞일 위험은 없나요?

**짧은 답**:
3 단 방어로 막았습니다. 첫째, Memory Store namespace 의 *첫 차원이 place_id* 라 다른 매장 조회 자체가 불가능합니다. 둘째, SQLite 의 모든 read/write 함수가 `place_id` 인자를 강제합니다. 셋째, chat agent tool 은 factory 패턴 closure 로 place_id 주입.

**보충 답변**:
코드 수준에서 bypass 가 *구조적으로* 불가능하도록 설계했습니다. `make_chat_tools(place_id)` 가 closure 로 묶어 tool 호출 시 매장 ID 를 받지 않아도 격리됩니다. 사장이 다른 매장에 잘못 입력해도 데이터가 흘러갈 길이 없습니다.

**근거**: `src/store/memory.py:get_*` (namespace prefix), `src/graph/chat/tools.py:make_chat_tools`, `docs/LANGGRAPH-LEARNING.md` §16 (Multi-tenant 격리 기본값)

---

### Q10. SQLite 로는 scale 한계가 있을 텐데, Postgres 로 언제 전환하시나요?

**짧은 답**:
매장 100 곳 / 일 1만 건 리뷰까지는 SQLite WAL 로 충분합니다. 그 이상에서 동시 write 락이 병목이 되면 Postgres 또는 D1 으로 전환합니다. ORM 없이 *함수 단위 추상화* 되어 있어 backend 교체 비용은 `src/store/sqlite.py` 한 파일.

**보충 답변**:
LangGraph 의 `PostgresStore` 도 cross-thread Memory Store 의 production 대안이라 함께 전환됩니다. 현재 Docker compose 의 `./data` 볼륨 마운트도 그 시점에 Postgres 컨테이너로 교체 예정. 측정 기반 전환 — 매 write 평균 latency 200ms 초과를 임계로 잡고 있습니다.

**근거**: `src/store/sqlite.py`, `migrations/`, PROPOSAL.md

---

## 카테고리 3 — 평가·검증

### Q4. 실제 사장님 대상 사용성 테스트는 했나요?

**짧은 답**:
정식 사용성 테스트는 진행 중이고, 골든셋 50건은 팀 5명이 cross-label 해 Fleiss kappa 로 합의도를 측정했습니다. 사용성은 *무가이드 5분 내 완료* 를 목표로 하되 발표 기준 측정값은 아직 없습니다.

**보충 답변**:
데모 시나리오로는 원클릭 데모 리셋부터 답글 수정 → 톤 학습 가시화까지 매끄럽게 흐르도록 다듬었습니다. 발표 후 *실제 자영업자 5명 대상* shadow test 를 계획 중입니다. 측정 항목은 (1) 무가이드 5분 완료율 (2) 답글 채택률 (3) 톤 학습 체감도 (전/후 비교).

**근거**: PROPOSAL.md, `docs/demo/scenarios.md`

---

### Q7. 골든셋 50건이 모집단 대표성 측면에서 부족하지 않나요?

**짧은 답**:
네, *MVP 검증* 수준이라는 한계는 인정합니다. 50건은 5 카테고리 × 3 sentiment × 다양한 매장 업종으로 stratified sampling 했고, 5명 cross-label Fleiss kappa 로 합의도 검증을 거쳤습니다.

**보충 답변**:
스케일 업 단계에서는 (1) 네이버·카카오맵 공개 리뷰 크롤링 후 500~1000건 확장 (2) 매장 업종별 (카페·식당·미용 등) 별도 평가셋 분리 (3) edge case (욕설·법적 위험·이모티콘 만) 별도 트랙 분리를 계획하고 있습니다. 50건은 *방향성 검증* 용으로 사용했습니다.

**근거**: `docs/spec/06-models-and-evaluation.md`

---

## 카테고리 4 — 비즈니스·확장

### Q8. SOMA Solar 크레딧 소진 후 운영 비용은 어떻게 되나요?

**짧은 답**:
매장 1곳 기준 *월 약 2,000원* 입니다. 일 10건 리뷰 × 노드당 LLM 호출 3회 × Solar Pro 2 단가 ($0.0001/1K input token, 짧은 호출 평균 0.05¢) 기준입니다. 매장 100곳 운영 시 월 20만원.

**보충 답변**:
비용 절감 방안 3가지를 준비했습니다. (1) classifier 노드는 Solar mini 로 다운그레이드 검토 (정확도 골든셋으로 검증 후) (2) 답글 token streaming 비활성화로 latency 감소 (3) batch graph 는 매일 → 매주 1회로 캐싱. 사장님 부담은 *기본 free + 톤 학습·체크리스트만 유료* 구조 검토 중입니다.

**근거**: `docs/spec/06-models-and-evaluation.md`, README 비용 섹션

---

### Q9. 외부 리뷰 플랫폼 (네이버·카카오맵·구글) 연동 계획은요?

**짧은 답**:
현재는 mock JSON 입력이고, 외부 플랫폼 API/크롤링은 *out-of-scope*. 다만 입력 layer 만 교체하면 되도록 graph 는 *입력 source 무관* 으로 설계했습니다.

**보충 답변**:
연동 우선순위는 (1) 네이버 비즈니스 API (공식, 안정) (2) 카카오맵 (사장 권한 토큰) (3) 구글 My Business API. 답글 *자동 발행* 은 별도 단계로 — 사장님 승인 후 1-click publish 를 1차 목표, 자동 발행은 *사용 패턴 안정화 후* 별도 토글. 외부 플랫폼은 ToS 검토와 매장 인증 (Business Verification) 이 선행 필요.

**근거**: PROPOSAL.md (Out-of-scope 섹션), `docs/spec/08-risks-and-deferrals.md`

---

## 추가 — 라이브 데모 중 문제 발생 시

| 상황 | 대응 멘트 |
|---|---|
| Solar API timeout | "지금 timeout 이 걸렸네요. mock 모드로 전환해서 보여드리겠습니다." → `REVIEW_OPS_LLM=mock` 로 재실행 |
| Streamlit hang / freeze | "새로고침 해보겠습니다" → 5초 내 복구 안 되면 미리 녹화한 영상 backup 으로 전환 |
| Mermaid 가 슬라이드에서 안 보임 | "왼쪽이 메인 graph, 가운데가 batch, 오른쪽이 chat agent..." 식으로 *말로 그려가며* 진행 |
| 시연 중 빈 카드 | "기존 시드 데이터 reset 한 상태입니다. 사이드바 '⚠️ 데모 리셋' 클릭으로 복구하겠습니다" |

---

## 빠른 참조 — 한눈 답변

| # | 질문 핵심 | 한 줄 답 |
|---|---|---|
| 1 | 왜 Solar? | Ko-MT-Bench 81 + 호환성 + 비용 |
| 2 | Memory dump atomic? | MVP scope, Postgres 로 교체 예정 |
| 3 | 매장 격리? | 3단 방어, 구조적으로 bypass 불가 |
| 4 | 사용성 테스트? | 골든셋 진행 중, 실사용 테스트 계획 |
| 5 | LangGraph 굳이? | trace 인프라 + multi-tenant 기본값 가치 |
| 6 | 3 graph 분리? | conditional 폭발 회피 + surface 명확 |
| 7 | 골든셋 50건? | MVP 검증, 500건 확장 계획 |
| 8 | 크레딧 후 비용? | 매장당 월 ~2,000원, mini 다운그레이드 검토 |
| 9 | 외부 연동? | 입력 layer 교체만으로 가능하도록 설계 |
| 10 | SQLite scale? | 매장 100곳까지, 임계 측정 후 Postgres |
