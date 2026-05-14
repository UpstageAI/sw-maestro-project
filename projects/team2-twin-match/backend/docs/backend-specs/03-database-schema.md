# 데이터베이스 스키마 (Database Schema)

**프로젝트**: Multi-Agent Dating Platform
**DBMS**: SQLite 3
**ORM**: SQLAlchemy
**작성일**: 2026-05-07

---

## 1. ERD (Entity Relationship Diagram)

```
┌─────────────────┐
│     agents      │
├─────────────────┤
│ id (PK)         │
│ persona_text    │
│ system_prompt   │
│ created_at      │
└─────────────────┘
        │
        │ 1
        │
        │ N
        ├──────────────────────┐
        │                      │
┌───────▼──────────┐   ┌───────▼──────────┐
│  conversations   │   │    messages      │
├──────────────────┤   ├──────────────────┤
│ id (PK)          │   │ id (PK)          │
│ agent_a_id (FK)  │   │ conversation_id  │
│ agent_b_id (FK)  │───│   (FK)           │
│ status           │ 1 │ agent_id (FK)    │
│ created_at       │   │ content          │
│ completed_at     │ N │ turn_number      │
└──────────────────┘   │ created_at       │
        │              └──────────────────┘
        │ 1
        │
        │ 1
┌───────▼────────────────┐
│ chemistry_analyses     │
├────────────────────────┤
│ id (PK)                │
│ conversation_id (FK)   │
│ score                  │
│ summary                │
│ good_points            │
│ concerns               │
│ final_comment          │
│ created_at             │
└────────────────────────┘

┌─────────────────┐      ┌─────────────────────────┐
│      jobs       │      │  matching_queue [Opt]   │
├─────────────────┤      ├─────────────────────────┤
│ id (PK)         │      │ id (PK)                 │
│ conversation_id │      │ agent_id (FK)           │
│   (FK)          │      │ status (waiting/matched)│
│ status          │      │ conversation_id (FK)    │
│ result          │      │ created_at              │
│ error           │      └─────────────────────────┘
│ created_at      │
│ updated_at      │
└─────────────────┘
```

**관계 설명**:
- Agent 1 : N Conversation (agent_a_id)
- Agent 1 : N Conversation (agent_b_id)
- Conversation 1 : N Message
- Agent 1 : N Message
- Conversation 1 : 1 ChemistryAnalysis
- Conversation 1 : 1 Job

---

## 2. 테이블 정의

### 2.1 agents 테이블
Clone Agent 및 Matchmaker Agent 정보

| 컬럼명 | 데이터 타입 | 제약조건 | 설명 |
|--------|-------------|----------|------|
| id | TEXT | PRIMARY KEY | Agent 고유 ID (UUID) |
| agent_type | TEXT | NOT NULL | Agent 종류 ("clone" 또는 "matchmaker") |
| name | TEXT | NULL | Clone Agent: 이름/닉네임 (Matchmaker는 NULL) |
| age | INTEGER | NULL | Clone Agent: 나이 (Matchmaker는 NULL) |
| gender | TEXT | NULL | Clone Agent: 성별 ("F", "M", "X") |
| job | TEXT | NULL | Clone Agent: 직업 (예: "개발자", "마케터") |
| tags | TEXT | NULL | Clone Agent: 성격 태그 (JSON 배열, 예: ["#INTP", "#등산"]) |
| persona_text | TEXT | NULL | Clone Agent: 사용자 페르소나 텍스트 |
| system_prompt | TEXT | NOT NULL | 생성된 시스템 프롬프트 |
| created_at | TEXT | NOT NULL | 생성 시간 (ISO 8601) |

**인덱스**:
- PRIMARY KEY: `id`
- INDEX: `idx_agents_created_at` on `created_at` (목록 조회 최적화)
- INDEX: `idx_agents_type` on `agent_type` (Agent 종류별 조회)

