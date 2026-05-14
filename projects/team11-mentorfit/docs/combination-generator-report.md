# 멘토 조합 생성 모듈 구현 결과 보고서

> 작성일: 2026-05-10  
> 브랜치: `feat/combination`  
> 커밋 범위: `4f0bde5` → `d69118b` (7 commits)

---

## 1. 구현 요약

멘토 후보 검색 결과를 LLM으로 분석·보강하고, 각 후보를 기준 멘토로 삼아 전체 멘토 풀에서 약점을 보완하는 2명을 선정해 3인 조합을 생성하는 파이프라인 4단계를 완료했다.

---

## 2. 변경 파일 목록

| 파일 | 유형 | 내용 |
|------|------|------|
| `app/core/upstage.py` | 수정 | `UpstageClient.chat_completion()` 추가 |
| `app/core/config.py` | 수정 | `combination_model: str = "solar-pro"` 추가 |
| `app/modules/mentor_candidate/schemas.py` | 수정 | `CandidateResult`에 `rank`, `reason`, `weak_point` 필드 추가 |
| `app/modules/mentor_candidate/service.py` | 수정 | `MentorCandidateService` 클래스 추가 |
| `app/modules/combination_generator/__init__.py` | 신규 | 패키지 마커 |
| `app/modules/combination_generator/schemas.py` | 신규 | `CombCandidateResult`, `CombinationResponse` |
| `app/modules/combination_generator/service.py` | 신규 | `CombinationGeneratorService` 클래스 |
| `tests/modules/mentor_candidate/test_service.py` | 수정 | `MentorCandidateService` 테스트 2개 추가 |
| `tests/modules/combination_generator/__init__.py` | 신규 | 패키지 마커 |
| `tests/modules/combination_generator/test_service.py` | 신규 | `CombinationGeneratorService` 테스트 4개 |

---

## 3. 구현 상세

### 3-1. UpstageClient.chat_completion()

```python
async def chat_completion(self, messages: list[dict], model: str = "solar-pro") -> str
```

기존 `get_embedding()`과 동일한 재시도 패턴(최대 3회, 지수 backoff)으로 Solar chat completion을 호출한다. 이 메서드는 `MentorCandidateService`와 `CombinationGeneratorService` 두 곳에서 공유한다.

### 3-2. MentorCandidateService

기존 `search_candidates()` 함수를 내부에서 호출하고 결과를 LLM으로 보강하는 래퍼 클래스. 기존 함수는 무수정이다.

**데이터 흐름:**
```
search_candidates() 호출
  └─ top_k 후보 반환
       └─ 각 후보별 _analyze_candidate() 호출 (LLM 1 call)
            └─ {"reason": "...", "weak_point": "..."} JSON 파싱
                 └─ rank, reason, weak_point 보강된 CandidateResult 반환
```

**스펙 불일치 해소:**  
원본 스펙의 `CandidateResult`에는 `rank`, `reason`, `weak_point`가 포함되어 있었으나 실제 코드에 미반영 상태였다. `schemas.py`에 기본값이 있는 선택적 필드로 추가해 기존 코드와의 하위 호환성을 유지하면서 스펙을 충족했다.

### 3-3. CombinationGeneratorService

**데이터 흐름:**
```
generate(team_profile, candidates) 호출
  └─ 후보 N개 순회
       └─ 각 후보별 _generate_single() 호출
            └─ _build_prompt(): 기준 멘토 + 팀 프로필 + 전체 멘토 풀(기준 멘토 제외)
                 └─ LLM 1 call → {second_mentor_id, third_mentor_id, strengths, weak_points, reason}
                      └─ _parse_llm_response(): ID 유효성 검증 + CombCandidateResult 생성
  └─ list[CombCandidateResult] 반환
```

**설계 결정사항:**

