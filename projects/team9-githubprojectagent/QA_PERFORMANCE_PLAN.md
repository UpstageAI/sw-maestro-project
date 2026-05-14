# QA & 성능 테스트 플랜 — GitHub Portfolio Agent

> 작성일: 2026-05-08  
> 담당자: QA Engineer  
> 대상 버전: main 브랜치 현재 상태

---

## 1. 프로젝트 개요 및 테스트 범위

### 시스템 구성

```
사용자 브라우저
    ↓
FastAPI (src/api/)           ← REST API + 정적 파일 서빙
    ↓
LangGraph Orchestrator       ← 10개 노드 StateGraph
    ↓
AI Agents (src/agents/)      ← Upstage Solar Pro 3 (분당 ~30 RPM 한도)
    ↓
Services (src/services/)     ← GitHub Loader / Notion Publisher / PDF Publisher
```

### 테스트 범위 정의

| 구분 | 포함 | 제외 |
|------|------|------|
| API 레이어 | session CRUD, 상태 폴링, 파일 다운로드 | 정적 HTML/JS 렌더링 |
| 워크플로우 | 전체 10개 노드 파이프라인, abort, refine 루프 | LangGraph 내부 구현 |
| AI 출력 품질 | 섹션 내용 평가, validator 채점 | 모델 자체 정확도 |
| 성능 | API 응답시간, LLM 호출 비용, 처리량 | 정적 파일 서빙 속도 |
| 외부 연동 | GitHub API, Notion API, PDF 생성 | Upstage 내부 인프라 |

---

## 2. 테스트 전략

### 2.1 테스트 레벨

```
E2E 테스트        ← 실제 GitHub Repo → PDF/Notion 전체 흐름
    ↑
통합 테스트       ← API + 오케스트레이터 + 에이전트 연동
    ↑
단위 테스트       ← 각 모듈/함수 독립 검증
```

### 2.2 테스트 도구

| 목적 | 도구 | 설치 |
|------|------|------|
| 단위/통합 테스트 | `pytest` + `pytest-asyncio` | `pip install pytest pytest-asyncio` |
| API 테스트 | `httpx` (이미 deps에 있음) + `TestClient` | FastAPI 내장 |
| 모킹 | `unittest.mock` / `pytest-mock` | `pip install pytest-mock` |
| 부하 테스트 | `locust` | `pip install locust` |
| 코드 커버리지 | `pytest-cov` | `pip install pytest-cov` |
| 응답시간 측정 | `time` 내장 + `pytest-benchmark` | `pip install pytest-benchmark` |

### 2.3 테스트 환경

```bash
# .env.test (실제 API 키 없이 테스트 가능하게 분리)
UPSTAGE_API_KEY=test-key-mock
NOTION_TOKEN=test-notion-token
GITHUB_PAT=test-github-pat
MAX_REFINE_ITER=1
SCORE_THRESHOLD=50   # 테스트에서 빠른 통과
LOG_LEVEL=DEBUG
```

---

## 3. 단위 테스트 (Unit Tests)

### 3.1 테스트 파일 구조

```
tests/
├── conftest.py                  # 공통 fixture
├── unit/
│   ├── test_session_manager.py
│   ├── test_config.py
│   ├── test_cost_tracker.py
│   ├── test_secret_scanner.py
│   └── test_models.py
├── integration/
│   ├── test_api_session.py
│   ├── test_orchestrator.py
│   └── test_agents.py
├── e2e/
│   └── test_full_pipeline.py
└── performance/
    ├── test_api_perf.py
    └── locustfile.py
```

### 3.2 Session Manager 테스트

**파일:** `tests/unit/test_session_manager.py`

