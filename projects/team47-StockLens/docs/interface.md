# Agent 간 인터페이스 계약

Agent 1 → Agent 2로 넘기는 데이터 스키마 정의.
이 파일이 팀 간 계약서 역할을 하며, 수정 시 반드시 팀에 공유해야 함.

---

## Agent 1 출력 스키마 (`CollectedData`)

```python
from __future__ import annotations
from pydantic import BaseModel
from typing import Optional
from datetime import date

class PriceRecord(BaseModel):
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int
    pct_change: float          # 전일 대비 등락률 (%)

class BenchmarkComparison(BaseModel):
    ticker: str                # 비교 대상 티커 (e.g. "^GSPC", "XLK")
    label: str                 # 표시 이름 (e.g. "S&P500", "Tech Sector ETF")
    pct_change_period: float   # 분석 기간 전체 등락률 (%)

class NewsArticle(BaseModel):
    title: str
    source: str
    published_at: str          # ISO 8601 (e.g. "2024-01-15T09:30:00Z")
    url: str
    summary: Optional[str] = None

class SECFiling(BaseModel):
    form_type: str             # e.g. "8-K", "10-Q"
    filed_at: str              # "YYYY-MM-DD"
    description: str
    url: str

class PriceStats(BaseModel):
    period_pct_change: float           # 분석 기간 전체 등락률 (%)
    max_single_day_gain: float         # 기간 내 최대 단일 일 상승률 (%)
    max_single_day_loss: float         # 기간 내 최대 단일 일 하락률 (%)
    avg_volume: float                  # 기간 평균 거래량
    volume_spike_dates: list[str]      # 거래량 급증일 (평균 대비 2배 이상)
    is_abnormal_move: bool             # 비정상 움직임 여부 (±5% 이상 단일 일 변동)

class CollectedData(BaseModel):
    # 요청 메타
    ticker: str
    start_date: date
    end_date: date
    company_name: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None  # yfinance industry 필드 (sector보다 세분화)

    # 주가 데이터 (주가 수집 실패 시 파이프라인 중단 → 항상 존재)
    prices: list[PriceRecord] = []
    price_stats: Optional[PriceStats] = None

    # 비교 데이터 (수집 실패 시 빈 리스트)
    benchmarks: list[BenchmarkComparison] = []
    peer_tickers: list[str] = []

    # 뉴스 및 공시 (수집 실패 시 빈 리스트 + data_quality_warnings에 경고)
    news_articles: list[NewsArticle] = []
    sec_filings: list[SECFiling] = []

    # 수집 메타
    collected_at: str = ""             # ISO 8601, 수집 시각
    data_quality_warnings: list[str] = []  # 수집 실패/부분 누락 경고 메시지
```

---

## LangGraph 상태 정의 (`AgentState`)

전체 파이프라인에서 공유되는 상태.

```python
import operator
from typing import TypedDict, Optional, Annotated

class AgentState(TypedDict):
    # 입력
    ticker: str
    start_date: str    # "YYYY-MM-DD"
    end_date: str      # "YYYY-MM-DD"

    # Agent 1 출력
    collected_data: Optional[CollectedData]

    # Agent 2 출력
    hypotheses: Optional[list[dict]]   # 상세 스키마는 Agent 2 담당자 정의

    # Agent 3 출력
    report: Optional[dict]             # 상세 스키마는 Agent 3 담당자 정의

    # 에러 추적 — Annotated[..., operator.add] 로 각 노드가 추가(append)
    errors: Annotated[list[str], operator.add]
```

---

## 노드 이름 규칙

LangGraph 그래프에서 사용할 노드 이름 (오케스트레이터 연동 기준).

| 노드 이름 | 담당 | 설명 |
|-----------|------|------|
| `collect_price_data` | Agent 1 | 주가·거래량 조회 |
| `collect_benchmark_data` | Agent 1 | 벤치마크·섹터ETF·Peer 비교 |
| `collect_news_and_filings` | Agent 1 | 뉴스·SEC 공시 수집 |
| `filter_noise` | Agent 2 | 노이즈 필터링·중복 제거 |
| `generate_hypotheses` | Agent 2 | 원인 가설 생성 |
| `score_hypotheses` | Agent 2 | 가설 점수화·신뢰도 분류 |
| `generate_report` | Agent 3 | 구조화 보고서 생성 |
| `save_to_db` | Agent 3 | DB 저장 |

---

## 변경 이력

| 날짜 | 변경 내용 | 작성자 |
|------|-----------|--------|
| 2026-05-08 | 초안 작성 | 김진기 |
| 2026-05-08 | 구현 반영: CollectedData 필드 기본값 추가, AgentState.errors Annotated 타입으로 수정, SECFiling.filed_at 포맷 수정 | 김진기 |
| 2026-05-08 | CollectedData에 industry 필드 추가 (Peer 비교 정확도 개선) | 김진기 |
