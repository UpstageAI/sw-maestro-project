# 매억남 매매 원칙 (구조적 트레이딩 가이드)

> 목적: autocoin-ai MVP 트레이더 persona/RAG dataset.
> 범위: 공개 자료에 정리된 매억남 관련 매매 원칙을 Binance Spot Testnet 데모에 맞게 재해석한 mock knowledge.
> 주의: 원문 인터뷰/게시글을 직접 보증하는 canonical 자료가 아니다. 팀원 A가 실제 인터뷰/SNS/블로그 원문을 정리하면 이 파일을 교체한다.
> 투자 조언이 아니며, 데모용 의사결정 근거 데이터다.

## Metadata

- trader_id: `maeoaknam`
- display_name: `매억남`
- style: structural_elliott_wave_fibonacci_discretionary
- default_persona: `MODERATE`
- source_type: public Korean summaries / YouTube / community-derived notes
- primary_sources:
  - https://www.youtube.com/@maeoaknam

---

## 엘리어트 충격파동 구조 이해 (1-2-3-4-5)

시장의 무질서한 움직임 속에서도 반복되는 5개의 상승 파동이 있다. 1파(시작), 2파(되돌림), 3파(폭발), 4파(횡보 조정), 5파(마지막 불꽃)로 구성된 충격파동을 통해 현재 가격이 어디쯤 와 있는지 지도를 그린다. 파동의 위치를 파악하는 것이 매매의 출발점이다.

- chunk_id: `maeoaknam.elliott_impulse_wave_structure`
- keywords: `엘리어트`, `elliott wave`, `충격파동`, `1파`, `2파`, `3파`, `4파`, `5파`, `파동 구조`, `임펄스`
- preferred_action: identify current wave position before entry; trade with wave direction
- avoid_when: 현재 파동 위치가 불명확할 때, 파동 카운팅이 안 잡힐 때는 관망
- source_refs: `maeoaknam youtube summary`

## 3파동 집중 공략 (핵심 사냥터)

3파는 가장 길고 강력하며 거래량이 압도적으로 터지는 구간이다. 매억남이 가장 큰 수익을 내는 핵심 사냥터다. 가격이 오르는데 거래량이 이전 고점 거래량을 압도적으로 돌파하면 진짜 3파가 진행 중이라는 강력한 신호다.

- chunk_id: `maeoaknam.third_wave_focus`
- keywords: `3파`, `third wave`, `폭발`, `거래량`, `강력`, `핵심`, `임펄스`, `추세`
- preferred_action: BUY at 2-wave end (3-wave entry); maximize position size during confirmed 3rd wave with volume breakout
- avoid_when: 거래량이 동반되지 않은 상승 구간, 3파가 1파보다 짧아질 위험이 있을 때
- source_refs: `maeoaknam youtube summary`

## 2파 진입 타점 (3파 초입 잡기)

2파는 1파의 상승분을 크게 깎아 먹으며 개미들을 털어내는 구간이다. 보통 피보나치 0.618 지점까지 눌린다. 매억남은 2파 조정이 끝나고 3파가 시작되는 지점을 가장 중요한 매수 타점으로 삼는다.

- chunk_id: `maeoaknam.second_wave_entry_point`
- keywords: `2파`, `second wave`, `되돌림`, `진입 타점`, `0.618`, `피보나치`, `눌림`, `3파 초입`
- preferred_action: BUY at 2-wave end near fibonacci 0.618; this is the optimal risk/reward entry for 3rd wave
- avoid_when: 2파 조정이 아직 끝나지 않았을 때, 1파 시작점 아래로 내려갈 위험이 있을 때
- source_refs: `maeoaknam youtube summary`

## 5파 경계 (마지막 불꽃 주의)

5파는 상승의 마지막 단계로 거래량은 3파보다 적지만 가격은 고점을 갱신하며 개미들을 유혹한다. 5파에서 가격 고점을 갱신하는데 거래량이 3파보다 눈에 띄게 줄었다면 파동 종료가 임박한 것이다. 익절 준비를 한다.

