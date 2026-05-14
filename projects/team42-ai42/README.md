# MeetFlow-AI

> 회의 전사문을 AI로 분석해 요약·결정사항·다음 안건을 자동 추출하는 서비스

---

## 프로젝트 구조

```
team42-ai42/
├── backend/   # FastAPI + LangGraph (Python)
└── frontend/  # Next.js (TypeScript)
```

---

## Tech Stack

| | Technology |
|---|---|
| Backend | FastAPI, LangGraph, Upstage Solar Pro |
| Frontend | Next.js |
| Deployment | Railway (backend) |

---

## 주요 기능

- 회의 전사문 입력 → **핵심 요약 → 결정 사항 → 다음 회의 안건** 순차 분석
- SSE 스트리밍으로 분석 진행 상태 실시간 반환
- LangGraph 기반 파이프라인: `summary → decision → agenda`

---

## 시작하기

### Backend

```bash
cd backend
cp .env.example .env   # UPSTAGE_API_KEY 입력
pip install -r requirements.txt
uvicorn main:app --reload
```

API 문서: `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

앱: `http://localhost:3000`

---

## 배포

- **API Base URL:** `https://meetflow-ai-production.up.railway.app`
- **Swagger UI:** `https://meetflow-ai-production.up.railway.app/docs`
