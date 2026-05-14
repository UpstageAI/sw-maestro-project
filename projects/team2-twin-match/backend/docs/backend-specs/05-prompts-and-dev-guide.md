# 프롬프트 설계 + 개발 환경 가이드

**프로젝트**: Multi-Agent Dating Platform Backend
**작성일**: 2026-05-07

---

# Part 1: 프롬프트 설계 (Prompt Engineering)

## 1. Clone Agent 생성 System Prompt

### 1.1 템플릿 구조

Clone Agent 생성 시 사용자의 페르소나 텍스트를 기반으로 System Prompt를 자동 생성합니다.

```python
# app/prompts/agent_prompt.py

AGENT_SYSTEM_PROMPT_TEMPLATE = """
당신은 다음 정보를 가진 사람입니다:

{persona_text}

**대화 규칙:**
1. 답변은 2-3문장으로 짧게 유지하세요.
2. 상대방에게 자연스러운 질문을 포함하세요.
3. 한국어로만 대화하세요.
4. 절대 당신이 AI라는 사실을 밝히지 마세요.
5. 자연스럽고 인간적인 말투를 사용하세요.
6. 위 정보에 기반하여 일관된 성격과 관심사를 유지하세요.
""".strip()

def generate_system_prompt(persona_text: str) -> str:
    """
    사용자 페르소나 텍스트로 System Prompt 생성

    Args:
        persona_text: 정규화된 페르소나 텍스트

    Returns:
        완성된 System Prompt
    """
    return AGENT_SYSTEM_PROMPT_TEMPLATE.format(persona_text=persona_text)
```

### 1.2 예시

**입력 (persona_text)**:
```
저는 28세 개발자입니다. 주로 웹 개발을 하고 있고, 주말에는 등산을 좋아합니다.
조용하고 신중한 성격이지만, 친해지면 유머러스한 면도 있습니다.
```

**출력 (system_prompt)**:
```
당신은 다음 정보를 가진 사람입니다:

저는 28세 개발자입니다. 주로 웹 개발을 하고 있고, 주말에는 등산을 좋아합니다.
조용하고 신중한 성격이지만, 친해지면 유머러스한 면도 있습니다.

**대화 규칙:**
1. 답변은 2-3문장으로 짧게 유지하세요.
2. 상대방에게 자연스러운 질문을 포함하세요.
3. 한국어로만 대화하세요.
4. 절대 당신이 AI라는 사실을 밝히지 마세요.
5. 자연스럽고 인간적인 말투를 사용하세요.
6. 위 정보에 기반하여 일관된 성격과 관심사를 유지하세요.
```

---

## 2. 대화 생성 (Solar LLM API 호출)

### 2.1 API 호출 구조

Upstage Solar LLM은 OpenAI 호환 Chat Completions 엔드포인트를 제공한다.
공식 `openai` SDK를 그대로 쓰되 `base_url` 과 `api_key` 만 Upstage 값으로 덮어씀.

```python
# app/core/solar_client.py

import asyncio
from openai import AsyncOpenAI, RateLimitError
from app.core.config import config

_client = AsyncOpenAI(
    api_key=config.UPSTAGE_API_KEY,
    base_url=config.UPSTAGE_BASE_URL,  # https://api.upstage.ai/v1
)


async def generate_message(
    system_prompt: str,
    conversation_history: list[dict],
) -> str:
    """
    Upstage Solar LLM을 호출하여 Agent의 다음 발화 생성

    Args:
        system_prompt: Agent의 System Prompt
        conversation_history: 대화 기록 [{"role": "user/assistant", "content": "..."}]

    Returns:
        생성된 메시지 내용
    """
    messages = [{"role": "system", "content": system_prompt}] + conversation_history

    try:
        response = await _client.chat.completions.create(
            model=config.SOLAR_MODEL,  # "solar-pro2"
            messages=messages,
            temperature=0.8,
            max_tokens=200,
            top_p=0.9,
            frequency_penalty=0.3,
            presence_penalty=0.3,
        )
        return (response.choices[0].message.content or "").strip()

    except RateLimitError:
        # 1회 재시도
        await asyncio.sleep(2)
        return await generate_message(system_prompt, conversation_history)

    except Exception as e:
        raise Exception(f"Solar LLM API 호출 실패: {str(e)}")
```

### 2.2 파라미터 설명

