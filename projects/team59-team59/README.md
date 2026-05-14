# HWP Editor Chatbot

자연어로 HWPX 문서를 생성/편집하고 다운로드할 수 있는 웹 챗봇 서비스입니다.

## 서비스 구성

| 서비스 | 포트 | 설명 |
|--------|------|------|
| frontend | 3000 | Next.js 채팅 UI |
| backend | 8000 | FastAPI 백엔드 |
| hwpx-mcp | 3001 | HWPX 문서 조작 MCP 서버 |

## 실행 방법

### 1. 환경 변수 설정

```bash
cp .env.example .env
# .env 파일에서 ANTHROPIC_API_KEY를 실제 키로 교체하세요
```

### 2. Docker Compose로 실행

```bash
docker compose up --build
```

세 컨테이너가 모두 healthy 상태가 되면 서비스가 준비됩니다.

- 채팅 UI: http://localhost:3000
- API 서버: http://localhost:8000
- MCP 서버: http://localhost:3001

### 3. 종료

```bash
docker compose down
```

## 로컬 개발

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

## 요구사항

- Docker & Docker Compose
- Anthropic API 키 (Claude API 사용)
