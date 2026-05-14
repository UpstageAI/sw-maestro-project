---
title: 07 — Team & Demo
related:
  - 00-overview.md
  - 01-langgraph-architecture.md
  - 04-ux-and-streaming.md
  - 06-models-and-evaluation.md
last_updated: 2026-05-08
---

# Team & Demo

## 팀 5명 분담 (제안 — 팀 합의 후 확정)

| 멤버 | 역할 | 주요 책임 | 관련 spec |
|---|---|---|---|
| 윤성민 (본인) | **Skeleton + State + Router** | LangGraph build·State TypedDict·route_by_sentiment·conditional edges 설정·skeleton 노드 stub·통합 빌드 책임 | [`01`](./01-langgraph-architecture.md) |
| 멤버 A | **Classifier 노드** | classifier prompt·Haiku 호출·JSON 파싱·골든셋 평가 스크립트·분류 정확도 KPI | [`02`](./02-data-model.md), [`06`](./06-models-and-evaluation.md) |
| 멤버 B | **3 Drafter 노드** | thanks/apology/apology_lowconf/neutral prompt 4종·few-shot 주입 로직·Sonnet 승격 시 prompt 재튜닝 | [`05`](./05-personalization.md) |
| 멤버 C | **Pattern + Checklist + SQL Tool** | batch graph·SQL query tool 구현·SQLite 스키마·migration·PatternAgent prompt | [`02`](./02-data-model.md), [`01`](./01-langgraph-architecture.md) |
| 멤버 D | **UI + Memory Store integration** | Streamlit app·sidebar·main 카드·복사/수정 버튼·tone_samples append·diff hint 비동기 호출·load_context 노드 | [`02`](./02-data-model.md), [`04`](./04-ux-and-streaming.md), [`05`](./05-personalization.md) |

### 분담 원칙

- **노드 1개 = 멤버 1명**: 충돌 최소·소유 명확.
- **본인은 skeleton + Router**: graph 컴파일 책임 중앙. 다른 멤버는 자기 노드 함수 시그니처(input state → output state)에만 집중.
- **PII 마스킹 노드**: 가장 단순 (정규식만), W1 D1에 본인이 작성하여 skeleton에 포함.
- **load_context · memory_save**: 멤버 D 책임 (Memory Store 영역).

## 일정 (W1 D1 ~ W2 D5)

| 시점 | 목표 | 주요 결과물 | 책임 |
|---|---|---|---|
| **W1 D1 (월)** | 환경 + skeleton | uv 환경, pyproject.toml, Makefile, src/ 디렉토리, SQLite 마이그레이션, seed_places.json + mock_reviews_*.json (50~60건), graph skeleton (compile 통과) | 본인 + 멤버 D (seed) |
| **W1 D2 (화)** | 골든셋 50건 작성 + 라벨링 | eval/golden_50.jsonl, 5명 cross-label, Fleiss kappa 측정·합의 라벨 갱신 | 전원 |
| **W1 D3 (수)** | Classifier 1차 | classifier 노드 동작, 골든셋 분류 정확도 1차 (목표 ≥ 80%) | 멤버 A |
| **W1 D4 (목)** | Drafter 1차 | 4종 drafter 동작, 매장 메타·few-shot 주입, 답글 출력 정상 | 멤버 B + 멤버 D (load_context) |
| **W1 D5 (금)** | 통합 + Haiku 평가 | main graph end-to-end, Streamlit minimal UI 동작, 골든셋 분류 ≥ 85% 또는 Sonnet 승격 결정 | 본인 (통합) + 전원 |
| **W2 D1 (월)** | Sonnet 승격 결정 + Pattern 시작 | (필요 시) apology drafters Sonnet 전환·prompt 재튜닝, batch graph + SQL tool 시작 | 멤버 B + 멤버 C |
| **W2 D2 (화)** | Pattern + Checklist 동작 | batch graph 동작, TOP 3 + 체크리스트 출력, UI에 카드 표시 | 멤버 C + 멤버 D |
| **W2 D3 (수)** | Streaming + UI 완성 | node-level streaming 사이드바, 답글 복사/수정/diff hint 비동기, 데모 시연 흐름 결정 | 멤버 D + 본인 (streaming wiring) |
| **W2 D4 (목)** | QA + 사용성 테스트 + 발표 자료 | 사용성 테스트 3~5명, 골든셋 회귀 테스트, 발표 슬라이드 초안, recorded fallback screencast | 전원 |
| **W2 D5 (금)** | 발표 | 라이브 시연 + Q&A 대비 | 본인 (발표) + 멤버 A (Q&A 보조) |

