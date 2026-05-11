# AI47 — Stock Price Movement Analysis Agent

An AI agent service that takes a stock ticker and date range, then explains **why the stock moved** — producing 3–5 ranked cause hypotheses with confidence scores, a Bull/Bear case, a timeline of events, and a full markdown report.

**Team 47:** 김대연 · 김민석 · 김진기 · 박성준 · 황채원

**Live API:** `http://3.34.109.154` (port 80 via Nginx → FastAPI on port 8000 internally)

---

## What It Does

```
User Input: AAPL  2024-01-02 ~ 2024-01-05
                       ↓
              FastAPI /analyze
                       ↓
         ┌─────── LangGraph Pipeline ──────┐
         │                                 │
         │  Agent 1 — Data Collection      │
         │    ├ OHLCV prices (yfinance)    │
         │    ├ S&P500 / Sector ETF /      │
         │    │  Peer comparison           │
         │    └ News + SEC filings         │
         │              ↓                  │
         │  Agent 2 — Hypothesis Gen       │
         │    ├ Filter & deduplicate news  │
         │    ├ GPT-4o: generate 3–5       │
         │    │  cause hypotheses          │
         │    └ Score & rank by confidence │
         │              ↓                  │
         │  Agent 3 — Report Generation   │
         │    ├ GPT-4o: full markdown      │
         │    │  report + Bull/Bear case   │
         │    └ Save to DB                 │
         └─────────────────────────────────┘
                       ↓
         Hypotheses + Report + Disclaimer
```

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Agent pipeline | Python 3.11, LangGraph |
| API server | FastAPI + Uvicorn |
| LLM | Upstage Solar Pro (`solar-pro`) via OpenAI-compatible API |
| Price data | yfinance (OHLCV, sector, peer comparison) |
| News | NewsAPI (recent articles) |
| SEC filings | SEC EDGAR API (8-K, 10-Q, 10-K, Form 4) |
| Data models | Pydantic v2 |
| Deployment | AWS EC2 (Ubuntu 22.04) + Nginx |

---

## Project Structure

```
AI47/
├── agent/
│   ├── agent1/                    # Data Collection
│   │   ├── nodes/
│   │   │   ├── collect_price.py       # yfinance OHLCV + company info
│   │   │   ├── collect_benchmark.py   # S&P500, sector ETF, peer stocks
│   │   │   └── collect_news_filings.py # NewsAPI + SEC EDGAR
│   │   ├── tools/
│   │   │   ├── price.py               # yfinance wrapper
│   │   │   ├── benchmark.py           # benchmark + peer lookup
│   │   │   ├── news.py                # NewsAPI client
│   │   │   └── sec.py                 # SEC EDGAR client
│   │   └── graph.py                   # Agent 1 LangGraph graph
│   │
│   ├── agent2/                    # Analysis & Hypothesis Generation
│   │   ├── nodes/
│   │   │   ├── filter_noise.py        # Deduplicate & filter news
│   │   │   ├── generate_hypotheses.py # Solar Pro: generate 3–5 hypotheses
│   │   │   └── score_hypotheses.py    # Weighted scoring + confidence
│   │   ├── tools/
│   │   │   └── llm.py                 # Upstage Solar client + prompts
│   │   └── graph.py                   # Agent 2 LangGraph graph
│   │
│   └── agent3/                    # Report Generation
│       ├── nodes/
│       │   ├── generate_report.py     # Solar Pro: full markdown report
│       │   └── save_to_db.py          # PostgreSQL persistence
│       ├── tools/
│       │   └── llm.py                 # Upstage Solar client + prompts
│       └── graph.py                   # Agent 3 LangGraph graph
│
├── orchestrator/
│   └── graph.py           # Connects Agent1 → Agent2 → Agent3
│
├── api/
│   └── main.py            # FastAPI: POST /analyze, GET /health
│
├── models/
│   └── schema.py          # All Pydantic models (AgentState, CollectedData,
│                          #   CauseHypothesis, AnalysisReport, ...)
│
├── scripts/
│   └── setup_server.sh    # One-time EC2 bootstrap script
│
├── .github/
│   └── workflows/
│       └── deploy.yml     # GitHub Actions: push to main → auto-deploy to EC2
│
├── docs/
│   ├── interface.md       # Agent-to-Agent data contract
│   ├── data-sources.md    # API details and constraints
│   └── decisions.md       # Architecture Decision Records (ADRs)
│
├── tests/
│   ├── conftest.py            # Shared pytest fixtures
│   ├── test_score_hypotheses.py # Scoring logic and confidence thresholds
│   ├── test_filter_noise.py   # News dedup and filtering
│   ├── test_schema.py         # Pydantic model validation
│   ├── test_api.py            # FastAPI endpoints (mocked pipeline)
│   └── run_agent1.py          # Agent 1 standalone manual test
│
└── requirements.txt
```