```python
import threading
import pytest
from src.services.session_manager import SessionManager, State

class TestSessionManager:
    def setup_method(self):
        self.mgr = SessionManager()

    def test_create_session_generates_unique_id(self):
        s1 = self.mgr.create(repo_url="https://github.com/a/b")
        s2 = self.mgr.create(repo_url="https://github.com/a/b")
        assert s1.id != s2.id
        assert len(s1.id) == 12  # uuid4().hex[:12]

    def test_get_existing_session(self):
        s = self.mgr.create(repo_url="https://github.com/a/b")
        assert self.mgr.get(s.id) is s

    def test_get_nonexistent_returns_none(self):
        assert self.mgr.get("nonexistent") is None

    def test_state_transition(self):
        s = self.mgr.create(repo_url="https://github.com/a/b")
        s.set_state(State.FETCHING, "테스트")
        assert s.state == State.FETCHING
        assert len(s.log) > 0
        assert "FETCHING" in s.log[-1]

    def test_abort_flow(self):
        s = self.mgr.create(repo_url="https://github.com/a/b")
        s.request_abort("테스트 중단")
        assert s.state == State.ABORTED
        assert s.abort_event.is_set()
        with pytest.raises(RuntimeError, match="aborted"):
            s.check_abort()

    def test_set_state_is_thread_safe(self):
        s = self.mgr.create(repo_url="https://github.com/a/b")
        errors = []
        def toggle():
            try:
                for state in [State.FETCHING, State.GENERATING, State.DONE]:
                    s.set_state(state)
            except Exception as e:
                errors.append(e)
        threads = [threading.Thread(target=toggle) for _ in range(10)]
        for t in threads: t.start()
        for t in threads: t.join()
        assert not errors
```

### 3.3 Config 테스트

**파일:** `tests/unit/test_config.py`

```python
import os
import pytest

class TestConfig:
    def test_max_refine_iter_default(self):
        from src import config
        assert isinstance(config.MAX_REFINE_ITER, int)
        assert config.MAX_REFINE_ITER >= 1

    def test_score_threshold_range(self):
        from src import config
        assert 0 <= config.SCORE_THRESHOLD <= 100

    def test_output_dir_created(self):
        from src import config
        assert config.OUTPUT_DIR.exists()

    def test_cache_dir_created(self):
        from src import config
        assert config.CACHE_DIR.exists()
```

### 3.4 Secret Scanner 테스트

**파일:** `tests/unit/test_secret_scanner.py`

```python
# src/tools/secret_scanner.py의 동작 검증
# 실제 키 패턴이 감지되는지, 정상 문자열은 통과하는지

class TestSecretScanner:
    def test_detects_api_key_pattern(self):
        # API 키처럼 생긴 문자열이 감지되어야 함
        ...

    def test_normal_content_passes(self):
        # 일반 텍스트는 필터링 없이 통과해야 함
        ...
```

---

## 4. API 통합 테스트

### 4.1 테스트 픽스처 (conftest.py)

```python
# tests/conftest.py
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from src.api.main import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_orchestrator():
    """실제 LLM 호출 없이 오케스트레이터 모킹."""
    with patch("src.services.orchestrator.start_session") as mock:
        yield mock

@pytest.fixture
def mock_github():
    """GitHub API 호출 모킹."""
    with patch("src.services.github_loader.fetch_repo") as mock:
        mock.return_value = MagicMock(
            full_name="test/repo",
            readme="# Test Repo",
            commits=[],
            files={},
            languages={"Python": 100},
            user_attached_info=None,
        )
        yield mock
```

### 4.2 세션 API 테스트

**파일:** `tests/integration/test_api_session.py`

```python
class TestSessionAPI:

    # POST /api/session
    def test_create_session_success(self, client, mock_orchestrator):
        res = client.post("/api/session", json={"repo_url": "https://github.com/a/b"})
        assert res.status_code == 200
        assert "session_id" in res.json()
        mock_orchestrator.assert_called_once()

    def test_create_session_empty_url_returns_400(self, client):
        res = client.post("/api/session", json={"repo_url": "  "})
        assert res.status_code == 400
        assert "repo_url" in res.json()["detail"]

    def test_create_session_missing_url_returns_422(self, client):
        res = client.post("/api/session", json={})
        assert res.status_code == 422

    # GET /api/session/{sid}
    def test_get_session_status(self, client, mock_orchestrator):
        create_res = client.post("/api/session", json={"repo_url": "https://github.com/a/b"})
        sid = create_res.json()["session_id"]
        status_res = client.get(f"/api/session/{sid}")
        assert status_res.status_code == 200
        data = status_res.json()
        assert data["id"] == sid
        assert data["state"] in ("INIT", "FETCHING", "COMPRESSING")
        assert "log" in data
        assert "elapsed_sec" in data

    def test_get_nonexistent_session_returns_404(self, client):
        res = client.get("/api/session/nonexistent123")
        assert res.status_code == 404

    # POST /api/session/{sid}/abort
    def test_abort_session(self, client, mock_orchestrator):
        create_res = client.post("/api/session", json={"repo_url": "https://github.com/a/b"})
        sid = create_res.json()["session_id"]
        abort_res = client.post(f"/api/session/{sid}/abort")
        assert abort_res.status_code == 200
        assert abort_res.json()["ok"] is True

    # POST /api/session/{sid}/answers
    def test_submit_answers_wrong_state_returns_400(self, client, mock_orchestrator):
        create_res = client.post("/api/session", json={"repo_url": "https://github.com/a/b"})
        sid = create_res.json()["session_id"]
        # 세션이 INTERVIEWING 상태가 아닌 경우
        res = client.post(f"/api/session/{sid}/answers", json={"answers": ["답변"]})
        assert res.status_code == 400

    def test_submit_answers_count_mismatch_returns_400(self, client):
        # 질문 2개인데 답변 1개만 보내는 경우
        ...

    # GET /health
    def test_health_endpoint(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        data = res.json()
        assert data["ok"] is True
        assert "model" in data
        assert "score_threshold" in data

    # GET /api/session/{sid}/templates
    def test_get_templates_wrong_state_returns_400(self, client, mock_orchestrator):
        create_res = client.post("/api/session", json={"repo_url": "https://github.com/a/b"})
        sid = create_res.json()["session_id"]
        res = client.get(f"/api/session/{sid}/templates")
        assert res.status_code == 400  # 아직 READY_FOR_TEMPLATE 아님

    # GET /api/session/{sid}/download/{filename}
    def test_download_path_traversal_blocked(self, client, mock_orchestrator):
        create_res = client.post("/api/session", json={"repo_url": "https://github.com/a/b"})
        sid = create_res.json()["session_id"]
        # path traversal 시도
        res = client.get(f"/api/session/{sid}/download/../../../etc/passwd")
        assert res.status_code in (400, 404)
```