| 파라미터 | 값 | 설명 |
|----------|-----|------|
| model | solar-pro2 | Upstage Solar LLM 기본 모델 (`SOLAR_MODEL` 로 오버라이드 가능) |
| temperature | 0.8 | 창의성과 일관성의 균형 (0-2, 높을수록 창의적) |
| max_tokens | 200 | 2-3문장 정도의 길이 제한 |
| top_p | 0.9 | 다양성 조절 (nucleus sampling) |
| frequency_penalty | 0.3 | 같은 단어/구문 반복 감소 |
| presence_penalty | 0.3 | 새로운 주제 도입 장려 |

### 2.3 대화 컨텍스트 구조

```python
# 대화 시작 (Agent A 첫 발화)
context_a = []
message_a = await generate_message(agent_a.system_prompt, context_a)
# → "안녕하세요! 반가워요. 어떤 일 하세요?"

# Agent A의 컨텍스트에 자신의 발화 추가
context_a.append({"role": "assistant", "content": message_a})

# Agent B의 컨텍스트에 Agent A의 발화를 user로 추가
context_b = [{"role": "user", "content": message_a}]

# Agent B 발화
message_b = await generate_message(agent_b.system_prompt, context_b)
# → "안녕하세요! 저는 디자이너로 일하고 있어요. 혹시 개발자이신가요?"

# Agent B의 컨텍스트 업데이트
context_b.append({"role": "assistant", "content": message_b})

# Agent A의 컨텍스트 업데이트
context_a.append({"role": "user", "content": message_b})

# ... 20턴 반복
```

---

## 3. Matchmaker Agent System Prompt

### 3.1 Matchmaker Agent 역할

Matchmaker Agent는 Clone Agent 간의 대화를 분석하여 케미를 평가하는 전문 주선자 역할을 수행합니다.

### 3.2 System Prompt 템플릿

```python
# app/prompts/matchmaker_prompt.py

MATCHMAKER_SYSTEM_PROMPT = """
당신은 두 사람의 대화를 분석하여 케미(궁합)를 평가하는 전문 주선자 AI입니다.

**당신의 역할:**
1. 객관적이고 공정한 제3자 관점에서 대화를 분석합니다.
2. 대화의 흐름, 상호작용, 감정적 교류를 면밀히 관찰합니다.
3. 정량적 점수와 정성적 피드백을 모두 제공합니다.

**분석 기준:**
1. 대화의 자연스러움 (20점): 티키타카가 잘 이어지는가?
2. 공통 관심사 발견 (20점): 취미, 가치관, 관심사의 유사성
3. 대화 스타일 조화 (20점): 말투, 호흡, 이모티콘 사용 등
4. 유머 감각 일치 (20점): 농담에 대한 반응, 유머 코드
5. 상호 관심도 (20점): 서로에게 질문하고 경청하는 정도

총 100점 만점으로 평가하며, 각 영역별 점수를 합산하여 최종 점수를 산출합니다.

**응답 원칙:**
- 긍정적인 면과 우려되는 면을 균형있게 제시합니다.
- 구체적인 대화 예시를 근거로 평가합니다.
- 단순히 점수만이 아닌 개선 방향도 제시합니다.
- 반드시 JSON 형식으로만 응답합니다.
""".strip()


def create_matchmaker_agent(db):
    """
    시스템 시작 시 Matchmaker Agent 생성

    Args:
        db: 데이터베이스 세션

    Returns:
        생성된 Matchmaker Agent 객체
    """
    from app.models.agent import Agent
    import uuid
    from datetime import datetime, timezone

    matchmaker = Agent(
        id="matchmaker-00000000-0000-0000-0000-000000000001",
        agent_type="matchmaker",
        persona_text=None,
        system_prompt=MATCHMAKER_SYSTEM_PROMPT,
        created_at=datetime.now(timezone.utc).isoformat()
    )

    db.add(matchmaker)
    db.commit()
    db.refresh(matchmaker)

    return matchmaker
```

---

## 4. 케미 분석 (Matchmaker Agent 활용)

### 4.1 분석 요청 Prompt 템플릿