---

## LangGraph Pipeline Detail

### Agent 1 — Data Collection

```
collect_price_data
      │  (fails → pipeline aborts with error)
      ↓
collect_benchmark_data
      │  (fails → warning added, continues)
      ↓
collect_news_and_filings
      │  (fails → warning added, continues)
      ↓
     END  →  CollectedData
```

**Output — `CollectedData`:**
- `prices` — daily OHLCV for the period
- `price_stats` — period % change, max gain/loss, avg volume, volume spike dates, `is_abnormal_move`
- `benchmarks` — S&P500, sector ETF, up to 3 peer stocks
- `news_articles` — up to 50 recent news articles
- `sec_filings` — 8-K, 10-Q, 10-K, Form 4 within date range

### Agent 2 — Hypothesis Generation

```
filter_noise
      ↓
generate_hypotheses   (Solar Pro, temperature=0.3)
      │  (fails → pipeline aborts with error)
      ↓
score_hypotheses
      ↓
     END  →  list[CauseHypothesis]
```

**Scoring weights:**
| Component | Weight |
|-----------|--------|
| Timing alignment | 30% |
| Source credibility | 25% |
| Stock specificity | 20% |
| Volume confirmation | 15% |
| Independent source confirmation | 10% |

**Confidence levels:** High ≥ 0.75 · Medium ≥ 0.45 · Low < 0.45

### Agent 3 — Report Generation

```
generate_report   (Solar Pro, temperature=0.2)
      │  (fails → error logged, pipeline continues)
      ↓
save_to_db
      ↓
     END  →  AnalysisReport
```

**Output — `AnalysisReport`:**
- `one_line_conclusion` — single sentence summary
- `final_report_markdown` — full structured report
- `bull_case` / `bear_case` — scenario analysis
- `watch_next` — 3–5 items to monitor
- `timeline` — key events with timestamps

---

## Local Setup

### 1. Install dependencies

```bash
# uv (recommended)
curl -LsSf https://astral.sh/uv/install.sh | sh
uv venv --python 3.11
uv pip install -r requirements.txt --python .venv/bin/python

# or pip
pip install -r requirements.txt
```

### 2. Set environment variables

```bash
cp .env.example .env
```

Edit `.env`:

```env
UPSTAGE_API_KEY=up_...        # Upstage Solar API — https://console.upstage.ai
NEWSAPI_KEY=...                # https://newsapi.org (free plan: last 30 days only)
DATABASE_URL=postgresql://user:password@localhost:5432/ai47
```

### 3. Run the server

```bash
uv run uvicorn api.main:app --reload
```

- Swagger docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

### 4. Run the test suite

```bash
python -m pytest tests/test_score_hypotheses.py tests/test_filter_noise.py tests/test_schema.py tests/test_api.py -v
```

33 tests covering scoring logic, noise filtering, schema validation, and API endpoints. No external API calls required.

### 5. Test Agent 1 standalone (hits real APIs)

```bash
uv run python -m tests.run_agent1 AAPL 2024-01-02 2024-01-05
#                                 {ticker} {start} {end}
```

---

## API Reference

### `POST /analyze`

**Request:**
```json
{
  "ticker": "NVDA",
  "start_date": "2024-02-20",
  "end_date": "2024-02-23"
}
```

