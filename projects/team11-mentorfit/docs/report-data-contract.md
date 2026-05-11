# Report 모듈 데이터 계약

이 문서는 sample report가 아니라 실제 모듈 간 데이터 계약을 정의한다.

## 입력 계약

```python
class ReportGenerationRequest(BaseModel):
    team_profile: TeamProfile
    team_report: str
    candidates: list[CandidateResult]
    combinations: list[CombCandidateResult]
    mentors: list[Mentor]
    current_matching_status: str | None = None
```

| 필드 | 출처 | 설명 |
|------|------|------|
| `team_profile` | `team_profile` | 현재 `mentor_candidate.schemas.TeamProfile` 계약을 따르는 구조화 팀 정보 |
| `team_report` | `team_profile` | 사용자가 검토하는 팀 리포트 원문 |
| `candidates` | `mentor_candidate` | 후보 멘토 검색 결과 |
| `combinations` | `combination_generator` | 메인 멘토 + 보완 멘토 조합 결과 |
| `mentors` | `data/mentors.json` | 후보 및 조합 id를 실제 멘토 정보로 해석하기 위한 원본 데이터 |
| `current_matching_status` | UI/API 호출자 | 현재 매칭 현황 또는 가용성 관련 메모 |

## 재사용 모델

### `TeamProfile`

```python
class TeamProfile(BaseModel):
    members_rnr: str
    project_plan_tech_goals: str
    mentoring_needs: str
    fit_conditions: str = ""
    maestro_program_goals: str
    skills: str
```

### `CandidateResult`

```python
class CandidateResult(BaseModel):
    mentor_id: int
    rank: int
    reason: str
    weak_point: str
```

### `CombCandidateResult`

`CombCandidateResult`는 `app.modules.combination_generator.schemas`가 소유한다.

```python
class CombCandidateResult(BaseModel):
    mentor_id: int
    candidate_ids: list[int]
    strengths: list[str]
    weak_points: list[str]
    rank: int
    reason: str
    weak_point: str
```

- `mentor_id`: 메인 멘토 id
- `candidate_ids`: 보완 멘토 2명의 id
- `strengths`: 조합 강점, 최대 3개
- `weak_points`: 조합 약점, 최대 3개
- `reason`: 조합 추천 근거
- `weak_point`: 메인 멘토 기준 보완 필요점

## 출력 계약

```python
class ReportMentorSummary(BaseModel):
    mentor_id: int
    name: str
    role: Literal["main", "supplement"]
    reason: str
    weak_point: str

class ReportCombination(BaseModel):
    rank: int
    main_mentor: ReportMentorSummary
    supplement_mentors: list[ReportMentorSummary]
    strengths: list[str]
    weak_points: list[str]
    recommendation_reason: str

class RecommendationReport(BaseModel):
    team_summary: str
    confidence_basis: str
    candidate_summary: str
    combinations: list[ReportCombination]
    final_recommendation: str
    cautions: list[str]
    generated_at: str
```

## 표시 정보

추천 리포트 페이지는 다음 정보를 표시한다.

1. 팀 요약
2. 팀 리포트 원문
3. 후보 멘토 요약
4. 추천 조합 목록
   - 메인 멘토
   - 보완 멘토 2명
   - 조합 강점
   - 조합 약점
   - 추천 근거
5. 최종 추천
6. 신뢰도 판단 근거
7. 주의사항