```python
# app/prompts/chemistry_prompt.py

CHEMISTRY_ANALYSIS_PROMPT = """
다음은 두 사람(Agent A와 Agent B)의 소개팅 대화 내역입니다.
이 대화를 분석하여 두 사람의 케미(궁합)를 평가해 주세요.

**대화 내역:**
{conversation_transcript}

**분석 기준:**
1. 대화의 자연스러움 (티키타카가 잘 이루어지는가?)
2. 공통 관심사나 가치관 발견
3. 대화 스타일의 조화 (말투, 호흡 등)
4. 유머 감각의 일치
5. 서로에게 관심을 보이는 정도

**응답 형식 (JSON):**
{{
  "score": <0-100 사이의 정수>,
  "summary": "<관계를 1-2문장으로 요약>",
  "good_points": ["<잘 맞는 점 1>", "<잘 맞는 점 2>", ...],
  "concerns": ["<우려되는 점 1>", "<우려되는 점 2>", ...],
  "final_comment": "<최종 한마디>"
}}

**중요:**
- score는 0-100 사이의 정수로 정확히 평가하세요.
- good_points는 최소 1개, 최대 5개로 작성하세요.
- concerns는 최소 0개, 최대 3개로 작성하세요.
- 객관적이고 구체적으로 분석하세요.
- 반드시 JSON 형식으로만 응답하세요.
""".strip()


def generate_chemistry_prompt(messages: list) -> str:
    """
    대화 내역을 기반으로 케미 분석 프롬프트 생성

    Args:
        messages: Message 객체 리스트 (시간순 정렬)

    Returns:
        완성된 케미 분석 프롬프트
    """
    # 대화 내역을 텍스트로 변환
    transcript_lines = []
    for msg in messages:
        # Agent A는 홀수 턴, Agent B는 짝수 턴
        speaker = "Agent A" if msg.turn_number % 2 == 1 else "Agent B"
        transcript_lines.append(f"{speaker}: {msg.content}")

    conversation_transcript = "\n".join(transcript_lines)

    return CHEMISTRY_ANALYSIS_PROMPT.format(
        conversation_transcript=conversation_transcript
    )
```

### 4.2 Matchmaker Agent API 호출

```python
# app/services/chemistry_service.py

import json
from app.core.config import config
from app.core.solar_client import get_client


async def analyze_chemistry_with_matchmaker(messages: list, db) -> dict:
    """
    Matchmaker Agent를 통해 대화 분석 및 케미 점수 산출

    Args:
        messages: 대화 메시지 리스트
        db: 데이터베이스 세션

    Returns:
        케미 분석 결과 (dict)
    """
    # 1. Matchmaker Agent 조회
    from app.models.db.agent import Agent
    matchmaker = db.query(Agent).filter(Agent.agent_type == "matchmaker").first()

    if not matchmaker:
        raise Exception("Matchmaker Agent를 찾을 수 없습니다")

    # 2. 대화 로그 포맷팅
    prompt = generate_chemistry_prompt(messages)

    try:
        # 3. Matchmaker Agent의 System Prompt 사용 (Solar LLM 호출)
        client = get_client()
        response = await client.chat.completions.create(
            model=config.SOLAR_MODEL,  # "solar-pro2"
            messages=[
                {"role": "system", "content": matchmaker.system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,  # 일관성 중요 (낮은 temperature)
            response_format={"type": "json_object"}  # JSON 응답 강제
        )

        result_text = response.choices[0].message.content
        result = json.loads(result_text)

        # 검증
        assert 0 <= result["score"] <= 100
        assert isinstance(result["good_points"], list)
        assert isinstance(result["concerns"], list)

        return result

    except json.JSONDecodeError as e:
        raise Exception(f"JSON 파싱 실패: {str(e)}")
    except Exception as e:
        raise Exception(f"케미 분석 실패: {str(e)}")
```

### 3.3 분석 결과 예시

**입력 (대화 내역)**:
```
Agent A: 안녕하세요! 반가워요. 어떤 일 하세요?
Agent B: 안녕하세요! 저는 디자이너로 일하고 있어요. 혹시 개발자이신가요?
Agent A: 네 맞아요! 웹 개발하고 있어요. 디자이너분이시면 협업할 일도 많을 것 같네요 ㅎㅎ
Agent B: 맞아요! 저도 개발자분들과 자주 일해요. 주말엔 뭐 하세요?
Agent A: 주로 등산 다녀요. 요즘 날씨가 좋아서 자주 가는 편이에요. 혹시 운동 좋아하세요?
...
```