**Response:**
```json
{
  "ticker": "NVDA",
  "collected_data": {
    "ticker": "NVDA",
    "company_name": "NVIDIA Corporation",
    "sector": "Technology",
    "industry": "Semiconductors",
    "start_date": "2024-02-20",
    "end_date": "2024-02-23",
    "price_stats": {
      "period_pct_change": 13.48,
      "max_single_day_gain": 16.4,
      "max_single_day_loss": -0.76,
      "avg_volume": 321450000,
      "volume_spike_dates": ["2024-02-22"],
      "is_abnormal_move": true
    },
    "benchmarks": [
      { "ticker": "^GSPC", "label": "S&P 500",              "pct_change_period": 1.68 },
      { "ticker": "XLK",   "label": "Technology ETF (XLK)", "pct_change_period": 3.21 },
      { "ticker": "AMD",   "label": "AMD",                  "pct_change_period": 2.15 }
    ],
    "news_articles": [ { "title": "...", "source": "Reuters", "url": "https://...", "published_at": "..." } ],
    "sec_filings":   [ { "form_type": "8-K", "filed_at": "2024-02-21", "url": "https://..." } ],
    "data_quality_warnings": []
  },
  "hypotheses": [
    {
      "id": "hypothesis-1",
      "title": "Earnings beat drove massive gap-up",
      "category": "earnings",
      "confidence": "High",
      "score": 0.87,
      "explanation": "NVIDIA reported Q4 FY2024 earnings on Feb 21...",
      "evidence": ["Revenue beat consensus by 20%", "Data center revenue +409% YoY"],
      "counterpoints": ["Stock already priced in strong results"],
      "score_components": {
        "timing_alignment": 0.95,
        "source_credibility": 0.90,
        "stock_specificity": 0.95,
        "volume_confirmation": 0.85,
        "independent_source_confirmation": 0.80
      }
    }
  ],
  "report": {
    "one_line_conclusion": "NVIDIA surged 13.48% after a historic Q4 earnings beat driven by AI data center demand.",
    "final_report_markdown": "## One-Line Conclusion\n...",
    "bull_case": "Sustained AI infrastructure buildout...",
    "bear_case": "Valuation stretched at 30x sales...",
    "watch_next": ["Q1 FY2025 guidance", "Data center order backlog", "AMD MI300X adoption"],
    "timeline": [
      { "datetime": "2024-02-21T21:00:00Z", "type": "earnings", "description": "NVDA Q4 FY2024 earnings release" }
    ]
  },
  "errors": [],
  "disclaimer": "본 분석은 참고용 정보이며, 투자 결정의 책임은 사용자에게 있습니다."
}
```

### `GET /health`

```json
{ "status": "ok" }
```

---

## EC2 Deployment

**First-time server setup** (run once):

```bash
ssh -i your-key.pem ubuntu@3.34.109.154
bash ~/AI47/scripts/setup_server.sh
```

Then create `.env` on the server:

```bash
cat > ~/AI47/.env << 'EOF'
UPSTAGE_API_KEY=up_...
NEWSAPI_KEY=...
DATABASE_URL=postgresql://user:password@localhost:5432/ai47
EOF
sudo systemctl restart ai47
```

**After that — auto-deploy on every push to `main`:**

Add `EC2_SSH_KEY` (your `.pem` file contents) to:
**GitHub → Settings → Secrets → Actions → New repository secret**

Then push to `main` and GitHub Actions handles the rest:
1. **test** job — runs the 33-test pytest suite on the GitHub Actions runner
2. **deploy** job — only runs if tests pass; SSHs into EC2, pulls `main`, reinstalls deps, restarts the service, and runs a `/health` check to confirm startup

**Server info:**
- App runs: `systemd` service → `uvicorn` on port 8000
- Proxy: Nginx → port 80 → port 8000
- API: `http://3.34.109.154/analyze`

---

## Data Sources & Constraints

| Source | Purpose | Key Constraint |
|--------|---------|----------------|
| yfinance | OHLCV, sector, peers | Unofficial API — may break on Yahoo Finance changes |
| NewsAPI | News articles | Free plan: last 30 days only, 100 req/day |
| SEC EDGAR | 8-K, 10-Q, 10-K, Form 4 | US companies only, 10 req/sec |
| Upstage Solar Pro | Hypothesis & report generation | Paid API — $60 credit |

**Sector ETF mapping** (11 sectors):
`Technology→XLK` · `Healthcare→XLV` · `Financials→XLF` · `Energy→XLE` · `Industrials→XLI` · `Consumer Disc.→XLY` · `Consumer Staples→XLP` · `Materials→XLB` · `Real Estate→XLRE` · `Utilities→XLU` · `Communication→XLC`

**Peer lookup** — 32 industry groups mapped (e.g. Semiconductors → NVDA, AMD, INTC, QCOM, AVGO)

---

## Error Handling

| Situation | Behaviour |
|-----------|-----------|
| Price data unavailable | **Pipeline aborts** — analysis requires price data |
| News collection fails | Warning added to `data_quality_warnings`, continues |
| SEC filing fetch fails | Warning added, continues |
| Benchmark/peer fetch fails | Warning added, continues without comparison |
| LLM call fails (Agent 2) | Pipeline aborts with error |
| LLM call fails (Agent 3) | Error logged, report field is null |

---

## Important Notes

- **No investment advice** — all responses include a disclaimer
- **No buy/sell recommendations** — explicitly prohibited in LLM system prompt
- **US stocks only** — yfinance and SEC EDGAR cover US-listed tickers
- **On-demand collection** — no caching; every request calls external APIs fresh

---

> **Disclaimer:** 본 서비스는 참고용 정보 제공을 목적으로 하며, 투자 결정의 책임은 사용자에게 있습니다.
> This service provides informational analysis only. Investment decisions are solely the user's responsibility.