- chunk_id: `maeoaknam.fifth_wave_exit_warning`
- keywords: `5파`, `fifth wave`, `마지막 불꽃`, `거래량 다이버전스`, `익절`, `파동 종료`, `고점`, `경계`
- preferred_action: reduce position and prepare exit at 5th wave; watch for volume divergence as exit signal
- avoid_when: 5파 구간에서 신규 대량 진입을 하려 할 때, 거래량 감소 무시하고 홀딩할 때
- source_refs: `maeoaknam youtube summary`

## ABC 조정파동 이해 (시드 지키는 구간)

상승 5파 이후 반드시 오는 A-B-C 형태의 하락파동이다. A파(개미 매수 구간), B파(가짜 반등 데드캣), C파(절망의 하락)로 구성된다. B파는 전고점을 넘지 못하고 꺾이며, C파는 손절 물량이 쏟아지며 1파 시작점 근처까지 밀리기도 한다.

- chunk_id: `maeoaknam.abc_corrective_wave`
- keywords: `ABC 조정`, `corrective wave`, `A파`, `B파`, `C파`, `데드캣`, `조정`, `하락파동`
- preferred_action: HOLD new entries during ABC correction; wait for C-wave end as reversal entry; avoid B-wave dead-cat bounce traps
- avoid_when: B파 가짜 반등을 추세 전환으로 착각해 진입할 때, C파 진행 중 추가 매수할 때
- source_refs: `maeoaknam youtube summary`

## 파동 카운팅 절대 규칙 3가지

파동을 제멋대로 해석하지 않기 위한 3가지 절대 규칙이다. 1) 2파는 절대로 1파 시작점 아래로 내려갈 수 없다. 2) 3파는 1, 3, 5파 중 절대로 가장 짧은 파동일 수 없다. 3) 4파 저점은 1파 고점과 겹칠 수 없다. 이 규칙이 어긋나면 카운팅을 폐기하고 관망한다.

- chunk_id: `maeoaknam.wave_counting_absolute_rules`
- keywords: `카운팅 규칙`, `2파 한계`, `3파 최장`, `4파 겹침 금지`, `파동 폐기`, `관망`, `절대 규칙`
- preferred_action: invalidate wave count and HOLD when any of the 3 rules are violated; restart counting from scratch
- avoid_when: 카운팅 규칙이 깨졌는데도 기존 시나리오를 고집할 때, 억지로 파동을 맞추려 할 때
- source_refs: `maeoaknam youtube summary`

## 프랙탈 다중 타임프레임 분석

큰 파동 속에 작은 파동이 들어있다. 일봉의 1파 안을 15분봉으로 쪼개보면 그 안에도 작은 1-2-3-4-5파가 존재한다. 큰 추세(일봉)가 상승 3파인 것을 확인했다면 작은 파동(15분봉)이 조정 4파를 끝내고 5파로 넘어가려는 찰나에 진입한다. 이것이 승률과 손익비를 동시에 잡는 비결이다.

- chunk_id: `maeoaknam.fractal_multi_timeframe`
- keywords: `프랙탈`, `fractal`, `다중 타임프레임`, `일봉`, `15분봉`, `내부 파동`, `타점 정교화`, `multi-timeframe`
- preferred_action: confirm higher timeframe wave, then time entry with lower timeframe sub-wave completion
- avoid_when: 상위 타임프레임 확인 없이 하위 타임프레임 신호만으로 진입할 때
- source_refs: `maeoaknam youtube summary`

## 피보나치 0.618 황금비율 타점

매억남이 가장 사랑하는 타점이다. 1파 이후 2파 조정이나 전체 상승에 대한 ABC 조정의 끝이 0.618 자리에서 자주 발생한다. 이 자리를 손익비가 가장 좋은 자리라고 부른다. 하락하던 차트가 0.618 근처에서 멈칫하며 캔들 꼬리를 만든다면 매수 세력이 대기하고 있다는 강력한 증거다.

