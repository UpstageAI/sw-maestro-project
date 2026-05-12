# 시스템 아키텍처 (System Architecture)

**프로젝트**: Multi-Agent Dating Platform Backend
**프레임워크**: FastAPI (Python 3.11+)
**작성일**: 2026-05-07

---

## 1. 전체 시스템 구성도

```
┌──────────────────────────────────────────────────────────────┐
│                      클라이언트                                │
│                   (Next.js Frontend)                         │
└──────────────────────┬───────────────────────────────────────┘
                       │ HTTP/JSON
                       │
┌──────────────────────▼──────────────────────────────────────┐
│                   FastAPI Application                       │
│  ┌────────────────────────────────────────────────────────┐ │
│  │                 API Layer (Routers)                    │ │
│  │  /api/agents  /api/conversations  /api/jobs  /health   │ │
│  └────────────────────┬───────────────────────────────────┘ │
│                       │                                     │
│  ┌────────────────────▼───────────────────────────────────┐ │
│  │              Service Layer (Business Logic)            │ │
│  │  AgentService  ConversationService  ChemistryService   │ │
│  │  JobService                                            │ │
│  └────────────────────┬───────────────────────────────────┘ │
│                       │                                     │
│  ┌────────────────────▼───────────────────────────────────┐ │
│  │           Repository Layer (Data Access)               │ │
│  │  AgentRepo  ConversationRepo  MessageRepo              │ │
│  │  ChemistryRepo  JobRepo                                │ │
│  └────────────────────┬───────────────────────────────────┘ │
│                       │                                     │
└───────────────────────┼─────────────────────────────────────┘
                        │
           ┌────────────┼────────────┐
           │            │            │
┌──────────▼─────┐  ┌──────────┐  ┌──────────────┐
│  SQLite DB     │  │ Upstage  │  │ Background   │
│  (app.db)      │  │ Solar API│  │ Task Queue   │
└────────────────┘  └──────────┘  └──────────────┘
```

---

## 2. 프로젝트 폴더 구조

```
llm-blind-date/
├── backend/                        # 백엔드 루트
│   ├── app/                        # FastAPI 애플리케이션
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI 앱 진입점
│   │   │
│   │   ├── api/                    # API Layer (Routers)
│   │   │   ├── __init__.py
│   │   │   ├── dependencies.py     # 공통 의존성 (DB 세션 등)
│   │   │   └── v1/                 # API 버전 1
│   │   │       ├── __init__.py
│   │   │       ├── agents.py       # Agent 관련 엔드포인트
│   │   │       ├── conversations.py # Conversation 관련 엔드포인트
│   │   │       ├── jobs.py         # Job 관련 엔드포인트
│   │   │       └── health.py       # 헬스체크 엔드포인트
│   │   │
│   │   ├── services/               # Service Layer (Business Logic)
│   │   │   ├── __init__.py
│   │   │   ├── agent_service.py    # Agent 생성 로직
│   │   │   ├── conversation_service.py # 매칭, 대화 로직
│   │   │   ├── chemistry_service.py # 케미 분석 로직
│   │   │   ├── job_service.py      # Job 관리 로직
│   │   │   └── solar_client.py     # Upstage Solar LLM 클라이언트 (app/core/ 에 위치)
│   │   │
│   │   ├── repositories/           # Repository Layer (Data Access)
│   │   │   ├── __init__.py
│   │   │   ├── agent_repository.py
│   │   │   ├── conversation_repository.py
│   │   │   ├── message_repository.py
│   │   │   ├── chemistry_repository.py
│   │   │   └── job_repository.py
│   │   │
│   │   ├── models/                 # SQLAlchemy ORM Models
│   │   │   ├── __init__.py
│   │   │   ├── agent.py
│   │   │   ├── conversation.py
│   │   │   ├── message.py
│   │   │   ├── chemistry_analysis.py
│   │   │   └── job.py
│   │   │
│   │   ├── schemas/                # Pydantic Schemas (Request/Response)
│   │   │   ├── __init__.py
│   │   │   ├── agent.py            # AgentCreate, AgentResponse
│   │   │   ├── conversation.py     # ConversationCreate, ConversationResponse
│   │   │   ├── message.py
│   │   │   ├── chemistry.py
│   │   │   └── job.py
│   │   │
│   │   ├── core/                   # 핵심 설정 및 유틸리티
│   │   │   ├── __init__.py
│   │   │   ├── config.py           # 환경 변수 설정
│   │   │   ├── database.py         # DB 연결 설정
│   │   │   ├── exceptions.py       # 커스텀 예외
│   │   │   └── logging.py          # 로깅 설정
│   │   │
│   │   ├── prompts/                # 프롬프트 템플릿
│   │   │   ├── __init__.py
│   │   │   ├── agent_prompt.py     # Agent 생성 프롬프트
│   │   │   └── chemistry_prompt.py # 케미 분석 프롬프트
│   │   │
│   │   └── utils/                  # 유틸리티 함수
│   │       ├── __init__.py
│   │       ├── text_utils.py       # 텍스트 정규화 등
│   │       └── datetime_utils.py   # 날짜/시간 유틸리티
│   │
│   ├── tests/                      # 테스트 코드
│   │   ├── __init__.py
│   │   ├── test_agents.py
│   │   ├── test_conversations.py
│   │   └── test_chemistry.py
│   │
│   ├── scripts/                    # 유틸리티 스크립트
│   │   ├── seed_db.py              # 시드 데이터 삽입
│   │   └── init_db.py              # DB 초기화
│   │
│   ├── Dockerfile                  # Docker 이미지 빌드
│   ├── docker-compose.yml          # Docker Compose 설정
│   ├── requirements.txt            # Python 의존성
│   ├── .env.example                # 환경 변수 예시
│   ├── .gitignore
│   └── README.md
│
├── docs/                           # 문서
│   └── backend-specs/              # 백엔드 명세서
│
└── ...
```