**비즈니스 규칙**:
- UUID는 Python의 `uuid.uuid4()`로 생성
- `agent_type`은 "clone" 또는 "matchmaker"만 허용
- Clone Agent: `persona_text` 필수 (50자 이상), 사용자가 생성
- Matchmaker Agent: `persona_text` NULL, 시스템에서 자동 생성
- `system_prompt`는 자동 생성됨 (사용자 입력 아님)
- Matchmaker Agent는 시스템 시작 시 1개만 생성
- 삭제 불가 (MVP)

---

### 2.2 conversations 테이블
두 Agent 간의 대화 세션

| 컬럼명 | 데이터 타입 | 제약조건 | 설명 |
|--------|-------------|----------|------|
| id | TEXT | PRIMARY KEY | 대화 세션 ID (UUID) |
| agent_a_id | TEXT | NOT NULL, FOREIGN KEY | Agent A ID |
| agent_b_id | TEXT | NOT NULL, FOREIGN KEY | Agent B ID |
| status | TEXT | NOT NULL | 대화 상태 (pending, processing, completed, failed) |
| created_at | TEXT | NOT NULL | 생성 시간 (ISO 8601) |
| completed_at | TEXT | NULL | 완료 시간 (ISO 8601), 미완료 시 NULL |

**외래키**:
- `agent_a_id` → `agents(id)` ON DELETE CASCADE
- `agent_b_id` → `agents(id)` ON DELETE CASCADE

**인덱스**:
- PRIMARY KEY: `id`
- INDEX: `idx_conversations_status` on `status` (상태별 조회 최적화)
- INDEX: `idx_conversations_agent_a` on `agent_a_id` (Agent별 대화 조회)
- INDEX: `idx_conversations_agent_b` on `agent_b_id`

**비즈니스 규칙**:
- `agent_a_id`와 `agent_b_id`는 서로 달라야 함 (애플리케이션 레벨 검증)
- `status` 값: "pending", "processing", "completed", "failed"
- `completed_at`은 대화 완료 시에만 설정됨

---

### 2.3 messages 테이블
대화 중 개별 메시지

| 컬럼명 | 데이터 타입 | 제약조건 | 설명 |
|--------|-------------|----------|------|
| id | TEXT | PRIMARY KEY | 메시지 ID (UUID) |
| conversation_id | TEXT | NOT NULL, FOREIGN KEY | 대화 세션 ID |
| agent_id | TEXT | NOT NULL, FOREIGN KEY | 발화한 Agent ID |
| content | TEXT | NOT NULL | 메시지 내용 |
| turn_number | INTEGER | NOT NULL | 턴 번호 (1-40) |
| created_at | TEXT | NOT NULL | 생성 시간 (ISO 8601) |

**외래키**:
- `conversation_id` → `conversations(id)` ON DELETE CASCADE
- `agent_id` → `agents(id)` ON DELETE CASCADE

**인덱스**:
- PRIMARY KEY: `id`
- INDEX: `idx_messages_conversation` on `conversation_id` (대화별 메시지 조회)
- UNIQUE INDEX: `idx_messages_conversation_turn` on `(conversation_id, turn_number)` (턴 중복 방지)

**비즈니스 규칙**:
- `turn_number`는 1부터 시작하여 40까지 (20턴 × 2 Agent)
- Agent A: 홀수 턴 (1, 3, 5, ..., 39)
- Agent B: 짝수 턴 (2, 4, 6, ..., 40)
- 동일 conversation 내에서 turn_number는 유니크해야 함

---

### 2.4 chemistry_analyses 테이블
대화 기반 케미 분석 결과