### 4.3 상태 머신 전이 테스트

```python
class TestStateMachine:
    """State 전이가 올바른 순서로 발생하는지 검증."""

    VALID_TRANSITIONS = {
        "INIT": ["FETCHING"],
        "FETCHING": ["COMPRESSING", "ERROR", "ABORTED"],
        "COMPRESSING": ["INTERVIEWING", "ERROR", "ABORTED"],
        "INTERVIEWING": ["GENERATING", "ERROR", "ABORTED"],
        "GENERATING": ["VALIDATING", "ERROR", "ABORTED"],
        "VALIDATING": ["REFINING", "DIAGRAMMING", "ERROR", "ABORTED"],
        "REFINING": ["VALIDATING", "ERROR", "ABORTED"],
        "DIAGRAMMING": ["MERGING", "ERROR", "ABORTED"],
        "MERGING": ["READY_FOR_TEMPLATE", "ERROR", "ABORTED"],
        "READY_FOR_TEMPLATE": ["PUBLISHING"],
        "PUBLISHING": ["DONE", "ERROR"],
    }

    def test_all_states_defined(self):
        from src.services.session_manager import State
        expected = {
            "INIT", "FETCHING", "COMPRESSING", "INTERVIEWING",
            "GENERATING", "VALIDATING", "REFINING", "DIAGRAMMING",
            "MERGING", "READY_FOR_TEMPLATE", "PUBLISHING", "DONE",
            "ERROR", "ABORTED",
        }
        actual = {v for k, v in vars(State).items() if not k.startswith("_")}
        assert expected == actual
```

---

## 5. 오케스트레이터 통합 테스트

### 5.1 파이프라인 노드 테스트

**파일:** `tests/integration/test_orchestrator.py`