---

## 3. Multi-Agent 시스템 구조

### 3.1 Agent 타입

시스템은 두 가지 타입의 Agent를 사용합니다:

#### Clone Agent (사용자 페르소나)
- **목적**: 사용자의 페르소나를 시뮬레이션하는 대화형 Agent
- **생성**: 사용자가 페르소나 텍스트를 입력하면 AgentService가 생성
- **System Prompt**: 페르소나 기반으로 자동 생성 (2-3문장 답변, 자연스러운 질문 포함)
- **사용**: 1:1 대화에서 상대방과 20턴 대화 진행
- **DB 저장**: `agent_type = 'clone'`, `persona_text`는 사용자 입력값

#### Matchmaker Agent (주선자)
- **목적**: 두 Clone Agent 간의 대화를 분석하여 케미(궁합)를 평가하는 전문 분석 Agent
- **생성**: 시스템 초기화 시 자동 생성 (seed 데이터 또는 startup event)
- **System Prompt**: 고정된 케미 분석 전문 프롬프트 (5개 분석 기준 포함)
- **사용**: ChemistryService가 대화 완료 후 케미 분석 요청 시 활용
- **DB 저장**: `agent_type = 'matchmaker'`, `persona_text = NULL`

### 3.2 Multi-Agent 데이터 흐름

```
┌──────────────────────────────────────────────────────────────┐
│                     사용자 A, B                                │
└──────┬───────────────────────────────────────────┬───────────┘
       │ 페르소나 입력                              │
       ▼                                            ▼
┌──────────────┐                            ┌──────────────┐
│ Clone Agent A│                            │ Clone Agent B│
│ (agent_type: │                            │ (agent_type: │
│  clone)      │                            │  clone)      │
└──────┬───────┘                            └──────┬───────┘
       │                                            │
       └──────────────┬─────────────────────────────┘
                      │ 매칭 후 20턴 대화
                      ▼
           ┌─────────────────────┐
           │  Conversation       │
           │  (40개 Messages)    │
           └──────────┬──────────┘
                      │ 대화 내역 전달
                      ▼
           ┌─────────────────────┐
           │ Matchmaker Agent    │
           │ (agent_type:        │
           │  matchmaker)        │
           │                     │
           │ - 대화 흐름 분석       │
           │ - 5개 기준 평가       │
           │ - 점수 산출 (0-100)   │
           └──────────┬──────────┘
                      │
                      ▼
           ┌─────────────────────┐
           │ Chemistry Analysis  │
           │ - score: 78         │
           │ - summary           │
           │ - good_points       │
           │ - concerns          │
           │ - final_comment     │
           └─────────────────────┘
```