- chunk_id: `maeoaknam.fibonacci_0618_entry`
- keywords: `피보나치`, `fibonacci`, `0.618`, `황금비율`, `되돌림`, `타점`, `손익비`, `지지`
- preferred_action: prioritize entries at fibonacci 0.618 retracement; treat price hesitation with wicks at 0.618 as entry signal
- avoid_when: 0.618을 이탈하고 0.786, 0.886까지 밀릴 때 추가 진입 자제
- source_refs: `maeoaknam youtube summary`

## 피보나치 되돌림 구간별 의미

0.382는 강한 추세에서 4파 조정이 멈추는 구간이다. 0.5는 심리적 마지노선으로 단독 근거보다 다른 지지선과 겹칠 때 참고한다. 0.786~0.886은 추세가 죽기 직전 마지막 지지선으로 여기까지 밀리면 반등이 나와도 추세가 꺾일 위험이 크다.

- chunk_id: `maeoaknam.fibonacci_retracement_levels`
- keywords: `피보나치 구간`, `0.382`, `0.5`, `0.786`, `0.886`, `되돌림`, `지지`, `추세 위험`
- preferred_action: 0.382 = light entry for strong trend; 0.618 = primary entry; 0.786+ = caution zone, reduce size
- avoid_when: 0.886을 이탈했는데도 반등을 기대하며 추가 매수할 때
- source_refs: `maeoaknam youtube summary`

## 피보나치 확장으로 목표가 설정

수익을 극대화하기 위해 피보나치 확장을 사용한다. 1파와 2파의 크기를 재서 3파가 어디까지 뻗어 나갈지 예측한다. 1.618 확장이 3파의 1차 목표가(TP)다. ABC 조정에서 A파와 C파가 1:1로 만나는 지점은 조정 끝의 필수 체크 포인트다. 2.618 이상 연장될 때는 무리하게 익절하지 않고 추세를 끝까지 지켜본다.

- chunk_id: `maeoaknam.fibonacci_extension_target`
- keywords: `피보나치 확장`, `extension`, `1.618`, `목표가`, `TP`, `ABC 1:1`, `2.618`, `연장`
- preferred_action: set 1.618 extension as primary take-profit target; check ABC 1:1 equality for correction end
- avoid_when: 1.618 도달 전에 조급하게 전량 익절할 때, 2.618 연장 구간에서 무리하게 숏 진입할 때
- source_refs: `maeoaknam youtube summary`

## 중첩(Confluence) 원리 - 근거 겹치기

피보나치 수치 하나만 보고 들어가지 않는다. 여러 파동의 수치가 겹치는 구간을 찾는다. 피보나치 0.618 지점이 과거 강력한 지지/저항 라인(매물대)과 일치하거나, 큰 파동과 내부 파동의 피보나치 수치가 겹칠 때 신뢰도가 90% 이상으로 올라간다.

- chunk_id: `maeoaknam.confluence_overlap_principle`
- keywords: `중첩`, `confluence`, `겹치기`, `매물대`, `피보나치 중첩`, `신뢰도`, `근거 쌓기`
- preferred_action: require minimum 2 confluent signals before entry; higher confluence = larger position size
- avoid_when: 근거가 하나뿐일 때 큰 비중으로 진입하려 할 때
- source_refs: `maeoaknam youtube summary`

## 로그 차트 + 캔들 꼬리 기준 피보나치 설정

코인처럼 변동성이 큰 종목은 반드시 로그(Log) 눈금을 켜고 피보나치를 그려야 수치가 정확하게 맞는다. 피보나치는 캔들의 최고점 꼬리와 최저점 꼬리를 연결한다. 시장의 극단적인 심리까지 데이터에 포함해야 하기 때문이다.

