---
title: 08 — Risks & Deferrals
related:
  - 00-overview.md
  - 01-langgraph-architecture.md
  - 06-models-and-evaluation.md
  - CHANGES-FROM-PROPOSAL.md
last_updated: 2026-05-08
---

# Risks & Deferrals

이 문서는 (1) 알려진 리스크와 mitigation, (2) **의도적으로 채택하지 않은** 후보들의 사유 — 두 가지를 기록합니다. 평가·회고 시 "왜 안 했나"에 답하기 위함.

## 알려진 리스크

### R1. Haiku 한국어 답글 품질이 부족할 수 있음

- **확률**: 중. Haiku 4.5는 분류·요약은 강하지만 *창의적 한국어 작성*은 Sonnet 대비 검증 부족.
- **영향**: 답글 부자연·과한 정중체로 사장 만족도 저하. KPI "답글 사용 의향 ≥ 70%" 미달.
- **Mitigation**: W1 D5 골든셋 평가에 *답글 적합성* 사람 평가 (5점 척도, 5명 평균) 포함. < 4.0 이면 W2 D1에 apology drafters만 Sonnet 4.6 승격. 비용 영향 미미 ([`06`](./06-models-and-evaluation.md) 참고).

### R2. 골든셋 50건이 부족

- **확률**: 낮음. 단 자체 작성이라 외부 검증 부족.
- **영향**: 평가 KPI 신뢰도 저하. 평가자(SOMA)가 "외부 데이터셋 없는 평가는 자위 아닌가" 질문 가능.
- **Mitigation**: 5명 cross-label + Fleiss kappa ≥ 0.6 명시 → "팀 내 일관성 확보된 평가셋"으로 포지셔닝. AIHub fallback은 [`06`](./06-models-and-evaluation.md) 참고 (의도적 미채택).

### R3. Multi-tenant 코드와 단일 매장 demo의 갭

- **확률**: 낮음.
- **영향**: 평가자가 "왜 multi-tenant 코드인데 데모는 단일?" 질문 시 의도 설명 필요.
- **Mitigation**: 발표에서 "코드는 확장성 위해 multi-tenant, 시연은 임팩트 위해 단일 매장 집중"임을 명시. sidebar 매장 전환 1회만 포함 (PLACE_002 신규 매장 → namespace 격리 시연).

### R4. mock 데이터의 timestamp 분포 부적절

- **확률**: 중. mock 50건 중 4주 윈도우에 부정 리뷰가 충분히 분포해야 PatternAgent의 TOP 3가 의미 있게 나옴.
- **영향**: PatternAgent 출력이 "데이터 부족" 또는 "TOP 1만 의미 있음" 형태 → 데모 임팩트 저하.
- **Mitigation**: W1 D2 골든셋 작성 시 부정 리뷰 22건의 카테고리 분포를 의도적으로 (대기시간 8건, 위생 6건, 가격 4건, 서비스 3건, 맛 1건) 비대칭으로 작성 → TOP 3가 명확히 나오도록.

### R5. Streamlit re-run 모델로 인한 graph 상태 손실

- **확률**: 중.
- **영향**: 사장이 답글 카드에서 [수정] 클릭 시 Streamlit 재실행 → graph는 이미 종료 상태라 영향 없음 (의도된 설계). 단 *진행 중인 graph stream*이 재실행 중간에 끊길 수 있음.
- **Mitigation**: graph는 1 review = 1 invocation으로 짧음 (~3~5초). 실행 중에는 Streamlit 위젯 disable. `st.session_state["processing"] = True` 가드.

### R6. SQLite DB lock (다중 process 동시 쓰기)

- **확률**: 매우 낮음 — 단일 프로세스이므로 거의 발생 안 함. diff hint 비동기 thread만 쓰기 가능.
- **Mitigation**: `aiosqlite` 또는 thread-safe lock. 단순화하려면 diff hint 호출도 main thread에서 sync로 (UX 영향 미미, 1초 미만 추가).

### R7. 발표날 라이브 시연 실패 (네트워크·API)

- **확률**: 중.
- **Mitigation**: recorded screencast (W2 D4 작성), Anthropic API 키 백업, 발표 직전 DB reset. [`07`](./07-team-and-demo.md) "데모 안전망" 참고.

### R8. 팀 분담이 노드 경계 안에서 충돌

- **확률**: 낮음.
- **영향**: 멤버 B (Drafter)가 매장 메타·tone_samples에 의존, 멤버 D (UI + Memory Store)가 같은 객체에 의존 → 인터페이스 동기화 필요.
- **Mitigation**: W1 D1에 **State TypedDict + Memory Store wrapper API**를 본인이 먼저 fix → 다른 멤버는 그 인터페이스만 보고 작업. 변경은 PR + 본인 승인 필수.

## 의도적으로 채택하지 않은 후보 (Deferrals)

학습-only 렌즈로 결정. 각 항목은 PROPOSAL.md 또는 인터뷰 라운드에서 거론된 후 *의도적으로* 제외됨.

### D1. HITL (`interrupt`/`resume`) — LangGraph 고급 surface