```python
from unittest.mock import patch, MagicMock
import pytest
from src.services.session_manager import Session, State, SessionManager

@pytest.fixture
def session():
    mgr = SessionManager()
    return mgr.create(repo_url="https://github.com/test/repo")

class TestOrchestratorNodes:

    @patch("src.services.github_loader.fetch_repo")
    @patch("src.services.context_builder.sanitize_files")
    def test_fetch_node_success(self, mock_sanitize, mock_fetch, session):
        from src.services.orchestrator import fetch_node
        mock_ctx = MagicMock(full_name="test/repo", user_attached_info=None)
        mock_fetch.return_value = mock_ctx
        mock_sanitize.return_value = mock_ctx

        state = {
            "session_id": session.id,
            "repo_url": session.repo_url,
        }
        result = fetch_node(state)
        assert "repo_ctx" in result
        assert session.state == State.FETCHING

    def test_abort_check_raises_on_aborted_session(self, session):
        from src.services.orchestrator import fetch_node
        session.request_abort("test")
        with pytest.raises(RuntimeError, match="aborted"):
            fetch_node({"session_id": session.id, "repo_url": session.repo_url})

    @patch("src.agents.validator_agent.run")
    def test_validate_node_pass(self, mock_validator, session):
        from src.services.orchestrator import validate_node
        from src.models.story import Verdict, ScoreEntry
        mock_verdict = MagicMock(
            overall_pass=True,
            scores=[ScoreEntry(name="problem", score=95)],
            weakest="problem",
        )
        mock_validator.return_value = mock_verdict
        state = {
            "session_id": session.id,
            "history": [],
            "iter_n": 0,
            "problem": MagicMock(), "status": MagicMock(),
            "cause": MagicMock(), "result": MagicMock(),
        }
        result = validate_node(state)
        assert result["verdict"].overall_pass is True
        assert result["iter_n"] == 1

    def test_should_refine_passes_when_overall_pass(self):
        from src.services.orchestrator import should_refine
        from unittest.mock import MagicMock
        verdict = MagicMock(overall_pass=True)
        state = {"verdict": verdict, "iter_n": 1}
        assert should_refine(state) == "diagram"

    def test_should_refine_refines_when_fail_and_under_limit(self):
        from src.services.orchestrator import should_refine
        from src import config
        verdict = MagicMock(overall_pass=False)
        state = {"verdict": verdict, "iter_n": 0}
        result = should_refine(state)
        assert result == "refine"

    def test_should_refine_diagrams_when_max_iter_reached(self):
        from src.services.orchestrator import should_refine
        from src import config
        verdict = MagicMock(overall_pass=False)
        state = {"verdict": verdict, "iter_n": config.MAX_REFINE_ITER}
        assert should_refine(state) == "diagram"
```

### 5.2 Rate Limit 재시도 테스트

```python
class TestRateLimitRetry:

    def test_429_triggers_retry(self):
        """429 에러 시 RATE_LIMIT_WAITS_SEC 순서대로 재시도 확인."""
        from src.agents.base import _safe_call
        import time

        call_count = [0]
        def flaky_fn():
            call_count[0] += 1
            if call_count[0] < 3:
                raise Exception("429 too_many_requests")
            return "success"

        with patch("time.sleep"):  # sleep 모킹으로 테스트 속도화
            result = _safe_call(flaky_fn)
        assert result == "success"
        assert call_count[0] == 3

    def test_persistent_429_raises_runtime_error(self):
        from src.agents.base import _safe_call, RATE_LIMIT_WAITS_SEC

        def always_429():
            raise Exception("429 rate limit")

        with patch("time.sleep"):
            with pytest.raises(RuntimeError, match="재시도"):
                _safe_call(always_429)
```

---

## 6. AI 출력 품질 테스트

### 6.1 품질 기준 정의

| 섹션 | 최소 길이 | 필수 포함 요소 | 금지 요소 |
|------|----------|---------------|-----------|
| problem | 200자 | 문제/배경 설명 | 코드 블록만으로 구성 |
| status | 150자 | 기술 스택 언급 | 빈 응답 |
| cause | 200자 | 원인 분석 | 단순 나열 |
| result | 150자 | 성과/결과 | 미래형 문장만 |
| architecture | 50자 | Mermaid 다이어그램 | 없음 |
| dataflow | 50자 | Mermaid 다이어그램 | 없음 |

### 6.2 출력 검증 테스트

```python
class TestAgentOutputQuality:

    @patch("src.agents.base.invoke")
    def test_problem_agent_minimum_length(self, mock_invoke, mock_repo_ctx):
        from src.agents import problem_agent
        mock_invoke.return_value = "충분한 길이의 문제 설명입니다. " * 20
        section = problem_agent.run(mock_repo_ctx)
        assert len(section.content) >= 200

    def test_architecture_agent_contains_mermaid(self, mock_repo_ctx):
        from src.agents import architecture_agent
        with patch("src.agents.base.invoke") as mock:
            mock.return_value = "```mermaid\ngraph TD\n  A --> B\n```"
            result = architecture_agent.run(mock_repo_ctx)
            assert "mermaid" in result.lower() or "graph" in result

    def test_validator_scores_all_sections(self, mock_draft):
        from src.agents import validator_agent
        with patch("src.agents.base.invoke") as mock:
            mock.return_value = '{"scores": [{"name": "problem", "score": 85}, ...]}'
            # validator가 모든 섹션에 점수를 매기는지 확인
            ...
```

---

## 7. 성능 테스트

### 7.1 API 응답시간 기준값 (SLA)