- chunk_id: `maeoaknam.log_chart_wick_fibonacci`
- keywords: `로그 차트`, `log scale`, `캔들 꼬리`, `wick`, `피보나치 설정`, `정확도`, `극단 심리`
- preferred_action: always use log scale for crypto fibonacci; draw from wick high to wick low for accuracy
- avoid_when: 선형 차트로 피보나치를 그어 수치가 어긋날 때, 캔들 몸통만 기준으로 피보나치를 설정할 때
- source_refs: `maeoaknam youtube summary`

## 상승 다이버전스 - 바닥 잡기 타점

하락장 끝에서 반등을 확신하는 타점이다. 차트 저점은 낮아졌는데 RSI 지표 저점은 오히려 올라가는 모습이다. 가격은 더 떨어졌지만 매수 힘이 더 강해졌다는 의미다. 피보나치 0.618 지점과 상승 다이버전스가 동시에 발견되면 강력하게 진입한다.

- chunk_id: `maeoaknam.bullish_divergence_entry`
- keywords: `상승 다이버전스`, `bullish divergence`, `RSI`, `바닥`, `저점 불일치`, `반등`, `매수 타점`
- preferred_action: BUY when price makes lower low but RSI makes higher low; combine with fibonacci confluence for high-conviction entry
- avoid_when: 다이버전스 캔들이 아직 마감되지 않아 RSI가 확정되지 않았을 때
- source_refs: `maeoaknam youtube summary`

## 하락 다이버전스 - 고점 회피 및 익절

상승장 고점을 포착하는 타점이다. 차트 고점은 높아졌는데 RSI 지표 고점은 낮아지는 모습이다. 가격은 비싸졌지만 돈의 힘이 약해졌다는 의미로 세력이 개미에게 물량을 떠넘기는 신호다. 상승 5파동의 끝에서 이 신호가 나오면 전량 익절하거나 매도로 전환한다.

- chunk_id: `maeoaknam.bearish_divergence_exit`
- keywords: `하락 다이버전스`, `bearish divergence`, `RSI`, `고점`, `익절`, `5파 끝`, `물량 처분`, `세력`
- preferred_action: exit or reduce at 5th wave top with bearish RSI divergence; treat as strongest exit signal
- avoid_when: 하락 다이버전스 신호가 나왔는데도 더 갈 것이라는 기대로 홀딩할 때
- source_refs: `maeoaknam youtube summary`

## 시간봉별 다이버전스 파괴력 (체급 차이)

다이버전스는 어떤 시간봉에서 보느냐에 따라 파괴력이 완전히 다르다. 5분봉 다이버전스는 단타용 잠깐의 반등만 준다. 1시간봉, 4시간봉 다이버전스는 추세 자체가 바뀌는 경우가 많다. 매억남 매매의 메인 타겟은 1시간봉~4시간봉 다이버전스다.

- chunk_id: `maeoaknam.divergence_timeframe_strength`
- keywords: `다이버전스`, `시간봉`, `체급`, `1시간봉`, `4시간봉`, `파괴력`, `추세 전환`, `단타`
- preferred_action: weight 1H/4H divergence as primary signals; treat 5min divergence as scalp only
- avoid_when: 5분봉 다이버전스만 보고 추세 전환으로 판단해 대규모 진입할 때
- source_refs: `maeoaknam youtube summary`

## 캔들 마감 후 컨펌 대기 (뇌동매매 금지)

캔들이 마감되어 RSI 수치가 확정될 때까지 기다린다. 뜰 것 같아서 미리 들어가는 것은 매억남이 가장 경계하는 뇌동매매다. 다이버전스는 캔들이 마감된 후에만 유효한 신호다.

- chunk_id: `maeoaknam.candle_close_confirmation`
- keywords: `컨펌`, `confirmation`, `캔들 마감`, `뇌동매매`, `대기`, `RSI 확정`, `성급한 진입 금지`
- preferred_action: wait for candle close before acting on divergence or fibonacci touch; never enter on open candle signal
- avoid_when: 캔들이 마감되기 전에 다이버전스가 뜰 것 같다는 이유로 선진입할 때
- source_refs: `maeoaknam youtube summary`

