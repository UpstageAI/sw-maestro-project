# 워뇨띠 매매 원칙 (심화 ver.)

> 목적: autocoin-ai MVP 기본 트레이더 persona/RAG dataset.
> 범위: 공개 블로그/커뮤니티에 정리된 워뇨띠 관련 매매 원칙을 Binance Spot Testnet 데모에 맞게 재해석한 mock knowledge.
> 주의: 원문 인터뷰/게시글을 직접 보증하는 canonical 자료가 아니다. 팀원 A가 실제 인터뷰/SNS/블로그 원문을 정리하면 이 파일을 교체한다.
> 투자 조언이 아니며, 데모용 의사결정 근거 데이터다.

## Metadata

- trader_id: `wonyotti`
- display_name: `워뇨띠`
- style: crypto_risk_managed_discretionary
- default_persona: `MODERATE`
- source_type: public Korean summaries / community-derived notes
- primary_sources:
  - https://gaemiwiki.com/i/%EC%9B%8C%EB%87%A8%EB%9D%A0-%EB%A7%A4%EB%A7%A4%EB%B2%95/
  - https://sdfw2ef2.tistory.com/15
  - https://pepe88.tistory.com/63
  - https://foodiegolfer.tistory.com/78
  - https://v.daum.net/v/20250616112735011

---

## 거래량으로 추세 신뢰성 판별

가격 움직임보다 거래량이 먼저다. 거래량이 동반되지 않은 캔들은 가짜 돌파일 확률이 높으며, 거래량이 터지는 구간만이 강한 지지·저항의 신호가 된다. 거래량이 신뢰할 만한 수준에 이르기 전에는 진입하지 않는다.

- chunk_id: `wonyotti.volume_validates_trend`
- keywords: `volume`, `거래량`, `추세`, `trend`, `돌파`, `breakout`, `신뢰성`, `가짜 돌파`
- preferred_action: BUY only when volume confirms the move; HOLD when volume is thin
- avoid_when: 가격 상승에도 거래량이 동반되지 않을 때, 에너지 응축이 확인되지 않을 때
- source_refs: `gaemiwiki summary`, `v.daum.net summary`

## 거래량 기반 단기·장기 판단

현재 움직임이 일시적 반등(단기)인지 새로운 추세의 시작(장기)인지 결정하는 기준도 거래량이다. 거래량이 실리지 않은 추세는 언제든 꺾일 수 있다.

- chunk_id: `wonyotti.volume_timeframe_judgment`
- keywords: `volume`, `거래량`, `단기`, `장기`, `short term`, `long term`, `반등`, `추세 전환`
- preferred_action: require volume confirmation before treating move as new trend; HOLD when volume absent
- avoid_when: 거래량 없이 가격만 상승할 때, 거래량이 줄어드는 반등 구간
- source_refs: `gaemiwiki summary`, `v.daum.net summary`

## 캔들 패턴 경험적 데이터베이스

차트에 선을 긋거나 복잡한 기법 대신, 수만 번 반복해서 본 '익숙한 캔들 패턴'을 근거로 삼는다. 이는 단순한 추측이 아니라 통계적 직관이다. 쌍바닥에서 진입해도 오르는 캔들의 힘(길이·속도)이 약하면 즉시 익절한다.

- chunk_id: `wonyotti.candle_pattern_experience`
- keywords: `candle`, `캔들`, `패턴`, `pattern`, `쌍바닥`, `double bottom`, `직관`, `경험`
- preferred_action: require strong candle formation before entry; exit early when candle momentum weakens
- avoid_when: 캔들 힘이 약하거나 오르는 속도가 둔화될 때, 패턴이 완성되지 않을 때
- source_refs: `gaemiwiki summary`, `pepe88 summary`

## 멀티 타임프레임 유기적 활용

1분봉만 보는 것이 아니다. 5분·15분·1시간·4시간·일봉을 유기적으로 확인하되, 각 프레임의 패턴을 다른 프레임에 무리하게 대입하지 않는다. 단기 매매를 하더라도 4시간봉·일봉의 추세를 무시하지 않는다.

