# 시스템 아키텍처

## 전체 파이프라인

```text
[Streamlit UI: 팀 정보 입력/대화]
  - 좌측: 팀원, 팀 핏, 팀 전체 목적에 대한 프롬프트와 대화 로그
  - 우측: LLM이 생성한 팀 리포트와 구조화된 TeamProfile
        │
        ▼
[1] team_profile
  - 사용자 프롬프트와 대화 로그를 TeamProfile로 구조화
  - 팀 리포트(team_report)를 사용자용 서술형 요약으로 생성
        │
        ▼
[2] mentor_candidate
  - 실제 멘토 데이터 전체를 Solar 임베딩으로 1차 필터링
  - 필터링된 후보를 Solar LLM Structured Output에 전달
  - CandidateResult(mentor_id, rank, reason, weak_point) 생성
        │
        ▼
[3] combination_generator
  - CandidateResult의 mentor_id를 실제 Mentor 데이터와 연결
  - 메인 멘토 1명 + 보완 멘토 2명 조합 생성
  - CombCandidateResult(rank, strengths, weak_points, reason, weak_point) 생성
        │
        ▼
[4] report
  - TeamProfile, team_report, CandidateResult, CombCandidateResult, Mentor 데이터를 입력으로 수신
  - 최종 사용자용 RecommendationReport 생성
        │
        ▼
[Streamlit UI: 추천 리포트 페이지]
  - 팀 요약, 후보 멘토, 추천 조합, 최종 추천, 주의사항 표시
```

## 컴포넌트 역할 분리

| 계층 | 담당 |
|------|------|
| `app/modules/*/router.py` | HTTP 요청 수신, 입출력 직렬화 |
| `app/modules/*/service.py` | 모듈별 파이프라인 오케스트레이션과 비즈니스 로직 |
| `app/modules/*/schemas.py` | Pydantic 모델과 모듈 간 데이터 계약 |
| `app/core/config.py` | 환경변수, 모델명, 후보 수 등 전역 설정 |
| `app/core/upstage.py` | Solar API 클라이언트(임베딩, 채팅 완성) |
| `app/data/mentors.py` | 로컬 멘토 데이터 로딩과 캐시 |

## 모듈별 책임

### `team_profile`

사용자의 자유 입력과 대화 로그를 읽어 현재 `mentor_candidate.schemas.TeamProfile` 계약에 맞는 구조화 데이터를 만든다. 동시에 사용자가 바로 검토할 수 있는 `team_report`를 생성한다.

### `mentor_candidate`

후보 검색만 담당한다. 출력은 `CandidateResult`이며, 후보 조합이나 최종 리포트 문구를 만들지 않는다.

### `combination_generator`

후보별 약점을 기준으로 보완 멘토 2명을 선정한다. `CombCandidateResult`는 조합 생성 모듈의 소유 모델이며, `report` 모듈은 이 모델을 재정의하지 않고 import해서 사용한다.

### `report`

상위 모듈의 실제 산출물을 최종 사용자용 추천 리포트로 변환한다. sample JSON은 사용하지 않으며, `POST /api/report` 입력으로 전달된 실제 데이터를 기준으로 생성한다.

## 데이터 흐름 상세

```text
ReportGenerationRequest
├── team_profile: TeamProfile
├── team_report: str
├── candidates: list[CandidateResult]
├── combinations: list[CombCandidateResult]
├── mentors: list[Mentor]
└── current_matching_status: str | None
        │
        ▼
RecommendationReport
├── team_summary
├── confidence_basis
├── candidate_summary
├── combinations
├── final_recommendation
├── cautions
└── generated_at
```

## Upstage Solar API 활용

| 용도 | 모델 | 호출 위치 |
|------|------|-----------|
| 팀 프로필 구조화 및 팀 리포트 생성 | `solar-pro` 또는 `solar-1-mini` | `team_profile` |
| 멘토 후보 임베딩 필터링 | `solar-embedding-1-large` | `mentor_candidate.retriever` |
| 멘토 후보 최종 선정 | `solar-pro` 또는 `solar-1-mini` | `mentor_candidate.llm_selector` |
| 멘토 조합 생성 | `solar-pro` | `combination_generator` |
| 최종 추천 리포트 생성 | `solar-pro` | `report` |

`MOCK_MODE=true`에서는 외부 LLM 호출 없이 결정적인 테스트용 데이터를 반환한다.

## MVP 범위

**포함**

- 로컬 FastAPI + Streamlit 실행
- 실제 멘토 JSON 데이터 기반 후보 추천
- 프롬프트 기반 팀 리포트 생성
- 메인 멘토 1명 + 보완 멘토 2명 조합 추천
- 실제 입력 데이터 기반 최종 추천 리포트

**제외**

- 멘토 자동 연락, 일정 조율
- 사용자 계정 관리, 다중 팀 관리
- 실시간 Notion 동기화 보장
- 브라우저 localStorage 영속화