## 히든 다이버전스 - 눌림목 추가 매수

일반 다이버전스가 반전을 의미한다면 히든 다이버전스는 추세의 지속을 의미한다. 상승장 중 눌림목에서 가격 저점은 높아졌는데 RSI 저점이 오히려 과매도권까지 푹 꺼졌을 때다. 에너지를 충전했으니 다시 원래 방향으로 세게 쏘겠다는 신호로 불타기 및 눌림목 추가 매수 타점으로 활용한다.

- chunk_id: `maeoaknam.hidden_divergence_continuation`
- keywords: `히든 다이버전스`, `hidden divergence`, `추세 지속`, `눌림목`, `불타기`, `추가 매수`, `에너지 충전`
- preferred_action: add to position on hidden bullish divergence during uptrend pullback
- avoid_when: 하락 추세에서 히든 다이버전스를 상승 지속으로 오해할 때
- source_refs: `maeoaknam youtube summary`

## 파동 + 피보나치 1차 중첩 (기본 근거)

파동의 끝과 피보나치 수치를 결합하는 가장 기본적이면서도 강력한 중첩이다. ABC 조정의 C파 끝과 전체 상승분의 0.618 피보나치 되돌림이 일치하는 자리는 파동 트레이더와 피보나치 트레이더가 동시에 매수하는 구간이 된다. 매수세 집중으로 강력한 반등 확률이 80% 이상이다.

- chunk_id: `maeoaknam.wave_fibonacci_first_confluence`
- keywords: `1차 중첩`, `파동 끝`, `피보나치`, `ABC C파`, `0.618`, `매수 집중`, `80%`, `기본 중첩`
- preferred_action: enter when wave endpoint (ABC C-wave end) aligns with fibonacci 0.618; this is minimum viable confluence
- avoid_when: 파동 끝과 피보나치 수치가 어긋날 때, 둘 중 하나만 충족될 때는 비중 줄이기
- source_refs: `maeoaknam youtube summary`

## RSI 다이버전스 2차 중첩 (지표 확증)

파동과 피보나치로 지점을 정했다면 그 지점에서 실제로 힘이 바뀌는지 확인하는 단계다. 미리 찍어둔 피보나치 0.618 + ABC 1:1 자리에 도달했을 때 1시간봉~4시간봉 상승 다이버전스까지 나타난다면 손절을 짧게 잡고 큰 비중으로 진입할 수 있는 꿀통 타점이다.

- chunk_id: `maeoaknam.rsi_divergence_second_confluence`
- keywords: `2차 중첩`, `RSI 다이버전스`, `확증`, `꿀통`, `지표 컨펌`, `고비중`, `3개 근거`
- preferred_action: upgrade to high-conviction entry when wave + fibonacci + RSI divergence all align; can increase size significantly
- avoid_when: 두 가지 근거만 있을 때는 표준 비중으로만 진입
- source_refs: `maeoaknam youtube summary`

## 매물대 3차 중첩 (역사적 지지 확인)

지금 사려는 자리가 과거에 강력하게 지지받았던 구간이거나 엄청난 거래량이 터지며 돌파했던 매물대 위라면 신뢰도가 더욱 상승한다. 피보나치 수치(수학)와 매물대(역사)가 겹치는 구간은 쉽게 뚫리지 않는 강철 바닥이 된다. 이런 자리에서 도지나 망치형 캔들이 나오면 최종 진입 확정이다.

- chunk_id: `maeoaknam.support_zone_third_confluence`
- keywords: `매물대`, `horizontal support`, `3차 중첩`, `역사적 지지`, `강철 바닥`, `도지`, `망치형`, `최종 컨펌`
- preferred_action: confirm entry when price action (doji/hammer) forms at triple confluence zone (wave + fibonacci + historical support)
- avoid_when: 매물대 지지가 확인되지 않은 신고점 구간의 피보나치 수치에만 의존할 때
- source_refs: `maeoaknam youtube summary`

