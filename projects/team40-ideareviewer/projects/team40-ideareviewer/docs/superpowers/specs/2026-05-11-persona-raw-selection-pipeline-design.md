# Persona Raw Selection Pipeline Design

## Goal

Hugging Face `nvidia/Nemotron-Personas-Korea` 데이터셋에서 한국 서비스 전반 리뷰에 쓸 수 있는 raw persona 후보를 단계적으로 선별한다.

최종 목표는 `raw_personas.selected_100.json` 100건이다. 이 100건은 이후 `persona_cards.selected.json`으로 변환되어, RAG 없이 LLM이 기획 텍스트에 맞는 persona를 직접 고르는 후보 풀로 쓰인다.

## Scope

이번 작업의 범위는 raw 데이터 확보와 선별 파일 생성이다.

- 원본 데이터셋에서 초기 후보 10,000건 확보
- 10,000건에서 균형 후보 1,000건 선별
- 1,000건에서 최종 raw 100건 선별
- 각 단계의 분포와 선별 기준을 요약 파일로 저장

이번 작업에서 제외하는 범위:

- persona card 100개 생성
- 앱의 persona loader 변경
- RAG 또는 vector index 구성
- LLM 기반 persona pair selector 변경

## Output Files

```text
data/personas/raw_personas.pool_10000.json
data/personas/raw_personas.candidate_1000.json
data/personas/raw_personas.selected_100.json
data/personas/persona_selection_summary.json
```

`raw_personas.pool_10000.json`은 최소 품질 필터를 통과한 넉넉한 raw 후보 풀이다.

`raw_personas.candidate_1000.json`은 연령, 성별, 지역, 직업군, 가족형태, 교육수준, 도시/비도시 맥락, 디지털 사용 단서를 고려해 줄인 균형 후보 풀이다.

`raw_personas.selected_100.json`은 서비스 기획 리뷰에서 서로 다른 반응을 낼 가능성이 높은 최종 raw 세트다.

`persona_selection_summary.json`은 각 단계의 count, seed, 분포, 기준, 생성 시각을 기록한다.

## Selection Design

### Stage 1: Pool 10,000

원본 데이터셋에서 seed 고정 랜덤 순회로 후보를 가져온다. 아래 조건을 통과한 row만 저장한다.

- `uuid`, `persona`, `cultural_background`, `skills_and_expertise`, `hobbies_and_interests`, `career_goals_and_ambitions` 존재
- `age`, `sex`, `occupation`, `province` 존재
- 주요 텍스트 필드 합산 길이가 충분함
- age가 정상 범위 안에 있음

이 단계는 다양성보다 품질 결측 제거와 재현성을 우선한다.

### Stage 2: Candidate 1,000

10,000건에서 deterministic scoring과 quota를 사용해 1,000건을 만든다.

연령대 목표 분포:

```text
20s: 120
30s: 140
40s: 160
50s: 180
60s: 200
70plus: 200
```

각 연령대 안에서는 아래 요소가 한쪽으로 몰리지 않도록 뽑는다.

- 성별
- `province`
- 직업군
- 가족형태
- 교육수준
- 디지털 단서 유무
- 리뷰 민감도 태그

직업군은 원본 `occupation` 텍스트를 규칙 기반으로 묶는다. 정확한 통계 분류가 아니라 리뷰 다양성 확보용 group이다.

디지털 단서는 `스마트폰`, `유튜브`, `블로그`, `앱`, `온라인`, `키오스크`, `SNS`, `음성 입력` 같은 표현을 주요 텍스트에서 탐지한다.

### Stage 3: Selected 100

1,000건에서 최종 100건을 고른다. 기본 목표 분포는 다음과 같다.

```text
20s: 12
30s: 14
40s: 16
50s: 18
60s: 20
70plus: 20
```

최종 100건은 다음 리뷰 관점이 빠지지 않도록 선별한다.

- 접근성
- 가격 부담
- 신뢰와 사기 우려
- 개인정보와 보안
- 시간 절약
- 가족 돌봄
- 지역 생활
- 건강과 안전
- 복잡한 절차에 대한 거부감
- 고객지원 필요

동일한 `age_group + province + occupation_group + family_type` 조합이 반복되면, 텍스트 품질과 리뷰 관점이 더 뚜렷한 row를 우선한다.

## LLM Use

초기 10,000건 확보와 1,000건 균형 선별은 LLM 없이 규칙 기반으로 처리한다. 이 단계는 재현성과 분포 통제가 더 중요하다.

최종 100건 선별은 우선 규칙 기반 다양성 점수로 수행한다. 이후 필요하면 별도 단계에서 LLM 검증 루프를 추가한다. LLM 검증은 100건을 확정한 뒤 “중복이 심한 persona”, “기획 리뷰 관점이 약한 persona”, “빠진 리뷰 관점”을 찾는 용도로 쓰는 것이 적절하다.

## Error Handling

- Hugging Face 접근 실패 시 명확한 에러를 출력하고 기존 파일을 덮어쓰지 않는다.
- 목표 count를 채우지 못하면 실제 count와 부족한 quota를 summary에 기록한다.
- JSON 저장은 UTF-8, `ensure_ascii=False`, stable sort 없이 원래 선별 순서를 유지한다.
- 같은 `uuid`는 한 번만 저장한다.

## Verification

- 스크립트 실행 후 세 output JSON을 모두 읽어 schema 수준의 필수 필드가 있는지 확인한다.
- 각 단계 count가 10,000, 1,000, 100인지 확인한다.
- summary에서 연령대, 성별, 지역, 직업군 분포를 확인한다.
- 기존 seed 파일과 app 로더는 변경하지 않는다.

