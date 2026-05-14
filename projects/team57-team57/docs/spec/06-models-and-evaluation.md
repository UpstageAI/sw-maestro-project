---
title: 06 — Models & Evaluation
related:
  - 00-overview.md
  - 01-langgraph-architecture.md
  - 02-data-model.md
  - 08-risks-and-deferrals.md
last_updated: 2026-05-08
---

# Models & Evaluation

## 모델 분담 — Solar Pro 2 단일

전 노드 **`solar-pro2`** 사용 (Upstage Solar API, OpenAI 호환). 한국어 강점 (Ko-MT-Bench 81.0). 16만원 free credit 으로 학습·평가·데모 모두 가능.

| 노드 | 모델 | 비고 |
|---|---|---|
| classifier | solar-pro2 | structured output (`response_format=json_schema`) |
| thanks_drafter | solar-pro2 | text |
| apology_drafter | solar-pro2 | text + few-shot |
| apology_drafter_lowconf | solar-pro2 | text + 보수적 prompt |
| neutral_drafter | solar-pro2 | text |
| pattern_aggregator | solar-pro2 | **bind_tools(query_review_stats)** — LLM-driven tool calling |
| checklist_generator | solar-pro2 | structured output |
| diff_hint (UI 비동기) | solar-pro2 | text |

### Solar Pro 2 vs Mini 검토 (W2 D1)

W1 골든셋 평가 결과 보고:
- 분류 정확도 ≥ 90% AND 답글 적합성 ≥ 4.5/5.0 → **classifier·pattern·checklist 만 solar-mini 다운그레이드** 검토 (output 비용 절감).
- 일관 미달 시 → solar-pro2 유지.

비용 추정 (Solar Pro 2: input $0.15 / output $0.60 per 1M tok):
- 1 review main graph ≈ input 2K + output 200 = **$0.0004**.
- 5 review batch ≈ $0.002.
- batch graph (TOP 3 + 체크리스트) ≈ $0.001.
- 학습·평가 누적 (~1000 호출) ≈ **$0.5 미만**, 16만원 (~$115) credit 으로 19만 호출 추정 가능.

## 골든셋 50건 — 자체 작성 + cross-label

### 작성 (W1 D1~D2)

5명이 각자 10건씩 한국어 리뷰 작성. 분포 가이드:
- 감정: 긍정 18건, 부정 22건, 중립 10건 (현실 분포 ≈ 부정 우세).
- 카테고리: 5대 카테고리 균등 (각 10건) + 멀티라벨 5건 (예: 맛+서비스).
- 길이: 10~250자 다양.
- risk 케이스 5건 (욕설·법적 표현 약하게).
- 이모지·맞춤법 오류 의도적 포함 (실데이터 닮음).

저장: `eval/golden_50.jsonl`.

```json
{"review_id": "GOLD_001", "review_text": "...", "ground_truth": {"sentiment": "negative", "categories": ["대기시간"], "risk_flag": false}}
```

### Cross-label 검증 (W1 D2)

각 5명이 다른 사람의 10건을 (총 50건 = 본인 10 + 타인 40) 라벨링:

```python
# eval/labeling_<member>.jsonl 양식
{"review_id": "GOLD_001", "labeler": "박세민", "sentiment": "negative", "categories": ["대기시간"], "risk_flag": false}
```

5명이 모두 50건 라벨 → review당 5라벨 → **Cohen's kappa** (또는 Fleiss' kappa) 계산:

```python
from sklearn.metrics import cohen_kappa_score
# pairwise 10쌍 평균 또는 Fleiss
kappa = fleiss_kappa(label_matrix)  # 0.6+ 목표
```

kappa < 0.6인 항목은 팀 토론 → 합의 라벨로 갱신. 합의된 라벨이 `ground_truth`.

### 평가 (W1 D5, 그리고 매 prompt 변경 후)

```python
# eval/run_classifier.py
import json
from src.graph.nodes.classifier import run_classifier

correct = 0
total = 0
for line in open("eval/golden_50.jsonl"):
    item = json.loads(line)
    pred = run_classifier(item["review_text"])
    if pred["sentiment"] == item["ground_truth"]["sentiment"]:
        correct += 1
    total += 1
print(f"Sentiment accuracy: {correct/total:.2%}")
# 카테고리는 multi-label F1 별도
```