| 컬럼명 | 데이터 타입 | 제약조건 | 설명 |
|--------|-------------|----------|------|
| id | TEXT | PRIMARY KEY | 분석 결과 ID (UUID) |
| conversation_id | TEXT | NOT NULL, UNIQUE, FOREIGN KEY | 대화 세션 ID |
| score | INTEGER | NOT NULL | 케미 점수 (0-100) |
| oneliner | TEXT | NOT NULL | 한 줄 평 (예: "서로의 대화가 아주 자연스럽습니다") |
| summary | TEXT | NOT NULL | 관계 요약 (1-2문장) |
| good_points | TEXT | NOT NULL | 잘 맞는 점 목록 (JSON 배열) |
| concerns | TEXT | NOT NULL | 우려되는 점 목록 (JSON 배열) |
| metrics | TEXT | NOT NULL | 상세 지표 점수 (JSON 객체: 티키타카, 공통 화제 등) |
| final_comment | TEXT | NOT NULL | 최종 한마디 |
| created_at | TEXT | NOT NULL | 분석 시간 (ISO 8601) |

**외래키**:
- `conversation_id` → `conversations(id)` ON DELETE CASCADE

**인덱스**:
- PRIMARY KEY: `id`
- UNIQUE INDEX: `idx_chemistry_conversation` on `conversation_id` (1:1 관계 보장)

**비즈니스 규칙**:
- 한 대화당 하나의 분석만 존재 (UNIQUE 제약)
- `good_points`, `concerns`는 JSON 배열로 저장 (예: `["항목1", "항목2"]`)
- `score`는 0-100 사이 정수 (애플리케이션 레벨 검증)

---

### 2.5 jobs 테이블
비동기 작업 상태 추적

| 컬럼명 | 데이터 타입 | 제약조건 | 설명 |
|--------|-------------|----------|------|
| id | TEXT | PRIMARY KEY | 작업 ID (UUID) |
| conversation_id | TEXT | NOT NULL, FOREIGN KEY | 대화 세션 ID |
| status | TEXT | NOT NULL | 작업 상태 (pending, processing, completed, failed) |
| result | TEXT | NULL | 완료 시 결과 (JSON), 미완료 시 NULL |
| error | TEXT | NULL | 실패 시 에러 메시지, 성공 시 NULL |
| created_at | TEXT | NOT NULL | 생성 시간 (ISO 8601) |
| updated_at | TEXT | NOT NULL | 최종 업데이트 시간 (ISO 8601) |

**외래키**:
- `conversation_id` → `conversations(id)` ON DELETE CASCADE

**인덱스**:
- PRIMARY KEY: `id`
- INDEX: `idx_jobs_status` on `status` (상태별 조회)
- INDEX: `idx_jobs_conversation` on `conversation_id`

**비즈니스 규칙**:
- `status` 값: "pending", "processing", "completed", "failed"
- `result`는 완료 시 대화 및 메시지 전체 데이터를 JSON으로 저장
- `updated_at`은 상태 변경 시마다 갱신

---

### 2.6 matching_queue 테이블 [Optional]
실시간 대기큐(전략 B) 사용 시 대기자 관리

| 컬럼명 | 데이터 타입 | 제약조건 | 설명 |
|--------|-------------|----------|------|
| id | TEXT | PRIMARY KEY | 큐 항목 ID (UUID) |
| agent_id | TEXT | NOT NULL, FOREIGN KEY | 대기 중인 Agent ID |
| status | TEXT | NOT NULL | 대기 상태 (waiting, matched, cancelled) |
| conversation_id | TEXT | NULL, FOREIGN KEY | 매칭 성공 시 생성된 대화 ID |
| created_at | TEXT | NOT NULL | 큐 진입 시간 (ISO 8601) |

**외래키**:
- `agent_id` → `agents(id)` ON DELETE CASCADE
- `conversation_id` → `conversations(id)` ON DELETE SET NULL

**인덱스**:
- INDEX: `idx_queue_status` on `status` (대기자 조회 최적화)

**비즈니스 규칙**:
- 전략 B(대기큐 매칭) 활성화 시에만 사용됨
- 매칭 성공 시 `status`를 "matched"로 변경하고 `conversation_id` 연결

