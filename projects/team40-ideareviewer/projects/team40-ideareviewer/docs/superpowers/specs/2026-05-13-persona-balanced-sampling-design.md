# 페르소나 균형 샘플링 재설계

- 작성일: 2026-05-13
- 대상 파일: `scripts/sample_hf_personas.py`, `tests/test_sample_hf_personas.py`
- 관련 노드: `nodes/f1_select.py` (이 panel에서 2명을 LLM이 선정)

## 1. 배경과 문제

현재 `raw_personas.selected_100.json`은 다음 편향을 가짐.

- 60대+ 40명 (의도된 시니어 가중)
- 무직 31명 (통제 안 됨)
- 충청북 15명 / 서울 8명 (지역 통제 안 됨)
- 직업 49종 long tail, `other` 그룹이 풀에서 27% (분류 규칙 누락)
- 10대 0명, 학생·자영업 0명 (데이터셋 한계 + 분류 누락)

`f1_select`는 이 100명 중 LLM이 demographic 매칭으로 2명을 뽑는 구조이므로, panel이 한쪽으로 쏠리면 "다양한 타겟별 기획"에서 보완적 2인 구성이 불가능해진다.

## 2. 목표

**다양한 타겟별 기획을 2명 페르소나가 리뷰할 수 있도록 panel을 균등화한다.**

- 연령·직업이라는 두 핵심 축에서 어떤 기획이 와도 매칭 가능한 후보가 보장되어야 함.
- 지역·성별·가족·학력은 일정 수준 다양성만 확보(엄격 quota 불필요).

## 3. 의사 결정 요약

| 결정 | 값 | 근거 |
|---|---|---|
| 기획 범위 | 다양한 타겟별 균등 | 사용자 결정 |
| 강제 quota 축 | 연령 + 직업 | 사용자 결정 |
| 연령 분포 | 20s/30s/40s/50s 각 17, 60s/70+ 각 16 | 시니어 편중 해소, 6군 평탄화 |
| 10대 포함 여부 | 포기 | 풀(9778)·원본 데이터셋에 10대 사실상 없음 |
| 학생 그룹 | 포기 | 풀에 "학생" 직업 0건 |
| 직업 분류 | 키워드 규칙 보강 후 11군 marginal quota | 현 `other` 27% 안의 일반 직업들을 정상 그룹으로 재분류 |
| 충돌 처리 | greedy 점수 합산 (연령 deficit + 직업 deficit + rarity) | 100명에 2D cell quota는 비현실적 |
| 풀 재구축 | 불필요 | 20대+만 사용 |
| KSCO 표준 분류 | 채택 안 함 | 100명 규모에 오버엔지니어링 (YAGNI) |

## 4. 연령 quota

```
20s: 17
30s: 17
40s: 17
50s: 17
60s: 16
70+: 16
합계: 100
```

`AGE_GROUP_ORDER`, `AGE_GROUP_WEIGHTS` 갱신.

## 5. 직업 quota

```
office             : 13
service_sales      : 12
field_labor        : 12
professional       : 11
retired_unemployed : 10   (상한 캡)
education          :  9
care_health        :  8
self_employed      :  8   (신규: 분류 보강 후 활성)
agriculture        :  6
arts_media         :  6
homemaker          :  5
합계               : 100
```

풀 supply가 quota 미달인 군(agriculture, arts_media, homemaker)은 가능한 만큼만 채우고, **부족분은 supply가 충분한 군(office, service_sales, field_labor) 순서로 흘림**.

신규 상수 `OCCUPATION_GROUP_WEIGHTS` 도입. `make_age_quotas`는 `make_quotas(total, weights)`로 일반화.

## 6. `occupation_group` 분류 규칙 보강

`scripts/sample_hf_personas.py:168` 의 `occupation_group` 키워드 보강.

| 그룹 | 추가 키워드 | 흡수되는 풀 직업 (출현 수) |
|---|---|---|
| `field_labor` | `청소`, `경비`, `용접`, `건립`, `포장`, `보조`, `조작`, `수리` | 건물 청소원(189), 건물 경비원(168), 시설 경비원(114), 주방 보조원(76), 전기 용접원(49), 강구조물 건립원(19), 수동 포장원(19), 그 외 물품 이동 장비 조작원(20) |
| `service_sales` | `상담원`, `비서`, `안내` | 전화 상담원(111), 일반 비서(102) |
| `professional` | `프로그래머`, `컨설턴트`, `기획자`, `안전원`, `시스템 운영` | 범용 SW 프로그래머(29), 경영 컨설턴트(43), 상품 기획자(22), 산업 안전원(77), 정보 시스템 운영자(27) |
| `self_employed` | `경영자`, `임원`, `사장`, `점장` | 소규모 상점 경영자(48), 기업 고위 임원(37) |

**규칙 적용 순서 고정** — 예: 산업 안전원이 `field_labor`("산업" 키워드)가 아니라 `professional`("안전원")로 잡혀야 하므로 더 구체적인 키워드를 가진 그룹을 위로. 보강 후 풀에서 `other` 비중이 5% 이하가 되는지 dry-run으로 검증.