### 3.3 서비스별 Agent 사용

| Service | 사용하는 Agent | 역할 |
|---------|----------------|------|
| AgentService | Clone Agent (생성) | 사용자 페르소나 → System Prompt 생성 → DB 저장 |
| ConversationService | Clone Agent A, B (조회) | 두 Clone Agent를 매칭하고 20턴 대화 시뮬레이션 |
| ChemistryService | Matchmaker Agent (조회) | Matchmaker Agent의 system_prompt를 사용하여 대화 분석 |

---

## 4. 레이어 분리 전략

### 3.1 3-Layer Architecture

FastAPI 애플리케이션을 다음 3개 레이어로 분리:

```
API Layer (Routers)
    ↓
Service Layer (Business Logic)
    ↓
Repository Layer (Data Access)
```

#### **API Layer (Routers)**
- **책임**: HTTP 요청/응답 처리, 입력 검증, 응답 직렬화
- **의존성**: Service Layer
- **도구**: FastAPI, Pydantic
- **예시**: `api/v1/agents.py`

```python
from fastapi import APIRouter, Depends
from app.schemas.agent import AgentCreate, AgentResponse
from app.services.agent_service import AgentService

router = APIRouter(prefix="/api/agents", tags=["agents"])

@router.post("/", response_model=AgentResponse, status_code=201)
async def create_agent(
    agent_data: AgentCreate,
    agent_service: AgentService = Depends()
):
    """Agent 생성 API"""
    return await agent_service.create_agent(agent_data)
```

#### **Service Layer (Business Logic)**
- **책임**: 비즈니스 로직 구현, Solar LLM API 호출, 프롬프트 생성
- **의존성**: Repository Layer, External APIs
- **도구**: `openai` SDK + Upstage `base_url` 오버라이드, 프롬프트 템플릿
- **예시**: `services/agent_service.py`

```python
from app.repositories.agent_repository import AgentRepository
from app.prompts.agent_prompt import generate_system_prompt
from app.utils.text_utils import normalize_text

class AgentService:
    def __init__(self, repo: AgentRepository = Depends()):
        self.repo = repo

    async def create_agent(self, agent_data: AgentCreate) -> AgentResponse:
        # 1. 텍스트 정규화
        normalized_text = normalize_text(agent_data.persona_text)

        # 2. System Prompt 생성
        system_prompt = generate_system_prompt(normalized_text)

        # 3. DB 저장
        agent = await self.repo.create(normalized_text, system_prompt)

        return agent
```

#### **Repository Layer (Data Access)**
- **책임**: 데이터베이스 CRUD 작업
- **의존성**: SQLAlchemy Models, Database Session
- **도구**: SQLAlchemy ORM
- **예시**: `repositories/agent_repository.py`

```python
from sqlalchemy.orm import Session
from app.models.agent import Agent
import uuid

class AgentRepository:
    def __init__(self, db: Session = Depends(get_db)):
        self.db = db

    async def create(self, persona_text: str, system_prompt: str) -> Agent:
        agent = Agent(
            id=str(uuid.uuid4()),
            persona_text=persona_text,
            system_prompt=system_prompt
        )
        self.db.add(agent)
        self.db.commit()
        self.db.refresh(agent)
        return agent

    async def get_by_id(self, agent_id: str) -> Agent | None:
        return self.db.query(Agent).filter(Agent.id == agent_id).first()
```

---

## 5. 주요 모듈별 책임

### 5.1 API 모듈 (`api/v1/`)

