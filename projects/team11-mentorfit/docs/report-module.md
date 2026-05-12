# 추천 리포트 생성 모듈 (`report`)

## 역할

`report` 모듈은 후보 검색과 조합 생성이 끝난 뒤, 실제 상위 모듈 산출물을 최종 사용자가 읽을 수 있는 추천 리포트로 변환한다.

이 모듈은 다음을 하지 않는다.

- sample JSON 로딩
- 멘토 후보 검색
- 멘토 조합 생성
- 없는 멘토 정보 추론

## 모듈 경로

```text
app/modules/report/
├── __init__.py
├── router.py
├── schemas.py
└── service.py
```

## API 엔드포인트

### `POST /api/report`

실제 팀 프로필, 후보 추천 결과, 조합 결과, 멘토 원본 데이터를 받아 최종 추천 리포트를 생성한다.

**Request**

```python
ReportGenerationRequest(
    team_profile=TeamProfile,
    team_report=str,
    candidates=list[CandidateResult],
    combinations=list[CombCandidateResult],
    mentors=list[Mentor],
    current_matching_status=str | None,
)
```

**Response**

```python
RecommendationReport(
    team_summary=str,
    confidence_basis=str,
    candidate_summary=str,
    combinations=list[ReportCombination],
    final_recommendation=str,
    cautions=list[str],
    generated_at=str,
)
```

## 데이터 모델

| 모델 | 설명 |
|------|------|
| `ReportGenerationRequest` | report 생성에 필요한 전체 입력 계약 |
| `ReportMentorSummary` | 리포트 화면에 표시할 멘토 요약 |
| `ReportCombination` | 메인 멘토 1명과 보완 멘토 목록, 강점/약점/추천 근거 |
| `RecommendationReport` | 최종 리포트 최상위 출력 모델 |

`CombCandidateResult`는 `app.modules.combination_generator.schemas`에서 import한다. `report` 모듈에서 같은 모델을 다시 정의하지 않는다.

## 처리 과정

1. 입력 데이터 구조를 Pydantic으로 검증한다.
2. `mentor_id` 기준으로 `CandidateResult`, `CombCandidateResult`, `Mentor`를 매핑한다.
3. 누락된 mentor id가 있으면 명확한 예외를 반환한다.
4. 팀 리포트, 후보 추천 근거, 조합 강점/약점, 현재 매칭 현황을 LLM 프롬프트에 넣는다.
5. Solar LLM 응답을 JSON으로 파싱한다.
6. 파싱된 데이터를 `RecommendationReport`로 검증해 반환한다.

## LLM 작성 규칙

- 추천 결과는 참고 자료이며 최종 멘토 선택과 연락은 사용자가 판단한다고 명시한다.
- 멘토 원본 데이터에 없는 기술, 경력, 네트워크를 추론하지 않는다.
- 현재 매칭 현황이 불확실하면 신뢰도 판단 근거와 주의사항에 반영한다.
- 조합마다 메인 멘토와 보완 멘토 역할을 분리한다.
- 강점과 약점은 과장하지 않는다.

## 테스트 전략

```bash
uv run pytest tests/modules/report/ -v
```

필수 검증 항목:

- `ReportGenerationRequest` validation
- `CombCandidateResult` 입력 호환성
- mentor id 매핑 성공
- mentor id 누락 시 명확한 실패
- LLM JSON 응답 파싱 성공
- LLM JSON 응답 파싱 실패 처리
- `POST /api/report` 응답 계약
- sample report 의존 제거