| 결정 | 선택한 방향 | 이유 |
|------|------------|------|
| 보완 멘토 탐색 범위 | 전체 멘토 풀 | 후보 풀에만 국한하면 좋은 보완 멘토를 놓칠 수 있음 |
| 보완 멘토 선정 방법 | LLM 판단 위임 | 자연어 약점을 태그 매칭보다 정확히 해석 가능 |
| LLM 호출 수 | 조합당 1 call | 2nd/3rd 멘토 선정 + 조합 메타데이터를 한 번에 처리해 비용 절감 |
| API 인터페이스 | 메서드 호출 | HTTP 엔드포인트 불필요, 파이프라인 내부 호출로 충분 |

### 3-4. 에러 처리

| 상황 | 처리 결과 |
|------|-----------|
| JSON 파싱 실패 (`JSONDecodeError`) | 빈 필드 + `reason` 승계, 예외 미전파 |
| 비dict JSON 응답 (`AttributeError`) | 동일하게 graceful 처리 |
| 존재하지 않는 mentor_id | 풀 ID set으로 검증 후 빈 문자열 처리 |
| LLM API 3회 실패 | 예외 전파 (호출 측에서 처리) |
| `mock_mode = True` | LLM 호출 없이 빈 값 반환 |

---

## 4. 테스트 결과

```
======================== 21 passed in 0.36s ========================
```

| 테스트 파일 | 테스트 수 | 결과 |
|-------------|-----------|------|
| `tests/modules/combination_generator/test_service.py` | 4 | ✅ PASS |
| `tests/modules/mentor_candidate/test_service.py` | 8 (기존 6 + 신규 2) | ✅ PASS |
| `tests/modules/mentor_candidate/test_tag_scorer.py` | 9 (기존, 무수정) | ✅ PASS |

### 신규 테스트 목록

**MentorCandidateService (2개)**
- `test_mentor_candidate_service_search_enriches_candidates` — `rank`, `reason`, `weak_point`가 LLM 응답으로 채워짐
- `test_mentor_candidate_service_mock_mode_skips_llm` — `mock_mode=True`시 빈 문자열 반환

**CombinationGeneratorService (4개)**
- `test_generate_returns_n_combinations` — 후보 N개 → 조합 N개, rank 승계 확인
- `test_base_mentor_excluded_from_candidate_ids` — 기준 멘토 ID가 `candidate_ids`에 미포함
- `test_parse_failure_returns_partial_result` — invalid JSON 응답 → 빈 필드 + `reason` 승계
- `test_unknown_mentor_id_handled` — 없는 ID 반환 → 제거, 유효 ID만 포함

---

## 5. 커밋 이력

| 커밋 | 내용 |
|------|------|
| `4f0bde5` | `feat(upstage): ✨ add chat_completion method to UpstageClient` |
| `3dd02a7` | `chore(config): 🔧 add combination_model setting` |
| `5401aa5` | `feat(mentor-candidate): ✨ add rank/reason/weak_point fields to CandidateResult` |
| `cb1fa5c` | `feat(mentor-candidate): ✨ add MentorCandidateService with LLM enrichment` |
| `2915bfc` | `feat(combination-generator): ✨ add combination_generator schemas` |
| `9efdb09` | `feat(combination-generator): ✨ implement CombinationGeneratorService` |
| `d69118b` | `fix(combination-generator): 🐛 catch AttributeError in _parse_llm_response` |

---

## 6. 미구현 및 향후 과제

| 항목 | 내용 |
|------|------|
| LLM 병렬 호출 | 현재 후보 순차 처리. `asyncio.gather()`로 병렬화 시 latency 단축 가능 |
| `mock_mode` 조합 테스트 | `CombinationGeneratorService`의 `mock_mode` 경로 테스트 미작성 |
| 팀 프로필 필드 토큰 제한 | `mentor.bio[:100]`은 적용되어 있으나 `team_profile` 필드는 길이 제한 없음 |
| 파이프라인 통합 | `report` 모듈(5단계)에서 `CombinationGeneratorService` 연결 필요 |