## 4개 근거 체크리스트 (매억남 필승 조합)

매억남이 가장 선호하는 중첩 시나리오다. 1) 대추세 파동 위치 확인, 2) 피보나치 주요 수치 도달, 3) 파동 조정 패턴(지그재그/플랫) 완성, 4) 단기봉 상승 다이버전스 컨펌. 이 4개 중 최소 3개에 YES여야 진입한다. 모르는 구간에서는 매매를 쉬는 것이 매억남식 절제다.

- chunk_id: `maeoaknam.four_factor_checklist`
- keywords: `체크리스트`, `checklist`, `4개 근거`, `최소 3개`, `절제`, `관망`, `필승 조합`, `컨펌`
- preferred_action: require minimum 3 of 4 factors (wave position + fibonacci level + corrective pattern + divergence) before entry
- avoid_when: 1~2개 근거만 있을 때 큰 비중으로 진입하려 할 때, 모르는 구간에서 감으로 매매할 때
- source_refs: `maeoaknam youtube summary`

## 근거 무효화 시 즉시 손절 및 관망

진입했는데 가격이 예상보다 더 밀려 다이버전스가 무효화되거나 파동 규칙이 어긋나면 근거 하나가 사라진 것이다. 매억남은 미련 없이 손절하거나 비중을 줄인다. 겹치기 전략은 확률을 사는 것이지 확신을 사는 것이 아니다. 카운팅이 깨지면 미련 없이 시나리오를 버린다.

- chunk_id: `maeoaknam.invalidation_instant_exit`
- keywords: `근거 무효화`, `즉시 손절`, `카운팅 폐기`, `시나리오 붕괴`, `관망`, `비중 축소`, `미련 없이`
- preferred_action: exit or reduce immediately when any entry basis is invalidated; reset scenario and observe
- avoid_when: 근거 중 하나가 깨졌는데도 나머지 근거만으로 포지션을 유지하려 할 때
- source_refs: `maeoaknam youtube summary`

## 1:3 손익비 원칙 (잃을 땐 1, 벌 땐 3)

진입하기 전에 반드시 잃을 금액과 벌 금액을 비교한다. 손절 거리가 -2%라면 익절가는 최소 +6% 이상인 자리에서만 진입한다. 손익비가 1:3이면 승률이 30%만 돼도 계좌가 줄지 않는다. 승률이 40%면 자산이 폭발적으로 늘어난다. 맞춰야 한다는 압박감에서 벗어나는 것이 핵심이다.

- chunk_id: `maeoaknam.one_to_three_risk_reward`
- keywords: `손익비`, `risk reward`, `1:3`, `손절 거리`, `익절가`, `승률`, `30%`, `압박감 해소`
- preferred_action: reject entries where reward is less than 3x the risk; calculate R:R before every entry
- avoid_when: 손익비가 1:1 또는 1:2밖에 안 되는 자리에서 진입하려 할 때, 손절가 설정 없이 들어갈 때
- source_refs: `maeoaknam youtube summary`

## 기계적 손절 - 무효화 지점이 손절가

매억남에게 손절은 패배가 아니라 다음 기회를 사기 위한 비용이다. 파동 카운팅이 어긋나거나 피보나치 0.886을 이탈할 때가 곧 손절가다. 진입과 동시에 손절 주문을 미리 걸어둔다. 좀 더 기다리면 반등하겠지라는 희망 회로가 작동하기 전에 시스템이 먼저 나를 구출한다.

- chunk_id: `maeoaknam.mechanical_stop_loss`
- keywords: `기계적 손절`, `stop loss`, `무효화 지점`, `SL 주문`, `0.886 이탈`, `시스템`, `선주문`, `자동 손절`
- preferred_action: set stop-loss order simultaneously with entry; place at wave invalidation level or fibonacci 0.886 breach
- avoid_when: 진입 후 손절가를 설정하지 않거나 나중에 수동으로 끊으려 할 때
- source_refs: `maeoaknam youtube summary`