| 엔드포인트 | 목표 응답시간 (p95) | 최대 허용 |
|-----------|-------------------|---------|
| `POST /api/session` | < 200ms | 500ms |
| `GET /api/session/{sid}` | < 100ms | 300ms |
| `POST /api/session/{sid}/abort` | < 100ms | 300ms |
| `GET /health` | < 50ms | 100ms |
| `GET /api/session/{sid}/templates` | < 500ms | 1s |
| `POST /api/session/{sid}/export-pdf` | < 10s | 30s |

### 7.2 전체 파이프라인 처리시간 기준값

| 단계 | 예상 소요시간 | 경고 임계값 | 에러 임계값 |
|------|-------------|-----------|-----------|
| fetch (GitHub API) | 5~30초 | 60초 | 120초 |
| compress | 30~90초 (LLM) | 120초 | 180초 |
| interview | 10~30초 (LLM) | 60초 | 120초 |
| generate (4섹션) | 120~300초 | 400초 | 600초 |
| validate | 30~60초 (LLM) | 90초 | 180초 |
| diagram | 60~120초 (LLM) | 180초 | 300초 |
| **전체 (refine 없음)** | **5~8분** | **12분** | **20분** |
| **전체 (refine 1회)** | **8~12분** | **18분** | **30분** |

### 7.3 Locust 부하 테스트 설정

**파일:** `tests/performance/locustfile.py`

```python
"""
실행: locust -f tests/performance/locustfile.py --host=http://localhost:8000
목표: 동시 10 사용자, 5분간 유지
"""
from locust import HttpUser, task, between
from unittest.mock import patch
import json

class PortfolioAgentUser(HttpUser):
    wait_time = between(1, 3)  # 요청 사이 1~3초 대기

    def on_start(self):
        """세션 생성 (오케스트레이터 실제 실행 안 함)."""
        # 주의: 실제 부하 테스트 시 LLM 비용 발생. 모킹 서버 권장.
        res = self.client.post("/api/session", json={
            "repo_url": "https://github.com/octocat/Hello-World"
        })
        if res.status_code == 200:
            self.session_id = res.json()["session_id"]
        else:
            self.session_id = None

    @task(5)
    def poll_session_status(self):
        """가장 빈번한 작업: 세션 상태 폴링 (프론트가 2초마다 호출)."""
        if self.session_id:
            self.client.get(f"/api/session/{self.session_id}")

    @task(1)
    def check_health(self):
        self.client.get("/health")

    @task(1)
    def check_index(self):
        self.client.get("/")
```

**실행 명령:**
```bash
# 스모크 테스트: 동시 1명, 30초
locust -f tests/performance/locustfile.py \
  --host=http://localhost:8000 \
  --users 1 --spawn-rate 1 --run-time 30s --headless

# 정상 부하: 동시 5명, 5분
locust -f tests/performance/locustfile.py \
  --host=http://localhost:8000 \
  --users 5 --spawn-rate 1 --run-time 5m --headless

# 최대 부하: 동시 10명, 10분
locust -f tests/performance/locustfile.py \
  --host=http://localhost:8000 \
  --users 10 --spawn-rate 2 --run-time 10m
```

### 7.4 API 응답시간 측정 테스트

**파일:** `tests/performance/test_api_perf.py`

```python
import time
import pytest
from fastapi.testclient import TestClient
from src.api.main import app
from unittest.mock import patch

client = TestClient(app)

def measure(fn, iterations=10):
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        fn()
        times.append(time.perf_counter() - start)
    return {
        "min": min(times),
        "max": max(times),
        "avg": sum(times) / len(times),
        "p95": sorted(times)[int(len(times) * 0.95)],
    }

class TestAPIResponseTime:

    def test_health_endpoint_under_50ms(self):
        stats = measure(lambda: client.get("/health"))
        assert stats["p95"] < 0.05, f"p95={stats['p95']:.3f}s > 50ms"

    @patch("src.services.orchestrator.start_session")
    def test_create_session_under_200ms(self, _mock):
        stats = measure(
            lambda: client.post("/api/session", json={"repo_url": "https://github.com/a/b"}),
            iterations=20,
        )
        assert stats["p95"] < 0.2, f"p95={stats['p95']:.3f}s > 200ms"

    @patch("src.services.orchestrator.start_session")
    def test_poll_session_under_100ms(self, _mock):
        res = client.post("/api/session", json={"repo_url": "https://github.com/a/b"})
        sid = res.json()["session_id"]
        stats = measure(
            lambda: client.get(f"/api/session/{sid}"),
            iterations=50,
        )
        assert stats["p95"] < 0.1, f"p95={stats['p95']:.3f}s > 100ms"
```

