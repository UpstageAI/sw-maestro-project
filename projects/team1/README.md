# Team 1: AI 기반 뉴스 요약 서비스

## 프로젝트 개요
AI를 활용하여 실시간 뉴스 기사를 자동으로 요약해주는 웹 서비스입니다.

## 팀원
- 김민수 (팀장) - 백엔드
- 이지은 - 프론트엔드
- 박준혁 - AI/ML

## 기술 스택
- **Backend**: Python, FastAPI
- **Frontend**: React, TypeScript
- **AI**: Solar API (Upstage)
- **Database**: PostgreSQL
- **Deployment**: Docker, AWS EC2

## 주요 기능
1. 뉴스 크롤링 및 실시간 수집
2. AI 기반 기사 요약 (Solar API 활용)
3. 카테고리별 뉴스 분류
4. 사용자 맞춤 뉴스 추천

## 실행 방법
```bash
# 백엔드
cd backend
pip install -r requirements.txt
uvicorn main:app --reload

# 프론트엔드
cd frontend
npm install
npm run dev
```

## 프로젝트 구조
```
team1/
├── backend/
│   ├── main.py
│   ├── requirements.txt
│   └── services/
│       └── summarizer.py
├── frontend/
│   ├── package.json
│   └── src/
│       └── App.tsx
└── README.md
```
