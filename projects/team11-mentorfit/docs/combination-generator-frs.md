# 멘토 조합 생성 모듈 기능 요구사항 명세서

> 작성일: 2026-05-10  
> 브랜치: `feat/combination`  
> 관련 스펙: `docs/combination-generator-module.md`

---

## 1. 목적

멘토 후보 검색 결과를 입력으로 받아, 각 후보 멘토의 약점을 보완하는 멘토 2명을 전체 멘토 풀에서 선정하여 3인 조합을 생성한다. 조합은 팀의 멘토링 니즈를 가장 넓게 커버하도록 구성되며, LLM 기반 분석으로 각 조합의 강점·약점·추천 이유를 함께 제공한다.

---

## 2. 범위

본 명세는 다음 두 서비스를 포함한다.

| 서비스 | 위치 | 역할 |
|--------|------|------|
| `MentorCandidateService` | `app/modules/mentor_candidate/service.py` | 후보 멘토별 추천 이유(`reason`)·약점(`weak_point`)·순위(`rank`) 생성 |
| `CombinationGeneratorService` | `app/modules/combination_generator/service.py` | 후보 멘토별 3인 조합 생성 |

두 서비스 모두 HTTP 엔드포인트 없이 **메서드 호출 방식**으로만 사용된다.

---

## 3. 입력

### 3-1. `MentorCandidateService.search()`

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `team_profile` | `TeamProfile` | 팀 기술 스택, 역할, 프로젝트, 목표, 멘토링 니즈 |
| `top_k` | `int` | 반환할 후보 멘토 수 (1–20) |

### 3-2. `CombinationGeneratorService.generate()`

| 파라미터 | 타입 | 설명 |
|----------|------|------|
| `team_profile` | `TeamProfile` | 팀 프로필 (조합 선정 맥락으로 사용) |
| `candidates` | `list[CandidateResult]` | `MentorCandidateService.search()` 반환값. `reason`, `weak_point`, `rank` 필드가 채워진 상태 |

---

## 4. 기능 요구사항

### FR-01: 후보 멘토 분석 (MentorCandidateService)

**FR-01-1** 각 후보 멘토에 대해 Solar LLM을 호출하여 다음을 생성한다.
- `reason`: 해당 팀에게 이 멘토를 추천하는 이유 1문장
- `weak_point`: 팀 관점에서 이 멘토가 부족한 점 1문장

**FR-01-2** 후보 목록은 `combined_score` 기준 내림차순 정렬 후 `rank`(1-based)를 부여한다.

**FR-01-3** `settings.mock_mode = True`인 경우 LLM 호출 없이 `reason`·`weak_point`를 빈 문자열로 반환한다.

**FR-01-4** LLM 응답 JSON 파싱 실패 시 해당 후보의 `reason`·`weak_point`를 빈 문자열로 처리하고 예외를 전파하지 않는다.

### FR-02: 3인 멘토 조합 생성 (CombinationGeneratorService)

**FR-02-1** 각 `CandidateResult`를 기준 멘토로 삼아 3인 조합을 1개 생성한다. 후보 N개 입력 시 조합 N개를 반환한다.

**FR-02-2** 보완 멘토 탐색 범위는 **전체 멘토 풀** (`data/sample/mentors.json`)이며 기준 멘토 자신은 제외한다.

**FR-02-3** 보완 멘토 선정은 Solar LLM에 위임한다. 조합당 **LLM 1 call**로 다음을 한 번에 반환받는다.
- `second_mentor_id`: 기준 멘토의 약점을 보완하는 2번째 멘토 ID
- `third_mentor_id`: 기준 + 2번째 멘토의 약점을 채우는 3번째 멘토 ID
- `strengths`: 조합 강점 3가지
- `weak_points`: 조합 약점 3가지
- `reason`: 조합 추천 이유 1문장

**FR-02-4** LLM이 반환한 mentor_id가 전체 멘토 풀에 존재하지 않으면 해당 ID를 빈 문자열로 처리한다.

**FR-02-5** LLM 응답 JSON 파싱 실패 또는 비dict 응답 시 `candidate_ids`·`strengths`·`weak_points`를 빈 리스트로, `reason`은 입력 `candidate.reason`을 그대로 승계하고 예외를 전파하지 않는다.

**FR-02-6** `settings.mock_mode = True`인 경우 LLM 호출 없이 `candidate_ids`·`strengths`·`weak_points` 빈 리스트, `reason`·`weak_point`은 입력값 승계로 반환한다.

### FR-03: LLM 호출 인프라

**FR-03-1** `UpstageClient.chat_completion(messages, model)`은 최대 3회 재시도 후 실패 시 예외를 전파한다.

**FR-03-2** 사용 모델은 `settings.combination_model`(기본값: `"solar-pro"`)로 설정 파일에서 제어한다.

---

## 5. 출력

### 5-1. `MentorCandidateService.search()` → `CandidateSearchResponse`

기존 `CandidateSearchResponse`와 동일하되, `candidates` 내 각 `CandidateResult`에 다음 필드가 추가된다.

| 필드 | 타입 | 설명 |
|------|------|------|
| `rank` | `int` | combined_score 기준 순위 (1-based) |
| `reason` | `str` | LLM 생성 추천 이유 |
| `weak_point` | `str` | LLM 생성 약점 |

### 5-2. `CombinationGeneratorService.generate()` → `list[CombCandidateResult]`

```python
class CombCandidateResult(BaseModel):
    mentor_id: str           # 기준 멘토 ID
    candidate_ids: list[str] # 2nd, 3rd 멘토 ID 목록
    strengths: list[str]     # 조합 강점 (최대 3개)
    weak_points: list[str]   # 조합 약점 (최대 3개)
    rank: int                # 기준 멘토의 rank 승계
    reason: str              # 조합 추천 이유
    weak_point: str          # 기준 멘토의 weak_point 승계
```

---

## 6. 비기능 요구사항

| 항목 | 요구사항 |
|------|---------|
| 호출 방식 | HTTP 엔드포인트 없이 Python 메서드 직접 호출 |
| 캡슐화 | 각 서비스는 클래스로 캡슐화, public 메서드 1개만 외부 노출 |
| 테스트 격리 | Solar API 의존성은 `monkeypatch`로 mock 처리 |
| mock_mode | `settings.mock_mode = True` 시 LLM 호출 없이 동작 |

---

## 7. 호출 예시

```python
from app.modules.mentor_candidate.service import MentorCandidateService
from app.modules.combination_generator.service import CombinationGeneratorService

# Step 1: 후보 검색 + 분석
candidate_service = MentorCandidateService()
response = await candidate_service.search(team_profile, top_k=5)
# response.candidates[i].reason, .weak_point, .rank 모두 채워진 상태

# Step 2: 조합 생성
combination_service = CombinationGeneratorService()
combinations = await combination_service.generate(team_profile, response.candidates)
# combinations[i] → CombCandidateResult (3인 조합 1개)
```
