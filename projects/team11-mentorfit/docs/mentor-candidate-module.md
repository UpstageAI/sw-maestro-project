# 멘토 후보 검색 모듈 (`mentor_candidate`)

## 역할

파이프라인의 3단계: 팀 프로필을 입력받아 조합 생성 모듈로 넘기기 전 1차 후보 멘토를 추출한다.
멘토 매칭 정원 제한을 없애고 전체 멘토(약 220명)를 대상으로 검색하되, LLM 컨텍스트 한계와 비용 효율성을 고려하여 **2-Stage Retrieval** 방식을 사용한다.

1. **임베딩 기반 사전 필터링 (RAG)**: 팀 프로필 텍스트와 전체 멘토 정보를 각각 Solar 임베딩(`solar-embedding-1-large-passage`) 모델로 벡터화하여 코사인 유사도를 계산하고, 상위 N명(기본 30명)을 1차로 추려낸다.
2. **LLM 기반 최종 선정**: 사전 필터링된 N명의 멘토 정보와 팀 프로필을 프롬프트에 주입하여, LLM(`solar-pro`)이 최종 후보 K명을 선정하고 각 후보의 추천 근거(reason)와 보완점(weak_point)을 JSON 형태로 출력한다. (Pydantic 객체로 파싱)

## 모듈 경로

```
app/modules/mentor_candidate/
├── __init__.py
├── service.py         # 2-Stage 비즈니스 로직 오케스트레이션
├── schemas.py         # Pydantic 입출력 모델 (TeamProfile, Mentor, CandidateResult 등)
├── retriever.py       # (Stage 1) 임베딩 벡터 유사도 계산 및 필터링
└── llm_selector.py    # (Stage 2) LLM 프롬프트 생성, 재시도 제어 및 Structured Output 파싱

app/core/upstage.py    # UpstageClient 싱글톤 (Chat Completion, Embedding, response_format 지원)
```

## 주요 함수

### `get_mentor_candidates(team_profile: TeamProfile, top_k: int) -> list[CandidateResult]`

중앙에서 절차적으로 호출하는 멘토 후보 추천 메인 함수.

**Input: `TeamProfile`**

```python
class TeamProfile(BaseModel):
    members_rnr: str
    project_plan_tech_goals: str
    mentoring_needs: str
    fit_conditions: str = ""
    maestro_program_goals: str
    skills: str
```

**Output: `list[CandidateResult]`**

```python
class CandidateResult(BaseModel):
    mentor_id: int
    rank: int
    reason: str      # 적합 이유 (한국어)
    weak_point: str  # 아쉬운 점 (한국어)
```

## 사전 필터링 로직 (`retriever.py`)

1. 팀 프로필 정보를 하나의 텍스트 덩어리로 변환하고 임베딩을 추출한다.
2. 각 멘토의 정보(기술 스택, 도메인, 목표, 관심사, 경력 등)를 텍스트화하여 임베딩을 추출한다. (캐시 기능 포함 `data/cache/mentor_embeddings_v2.json`)
3. 코사인 유사도를 기준으로 내림차순 정렬한 뒤, 상위 `prefilter_top_n`(기본 30명)개만 반환한다.

## LLM 선정 로직 (`llm_selector.py`)

`UpstageClient.get_chat_completion()`을 사용하여 필터링된 멘토 목록을 프롬프트에 포함해 전달한다.

- **System Prompt**: SW마에스트로 매칭 전문가 역할 부여
- **User Prompt**: 팀 상황 나열 + 가용 멘토 30명 정보 나열 -> `top_k`명 선정 요청
- **Structured Output**: Upstage API의 `response_format`(JSON Schema) 기능을 사용하여 반환 구조를 강제한다.
- **파싱 및 검증**: 응답받은 배열 형태의 JSON을 `TypeAdapter(list[CandidateResult]).validate_python()`으로 직접 파싱 및 타입 검증을 수행한다.
- **재시도 및 누적 (Retry & Accumulate)**: 
  - LLM이 요청한 수량(`top_k`)을 채우지 못하거나 중복된 멘토를 반환할 경우, 최대 3회까지 재시도한다.
  - 이전 응답을 대화 내역(History)에 누적하고, "이미 선정된 멘토를 제외하고 부족한 수량만큼 새롭게 선정해달라"는 구체적인 피드백을 전달하여 결과를 100% 보장한다.
  - 최악의 경우에도 가용 멘토 풀에서 부족한 인원을 채워넣는 Fallback 로직이 적용되어 있다.

## 환경 변수

```
UPSTAGE_API_KEY              # Solar API 인증 키
MOCK_MODE=False              # True일 경우 실제 API 호출 없이 테스트용 데이터 반환
MENTOR_DATA_PATH             # 멘토 데이터 경로
CANDIDATE_TOP_K=5            # 기본 반환 최종 후보 수
PREFILTER_TOP_N=30           # 1차 임베딩 필터링으로 추려낼 후보 수
EMBEDDING_CACHE_TTL=86400    # 임베딩 캐시 유지 시간 (초)
```

## 테스트 전략

- `tests/modules/mentor_candidate/verify_llm_selection.py`: LLM 선정 로직 전체 흐름 검증 (Mock 지원)