### 7.5 LLM 비용 추적 테스트

```python
class TestCostTracking:
    """파이프라인 실행 후 비용이 추적되는지 검증."""

    def test_cost_report_populated_after_run(self, completed_session):
        assert completed_session.cost_report is not None
        assert isinstance(completed_session.cost_report, dict)

    def test_cost_within_budget_per_session(self, completed_session):
        """세션당 LLM 비용이 예산 내에 있는지 확인.
        Solar Pro 3 기준: 세션당 $0.10 이하 목표."""
        report = completed_session.cost_report
        total_tokens = report.get("total_tokens", 0)
        # solar-pro3 가격 기준으로 계산 (토큰당 비용 * 총 토큰)
        # 실제 가격은 Upstage 콘솔에서 확인
        assert total_tokens < 500_000, f"토큰 과다 사용: {total_tokens}"
```

---

## 8. E2E 테스트

### 8.1 골든 패스 테스트 (실제 API 호출)

> **주의:** 이 테스트는 실제 Upstage, GitHub API를 호출하므로 비용 발생.  
> CI에서는 기본 제외, `pytest -m e2e` 로만 실행.

**파일:** `tests/e2e/test_full_pipeline.py`

```python
import pytest
import time
import httpx

BASE_URL = "http://localhost:8000"
TEST_REPO = "https://github.com/octocat/Hello-World"  # 가벼운 공개 레포
TIMEOUT = 600  # 10분

@pytest.mark.e2e
class TestFullPipeline:

    def test_happy_path_no_interview(self):
        """인터뷰 질문 없는 레포 → READY_FOR_TEMPLATE 도달."""
        with httpx.Client(timeout=30) as client:
            # 1. 세션 생성
            res = client.post(f"{BASE_URL}/api/session", json={
                "repo_url": TEST_REPO,
                "user_attached_info": "이 레포는 테스트용입니다."
            })
            assert res.status_code == 200
            sid = res.json()["session_id"]

            # 2. 완료까지 폴링
            deadline = time.time() + TIMEOUT
            final_state = None
            while time.time() < deadline:
                status = client.get(f"{BASE_URL}/api/session/{sid}").json()
                state = status["state"]
                print(f"  [{time.strftime('%H:%M:%S')}] state={state}")
                if state in ("READY_FOR_TEMPLATE", "DONE", "ERROR", "ABORTED"):
                    final_state = state
                    break
                if state == "INTERVIEWING":
                    # 빈 답변으로 스킵
                    client.post(f"{BASE_URL}/api/session/{sid}/answers",
                                json={"answers": [""] * len(status["questions"])})
                time.sleep(5)

            assert final_state == "READY_FOR_TEMPLATE", \
                f"기대: READY_FOR_TEMPLATE, 실제: {final_state}"

            # 3. 드래프트 내용 검증
            assert status["draft"]["problem"] is not None
            assert status["draft"]["merged"] is not None
            assert len(status["draft"]["merged"]) > 100

    @pytest.mark.e2e
    def test_abort_mid_pipeline(self):
        """파이프라인 실행 중 abort 요청 시 ABORTED 상태로 전환."""
        with httpx.Client(timeout=30) as client:
            res = client.post(f"{BASE_URL}/api/session", json={"repo_url": TEST_REPO})
            sid = res.json()["session_id"]
            time.sleep(3)  # 파이프라인 시작 대기
            abort_res = client.post(f"{BASE_URL}/api/session/{sid}/abort")
            assert abort_res.json()["ok"] is True
            # 이후 상태가 ABORTED로 수렴하는지 확인
            time.sleep(10)
            status = client.get(f"{BASE_URL}/api/session/{sid}").json()
            assert status["state"] == "ABORTED"

    @pytest.mark.e2e
    def test_pdf_export(self):
        """READY_FOR_TEMPLATE 상태에서 PDF 내보내기."""
        # ... 전체 파이프라인 완료 후 PDF 생성 검증
```

---

## 9. 테스트 케이스 체크리스트

### 9.1 기능 테스트