| 파일 | 엔드포인트 | 책임 |
|------|-----------|------|
| `agents.py` | POST /api/agents<br>GET /api/agents/{id}<br>GET /api/agents | Agent 생성, 조회 |
| `conversations.py` | POST /api/conversations/match<br>POST /api/conversations/{id}/start<br>GET /api/conversations/{id}/result<br>POST /api/conversations/{id}/analyze | 매칭, 대화 시작, 결과 조회, 케미 분석 |
| `jobs.py` | GET /api/jobs/{job_id} | 작업 상태 폴링 |
| `health.py` | GET /health | 헬스체크 |

### 5.2 Service 모듈 (`services/`)

| 파일 | 책임 |
|------|------|
| `agent_service.py` | Clone Agent 생성 로직, System Prompt 생성 |
| `conversation_service.py` | Clone Agent 랜덤 매칭, 대화 루프 실행 (20턴), Job 관리 |
| `chemistry_service.py` | Matchmaker Agent를 활용한 케미 분석, Solar LLM API 호출, 결과 파싱 |
| `job_service.py` | Job 생성, 상태 업데이트, 결과 저장 |
| `solar_client.py` (`app/core/`) | Upstage Solar LLM API 호출 추상화, 재시도 로직 |

### 5.3 Repository 모듈 (`repositories/`)

| 파일 | 책임 |
|------|------|
| `agent_repository.py` | Agent CRUD |
| `conversation_repository.py` | Conversation CRUD, 상태 업데이트 |
| `message_repository.py` | Message 생성, 대화별 메시지 조회 |
| `chemistry_repository.py` | 케미 분석 결과 저장, 조회 |
| `job_repository.py` | Job CRUD, 상태 업데이트 |

---

## 6. 비동기 처리 구조 (대화 루프)

### 6.1 대화 시뮬레이션 흐름

```
1. [POST /api/conversations/{id}/start]
   → API Layer: 요청 수신
   → Service Layer: Job 생성 및 즉시 반환 (job_id)

2. [백그라운드 태스크 시작]
   → FastAPI BackgroundTasks 사용
   → conversation_service.run_conversation_loop() 실행

3. [20턴 대화 루프]
   for turn in range(1, 21):
       - Agent A 발화 (Solar LLM API 호출)
       - Message 저장 (turn_number = turn*2-1)
       - 컨텍스트 업데이트

       - Agent B 발화 (Solar LLM API 호출)
       - Message 저장 (turn_number = turn*2)
       - 컨텍스트 업데이트

4. [완료 처리]
   → Conversation 상태 업데이트 (status = "completed")
   → Job 상태 업데이트 (status = "completed", result 저장)

5. [에러 발생 시]
   → Job 상태 업데이트 (status = "failed", error 저장)
   → Conversation 상태 업데이트 (status = "failed")
```

### 6.2 코드 예시

```python
from fastapi import BackgroundTasks

@router.post("/{conversation_id}/start")
async def start_conversation(
    conversation_id: str,
    background_tasks: BackgroundTasks,
    conv_service: ConversationService = Depends()
):
    # 1. Job 생성
    job = await conv_service.create_job(conversation_id)

    # 2. 백그라운드 태스크 등록
    background_tasks.add_task(
        conv_service.run_conversation_loop,
        conversation_id,
        job.id
    )

    # 3. 즉시 응답
    return {"job_id": job.id, "message": "대화가 시작되었습니다"}
```