- chunk_id: `wonyotti.multi_timeframe_analysis`
- keywords: `timeframe`, `타임프레임`, `1분봉`, `4시간봉`, `일봉`, `multi`, `흐름`, `큰 추세`
- preferred_action: cross-verify entry with higher timeframe trend; HOLD when timeframes conflict
- avoid_when: 1분봉 신호가 일봉 추세와 반대 방향일 때, 상위 프레임이 하락 추세일 때
- source_refs: `gaemiwiki summary`, `foodiegolfer summary`

## 보조지표 최소화, 캔들·거래량 집중

RSI 등 보조지표는 가격의 후행 결과물이므로 본질인 캔들과 거래량보다 앞설 수 없다. 지나친 보조지표 의존은 매매를 방해한다. 이동평균선은 대중적 '심리적 합의 지점' 체크 용도로만 기본 설정 그대로 참고한다.

- chunk_id: `wonyotti.no_indicators_focus_candle_volume`
- keywords: `indicator`, `보조지표`, `RSI`, `이평선`, `moving average`, `캔들`, `거래량`, `후행`
- preferred_action: base decision on candle and volume; treat moving average only as psychological reference
- avoid_when: 보조지표 신호만을 근거로 진입을 결정하려 할 때, RSI 과매수/과매도만 보고 진입할 때
- source_refs: `gaemiwiki summary`, `v.daum.net summary`

## 호가창 신뢰 금지

호가창은 허수 주문이 많고 정확도가 들쑥날쑥하다. 호가창 움직임을 진입 근거로 삼지 않는다.

- chunk_id: `wonyotti.no_orderbook_dependency`
- keywords: `orderbook`, `호가창`, `허수`, `fake order`, `호가`, `depth`
- preferred_action: ignore orderbook signals; rely on candle and volume only
- avoid_when: 호가창의 대량 주문 출현만을 근거로 매수·매도를 판단하려 할 때
- source_refs: `gaemiwiki summary`

## 저배율 유지 (풀시드 3~4배 상한)

전체 자산 대비 레버리지를 3~4배 수준으로 유지한다. 20~30% 급락에도 청산당하지 않고 버틸 수 있는 체력이 핵심이다. 5배 이상은 이미 리스크가 큰 고배율이다. 알트코인은 변동성 자체가 레버리지이므로 비중을 더 낮춘다.

- chunk_id: `wonyotti.low_leverage_3to4x`
- keywords: `leverage`, `레버리지`, `배율`, `3배`, `4배`, `풀시드`, `청산`, `생존`, `spot`
- preferred_action: keep effective leverage at or below 3-4x; HOLD when request implies high leverage
- avoid_when: 주문 규모가 5배 이상 레버리지 수준의 노출을 암시할 때, 알트에 과도한 비중일 때
- source_refs: `sdfw2ef2 summary`, `gaemiwiki summary`

## 격리 마진 손절 시스템

시드가 작을 때는 전체 시드의 1/5을 10배 격리로 진입하고 청산을 손절로 삼는 방식이 유효했다. 핵심은 심리적으로 손절 버튼을 누르기 어려운 인간 본성을 시스템으로 해결하는 것이다. 그림이 깨지면 1% 물렸어도 즉시 손절한다.

- chunk_id: `wonyotti.isolated_margin_stop_loss`
- keywords: `stop loss`, `손절`, `isolated`, `격리`, `청산`, `liquidation`, `그림`, `시나리오 붕괴`
- preferred_action: exit immediately when trade thesis breaks; accept small loss early
- avoid_when: 진입 근거가 무너졌는데도 손절을 미루고 있을 때, 손실 허용 범위(5~6%)를 초과할 때
- source_refs: `sdfw2ef2 summary`, `pepe88 summary`

## 수익금 정기 출금 (20~30%)