- **거론된 라운드**: R3 (선택), R4 (구체화), R7 (트리거 결정).
- **미채택 사유**: Streamlit re-run 모델과 충돌·Checkpointer 추가 surface 1개 더 필요·일정 1~1.5일 추가. 학습-only 렌즈에서 surface 4개 (Router·Store·Streaming·Tool use) 깊이 학습이 우선.
- **대체**: 답글 검토는 UI 차원의 [복사]/[수정] 버튼으로. PROPOSAL "발행은 사람이" 정신은 결과적으로 보존.
- **회복 시점**: W2 D4에 surface 4개가 *깊이 있게 동작*하면 W2 D4 여유 시 추가 검토 (낮은 우선순위).

### D2. FastAPI + Streamlit decoupled / cron / Google Places API

- **거론된 라운드**: R2 (input pivot), R3 (Google Places 선택), R8 (FastAPI 결정).
- **미채택 사유**: 학습-only 렌즈에서 LangGraph가 아닌 web/cloud 학습. 인증·결제·API 할당량·process orchestration 부담. cron 폐기 → FastAPI 명분 소멸 → 단일 Streamlit으로 회귀.
- **대체**: Mock JSON 파일 + "fetch batch" 버튼.
- **회복 시점**: 본 프로젝트 범위 외. 후속 프로젝트에서 별도.

### D3. Speed-up 버튼 / 시간 경과 시뮬레이션 슬라이더

- **거론된 라운드**: R9 (선택).
- **미채택 사유**: 학습 surface 0, 발표 sugar에 가까움. mock 50건 사전 주입만으로 Pattern·Checklist 동작 학습 가능.
- **대체**: mock 데이터의 timestamp 분포를 "이미 4주치 누적된 상태"로 작성 (R4 mitigation과 같은 mock 설계).
- **회복 시점**: 발표 데모에서 평가자가 "시간 시각화" 요구 시 W2 D4에 단순 slider 추가 가능 (~2시간).

### D4. CSV 업로드 보조 옵션

- **거론된 라운드**: 변경 분석 라운드.
- **미채택 사유**: mock JSON으로 입력 경로 단일화. CSV parser는 학습 surface 0.
- **대체**: mock JSON.

### D5. 매장 입력 "Skip + 단계적 prompt" UX

- **거론된 라운드**: R6 (입력 UX 선택), R10 (단계적 prompt 시점).
- **미채택 사유**: 학습-only 렌즈에서 UI surface 학습은 본 프로젝트 목적 외. seed 데이터 사전 작성으로 form 자체가 거의 불필요.
- **대체**: 첫 진입 시 form 강제 (새 매장 추가 시), seed 매장은 자동 로드 후 form skip.

### D6. AIHub 리뷰 데이터셋 + 외부 검증 라벨링

- **거론된 라운드**: R9 (골든셋 선택).
- **미채택 사유**: 다운로드·라이선스 동의·도메인 매핑에 0.5일 추가 + 자체 작성 50건이 빠르고 5명 cross-label로 일관성 확보 가능.
- **대체**: 자체 50건 + Fleiss kappa.

### D7. Sonnet/gpt-5.x-mini/Qwen 3종 모델 비교

- **거론된 라운드**: PROPOSAL 명시.
- **미채택 사유**: 학습 surface가 LangGraph 외 (멀티 vendor SDK). API 키 3종·환경변수·prompt 호환성 작업 ~2일.
- **대체**: Anthropic 단일 (Haiku/Sonnet 혼용 가능성, W2 D1 결정).

### D8. Send API / Parallel execution

- **거론된 라운드**: R3 (surface 선택).
- **미채택 사유**: 멀티라벨 폐기로 fan-out 필요 없음. 사용자가 5 surface 선택 시 미선택.
- **대체**: 1 review = 1 graph run 순차.

### D9. Checkpointer + Thread persistence

- **거론된 라운드**: R3 (surface 선택).
- **미채택 사유**: 다세션 누적은 Memory Store + SQLite로 해결. Checkpointer는 thread 내 시간 이동·중단 재개에 강점이지만 본 프로젝트는 그런 시나리오 없음.
- **대체**: stateless graph + Memory Store cross-thread.

### D10. Subgraph 합성

- **거론된 라운드**: R3 (surface 선택).
- **미채택 사유**: 7~8 노드는 단일 graph로 충분. 계층화 가치 ≦ 복잡도 비용.

## 후순위 (시간 부족 시 떨어뜨릴 항목 정리)

[`07`](./07-team-and-demo.md) 일정 기준 W2 D3까지 동작 안 하면 다음 순서로 후순위:

1. **Drafter token-level streaming** → node-level만 ([`04`](./04-ux-and-streaming.md))
2. **diff hint 생성 (비동기 Haiku)** → tone_samples만 append ([`05`](./05-personalization.md))
3. **batch graph (Pattern + Checklist)** → hardcoded 통계 카드로 대체 ([`04`](./04-ux-and-streaming.md))
4. **매장 등록 form** → seed 매장 2개로만 시연 ([`04`](./04-ux-and-streaming.md))
5. **Sonnet 승격** → Haiku 단일 고정 ([`06`](./06-models-and-evaluation.md))

각 항목은 단독 조치 가능. 후순위 떨어뜨릴 시 spec 본문은 *그대로* 두고 `risks-and-deferrals.md`에 "deferred at W2 D3" 표시만 추가.