---

## 3. DDL (CREATE TABLE)

### SQLite DDL 스크립트

```sql
-- agents 테이블
CREATE TABLE agents (
    id TEXT PRIMARY KEY,
    agent_type TEXT NOT NULL CHECK(agent_type IN ('clone', 'matchmaker')),
    name TEXT,
    age INTEGER,
    gender TEXT CHECK(gender IN ('F', 'M', 'X')),
    job TEXT,
    tags TEXT,
    persona_text TEXT,
    system_prompt TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE INDEX idx_agents_created_at ON agents(created_at DESC);
CREATE INDEX idx_agents_type ON agents(agent_type);

-- conversations 테이블
CREATE TABLE conversations (
    id TEXT PRIMARY KEY,
    agent_a_id TEXT NOT NULL,
    agent_b_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending', 'processing', 'completed', 'failed')),
    created_at TEXT NOT NULL,
    completed_at TEXT,
    FOREIGN KEY (agent_a_id) REFERENCES agents(id) ON DELETE CASCADE,
    FOREIGN KEY (agent_b_id) REFERENCES agents(id) ON DELETE CASCADE
);

CREATE INDEX idx_conversations_status ON conversations(status);
CREATE INDEX idx_conversations_agent_a ON conversations(agent_a_id);
CREATE INDEX idx_conversations_agent_b ON conversations(agent_b_id);

-- messages 테이블
CREATE TABLE messages (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    content TEXT NOT NULL,
    turn_number INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE,
    FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE,
    UNIQUE(conversation_id, turn_number)
);

CREATE INDEX idx_messages_conversation ON messages(conversation_id);
CREATE UNIQUE INDEX idx_messages_conversation_turn ON messages(conversation_id, turn_number);

-- chemistry_analyses 테이블
CREATE TABLE chemistry_analyses (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL UNIQUE,
    score INTEGER NOT NULL CHECK(score >= 0 AND score <= 100),
    oneliner TEXT NOT NULL,
    summary TEXT NOT NULL,
    good_points TEXT NOT NULL,
    concerns TEXT NOT NULL,
    metrics TEXT NOT NULL,
    final_comment TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE UNIQUE INDEX idx_chemistry_conversation ON chemistry_analyses(conversation_id);

-- jobs 테이블
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    conversation_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('pending', 'processing', 'completed', 'failed')),
    result TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE CASCADE
);

CREATE INDEX idx_jobs_status ON jobs(status);
CREATE INDEX idx_jobs_conversation ON jobs(conversation_id);

-- [Optional] matching_queue 테이블
CREATE TABLE matching_queue (
    id TEXT PRIMARY KEY,
    agent_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('waiting', 'matched', 'cancelled')),
    conversation_id TEXT,
    created_at TEXT NOT NULL,
    FOREIGN KEY (agent_id) REFERENCES agents(id) ON DELETE CASCADE,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id) ON DELETE SET NULL
);

CREATE INDEX idx_queue_status ON matching_queue(status);
```

---

## 4. SQLAlchemy 모델 예시