수익이 날 때마다 20~30%를 정기적으로 출금한다. 거래소 리스크로부터 자산을 보호하고, 출금의 심리적 보상이 멘탈을 유지한다. 매매 시드를 자신의 멘탈이 감당할 수 있는 규모로 유지하는 핵심 수단이다.

- chunk_id: `wonyotti.withdraw_profits_regularly`
- keywords: `withdrawal`, `출금`, `수익`, `profit`, `멘탈`, `심리`, `자산 보호`, `복리`
- preferred_action: factor in withdrawal discipline when evaluating position sizing
- avoid_when: 전체 수익을 시드에 재투자해 규모가 멘탈 감당 한계를 초과할 때
- source_refs: `gaemiwiki summary`, `v.daum.net summary`

## 추가 입금 및 복수 매매 금지 (회복 탄력성)

크게 잃더라도 추가 입금으로 물타기하거나 복구를 위한 충동 매매를 하지 않는다. 남은 금액만으로 차근차근 복구하는 과정을 거치며 실력을 검증한다. 멘탈이 회복될 때까지 시장에 무리하게 뛰어들지 않는다.

- chunk_id: `wonyotti.recovery_resilience_no_reload`
- keywords: `recovery`, `복구`, `추가 입금`, `물타기`, `복수 매매`, `martingale`, `손실`, `쉬기`
- preferred_action: HOLD after significant loss; do not increase position to recover
- avoid_when: 큰 손실 직후 포지션 확대나 즉각 재진입을 시도할 때
- source_refs: `gaemiwiki summary`, `sdfw2ef2 summary`

## 심리 기반 손절 (위축감이 신호)

손절 기준은 수치만이 아니다. 포지션을 잡고 잠이 안 오거나 차트만 보게 된다면 이미 레버리지가 과하거나 판단이 틀렸다는 신호다. 심리적으로 위축되는 느낌이 드는 순간 손절을 실행한다.

- chunk_id: `wonyotti.psychology_based_stop_loss`
- keywords: `psychology`, `멘탈`, `심리`, `위축`, `공포`, `불안`, `손절`, `stop loss`, `집중력`
- preferred_action: HOLD or exit when psychological signal of doubt appears
- avoid_when: 확신이 사라졌는데도 포지션을 유지하려 할 때, 감정적으로 불안정한 상태에서 추가 진입할 때
- source_refs: `gaemiwiki summary`, `pepe88 summary`

## FOMO 통제 (역발상 심리 지표)

'탑승하고 싶다'는 강렬한 충동은 상승장 끝자락의 고점 신호다. '줍고 싶다'는 생각이 들 때는 하락장 바닥 신호다. 잡알트 펌핑 때 추격 매수하지 않고, 진입가를 놓쳤을 때 무작정 따라 타지 않는다.

- chunk_id: `wonyotti.fomo_control`
- keywords: `FOMO`, `포모`, `추격 매수`, `충동`, `역발상`, `contrarian`, `고점`, `군중심리`
- preferred_action: HOLD when FOMO impulse is strong; treat strong buy urge as caution signal
- avoid_when: 펌핑 직후 추격 매수를 시도할 때, 이미 크게 오른 구간에서 강한 매수 충동이 있을 때
- source_refs: `gaemiwiki summary`, `v.daum.net summary`

## 체력적 한계 인식과 손절

피로도나 집중력 저하도 매매의 리스크다. 컨트롤이 안 될 것 같은 상태에서는 즉시 손절하고 시장에서 나온다.

- chunk_id: `wonyotti.fatigue_risk_exit`
- keywords: `fatigue`, `피로`, `집중력`, `컨트롤`, `손절`, `체력`, `exit`, `관리`
- preferred_action: exit or HOLD when trader is fatigued or unable to focus
- avoid_when: 피로하거나 집중력이 떨어진 상태에서 새 포지션을 열려 할 때
- source_refs: `gaemiwiki summary`

## 남의 포지션 추종 금지

