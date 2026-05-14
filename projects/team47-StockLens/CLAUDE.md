# AI47 - 주가 변동 원인 분석 Agent 프로젝트

## 프로젝트 개요

사용자가 주식 티커와 분석 기간을 입력하면, 해당 주가가 왜 움직였는지 원인 가설(3~5개)과 신뢰도를 근거와 함께 설명해주는 AI Agent 서비스.

**팀:** 47조 (김대연, 김민석, 김진기, 박성준, 황채원)
**담당:** 김진기 → Agent 1 (데이터 수집) + LangGraph 파이프라인 구조

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| Agent 파이프라인 | Python 3.10+, LangGraph |
| API 서버 | FastAPI |
| 프론트엔드 | Next.js (타 팀원 담당) |
| LLM | OpenAI GPT-4o |
| DB | PostgreSQL 16 |
| 데이터 수집 | yfinance, NewsAPI, SEC EDGAR |

## 서비스 아키텍처

```
사용자
  → 입력 UI (티커, 분석 기간)
  → Backend (API 엔드포인트 → 입력값 검증 / Rate Limit)
  → Orchestrator
  → LangGraph Agent Pipeline
       Agent 1 - 데이터 수집        ← 김진기 담당
         ├ 주가·거래량 조회
         ├ 벤치마크·섹터ETF·Peer 비교
         └ 뉴스·SEC 공시 수집
       Agent 2 - 분석·가설 생성
         ├ 노이즈 필터링·중복 제거
         ├ 원인 가설 3~5개 생성
         └ 가설 점수화·신뢰도 분류
       Agent 3 - 보고서 생성
         ├ 구조화 보고서 생성
         └ DB 저장
  → 출력 UI (결과보드, 가설순위, Bull/Bear Case, 출처)

Data Provider: yfinance / NewsAPI / SEC EDGAR / yfinance(벤치마크)
LLM: OpenAI GPT-4o
```

## 담당 범위 (Agent 1)

- `주가·거래량 조회`: 분석 기간 내 OHLCV 데이터
- `벤치마크·섹터ETF·Peer 비교`: S&P500, 섹터 ETF, 동종 기업 수익률 비교
- `뉴스·SEC 공시 수집`: 해당 기간 관련 뉴스 기사 + SEC EDGAR 공시
- Agent 2에 넘길 데이터 스키마 정의 및 준수 → `docs/interface.md` 참조

## 프로젝트 구조

```
AI47/
├── CLAUDE.md
├── docs/
│   ├── interface.md       # Agent 간 데이터 스키마 계약
│   ├── data-sources.md    # 사용 API 목록 및 제약
│   └── decisions.md       # 핵심 결정 이유 기록 (ADR)
├── agent/
│   ├── agent1/            # 데이터 수집 Agent (담당)
│   │   ├── nodes/         # LangGraph 노드 단위 구현
│   │   ├── tools/         # 각 데이터 소스별 도구
│   │   └── graph.py       # Agent 1 LangGraph 그래프 정의
│   ├── agent2/            # 분석·가설 생성 Agent (타 팀원)
│   └── agent3/            # 보고서 생성 Agent (타 팀원)
├── orchestrator/
│   └── graph.py           # 전체 파이프라인 LangGraph 그래프
├── api/
│   └── main.py            # FastAPI 엔드포인트
├── models/
│   └── schema.py          # Pydantic 데이터 모델
└── tests/
```

## 코드 컨벤션

- **언어:** Python 3.11+
- **타입힌트:** 모든 함수에 필수
- **데이터 모델:** Pydantic v2 사용
- **비동기:** FastAPI 엔드포인트는 `async def`
- **LangGraph 상태:** `TypedDict` 또는 Pydantic 모델로 정의
- **함수명:** snake_case
- **클래스명:** PascalCase
- **환경변수:** `.env` 파일 사용, `python-dotenv` 로드

## 하면 안 되는 것

- 매수/매도 추천 문구 출력 금지
- 모든 응답에 disclaimer 포함 필수 ("참고용 정보, 투자 결정 책임은 사용자에게 있음")
- Mock 데이터로 실제 API 대체 금지 (MVP라도 실제 API 사용)
- 실제 주문 실행 코드 작성 금지

## MVP 범위

**포함:**
- 미국 주식 (티커 기반)
- 분석 기간 지정 후 온디맨드 수집 (요청 시 API 호출, 별도 저장 없음)
- 원인 가설 3~5개 생성 및 신뢰도 점수화

**제외:**
- 실시간 차트
- 워치리스트 자동 분석
- 해외 종목 (미국 외)
- 가상자산
- 실적 발표 캘린더

## Agent 1 완료 조건 (Definition of Done)

"내 로컬에서 동작한다"가 완료가 아니다. **Agent 2가 이 출력을 받아서 바로 다음 단계를 진행할 수 있는 상태**가 완료다.

- [ ] 티커 + 기간 입력 시 `CollectedData` 스키마를 준수하는 객체를 반환한다
- [ ] 주가·거래량 데이터가 정상 수집되지 않으면 파이프라인을 중단하고 에러를 반환한다
- [ ] 뉴스·공시 수집 실패 시 `data_quality_warnings`에 경고를 추가하고 계속 진행한다
- [ ] S&P500, 섹터 ETF, Peer 기업 비교 데이터가 `benchmarks` 필드에 포함된다
- [ ] `price_stats.volume_spike_dates`와 `is_abnormal_move`가 계산되어 있다
- [ ] 실제 API를 호출하며 (Mock 금지), 수집 결과를 콘솔에서 눈으로 확인했다
- [ ] `AgentState`를 통해 LangGraph 노드로 통합 가능한 형태로 구현되어 있다

## 팀원 코드 연동

팀원 구현물이 공유되지 않은 상태. Agent 1은 `docs/interface.md`에 정의된 출력 스키마를 기준으로 독립 구현. 팀원 코드 수신 시 스키마 기준으로 연동.  
결정 배경 → `docs/decisions.md` ADR-004 참조.