```python
from sqlalchemy import Column, String, Integer, Text, ForeignKey, CheckConstraint, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime, timezone

Base = declarative_base()


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_type = Column(String, nullable=False, default="clone")
    name = Column(String, nullable=True)
    age = Column(Integer, nullable=True)
    gender = Column(String, nullable=True)
    job = Column(String, nullable=True)
    tags = Column(String, nullable=True)  # JSON array as string
    persona_text = Column(Text, nullable=True)  # Matchmaker Agent는 NULL
    system_prompt = Column(Text, nullable=False)
    created_at = Column(String, nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())

    __table_args__ = (
        CheckConstraint("agent_type IN ('clone', 'matchmaker')", name="check_agent_type"),
        CheckConstraint("gender IN ('F', 'M', 'X')", name="check_gender"),
    )

    # Relationships
    conversations_as_a = relationship("Conversation", foreign_keys="Conversation.agent_a_id", back_populates="agent_a")
    conversations_as_b = relationship("Conversation", foreign_keys="Conversation.agent_b_id", back_populates="agent_b")
    messages = relationship("Message", back_populates="agent")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_a_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    agent_b_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, nullable=False, default="pending")
    created_at = Column(String, nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    completed_at = Column(String, nullable=True)

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed')", name="check_status"),
    )

    # Relationships
    agent_a = relationship("Agent", foreign_keys=[agent_a_id], back_populates="conversations_as_a")
    agent_b = relationship("Agent", foreign_keys=[agent_b_id], back_populates="conversations_as_b")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    chemistry = relationship("ChemistryAnalysis", back_populates="conversation", uselist=False, cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="conversation", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    agent_id = Column(String, ForeignKey("agents.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    turn_number = Column(Integer, nullable=False)
    created_at = Column(String, nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())

    __table_args__ = (
        UniqueConstraint("conversation_id", "turn_number", name="unique_conversation_turn"),
    )

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    agent = relationship("Agent", back_populates="messages")


class ChemistryAnalysis(Base):
    __tablename__ = "chemistry_analyses"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, unique=True)
    score = Column(Integer, nullable=False)
    oneliner = Column(String, nullable=False)
    summary = Column(Text, nullable=False)
    good_points = Column(Text, nullable=False)  # JSON array as string
    concerns = Column(Text, nullable=False)  # JSON array as string
    metrics = Column(Text, nullable=False)  # JSON object as string
    final_comment = Column(Text, nullable=False)
    created_at = Column(String, nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())

    __table_args__ = (
        CheckConstraint("score >= 0 AND score <= 100", name="check_score_range"),
    )

    # Relationships
    conversation = relationship("Conversation", back_populates="chemistry")


class Job(Base):
    __tablename__ = "jobs"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    status = Column(String, nullable=False, default="pending")
    result = Column(Text, nullable=True)  # JSON as string
    error = Column(Text, nullable=True)
    created_at = Column(String, nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    updated_at = Column(String, nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())

    __table_args__ = (
        CheckConstraint("status IN ('pending', 'processing', 'completed', 'failed')", name="check_job_status"),
    )

    # Relationships
    conversation = relationship("Conversation", back_populates="jobs")
```

---

## 5. 시드 데이터 (Seed Data)

### 5.1 개발용 목 데이터

