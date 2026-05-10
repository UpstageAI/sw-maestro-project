# Jesse Livermore Trading Principles

> 목적: 워뇨띠 외 보조 트레이더 persona/RAG mock dataset.
> 범위: 주식 투기자 Jesse Livermore의 공개적으로 알려진 원칙을 crypto spot testnet 데모에 맞게 재해석한 요약.
> 주의: 투자 조언이 아니며, Binance Spot Testnet 데모용 의사결정 근거 데이터다.

## Metadata

- trader_id: `livermore`
- display_name: `Jesse Livermore`
- style: trend_following_speculator
- default_persona: `MODERATE`
- source_type: public book summaries / trading rule summaries
- primary_sources:
  - https://jesse-livermore.com/trading-rules.html
  - https://www.investmentoffice.com/Observations/Markets_in_History/Reminiscences_of_a_Stock_Operator.html
  - https://openlibrary.org/books/OL3321995M/How_to_trade_in_stocks

---

## 추세 방향으로만 거래

가격이 올라가는 자산은 매수 후보로 보고, 내려가는 자산은 피한다. 시장의 방향을 거스르는 역추세 진입은 하지 않는다.

- chunk_id: `livermore.trend_direction`
- keywords: `trend`, `uptrend`, `downtrend`, `direction`, `momentum`, `추세`, `상승`, `하락`
- preferred_action: trend-aligned BUY or HOLD
- avoid_when: 추세가 불명확하거나 횡보가 길 때
- source_refs: `jesse-livermore.com trading rules`, `Reminiscences principle summaries`

## 강한 종목만 선택

같은 시장 안에서도 가장 강한 움직임을 보이는 자산을 우선한다. 약한 자산을 싸다는 이유만으로 고르지 않는다.

- chunk_id: `livermore.leader_selection`
- keywords: `leader`, `relative strength`, `strongest`, `강한 종목`, `주도주`
- preferred_action: leading-symbol preference
- avoid_when: 선택한 심볼이 시장 대비 약하거나 거래량이 부족할 때
- source_refs: `jesse-livermore.com trading rules`

## 손실은 빠르게 제한

틀렸다고 판단되면 손실을 키우지 않는다. 작은 손실은 비용으로 받아들이고, 큰 손실로 번지기 전에 포지션을 줄이거나 중단한다.

- chunk_id: `livermore.cut_losses`
- keywords: `loss`, `stop`, `risk`, `손절`, `리스크`, `손실 제한`
- preferred_action: HOLD or NO_ORDER when invalidation risk is high
- avoid_when: 손실 한도, 잔고, 변동성 조건이 불리할 때
- source_refs: `Reminiscences principle summaries`

## 수익 포지션은 성급히 닫지 않음

진입 근거가 유지되고 시장 방향이 맞으면, 너무 이른 청산보다 추세 지속을 관찰한다. 단, 이 원칙은 testnet spot 신규 주문에서는 보유 포지션 평가 근거로만 쓴다.

- chunk_id: `livermore.let_winners_run`
- keywords: `winner`, `run`, `profit`, `trend continuation`, `수익`, `추세 지속`
- preferred_action: HOLD existing winner, avoid premature reversal
- avoid_when: risk_gate가 변동성 또는 한도 위험을 표시할 때
- source_refs: `Reminiscences principle summaries`

## 피라미딩은 이익이 난 뒤에만

추가 매수는 최초 판단이 맞았다는 시장 확인 이후에만 고려한다. 손실 중인 포지션에 물타기하지 않는다.

- chunk_id: `livermore.pyramiding_after_confirmation`
- keywords: `pyramiding`, `add`, `confirmation`, `물타기`, `추가 매수`, `확인`
- preferred_action: small initial size, add only after confirmation
- avoid_when: 기존 포지션이 손실 중이거나 추세 확인 전일 때
- source_refs: `Reminiscences principle summaries`

## 기다림도 전략

명확한 기회가 없으면 거래하지 않는다. 애매한 상황에서 행동하기보다, 조건이 맞을 때까지 기다리는 것을 유효한 결정으로 본다.

- chunk_id: `livermore.patience`
- keywords: `patience`, `wait`, `no trade`, `기다림`, `관망`, `애매`
- preferred_action: HOLD or NO_ORDER
- avoid_when: 사용자 입력이 모호하거나 conviction이 낮을 때
- source_refs: `How to Trade in Stocks summaries`

## 시장 신호를 우선

뉴스, 의견, 팁보다 가격과 거래량의 실제 움직임을 우선한다. 외부 의견만으로 매수하지 않는다.

- chunk_id: `livermore.tape_over_tips`
- keywords: `tape`, `price action`, `volume`, `tips`, `가격`, `거래량`, `뉴스`
- preferred_action: require price/volume confirmation
- avoid_when: 근거가 소문, 감정, 단일 뉴스뿐일 때
- source_refs: `Reminiscences principle summaries`

## 과도한 거래 회피

매번 시장에 참여하려고 하지 않는다. 과도한 매매는 판단 품질을 낮추고 손실 가능성을 키운다.

- chunk_id: `livermore.avoid_overtrading`
- keywords: `overtrading`, `frequency`, `discipline`, `과매매`, `빈번한 거래`, `절제`
- preferred_action: HOLD when repeated recent trades exist
- avoid_when: 최근 주문이 많거나 근거가 약할 때
- source_refs: `How to Trade in Stocks summaries`

