# 실시간 UI 상태와 SSE 연동

## UI와 연결되는 AI 상태

AI 파이프라인 상태는 UI에 반드시 드러나야 한다.

추천 상태:

- `수집 중`: RSS에서 새 기사를 가져오는 중
- `요약 중`: AI 요약 생성 중
- `요약 완료`: 홈 카드에 노출 가능
- `검토 필요`: 요약 검증 실패 또는 본문 부족
- `원문만 보기`: 본문 파싱 실패로 요약이 불가능한 상태
- `비공개`: 사용자 신고 또는 검증 실패로 숨김 처리

## 현재 UI와의 연결

현재 UI에서 AI 결과가 들어갈 위치는 다음과 같다.

- 홈 카드: `title`, `source`, `publishedAt`, `summary`, `keywords`, `status`
- 상세 상단: `title`, `source`, `publishedAt`, `originalUrl`
- 상세 본문: `summary`, `importance`, `context`
- 상세 퀴즈: `quiz.items`
- 리포트: `dailyReport.briefing`, `dailyReport.flow`, `dailyReport.headline`, `dailyReport.headlineSourceCount`, `dailyReport.subArticles`, `dailyReport.keywords`

리포트 UI는 C+ 보강형(타임라인 메타포)으로 확정됐다. 상단부터 다음 순서로 구성된다.

1. **헤더** — 큰 날짜 (`reportDate`) + 업데이트 시각 (`reportUpdatedAt`) + 요일 라벨
2. **AI 브리핑 카드** — `briefing`: DailyReportGenerator가 생성하는 오늘 하루 한 줄 요약. 단독 카드로 강조
3. **타임라인 (가장 많이 다뤄진 순)** — 클러스터 크기 기준 정렬된 노드 리스트
   - **헤드라인 노드** (큰 노드, 색상 ring): 1위 클러스터의 최고 importance_score 기사. 본문 미리보기 + `headlineSourceCount`개 매체 dots 시각화
   - **서브 노드 1~2개** (작은 노드): 2~3위 클러스터의 헤드라인과 다른 카테고리 기사. 한 줄 제목 + `source_count`개 매체 텍스트
4. **오늘의 흐름** — `flow`: 카테고리별 한 줄 요약 (TrendSummarizer 출력). 카테고리 라벨에 카테고리 컬러 적용
5. **오늘의 키워드** — `keywords`: 빈도 차등 클라우드. `data-w` 속성(2~9)으로 사이즈/불투명도 단계 표시
6. **마침표** — 점선 디바이더 + 체크 아이콘 + 다음 업데이트 안내 한 줄

타임라인의 시간 표시는 `tl-time` 필드에 들어가지만, "타임라인" 메타포보다 "가장 많이 다뤄진 순" 정렬이 우선이다. 시간 데이터가 좁게 모이는 날에도 메타포가 깨지지 않도록 헤더는 "가장 많이 다뤄진 순"으로 명시한다.

현재는 정적 예시 데이터로 채워져 있으며, 다음 단계는 실제 API 응답 형태에 맞춰 동적 데이터로 교체하는 것이다. 상태 UI(요약 중, 검토 필요 등)도 홈 카드와 상세 페이지에 추가 필요하다.

## 홈 로딩 화면 — 실시간 진행률 연동

기존의 "관심 카테고리 확인 / 주요 뉴스 수집 / AI 요약 생성" 3단계 텍스트 표시는 백엔드 진행률과 무관한 연출이었다. 사용자에게 신뢰를 주려면 실제 LangGraph 노드 진행을 SSE 또는 WebSocket으로 흘려 프론트에서 카운터로 갱신해야 한다.

### UI 단계 매핑

UI는 두 단계만 노출한다. (카테고리 확인은 DB 조회로 즉시 끝나므로 표시하지 않는다.)

| UI 단계 | LangGraph 노드 | 카운터 단위 |
|---|---|---|
| 주요 뉴스 수집 | Collector + Deduplicator | `N / 12 매체` (RSS 피드 수) |
| AI 요약 생성 | ArticleExtractor + Summarizer + SummaryValidator | `N / 8 기사` (당일 처리 대상 수) |

`12 매체`, `8 기사`는 예시 값이며, 실제로는 백엔드가 첫 이벤트로 `total`을 알려준 뒤 `current`를 점진 갱신한다.

### 권장 SSE 이벤트 스키마

```
event: step  data: {"step": "collect", "current": 0, "total": 12}
event: step  data: {"step": "collect", "current": 7, "total": 12}
event: step  data: {"step": "collect", "current": 12, "total": 12}
event: step  data: {"step": "summarize", "current": 0, "total": 8}
event: step  data: {"step": "summarize", "current": 3, "total": 8}
event: step  data: {"step": "summarize", "current": 8, "total": 8}
event: done  data: {"articleIds": [...]}
```

### LangGraph 연동 방법

LangGraph는 `astream_events` API를 통해 노드 진입/종료 이벤트를 노출한다. 백엔드는 이를 구독하여 위 SSE 스키마로 변환한다.

```python
async def stream_pipeline(user_id: str):
    yield sse("step", {"step": "collect", "current": 0, "total": len(feeds)})
    collected = 0
    async for event in graph.astream_events({"userId": user_id}, version="v2"):
        kind = event["event"]
        node = event.get("name")

        if kind == "on_chain_end" and node == "Collector":
            collected += 1
            yield sse("step", {"step": "collect", "current": collected, "total": len(feeds)})

        if kind == "on_chain_start" and node == "Summarizer":
            # 첫 Summarizer 진입 시 collect 100% 마감 + summarize 시작 알림
            ...

        if kind == "on_chain_end" and node == "SummaryValidator":
            summarized += 1
            yield sse("step", {"step": "summarize", "current": summarized, "total": total_articles})

    yield sse("done", {"articleIds": result_ids})
```

### 프론트 연동

현재 `script.js`의 `startHomeLoading`은 ease-out cubic 애니메이션으로 카운터를 mock한다. 실제 연동 시에는 mock 부분을 `EventSource` 구독으로 갈아끼우면 된다. DOM 구조(`.loading-step[data-step] [data-cur] / [data-total] / .loading-step-bar span`)는 그대로 재사용한다.

```js
const es = new EventSource("/api/refresh-stream");
es.addEventListener("step", (e) => {
  const { step, current, total } = JSON.parse(e.data);
  const el = document.querySelector(`.loading-step[data-step="${step}"]`);
  if (!el) return;
  el.classList.add("is-active");
  el.querySelector("[data-cur]").textContent = current;
  el.querySelector("[data-total]").textContent = total;
  el.querySelector(".loading-step-bar span").style.width = `${(current / total) * 100}%`;
  if (current === total) {
    el.classList.remove("is-active");
    el.classList.add("is-done");
  }
});
es.addEventListener("done", () => {
  document.querySelector('[data-page="home"]').classList.replace("is-loading", "is-loaded");
  es.close();
});
```

### 실패 처리

- 특정 매체 수집 실패: `current`는 그대로 두고 `event: warn`으로 별도 알림 (UI는 진행률에 영향 없이 진행)
- 요약 검증 실패 (`review_required` 또는 `skip`): `summarize` 카운트에는 포함하되, 최종 `done` 응답에서 제외
- 전체 파이프라인 타임아웃: `event: error` → 프론트는 로딩 화면 숨기고 "잠시 후 다시 시도" 빈 상태로 전환