**출력 (JSON)**:
```json
{
  "score": 78,
  "summary": "두 사람은 대화 스타일이 잘 맞고 공통 관심사(여행, 책)가 있어 긍정적인 관계 발전이 기대됩니다.",
  "good_points": [
    "대화가 자연스럽게 이어짐",
    "서로에게 질문하며 관심을 보임",
    "유머 감각이 비슷함 (ㅎㅎ 등 사용)",
    "공통 관심사 발견 (여행, 자연)"
  ],
  "concerns": [
    "활동적인 성향 vs 조용한 성향 차이",
    "가치관 차이가 나타날 가능성"
  ],
  "final_comment": "서로 다른 성격이지만, 상호 존중을 통해 좋은 관계를 맺을 수 있을 것 같아요!"
}
```

---

## 4. 프롬프트 튜닝 가이드

### 4.1 Agent 발화 품질 개선

**문제 상황별 해결책**:

| 문제 | 원인 | 해결책 |
|------|------|--------|
| 너무 긴 답변 | max_tokens 설정 부족 | max_tokens를 100-150으로 제한 |
| 반복적인 표현 | frequency_penalty 낮음 | frequency_penalty를 0.3-0.5로 증가 |
| 부자연스러운 말투 | 페르소나 정보 부족 | 사용자에게 더 상세한 페르소나 요청 |
| AI임을 밝힘 | System Prompt 강조 부족 | "절대 AI임을 밝히지 마세요" 강조 추가 |
| 질문이 없음 | System Prompt 규칙 미준수 | "상대방에게 질문을 포함" 규칙 강조 |

### 4.2 케미 분석 정확도 개선

**점수 분포 조정**:
- 너무 높은 점수 (90점 이상): temperature 낮추기 (0.2-0.3)
- 너무 낮은 점수 (40점 미만): 프롬프트에 "긍정적인 면도 고려" 추가
- 일관성 부족: temperature를 0.1로 고정

**분석 기준 세분화**:
```python
DETAILED_CHEMISTRY_PROMPT = """
...

**평가 기준 (각 20점 만점):**
1. 대화 흐름 (20점): 티키타카, 끊김 없는 대화
2. 공통점 (20점): 관심사, 가치관, 취미
3. 호감도 (20점): 서로에게 보이는 관심과 긍정적 반응
4. 말투 조화 (20점): 존댓말/반말, 이모티콘 사용 등
5. 깊이 (20점): 표면적 대화 vs 깊이 있는 대화

총점을 100점 만점으로 환산하세요.
"""
```

---

# Part 2: 개발 환경 가이드

## 1. 필요한 도구 및 버전

### 1.1 필수 도구

| 도구 | 최소 버전 | 권장 버전 | 용도 |
|------|----------|----------|------|
| Python | 3.11 | 3.11+ | 백엔드 런타임 |
| Docker | 20.10 | 최신 | 컨테이너화 |
| Docker Compose | 2.0 | 최신 | 오케스트레이션 |
| Git | 2.30 | 최신 | 버전 관리 |

### 1.2 Python 패키지

```txt
# requirements.txt

# FastAPI 및 서버
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6

# 데이터베이스
sqlalchemy==2.0.25
alembic==1.13.1  # (향후 마이그레이션용)

# LLM (Upstage Solar — OpenAI 호환 SDK 재사용)
openai==1.30.0

# 환경 변수
python-dotenv==1.0.0
pydantic-settings==2.1.0

# 유틸리티
python-dateutil==2.8.2

# 개발 도구 (선택적)
pytest==7.4.4
httpx==0.26.0  # FastAPI 테스트용
black==23.12.1  # 코드 포맷팅
isort==5.13.2   # import 정렬
```

---

## 2. 프로젝트 설치 및 초기화

### 2.1 저장소 클론

```bash
git clone <repository-url>
cd llm-blind-date/backend
```

### 2.2 환경 변수 설정

```bash
# .env.example 복사
cp .env.example .env

# .env 파일 편집
nano .env
```

**.env 파일 내용**:
```env
# Application
DEBUG=true
APP_NAME=Multi-Agent Dating Platform API
APP_VERSION=1.0.0

# Database
DATABASE_URL=sqlite:///./data/app.db

# Upstage Solar LLM
UPSTAGE_API_KEY=up_...your-upstage-key...
UPSTAGE_BASE_URL=https://api.upstage.ai/v1
SOLAR_MODEL=solar-pro2

# CORS
CORS_ORIGINS=http://localhost:3000
```