```sql
-- Matchmaker Agent 1개 생성 (필수)
INSERT INTO agents (id, agent_type, persona_text, system_prompt, created_at) VALUES
(
    'matchmaker-00000000-0000-0000-0000-000000000001',
    'matchmaker',
    NULL,
    '당신은 두 사람의 대화를 분석하여 케미(궁합)를 평가하는 전문 주선자입니다. 객관적이고 공정하게 분석하며, 대화의 자연스러움, 공통 관심사, 대화 스타일 조화, 유머 감각, 서로에 대한 관심도를 기준으로 0-100점의 점수를 부여합니다.',
    '2026-05-04T15:00:00.000000Z'
);

-- Clone Agent 3개 생성
INSERT INTO agents (id, agent_type, persona_text, system_prompt, created_at) VALUES
(
    '550e8400-e29b-41d4-a716-446655440000',
    'clone',
    '저는 28세 개발자입니다. 주로 웹 개발을 하고 있고, 주말에는 등산을 좋아합니다. 조용하고 신중한 성격이지만, 친해지면 유머러스한 면도 있습니다.',
    '당신은 다음 정보를 가진 사람입니다: 28세 개발자, 웹 개발 전문, 등산 취미, 조용하고 신중하지만 친해지면 유머러스함. 답변은 2-3문장으로 짧게 유지하고, 상대방에게 자연스러운 질문을 포함하세요. 절대 AI임을 밝히지 마세요.',
    '2026-05-04T15:21:45.035507Z'
),
(
    '550e8400-e29b-41d4-a716-446655440001',
    'clone',
    '저는 25세 디자이너입니다. UI/UX 디자인을 전문으로 하고, 주말에는 사진 찍기를 좋아합니다. 외향적이고 활발한 성격이며, 새로운 사람 만나는 것을 좋아합니다.',
    '당신은 다음 정보를 가진 사람입니다: 25세 디자이너, UI/UX 전문, 사진 취미, 외향적이고 활발함. 답변은 2-3문장으로 짧게 유지하고, 상대방에게 자연스러운 질문을 포함하세요. 절대 AI임을 밝히지 마세요.',
    '2026-05-04T15:20:30.123456Z'
),
(
    '550e8400-e29b-41d4-a716-446655440002',
    'clone',
    '저는 30세 마케터입니다. 브랜드 마케팅을 담당하고 있고, 독서와 영화 감상을 좋아합니다. 차분하고 분석적인 성격이며, 깊이 있는 대화를 선호합니다.',
    '당신은 다음 정보를 가진 사람입니다: 30세 마케터, 브랜드 마케팅 전문, 독서와 영화 취미, 차분하고 분석적. 답변은 2-3문장으로 짧게 유지하고, 상대방에게 자연스러운 질문을 포함하세요. 절대 AI임을 밝히지 마세요.',
    '2026-05-04T15:19:15.789012Z'
);
```

### 5.2 Python 시드 스크립트 예시

```python
import sqlite3
from datetime import datetime, timezone
import uuid

def seed_database(db_path: str = "app.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 1. Matchmaker Agent 생성 (필수)
    matchmaker = {
        "id": "matchmaker-00000000-0000-0000-0000-000000000001",
        "agent_type": "matchmaker",
        "persona_text": None,
        "system_prompt": "당신은 두 사람의 대화를 분석하여 케미(궁합)를 평가하는 전문 주선자입니다. 객관적이고 공정하게 분석하며, 대화의 자연스러움, 공통 관심사, 대화 스타일 조화, 유머 감각, 서로에 대한 관심도를 기준으로 0-100점의 점수를 부여합니다.",
        "created_at": datetime.now(timezone.utc).isoformat()
    }

    cursor.execute(
        """
        INSERT INTO agents (id, agent_type, persona_text, system_prompt, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (matchmaker["id"], matchmaker["agent_type"], matchmaker["persona_text"],
         matchmaker["system_prompt"], matchmaker["created_at"])
    )

    # 2. Clone Agent 시드 데이터
    seed_agents = [
        {
            "id": str(uuid.uuid4()),
            "agent_type": "clone",
            "persona_text": "저는 28세 개발자입니다. 주로 웹 개발을 하고 있고, 주말에는 등산을 좋아합니다.",
            "system_prompt": "당신은 28세 개발자입니다. 웹 개발과 등산을 좋아합니다. 2-3문장으로 답변하세요.",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "agent_type": "clone",
            "persona_text": "저는 25세 디자이너입니다. UI/UX 디자인을 전문으로 하고, 사진 찍기를 좋아합니다.",
            "system_prompt": "당신은 25세 디자이너입니다. UI/UX 디자인과 사진을 좋아합니다. 2-3문장으로 답변하세요.",
            "created_at": datetime.now(timezone.utc).isoformat()
        },
        {
            "id": str(uuid.uuid4()),
            "agent_type": "clone",
            "persona_text": "저는 30세 마케터입니다. 브랜드 마케팅을 담당하고 있고, 독서와 영화를 좋아합니다.",
            "system_prompt": "당신은 30세 마케터입니다. 브랜드 마케팅과 독서, 영화를 좋아합니다. 2-3문장으로 답변하세요.",
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]

    for agent in seed_agents:
        cursor.execute(
            """
            INSERT INTO agents (id, agent_type, persona_text, system_prompt, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (agent["id"], agent["agent_type"], agent["persona_text"],
             agent["system_prompt"], agent["created_at"])
        )

    conn.commit()
    conn.close()
    print(f"Matchmaker Agent 1개 + Clone Agent {len(seed_agents)}개 생성 완료")

if __name__ == "__main__":
    seed_database()
```