#### API 레이어
- [ ] `POST /api/session` — 정상 생성
- [ ] `POST /api/session` — 빈 URL 거부 (400)
- [ ] `POST /api/session` — URL 없음 (422)
- [ ] `GET /api/session/{sid}` — 정상 조회
- [ ] `GET /api/session/{sid}` — 없는 세션 (404)
- [ ] `GET /api/session/{sid}` — 응답 필드 완전성 검증
- [ ] `POST /api/session/{sid}/abort` — 정상 중단
- [ ] `POST /api/session/{sid}/abort` — 없는 세션 (404)
- [ ] `POST /api/session/{sid}/answers` — 정상 제출
- [ ] `POST /api/session/{sid}/answers` — 잘못된 state (400)
- [ ] `POST /api/session/{sid}/answers` — 개수 불일치 (400)
- [ ] `GET /api/session/{sid}/templates` — READY_FOR_TEMPLATE 상태에서 조회
- [ ] `GET /api/session/{sid}/templates` — 잘못된 state (400)
- [ ] `POST /api/session/{sid}/publish` — 정상 발행
- [ ] `POST /api/session/{sid}/export-pdf` — PDF 생성 성공
- [ ] `GET /api/session/{sid}/download/{filename}` — 정상 다운로드
- [ ] `GET /api/session/{sid}/download/{filename}` — path traversal 방어
- [ ] `GET /health` — 정상 응답 및 필드 검증

#### 오케스트레이터
- [ ] fetch_node — GitHub 레포 정상 fetch
- [ ] fetch_node — 잘못된 URL 에러 처리
- [ ] compress_node — 컨텍스트 압축 정상
- [ ] interview_node — 질문 생성 정상
- [ ] wait_for_answers_node — 질문 없을 때 통과
- [ ] merge_answers_node — 답변 컨텍스트 병합
- [ ] generate_node — 4섹션 병렬 생성
- [ ] validate_node — 채점 및 pass/fail 판정
- [ ] should_refine — 조건분기 3가지 케이스
- [ ] refine_node — weakest 섹션부터 재생성
- [ ] diagram_node — Mermaid 다이어그램 생성
- [ ] merge_node — 최종 머지 완료
- [ ] abort 체크 — 모든 노드 진입 시 abort 감지

#### 에이전트
- [ ] problem_agent — 출력 길이 및 형식
- [ ] status_agent — 출력 길이 및 형식
- [ ] cause_agent — 출력 길이 및 형식
- [ ] result_agent — 출력 길이 및 형식
- [ ] architecture_agent — Mermaid 포함
- [ ] dataflow_agent — Mermaid 포함
- [ ] interview_agent — 질문 리스트 형식
- [ ] validator_agent — 점수 형식 및 범위(0-100)
- [ ] merge_agent — 전체 섹션 통합

#### Rate Limit 방어
- [ ] 429 첫 번째 — 60초 대기 후 재시도
- [ ] 429 반복 — 최대 5회 재시도
- [ ] 429 지속 — RuntimeError 발생
- [ ] throttle — LLM 호출 사이 최소 2초 간격
- [ ] 전역 lock — 동시 LLM 호출 직렬화

### 9.2 성능 테스트

- [ ] `GET /health` p95 < 50ms
- [ ] `POST /api/session` p95 < 200ms
- [ ] `GET /api/session/{sid}` p95 < 100ms
- [ ] 동시 10 세션 — API 응답시간 저하 없음
- [ ] 전체 파이프라인 — refine 없음 < 8분
- [ ] 전체 파이프라인 — refine 1회 < 12분
- [ ] PDF 생성 < 30초
- [ ] 세션당 LLM 토큰 < 500,000
- [ ] 10분간 동시 폴링 10개 — 메모리 누수 없음

### 9.3 회귀 테스트

- [ ] 서버 재시작 후 세션 복구 불가 (in-memory — 예상 동작)
- [ ] 대형 레포 (>300 커밋) — MAX_COMMITS_FETCH 제한 준수
- [ ] 대형 파일 (>200KB) — MAX_FILE_SIZE_KB 제한 준수
- [ ] Notion 토큰 미설정 시 publish 에러 처리
- [ ] PDF 생성 실패 시 `success: false` 응답 (예외 전파 안 함)

---

## 10. 테스트 실행 프로세스

### 10.1 개발 중 (로컬)

```bash
# 1. 테스트 의존성 설치
pip install pytest pytest-asyncio pytest-mock pytest-cov pytest-benchmark locust httpx

# 2. 환경변수 설정
cp .env.example .env.test

# 3. 단위 테스트 (빠름, ~30초)
pytest tests/unit/ -v --tb=short

# 4. 통합 테스트 (모킹, ~2분)
pytest tests/integration/ -v --tb=short

# 5. 커버리지 리포트
pytest tests/unit/ tests/integration/ \
  --cov=src --cov-report=html --cov-report=term-missing \
  --cov-fail-under=70

# 6. 성능 테스트 (서버 실행 후)
uvicorn src.api.main:app --reload &
pytest tests/performance/test_api_perf.py -v
```