**주의**: `UPSTAGE_API_KEY`는 https://console.upstage.ai 에서 발급받으세요. OpenAI 키는 사용하지 않습니다.

### 2.3 로컬 개발 환경 (Python 가상환경)

```bash
# Python 가상환경 생성
python3.11 -m venv venv

# 가상환경 활성화
source venv/bin/activate  # macOS/Linux
# venv\Scripts\activate  # Windows

# 의존성 설치
pip install -r requirements.txt

# 데이터베이스 초기화
python scripts/init_db.py

# 시드 데이터 삽입
python scripts/seed_db.py

# 서버 실행
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**서버 접속**:
- API: http://localhost:8000
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 2.4 Docker Compose 환경 (권장)

```bash
# Docker Compose 빌드 및 실행
docker-compose up --build

# 또는 백그라운드 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f backend

# 컨테이너 접속
docker-compose exec backend bash

# 중지
docker-compose down

# 볼륨까지 삭제 (데이터 초기화)
docker-compose down -v
```

---

## 3. 데이터베이스 초기화 스크립트

### 3.1 `scripts/init_db.py`

```python
#!/usr/bin/env python3
"""
데이터베이스 초기화 스크립트
모든 테이블을 생성합니다.
"""

import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from app.models import Base
from app.core.config import settings

def init_database():
    """데이터베이스 생성 및 테이블 초기화"""
    print("데이터베이스 초기화 시작...")

    # 엔진 생성
    engine = create_engine(settings.DATABASE_URL, echo=True)

    # 모든 테이블 생성
    Base.metadata.create_all(engine)

    print("✅ 데이터베이스 초기화 완료!")

if __name__ == "__main__":
    init_database()