```python
# conversation_service.py
async def run_conversation_loop(self, conversation_id: str, job_id: str):
    try:
        # Job 상태 업데이트
        await self.job_service.update_status(job_id, "processing")

        # Conversation 및 Agent 정보 로드
        conversation = await self.repo.get_by_id(conversation_id)
        agent_a = await self.agent_repo.get_by_id(conversation.agent_a_id)
        agent_b = await self.agent_repo.get_by_id(conversation.agent_b_id)

        # 컨텍스트 초기화
        context_a = []
        context_b = []

        # 20턴 대화
        for turn in range(1, 21):
            # Agent A 발화
            message_a = await self.solar_client.generate_message(
                agent_a.system_prompt, context_a
            )
            await self.message_repo.create(
                conversation_id, agent_a.id, message_a, turn*2-1
            )
            context_a.append({"role": "assistant", "content": message_a})
            context_b.append({"role": "user", "content": message_a})

            # Agent B 발화
            message_b = await self.solar_client.generate_message(
                agent_b.system_prompt, context_b
            )
            await self.message_repo.create(
                conversation_id, agent_b.id, message_b, turn*2
            )
            context_b.append({"role": "assistant", "content": message_b})
            context_a.append({"role": "user", "content": message_b})

        # 완료 처리
        await self.repo.update_status(conversation_id, "completed")
        result = await self.get_conversation_result(conversation_id)
        await self.job_service.complete(job_id, result)

    except Exception as e:
        # 에러 처리
        await self.repo.update_status(conversation_id, "failed")
        await self.job_service.fail(job_id, str(e))
```

---

## 7. 의존성 관리

### 7.1 FastAPI Dependency Injection

```python
# app/api/dependencies.py
from sqlalchemy.orm import Session
from app.core.database import SessionLocal

def get_db():
    """데이터베이스 세션 생성"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_agent_service(db: Session = Depends(get_db)):
    """AgentService 인스턴스 생성"""
    from app.repositories.agent_repository import AgentRepository
    from app.services.agent_service import AgentService

    repo = AgentRepository(db)
    return AgentService(repo)
```

### 7.2 의존성 주입 예시

```python
# API Router
@router.post("/", response_model=AgentResponse)
async def create_agent(
    agent_data: AgentCreate,
    service: AgentService = Depends(get_agent_service)
):
    return await service.create_agent(agent_data)
```

---

## 8. 환경 설정 및 구성

### 8.1 환경 변수 (`core/config.py`)

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # 애플리케이션
    APP_NAME: str = "Multi-Agent Dating Platform API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False

    # 데이터베이스
    DATABASE_URL: str = "sqlite+aiosqlite:///./data/app.db"

    # Upstage Solar LLM (OpenAI 호환 엔드포인트)
    UPSTAGE_API_KEY: str
    UPSTAGE_BASE_URL: str = "https://api.upstage.ai/v1"
    SOLAR_MODEL: str = "solar-pro2"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000"]

    class Config:
        env_file = ".env"

settings = Settings()
```

### 8.2 `.env` 파일 예시

```env
# Application
DEBUG=true

# Upstage Solar LLM
UPSTAGE_API_KEY=up_...your-upstage-key...
UPSTAGE_BASE_URL=https://api.upstage.ai/v1
SOLAR_MODEL=solar-pro2

# CORS
CORS_ORIGINS=["http://localhost:3000"]
```

---

## 9. Docker Compose 구성

### 9.1 `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 시스템 의존성 설치
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Python 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사
COPY ./app ./app
COPY ./scripts ./scripts

# 환경 변수
ENV PYTHONUNBUFFERED=1

# 포트 노출
EXPOSE 8000

# 서버 시작
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

### 9.2 `docker-compose.yml`

```yaml
version: '3.8'

services:
  backend:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: llm-blind-date-backend
    ports:
      - "8000:8000"
    volumes:
      # 코드 핫 리로드용 볼륨 마운트
      - ./app:/app/app
      # SQLite DB 영속성
      - ./data:/app/data
    environment:
      - DEBUG=true
      - DATABASE_URL=sqlite:///./data/app.db
      - UPSTAGE_API_KEY=${UPSTAGE_API_KEY}
      - UPSTAGE_BASE_URL=${UPSTAGE_BASE_URL:-https://api.upstage.ai/v1}
      - SOLAR_MODEL=${SOLAR_MODEL:-solar-pro2}
    env_file:
      - .env
    command: >
      sh -c "
      python scripts/init_db.py &&
      python scripts/seed_db.py &&
      uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
      "
    restart: unless-stopped

volumes:
  data:
    driver: local
```

### 9.3 실행 방법