목표: **분류 정확도 ≥ 85%** (KPI 1번).

## KPI 자동화 가능성 (PROPOSAL 6개 KPI 기준)

| KPI | 목표 | 자동화 가능? | 측정 방법 |
|---|---|---|---|
| 분류 정확도 | ≥85% | **자동** | 골든셋 50건 vs Classifier 출력 |
| 답글 사용 의향 | ≥70% | 수작업 | 데모 시연 후 설문 (3~5명) |
| 처리 시간 단축 | 1/3 이하 | 반자동 | 타이머: 사장 직접 처리 5분 vs Agent + 사람 검토 |
| 다세션 TOP 3 정합성 | 3개 중 2개+ | 수작업 | 사람이 뽑은 TOP 3 vs PatternAgent 출력 |
| 사용성 (5분 내 도달) | ≥80% | 수작업 | 무가이드 사용성 테스트 3~5명 |
| 개인화 체감 (60% 향상) | ≥60% | 수작업 | 매장 컨텍스트 입력 전/후 답글 비교 응답 |

자동화 가능한 1번만 W1 D5 / W2 D1·D3에 매번 측정. 나머지 5개는 W2 D4 사용성 테스트 1회.

## 비용 / 사용량

Upstage Solar API 호출 (`UPSTAGE_API_KEY`). SOMA 발급 16만원 (~$115) free credit 으로 학습·평가·데모 모두 충분.

| 단계 | 호출 횟수 | 누적 비용 추정 |
|---|---|---|
| W1 prompt 튜닝 | 200~500회 | < $0.5 |
| 골든셋 평가 매 prompt 변경 | 50건 × N회 (5~10회) | < $0.3 |
| diff hint 생성 (피드백) | 사장 수정마다 1회 | 무시 |
| W2 통합 테스트 + 데모 리허설 | 200~500회 | < $0.5 |
| 발표 라이브 시연 (실패 대비 100회 여유) | ~50회 | < $0.05 |

**총 학습·발표 누적 ≈ $1~2 미만**, 16만원 credit 의 1.5% 수준만 사용.

## LLM 호출 패턴 (현재 구현)

```python
from src.llm.upstage import complete_text_with_meta, complete_json_with_meta

# 텍스트 (Drafter, diff hint)
reply, meta = complete_text_with_meta(
    prompt=user_message,
    system="You write a Korean reply ...",
    model="solar-pro2",
)

# Structured output (Classifier, Checklist) — Solar 의 response_format=json_schema 활용
result, meta = complete_json_with_meta(
    prompt=review_text,
    system="You are a Korean review classifier ...",
    schema={"type": "object", "properties": {...}, "required": [...]},
    model="solar-pro2",
)
```

내부 구현: `openai` SDK + `base_url="https://api.upstage.ai/v1"` (Solar 가 OpenAI 호환). meta 에 duration_ms · tokens · prompt/response preview 200자 포함 → trace 노출.

**Tool use (pattern node)**: `langchain-upstage` 의 `ChatUpstage.bind_tools([query_review_stats])` 로 LLM-driven tool calling. response.tool_calls 에 모델이 결정한 args 가 담김.

**히스토리**: 초기에는 `claude` CLI subprocess 로 Claude Max 구독을 사용했으나 Solar credit 발급 후 마이그레이션 (git history `6f9cc3c` 참고).

## 의도적으로 채택하지 않은 평가 방법

| 후보 | 미채택 사유 |
|---|---|
| AIHub 리뷰 데이터셋 | 다운로드·라이선스 동의·도메인 매핑 0.5일 추가, 자체 50건이 더 빠름 |
| Naver Sentiment Movie Corpus | 도메인 불일치 (영화 vs 소상공인) |
| Sonnet/gpt-mini/Qwen 3종 비교 | 학습 surface가 LangGraph 외 (멀티 vendor SDK), 일정·인증 부담 |
| BLEU/ROUGE 자동 평가 | 답글은 정답 없음 (창의적 생성), 사람 평가가 더 신뢰 |

상세 사유는 [`08-risks-and-deferrals.md`](./08-risks-and-deferrals.md).