## 데모 시나리오

### 주인공 매장: PLACE_001 ("예시 카페 A", 성숙)

- 메뉴 6~8개·tone_samples 3건·feedback 1건·mock 리뷰 25~30건 (4주 분포).
- sidebar에서 매장 전환 시 PLACE_002 ("예시 식당 B", 신규)도 보여 *multi-tenant + Memory Store namespace* 시연.

### 시연 흐름 (TBD — W2 D3 결정, 현 시점 후보 비트)

| 비트 | 내용 | 노출되는 surface |
|---|---|---|
| 1. 매장 선택 | sidebar에서 카페 A 클릭 → main에 매장 컨텍스트 표시 | Memory Store namespace |
| 2. "리뷰 5건 가져오기" | 버튼 클릭 → graph stream 시작 → 사이드바 노드 진행 ✓ | Streaming (node-level) |
| 3. 부정 리뷰 답글 검토 | apology_drafter 출력 답글 → 사장이 살짝 수정 → 복사 | Drafter prompt few-shot 활용, Memory Store write |
| 4. 다음 리뷰 처리 | 직전 수정이 tone_samples에 반영된 상태로 다음 답글 생성 | "쓸수록 똑똑해짐" 시연 |
| 5. "TOP 3 + 체크리스트" 버튼 | batch graph + SQL tool 호출 → 결과 카드 표시 | Tool use surface |
| 6. (선택) 매장 전환 PLACE_002 | 신규 매장 → 같은 리뷰 입력 시 generic 답글 (개인화 부재 비교) | namespace 격리 검증 |
| 7. (선택) Sidebar Graph 진행 패널 zoom | 평가자에게 LangGraph 5 surface 명시 | 발표 메시지 강조 |

각 비트 1~2분 → 총 5~10분 데모 가능. 발표 슬라이드와 어떻게 엮을지는 W2 D4 결정.

### 데모 안전망

- **recorded screencast** — W2 D4에 시연 흐름을 OBS 등으로 녹화. 라이브 실패 시 동영상 재생.
- **API 키 backup** — Anthropic API 키 2개 (메인 + 백업), `.env.demo`에 백업 키 보관.
- **mock 데이터 frozen** — mock_reviews_*.json은 W2 D2 이후 수정 금지 (재현성).
- **DB reset 버튼** — sidebar에 "데모 초기화" 버튼 (SQLite drop+recreate, Store reload). 발표 직전 깨끗한 상태.

## 협업 워크플로우

### Git

- `main` branch protection: PR 필수, 1+ approval, CI green.
- feature branch naming: `feat/<member>-<scope>` (e.g. `feat/sm-router-conditional`).
- commit message: 한글 OK, prefix만 `feat:`/`fix:`/`chore:`/`docs:`.
- 노드별 분담이라 충돌 적음 — `src/graph/nodes/<node>.py` 한 명 한 파일 원칙.

### Code review

- Skeleton·State·Router 변경: 본인 PR → 멤버 1명 review.
- 노드 PR: 노드 담당자 PR → 본인 review (skeleton 호환성 확인) + 1명 추가 review.

### CI (W1 D2까지 setup)

- GitHub Actions: pytest 실행 (단위 테스트 + 골든셋 회귀 (소량)).
- linting: ruff (지원), mypy는 옵션 (시간 부족 시 skip).

## 발표 흐름 (TBD)

W2 D4까지 결정. 현 시점 가설:

- 5분 압축: 1막 도입(30초) / 2막 라이브 시연(3분) / 3막 회고·감사(1분 30초).
- 10분 표준: 1막 문제 정의(1분) / 2막 LangGraph 4 surface 도식(2분) / 3막 라이브 시연(5분) / 4막 회고·KPI(2분).

발표 자료는 별도 슬라이드 — spec 외.