### 10.2 PR 머지 전 체크리스트

```bash
# 전체 테스트 실행 (E2E 제외)
pytest tests/unit/ tests/integration/ tests/performance/test_api_perf.py \
  --cov=src --cov-fail-under=70 -q

# 결과 기준:
# ✅ 단위 테스트 전체 통과
# ✅ 통합 테스트 전체 통과
# ✅ API 응답시간 SLA 충족
# ✅ 커버리지 70% 이상
```

### 10.3 릴리스 전 체크리스트

```bash
# E2E 포함 전체 실행 (비용 발생 주의)
pytest tests/ -m "not e2e" -q           # 자동화 테스트
pytest tests/e2e/ -m e2e -v -s          # E2E (수동 승인 후)

# 부하 테스트 (서버 실행 후)
locust -f tests/performance/locustfile.py \
  --host=http://localhost:8000 \
  --users 10 --spawn-rate 2 --run-time 10m --headless \
  --csv=results/load_test_$(date +%Y%m%d)

# 결과 기준:
# ✅ E2E 골든패스 통과
# ✅ 부하 테스트 실패율 < 1%
# ✅ p95 응답시간 SLA 충족
# ✅ 전체 파이프라인 처리시간 기준값 충족
```

### 10.4 CI/CD 파이프라인 (GitHub Actions 예시)

```yaml
# .github/workflows/test.yml
name: Tests

on: [push, pull_request]

jobs:
  unit-integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-asyncio pytest-mock pytest-cov
      - run: |
          pytest tests/unit/ tests/integration/ \
            --cov=src --cov-report=xml --cov-fail-under=70 -q
        env:
          UPSTAGE_API_KEY: "mock-key"
          GITHUB_PAT: "mock-pat"

  performance:
    runs-on: ubuntu-latest
    needs: unit-integration
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install -r requirements.txt pytest httpx
      - run: uvicorn src.api.main:app &
      - run: sleep 3 && pytest tests/performance/test_api_perf.py -v
```

---

## 11. 버그 리포트 템플릿

```markdown
## 버그 요약
[한 줄 설명]

## 환경
- OS: 
- Python: 
- 브랜치/커밋:

## 재현 단계
1. 
2. 
3. 

## 기대 결과
[무엇이 일어나야 했는지]

## 실제 결과
[무엇이 일어났는지]

## 로그/스크린샷
```
[오류 로그 붙여넣기]
```

## 심각도
- [ ] Critical (서비스 불가)
- [ ] High (주요 기능 불가)
- [ ] Medium (기능 저하)
- [ ] Low (사소한 이슈)
```

---

## 12. 성능 측정 결과 기록 양식

테스트 실행 후 아래 양식에 결과를 기록합니다.

```markdown
### 성능 테스트 결과 — YYYY-MM-DD

| 측정 항목 | 목표 | 실측 p50 | 실측 p95 | 통과 여부 |
|----------|------|---------|---------|---------|
| GET /health | < 50ms | ?ms | ?ms | ✅/❌ |
| POST /api/session | < 200ms | ?ms | ?ms | ✅/❌ |
| GET /api/session/{sid} | < 100ms | ?ms | ?ms | ✅/❌ |
| 전체 파이프라인 | < 8분 | ?분 | ?분 | ✅/❌ |
| PDF 생성 | < 30초 | ?초 | ?초 | ✅/❌ |
| 동시 10사용자 실패율 | < 1% | ?% | — | ✅/❌ |

**비고:**
```

---

## 13. 우선순위 로드맵

| 주차 | 작업 | 목표 |
|------|------|------|
| 1주차 | 테스트 환경 구성, pytest 설정, conftest.py | 기반 구축 |
| 1주차 | 단위 테스트 작성 (session_manager, config) | 핵심 모듈 검증 |
| 2주차 | API 통합 테스트 전체 엔드포인트 | API 안정성 확보 |
| 2주차 | 오케스트레이터 노드별 단위 테스트 | 파이프라인 검증 |
| 3주차 | 성능 테스트 (API 응답시간, Locust) | SLA 기준값 확인 |
| 3주차 | Rate limit 재시도 로직 테스트 | 안정성 강화 |
| 4주차 | E2E 테스트 (실제 API) | 통합 검증 |
| 4주차 | CI/CD 파이프라인 연동 | 자동화 완성 |
| 지속 | 커버리지 70% → 80% 향상 | 품질 향상 |
