# 멘토 조합 생성 모듈 기능 명세서

## 1. 모듈 입력
'3. 멘토 후보 검색 모듈' 결과, 다음과 같은 데이터 모델이 생성된다.

```python
@dataclass(frozen=True)
class CandidateResult(BaseModel):
    mentor_id: int
    rank: int
    reason: str
    weak_point: str
```

위 데이터 모델이 List에 담겨 전달된다. (type: `list[CandidateResult]`)  
전달은 메서드 파라미터를 통해 전달된다.

## 2. 모듈 동작
- 각각의 `CandidateResult`에 포함된 `mentor_id`를 통해 *data/mentors.json* 에서 멘토님을 매핑한다.
- 매핑된 멘토님 정보와 추천 이유(`reason`), 약점(`weak_point`) 정보를 이용해서 보완해야 할 약점을 강점으로 가지고 있는 멘토님을 찾아 한 명의 멘토님을 찾는다.
- 두 분의 약점을 채울 수 있는 마지막 다른 한 분의 멘토님을 찾는다.
- 위 동작을 모든 `CandidateResult`에 대해 수행한다.

## 3. 모듈 출력
모듈이 모든 동작을 마치면 다음과 같은 데이터 모델이 출력된다.

```python
@dataclass(frozen=True)
class CombCandidateResult(BaseModel):
    mentor_id: str
    candidate_ids: list[int] = []
    strengths: list[str] = []
    weak_points: list[str] = []
    rank: int
    reason: str
    weak_point: str
```

`CombCandidateResult`이 List에 담겨 반환된다. (type: `list[CombCandidateResult]`)
