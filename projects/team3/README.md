# Team 3: 학습 도우미 챗봇

## 프로젝트 개요
학생들이 교재 PDF를 업로드하면 내용을 기반으로 질의응답이 가능한 AI 학습 도우미 챗봇입니다.

## 팀원
- 윤재호 (팀장) - AI/ML
- 김하은 - 백엔드
- 이동훈 - 프론트엔드

## 기술 스택
- **Backend**: Python, Flask
- **Frontend**: Streamlit
- **AI**: Upstage Solar API, Document Parse
- **Vector DB**: ChromaDB
- **Deployment**: Streamlit Cloud

## 주요 기능
1. PDF 교재 업로드 및 파싱 (Upstage Document Parse)
2. 문서 임베딩 및 벡터 검색
3. RAG 기반 질의응답 챗봇
4. 학습 히스토리 관리

## 실행 방법
```bash
pip install -r requirements.txt
streamlit run app.py
```

## 프로젝트 구조
```
team3/
├── app.py
├── requirements.txt
├── utils/
│   ├── document_parser.py
│   └── rag_chain.py
└── README.md
```