**잔여 `other`** — quota에서 제외. `_rarity_score`에는 `unknown`과 동일하게 들어가서 균형에 영향만 주고 강제 채움은 없음.

## 7. Marginal quota greedy 알고리즘

`select_with_quotas`를 다음과 같이 교체.

```
입력: pool[], age_quota{group→n}, occ_quota{group→n}
출력: selected[] (길이 = total)

1. selected = []
2. 매 라운드:
   a. age_deficit[g]  = max(0, age_quota[g]  - count(selected, age_group=g))
      occ_deficit[g]  = max(0, occ_quota[g]  - count(selected, occ_group=g))
   b. 남은 풀에 대해 점수 계산:
      score(row) = W_AGE * age_deficit[row.age_group]
                 + W_OCC * occ_deficit[row.occ_group]
                 + rarity_score(row, frequencies(selected))
                 + 0.1 * quality_score(row)
   c. argmax score 의 row 를 selected 에 추가, 풀에서 제거
   d. len(selected) == total 이면 종료
3. 충돌·부족:
   - 모든 deficit 이 0 이 되어도 total 미만이면 quality_score 만으로 마저 채움
   - 어떤 그룹의 supply 가 quota 보다 적으면 deficit 은 자동으로 supply 한계에서 멈추고
     다른 그룹의 deficit 점수가 더 커져서 자연스럽게 흘러감
```

상수: `W_AGE = W_OCC = 10`, rarity 0~3 범위, quality 0~6 범위. quota 미달 동안 quota 신호가 압도, 만족 후 rarity·quality 가 작동.

`_rarity_score`에서 `occupation_group`은 제외(이미 quota 가 처리). 나머지 5축(`sex`, `province`, `family_type`, `education_level`, `has_digital_signal`)은 그대로 rarity 에 사용.

## 8. 변경 범위

### `scripts/sample_hf_personas.py`

- `AGE_GROUP_WEIGHTS` 6군 평탄화 (`20s:17, 30s:17, 40s:17, 50s:17, 60s:16, 70plus:16`)
- `OCCUPATION_GROUP_WEIGHTS` 신규 추가 (§5)
- `occupation_group` 키워드 보강 + 규칙 순서 재정렬 (§6)
- `make_age_quotas` → `make_quotas(total, weights)` 일반화. 호출부 두 곳 갱신.
- `select_with_quotas` → marginal greedy (§7)
- `_rarity_score` 에서 `occupation_group` 제거
- `build_summary` 의 `criteria` 와 `age_quotas` 필드 갱신 (직업 quota 도 포함)

### `tests/test_sample_hf_personas.py`

추가할 테스트 케이스:

1. **분류 규칙** — 각 신규 키워드별 매칭 확인.
   - "건물 청소원" → `field_labor`
   - "전화 상담원" → `service_sales`
   - "범용 소프트웨어 프로그래머" → `professional`
   - "경영 컨설턴트" → `professional`
   - "산업 안전원" → `professional` (field_labor가 아님)
   - "소규모 상점 경영자" → `self_employed`
   - "기업 고위 임원" → `self_employed`
2. **연령 quota 평탄화** — `make_quotas(100, AGE_GROUP_WEIGHTS)` 가 정확히 17·17·17·17·16·16 을 반환.
3. **직업 quota 합계** — `sum(OCCUPATION_GROUP_WEIGHTS.values()) == 100`.
4. **greedy 동시 만족** — 6×11 cell 합성 풀을 만들어 selected 100명의 연령·직업 marginal 이 정확히 quota 와 일치.
5. **supply 부족 흘리기** — agriculture quota 6 이지만 풀에 agri 가 2 명만 있을 때, selected 의 agri = 2 이고 총원 = 100 이며, 부족분은 office/service_sales/field_labor 로 흐름.
6. **잔여 `other` 처리** — `other` 만으로는 quota 가 채워지지 않는지(quota 에서 빠졌는지) 검증.

### 데이터

- 풀(`raw_personas.pool_10000.json`)은 재사용. 재구축 불필요.
- `candidate` 와 `selected` 는 새 스크립트로 재생성.

## 9. 운영 명령

```powershell
python scripts/sample_hf_personas.py `
  --pool-size 10000 --candidate-size 1000 --selected-size 100 `
  --source api --source-window-size 30000 --start-row 0
```

풀이 이미 있으면 풀 단계 캐시 재사용은 별도 PR 에서 검토(YAGNI). 현재는 풀까지 새로 받아도 무방한 비용.

## 10. 검증 기준 (구현 후)

새 `selected_100.json` 이 다음을 만족.

- 연령 분포: 17·17·17·17·16·16 (±0)
- 직업 분포: §5 표 ±1 이내(공급 부족 군 제외)
- 무직 비중: ≤ 10%
- 단일 province 비중: ≤ 12% (rarity 효과)
- `other` 비중: ≤ 5%
- 성별: 45~55% 범위

## 11. 명시적으로 빼는 것 (YAGNI)

- 직업×연령 2D cell quota
- KSCO 대분류 매핑 테이블
- 10대·학생 슬롯
- 풀 캐시 재사용 옵션
- LP solver, Hungarian 등 정밀 최적화 (greedy 로 충분)