```bash
# 환경 변수 설정
cp .env.example .env
# .env 파일에 UPSTAGE_API_KEY 입력

# Docker Compose 빌드 및 실행
docker-compose up --build

# 백그라운드 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f backend

# 중지
docker-compose down

# 볼륨까지 삭제 (데이터 초기화)
docker-compose down -v
```

---

## 10. 에러 처리 및 로깅

### 10.1 커스텀 예외 (`core/exceptions.py`)

```python
class AgentNotFoundException(Exception):
    """Agent를 찾을 수 없을 때"""
    pass

class InvalidPersonaTextException(Exception):
    """페르소나 텍스트가 유효하지 않을 때"""
    pass

class ConversationAlreadyCompletedException(Exception):
    """이미 완료된 대화를 재시작하려 할 때"""
    pass
```

### 10.2 예외 핸들러 (`main.py`)

```python
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from app.core.exceptions import AgentNotFoundException

app = FastAPI()

@app.exception_handler(AgentNotFoundException)
async def agent_not_found_handler(request: Request, exc: AgentNotFoundException):
    return JSONResponse(
        status_code=404,
        content={"detail": "Agent를 찾을 수 없습니다"}
    )
```

### 10.3 로깅 (`core/logging.py`)

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

logger = logging.getLogger("app")
```

---

## 11. 테스트 전략

### 11.1 테스트 구조
- **Unit Tests**: Service, Repository 단위 테스트
- **Integration Tests**: API 엔드포인트 통합 테스트
- **도구**: pytest, httpx (FastAPI 테스트)

### 11.2 테스트 예시

```python
# tests/test_agents.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_agent():
    response = client.post("/api/agents", json={
        "persona_text": "저는 28세 개발자입니다. " * 10  # 50자 이상
    })
    assert response.status_code == 201
    assert "id" in response.json()
```

---

## 12. 성능 고려사항

### 12.1 데이터베이스 최적화
- 인덱스 활용 (created_at, status 등)
- N+1 쿼리 방지 (SQLAlchemy eager loading)

### 12.2 Solar LLM API 호출 최적화
- 재시도 로직 (1회 재시도)
- 타임아웃 설정 (30초)
- 에러 로깅

### 12.3 MVP 범위에서 제외
- 캐싱 (Redis 등)
- 데이터베이스 커넥션 풀링 (SQLite 한계)
- API Rate Limiting

---

---

## 13. 매칭 메커니즘 상세 비교

시스템의 매칭 방식은 MVP의 단순성과 향후 확장성을 모두 고려하여 다음과 같이 설계되었습니다.

### 13.1 MVP: 즉시 매칭 (Instant Matching)
가장 빠르고 단순한 방식으로, 현재 DB에 존재하는 에이전트 풀을 활용합니다.

```
클라이언트 ──(매칭 요청)──▶ 서버 ──(DB에서 랜덤 선택)──▶ 결과 즉시 반환
```

- **특징**: 별도의 대기 프로세스나 상태 관리가 필요 없음.
- **시연 시나리오**: DB에 미리 생성된 여러 '시드 에이전트'들이 있다면 사용자가 접속하자마자 즉시 소개팅 시뮬레이션을 시작할 수 있음.

### 13.2 고도화 옵션: 대기큐 매칭 (Queue Matching) - 선택적 구현
실제 유저들이 동시에 접속하여 서로를 기다리는 '리얼타임' 느낌을 줄 수 있는 방식입니다.

```
클라이언트 ──(진입)──▶ 서버(큐 등록) ◀──(주기적 매칭 작업)── 백그라운드 워커
   │                                                         │
   └─────────(매칭 완료될 때까지 폴링 혹은 소켓 대기)───────────┘
```

- **특징**: 
  - `matching_queue`와 같은 별도의 상태 관리 테이블 혹은 Redis가 필요함.
  - 유저 수가 적을 경우를 대비해 일정 시간(예: 30초) 매칭이 안 되면 '가상 에이전트'와 강제로 매칭해 주는 'Fallback 로직'이 필수적으로 수반되어야 함.

---

**문서 버전**: 1.0.0
**최종 수정일**: 2026-05-07
**작성자**: 백엔드팀