---

## 6. 데이터베이스 초기화 및 관리

### 6.1 데이터베이스 생성

```python
from sqlalchemy import create_engine
from models import Base  # SQLAlchemy 모델들

# SQLite 데이터베이스 생성
engine = create_engine("sqlite:///app.db", echo=True)

# 모든 테이블 생성
Base.metadata.create_all(engine)
print("데이터베이스 초기화 완료")
```

### 6.2 서버 시작 시 자동 초기화 (FastAPI)

```python
# app/main.py
from fastapi import FastAPI
from sqlalchemy import create_engine
from app.database import Base, get_db
from app.seed import seed_database

app = FastAPI()

@app.on_event("startup")
def startup_event():
    # 데이터베이스 생성
    engine = create_engine("sqlite:///app.db")
    Base.metadata.create_all(engine)

    # Matchmaker Agent 확인 및 생성 (필수)
    db = next(get_db())
    from app.models import Agent

    matchmaker_exists = db.query(Agent).filter(Agent.agent_type == "matchmaker").count() > 0
    if not matchmaker_exists:
        # Matchmaker Agent 자동 생성
        from app.services.matchmaker_service import create_matchmaker_agent
        create_matchmaker_agent(db)
        print("Matchmaker Agent 생성 완료")

    # Clone Agent 시드 데이터 삽입 (기존 데이터 확인 후)
    clone_count = db.query(Agent).filter(Agent.agent_type == "clone").count()
    if clone_count == 0:
        seed_database()
        print("Clone Agent 시드 데이터 삽입 완료")
    else:
        print(f"기존 Clone Agent {clone_count}개 존재, 시드 스킵")
```

---

## 7. 데이터 타입 및 포맷 규칙

### 7.1 UUID 형식
- 하이픈 포함 36자 문자열: `550e8400-e29b-41d4-a716-446655440000`
- Python: `str(uuid.uuid4())`

### 7.2 날짜/시간 형식 (ISO 8601)
- 형식: `YYYY-MM-DDTHH:MM:SS.ffffffZ`
- 예시: `2026-05-04T15:21:45.035507Z`
- Python: `datetime.now(timezone.utc).isoformat()`
- SQLite에서는 TEXT로 저장, 애플리케이션에서 파싱

### 7.3 JSON 저장 (SQLite)
- SQLite는 네이티브 JSON 타입이 없으므로 TEXT로 저장
- Python에서 `json.dumps()` / `json.loads()` 사용
- 예시:
  ```python
  import json
  good_points = ["항목1", "항목2"]
  good_points_json = json.dumps(good_points, ensure_ascii=False)  # TEXT로 저장
  ```

---

## 8. 마이그레이션 전략

### 8.1 MVP 단계
- 스키마 변경 시 데이터베이스 재생성 (DROP + CREATE)
- 중요 데이터 없으므로 마이그레이션 도구 불필요

### 8.2 향후 고려사항
- Alembic 도입 (SQLAlchemy 마이그레이션 도구)
- PostgreSQL 전환 시 데이터 마이그레이션 스크립트 작성

---

## 9. 백업 및 복구

### 9.1 백업
```bash
# SQLite 데이터베이스 파일 복사
cp app.db app_backup_$(date +%Y%m%d_%H%M%S).db
```

### 9.2 복구
```bash
# 백업 파일로 복원
cp app_backup_20260504_153000.db app.db
```

---

**문서 버전**: 1.0.0
**최종 수정일**: 2026-05-07
**작성자**: 백엔드팀