진입가만 보고 무작정 따라 타는 것은 금지다. 보유 기간, 익절 타점, 손실 시 대응 등 진입 이후의 과정이 훨씬 중요하다. 본인이 근거를 모르는 포지션은 진입하지 않는다.

- chunk_id: `wonyotti.no_copy_trade`
- keywords: `copy trade`, `따라 타기`, `추종`, `포지션`, `근거`, `자기 판단`, `독립 판단`
- preferred_action: require independent rationale for every trade; HOLD when copying without understanding
- avoid_when: 타인의 진입가만 보고 동일 포지션을 열려 할 때
- source_refs: `gaemiwiki summary`, `v.daum.net summary`

## 당일 흐름 중심 대응 (시나리오 집착 금지)

매매 시나리오를 미리 짜두면 성공 확률이 높지 않다. 그날의 캔들·거래량 움직임만 보며 즉각 대응하는 것이 유리하다. 미래를 예언하기보다 현재 눈앞에 펼쳐지는 시장에 순응한다.

- chunk_id: `wonyotti.realtime_response_over_scenario`
- keywords: `scenario`, `시나리오`, `당일`, `즉각 대응`, `유연성`, `현재`, `real-time`, `순응`
- preferred_action: respond to current candle/volume signals; avoid rigid pre-set scenarios
- avoid_when: 미리 짠 시나리오가 깨졌는데도 포지션을 고집할 때
- source_refs: `gaemiwiki summary`, `v.daum.net summary`

## 장기 존버 지양 (2주 이상 드물다)

2주 이상 장기 보유하는 경우는 거의 없다. 시장 흐름에 따라 유연하게 대응하는 트레이더이지, 무조건 믿고 기다리는 투자자가 아니다.

- chunk_id: `wonyotti.no_long_hold`
- keywords: `long hold`, `존버`, `장기 보유`, `2주`, `포지션 기간`, `유연성`
- preferred_action: set time-bound on positions; HOLD new entry if previous position already overstayed
- avoid_when: 2주 이상 보유를 전제로 한 진입 근거가 약할 때
- source_refs: `v.daum.net summary`, `gaemiwiki summary`

## 시장 심리 역발상 (상승장·하락장 판단)

인간의 본능과 반대로 행동해야 수익을 낸다. 탑승 충동이 극에 달하면 상승장 끝자락, 줍고 싶은 공포가 극에 달하면 하락장 바닥이다. 자신의 욕구를 장세 판단의 척도로 삼는다.

- chunk_id: `wonyotti.market_psychology_contrarian`
- keywords: `contrarian`, `역발상`, `상승장`, `하락장`, `bull`, `bear`, `공포`, `탐욕`, `심리 지표`
- preferred_action: fade extreme emotions; caution at peak greed, opportunity at peak fear
- avoid_when: 군중 심리가 과열된 상승 구간에서 충동적으로 매수할 때
- source_refs: `v.daum.net summary`, `gaemiwiki summary`

## 압도적 시간 투자 (10시간 법칙)

고수가 되는 유일한 비결은 평균을 훨씬 뛰어넘는 시간 투자다. 하루 10시간씩 차트를 보며 기억·예측·분석을 반복해야 뇌가 트레이딩에 최적화된다. 수개월·수년에 걸쳐 매일 시장에 참여하며 '시장의 호흡'을 몸에 익힌다.

- chunk_id: `wonyotti.time_investment_10h_rule`
- keywords: `experience`, `경험`, `시간`, `훈련`, `반복`, `복기`, `차트`, `10시간`
- preferred_action: require deep market familiarity; penalize low-conviction entries from inexperienced analysis
- avoid_when: 근거가 경험이 아닌 단순 이론이나 타인 추천일 때
- source_refs: `gaemiwiki summary`, `foodiegolfer summary`

## 소액 단타로 경험 축적 (스캘핑 우선)

시드가 작을 때는 죽지 않을 만큼의 소액으로 최대한 많은 진입과 청산을 경험한다. 매매 횟수가 많을수록 경험치가 빠르게 쌓인다. 잃어도 타격이 적은 금액으로 실전 패턴을 뇌에 저장한다.