## 3단계 분할 익절 전략

고점에서 한 번에 다 팔려 하지 않고 수익의 확정을 통해 멘탈을 보호한다. 1차: 피보나치 주요 수치 또는 전고점에서 물량 30~50% 매도. 2차: 1차 익절 후 손절가를 진입가로 이동해 무위험 매매로 전환. 3차: 나머지는 파동 끝(5파 등)까지 최대한 길게 보유하며 수익 극대화.

- chunk_id: `maeoaknam.three_stage_take_profit`
- keywords: `분할 익절`, `take profit`, `1차 익절`, `본절 로스`, `무위험 매매`, `추세 추종`, `3단계`, `수익 확정`
- preferred_action: take 30-50% profit at first fibonacci target; move stop to breakeven; let remaining ride to wave completion
- avoid_when: 전량을 한 번에 팔아 큰 추세를 놓칠 때, 1차 익절 후 손절을 본전으로 옮기지 않아 수익이 손실로 반전될 때
- source_refs: `maeoaknam youtube summary`

## 본절 로스 이동 (무위험 매매 전환)

1차 익절 후에는 손절가를 진입가로 옮긴다. 이제 이 매매는 절대 손실이 나지 않는 무위험 매매가 된다. 심리적으로 매우 편안해지며 나머지 물량을 추세 끝까지 가져갈 수 있다.

- chunk_id: `maeoaknam.breakeven_stop_loss_move`
- keywords: `본절 로스`, `breakeven`, `무위험 매매`, `손절 이동`, `진입가`, `심리 안정`, `추세 추종`
- preferred_action: move stop-loss to entry price after first take-profit is hit; eliminate downside risk on remaining position
- avoid_when: 1차 익절 후에도 손절가를 원래 손절선에 그대로 두어 수익이 손실로 반전될 위험을 방치할 때
- source_refs: `maeoaknam youtube summary`

## 매매 횟수 제한 및 일상 분리 (멘탈 관리)

하루에 정해진 횟수 이상은 매매하지 않는다. 뇌동매매를 방지하기 위함이다. 모니터 앞을 떠나면 차트 생각을 하지 않는다. 돈을 잃어도 내 삶은 무너지지 않는다는 여유가 있을 때 비로소 최고의 타점이 보인다. 큰 수익이나 큰 손실 뒤의 흥분과 절망을 가장 경계한다.

- chunk_id: `maeoaknam.trade_frequency_limit_mental`
- keywords: `매매 횟수`, `뇌동매매`, `일상 분리`, `멘탈`, `흥분`, `절망`, `여유`, `제한`, `과매매`
- preferred_action: HOLD when daily trade limit is reached; exit trading session after big win or big loss to reset emotionally
- avoid_when: 큰 수익 후 흥분해서 즉시 재진입할 때, 큰 손실 후 복구 목적으로 연속 매매할 때
- source_refs: `maeoaknam youtube summary`

## 매매 일지와 오답 노트 (자기 통계 구축)

지독한 기록이 전설을 만든다. 진입 시점 차트 캡처, 진입 근거 3가지, 당시 감정 상태, 결과와 피드백을 기록한다. 나는 0.618 자리에서 승률이 높네, 다이버전스를 확인할 때 성급하게 들어가네 같은 자기 객관화가 이루어지면 매매는 더 이상 도박이 아닌 검증된 사업이 된다.

- chunk_id: `maeoaknam.trading_journal_self_statistics`
- keywords: `매매 일지`, `기록`, `오답 노트`, `자기 객관화`, `통계`, `근거 기록`, `감정 기록`, `피드백`
- preferred_action: treat journal-keeping as mandatory part of trading; use personal win-rate data to refine entry criteria
- avoid_when: 기록 없이 감각에만 의존해 같은 실수를 반복할 때
- source_refs: `maeoaknam youtube summary`