```

### 3.2 `scripts/seed_db.py`

```python
#!/usr/bin/env python3
"""
시드 데이터 삽입 스크립트
개발용 목 데이터를 생성합니다.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models.agent import Agent
from app.core.config import settings
import uuid
from datetime import datetime, timezone

def seed_database():
    """시드 데이터 삽입"""
    print("시드 데이터 삽입 시작...")

    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        # 기존 Agent 확인
        existing_count = db.query(Agent).count()
        if existing_count > 0:
            print(f"⚠️  이미 {existing_count}개의 Agent가 존재합니다. 시드 스킵.")
            return

        # 시드 데이터
        seed_agents = [
            {
                "persona_text": "저는 28세 개발자입니다. 주로 웹 개발을 하고 있고, 주말에는 등산을 좋아합니다. 조용하고 신중한 성격이지만, 친해지면 유머러스한 면도 있습니다.",
                "system_prompt": "당신은 28세 개발자입니다. 웹 개발과 등산을 좋아합니다. 2-3문장으로 답변하고 질문을 포함하세요."
            },
            {
                "persona_text": "저는 25세 디자이너입니다. UI/UX 디자인을 전문으로 하고, 주말에는 사진 찍기를 좋아합니다. 외향적이고 활발한 성격이며, 새로운 사람 만나는 것을 좋아합니다.",
                "system_prompt": "당신은 25세 디자이너입니다. UI/UX와 사진을 좋아합니다. 2-3문장으로 답변하고 질문을 포함하세요."
            },
            {
                "persona_text": "저는 30세 마케터입니다. 브랜드 마케팅을 담당하고 있고, 독서와 영화 감상을 좋아합니다. 차분하고 분석적인 성격이며, 깊이 있는 대화를 선호합니다.",
                "system_prompt": "당신은 30세 마케터입니다. 브랜드 마케팅, 독서, 영화를 좋아합니다. 2-3문장으로 답변하고 질문을 포함하세요."
            }
        ]

        for data in seed_agents:
            agent = Agent(
                id=str(uuid.uuid4()),
                persona_text=data["persona_text"],
                system_prompt=data["system_prompt"],
                created_at=datetime.now(timezone.utc).isoformat()
            )
            db.add(agent)

        db.commit()
        print(f"✅ {len(seed_agents)}개의 시드 Agent 생성 완료!")

    except Exception as e:
        db.rollback()
        print(f"❌ 시드 데이터 삽입 실패: {str(e)}")
        raise
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
```

---

## 4. 서버 실행 방법

### 4.1 개발 모드 (핫 리로드)

```bash
# 로컬 환경
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Docker Compose
docker-compose up
```

### 4.2 프로덕션 모드 (향후)

```bash
# Gunicorn + Uvicorn workers
gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000
```

---

## 5. API 테스트

### 5.1 Swagger UI (권장)

브라우저에서 http://localhost:8000/docs 접속하여 대화형 API 문서 사용

### 5.2 cURL

```bash
# Agent 생성
curl -X POST http://localhost:8000/api/agents \
  -H "Content-Type: application/json" \
  -d '{
    "persona_text": "저는 28세 개발자입니다. 웹 개발을 하고, 등산을 좋아합니다. 조용하고 신중한 성격이지만, 친해지면 유머러스한 면도 있습니다."
  }'

# Agent 목록 조회
curl http://localhost:8000/api/agents

# 헬스체크
curl http://localhost:8000/health
```

### 5.3 Python (httpx)

```python
import httpx

async def test_create_agent():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/agents",
            json={
                "persona_text": "저는 28세 개발자입니다. " * 10
            }
        )
        print(response.json())
```

---

## 6. 테스트 실행

### 6.1 pytest 설정

```bash
# 테스트 실행
pytest

# 상세 출력
pytest -v

# 커버리지 확인 (선택적)
pip install pytest-cov
pytest --cov=app
```

### 6.2 테스트 예시

```python
# tests/test_agents.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_create_agent_success():
    """Agent 생성 성공 테스트"""
    response = client.post("/api/agents", json={
        "persona_text": "저는 28세 개발자입니다. " * 10
    })
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert "system_prompt" in data

def test_create_agent_too_short():
    """페르소나 텍스트가 너무 짧을 때"""
    response = client.post("/api/agents", json={
        "persona_text": "짧은 텍스트"
    })
    assert response.status_code == 400
    assert "50자 이상" in response.json()["detail"]
```

---

## 7. 문제 해결 (Troubleshooting)

### 7.1 일반적인 문제

**문제: `ImportError: cannot import name 'X'`**
- 해결: 가상환경 재생성 또는 의존성 재설치
  ```bash
  rm -rf venv
  python3.11 -m venv venv
  source venv/bin/activate
  pip install -r requirements.txt
  ```

**문제: `UPSTAGE_API_KEY 가 설정되지 않았습니다`**
- 해결: `.env` 파일에 API 키 확인
  ```bash
  cat .env | grep UPSTAGE_API_KEY
  ```

**문제: SQLite 데이터베이스 잠김**
- 해결: 서버 재시작 또는 DB 파일 삭제 후 재생성
  ```bash
  rm app.db
  python scripts/init_db.py
  ```

**문제: Docker Compose 빌드 실패**
- 해결: 캐시 삭제 후 재빌드
  ```bash
  docker-compose down
  docker-compose build --no-cache
  docker-compose up
  ```

### 7.2 로그 확인

```bash
# 로컬 환경
# uvicorn 콘솔 출력 확인

# Docker Compose
docker-compose logs -f backend
```

---

## 8. 코드 품질 도구 (선택적)

### 8.1 Black (자동 포맷팅)

```bash
# 설치
pip install black

# 전체 프로젝트 포맷팅
black app/

# 확인만 (실제 변경 안 함)
black --check app/
```

### 8.2 isort (import 정렬)

```bash
# 설치
pip install isort

# 실행
isort app/
```

### 8.3 pre-commit hook 설정 (선택적)

```bash
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.12.1
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    rev: 5.13.2
    hooks:
      - id: isort
```

---

## 9. 배포 준비 (향후)

### 9.1 환경 변수 보안
- `.env` 파일을 git에 커밋하지 않기 (`.gitignore`에 추가)
- 프로덕션 환경에서는 환경 변수 또는 시크릿 관리 서비스 사용

### 9.2 로그 설정
- 프로덕션에서는 파일 로그 또는 로그 수집 서비스 (Sentry 등) 사용

### 9.3 성능 최적화
- Gunicorn + Uvicorn workers 사용
- PostgreSQL 전환 (SQLite는 프로덕션 부적합)
- 캐싱 (Redis) 도입

---

**문서 버전**: 1.0.0
**최종 수정일**: 2026-05-07
**작성자**: 백엔드팀
