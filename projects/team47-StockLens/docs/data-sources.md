# 데이터 소스 정의

Agent 1에서 사용하는 외부 데이터 소스 목록, 제약사항, 담당 데이터.

---

## 1. yfinance (주가·거래량·벤치마크)

| 항목 | 내용 |
|------|------|
| 라이브러리 | `yfinance` |
| 비용 | 무료 |
| API 키 | 불필요 |
| Rate Limit | 비공식, 과도한 요청 시 차단 가능 → 요청 간 0.5초 딜레이 권장 |
| 제공 데이터 | OHLCV, 기업 메타(sector, industry, longName), 시가총액 |

**수집 대상:**
- 분석 종목 주가·거래량 (OHLCV)
- S&P 500 (`^GSPC`)
- 섹터 ETF (종목 섹터에 따라 동적 선택)
- Peer 기업 주가 (섹터 내 시가총액 상위 3~5개)

**섹터 ETF 매핑:**
```python
SECTOR_ETF_MAP = {
    "Technology": "XLK",
    "Healthcare": "XLV",
    "Financials": "XLF",
    "Consumer Discretionary": "XLY",
    "Consumer Staples": "XLP",
    "Energy": "XLE",
    "Industrials": "XLI",
    "Materials": "XLB",
    "Real Estate": "XLRE",
    "Utilities": "XLU",
    "Communication Services": "XLC",
}
```

---

## 2. NewsAPI (뉴스 기사)

| 항목 | 내용 |
|------|------|
| 사이트 | https://newsapi.org |
| 비용 | 무료 플랜: 월 100건/일, 최근 1개월 이내 기사만 |
| API 키 | 필요 → `.env`에 `NEWSAPI_KEY` |
| Rate Limit | 무료: 100 req/day |
| 제공 데이터 | 제목, 출처, 발행일, URL, 본문 일부(200자) |

**주의사항:**
- 무료 플랜은 **최근 30일 이내 기사만** 조회 가능. 초과 시 `426 Upgrade Required` 에러 반환
- 30일 이전 분석 기간 입력 시 뉴스 수집 실패 → `data_quality_warnings`에 경고 추가 후 계속 진행
- 본문 전체 제공 안 됨 (헤드라인 + 200자 요약만)
- 한국어 기사 지원 약함 → 미국 주식 기준 영어 기사 위주

**검색 쿼리 전략:**
```
"{company_name}" OR "{ticker}" stock
기간: start_date ~ end_date
언어: en
정렬: relevancy   ← publishedAt 대비 종목 관련 기사가 상위에 노출됨
최대: 100건        ← 무료 플랜 최대치. Agent 2가 필터링 담당
```

---

## 3. SEC EDGAR (공시)

| 항목 | 내용 |
|------|------|
| API | `https://www.sec.gov/files/company_tickers.json` (ticker→CIK 매핑) |
| API | `https://data.sec.gov/submissions/CIK{cik10}.json` (회사별 공시 목록) |
| 비용 | 무료 |
| API 키 | 불필요 (User-Agent 헤더 필수) |
| Rate Limit | 10 req/sec |
| 제공 데이터 | 8-K (중요 사건), 10-Q (분기 보고), 10-K (연간 보고), 4 (내부자 거래) |

**수집 흐름:**
1. `company_tickers.json`에서 ticker → CIK 조회
2. `submissions/CIK{cik10}.json`에서 최근 공시 목록 가져옴
3. `form`, `filingDate` 필드로 대상 유형·기간 필터링

**수집 대상 공시 유형:**
- `8-K`: 중요 사건 (실적 발표, M&A, CEO 교체 등) → 우선순위 높음
- `4`: 내부자 거래
- `10-Q`, `10-K`: 기간이 맞으면 포함

**필수 헤더:**
```python
headers = {
    "User-Agent": "AI47-Project wlsrl723@gmail.com"
}
```

---

## 환경변수

`.env` 파일에 다음 키 필요:

```env
OPENAI_API_KEY=sk-...
NEWSAPI_KEY=...
DATABASE_URL=postgresql://...
```

---

## 데이터 수집 실패 처리

각 소스별 수집 실패 시 전체 파이프라인을 중단하지 않고, `data_quality_warnings`에 경고를 추가하고 계속 진행.

| 상황 | 처리 방식 |
|------|-----------|
| yfinance 조회 실패 | 파이프라인 중단 (주가 없으면 분석 불가) |
| NewsAPI 실패 / 기사 0건 | 경고 추가 후 계속 (뉴스 없이 분석 진행) |
| SEC EDGAR 실패 | 경고 추가 후 계속 (공시 없이 분석 진행) |
| Peer 기업 조회 실패 | 경고 추가, Peer 비교 제외하고 계속 |

---

## 변경 이력

| 날짜 | 변경 내용 | 작성자 |
|------|-----------|--------|
| 2026-05-08 | 초안 작성 | 김진기 |
| 2026-05-08 | SEC EDGAR 실제 사용 API 엔드포인트로 수정, NewsAPI 426 에러 및 30일 제한 명시 | 김진기 |
| 2026-05-08 | NewsAPI 정렬 publishedAt → relevancy, 최대 건수 20 → 100 변경 | 김진기 |