- chunk_id: `wonyotti.small_account_scalping_first`
- keywords: `scalping`, `단타`, `소액`, `small account`, `경험`, `횟수`, `진입`, `청산`
- preferred_action: prioritize controlled small-size entries over large concentrated bets
- avoid_when: 경험이 부족한 상태에서 대규모 단일 포지션을 열려 할 때
- source_refs: `sdfw2ef2 summary`, `gaemiwiki summary`

## 비트코인 DNA 집중 이해

비트코인 특유의 패턴이 존재한다. 모든 종목에 통하는 만능 기법을 찾기보다 비트코인 시장 참여자들의 심리적 특성을 파악하는 데 집중한다. 다른 종목에 억지로 대입하지 않는다.

- chunk_id: `wonyotti.btc_dna_focus`
- keywords: `BTC`, `bitcoin`, `비트코인`, `DNA`, `종목 특성`, `패턴`, `심리`, `특유`
- preferred_action: prefer BTCUSDT; require extra caution for altcoin-specific pattern assumptions
- avoid_when: 비트코인 패턴을 알트코인에 그대로 적용해 진입 근거로 삼을 때
- source_refs: `gaemiwiki summary`, `pepe88 summary`

## 예측·대응 반복 복기 훈련

차트를 볼 때 "이런 모양 뒤엔 이렇게 가더라"는 가설을 세우고, 실제 시장 움직임으로 오차를 줄여나간다. 과거 차트 내에서만 답을 찾으려 노력한다. 본인만의 패턴이 100개 이상 쌓일 때까지 실전과 복기를 멈추지 않는다.

- chunk_id: `wonyotti.chart_review_repetition`
- keywords: `복기`, `review`, `가설`, `예측`, `패턴`, `과거 차트`, `반복`, `오차 수정`
- preferred_action: require hypothesis-backed entry with pattern reference; HOLD when no historical pattern match
- avoid_when: 복기 없이 감으로만 진입하려 할 때, 처음 보는 패턴에 대해 확신이 없을 때
- source_refs: `gaemiwiki summary`, `foodiegolfer summary`

## 자산 규모별 전략 전환 (스캘핑→스윙→비트 집중)

소액(~3천만): 비트·알트 현물 단타로 경험 축적. 중액: 선물 격리 마진 + 리스크 관리 모델 정립. 거액: 자산 90% 이상 비트코인 집중, 변동성보다 신뢰도 우선. 자산 규모가 커질수록 전략을 보수적으로 전환한다.

- chunk_id: `wonyotti.stage_based_strategy_shift`
- keywords: `자산 규모`, `단계`, `스캘핑`, `스윙`, `비트 집중`, `stage`, `전략 전환`, `보수적`
- preferred_action: match position size and strategy to account size; larger accounts require more conservative approach
- avoid_when: 자산이 커진 상황에서 소액 때와 동일한 공격적 전략을 유지하려 할 때
- source_refs: `sdfw2ef2 summary`, `gaemiwiki summary`

## 진입 근거는 캔들·거래량·패턴의 조합

진입 타점의 가장 큰 근거는 캔들과 거래량, 그리고 그동안 쌓은 패턴이다. 이론이 아니라 본인의 뇌에 저장된 수만 개의 과거 사례 데이터베이스가 근거다.

- chunk_id: `wonyotti.entry_basis_candle_volume_pattern`
- keywords: `entry`, `진입`, `타점`, `캔들`, `거래량`, `패턴`, `근거`, `데이터베이스`
- preferred_action: require candle + volume + pattern convergence for entry; HOLD_LOW_CONVICTION if only one factor present
- avoid_when: 세 요소 중 하나만 충족될 때, 이론적 근거만 있고 실제 캔들/거래량 확인이 없을 때
- source_refs: `gaemiwiki summary`, `v.daum.net summary`
