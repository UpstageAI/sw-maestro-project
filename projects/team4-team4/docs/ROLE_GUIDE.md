# Role Guide

## 1번: 발표, 기획 - 임준현

### 책임

- 전체 서비스 컨셉과 MVP 범위 확정
- 팀 공통 reference 문서 관리
- 발표 스토리와 데모 시나리오 작성
- 기능 욕심이 커질 때 2주 범위로 다시 줄이기

### 산출물

- README 및 docs 문서
- 발표 대본
- 발표용 입력 예시 3개
- 기능 우선순위 표

## 2번: Frontend - 박서연

### 책임

- Next.js 입력/결과 화면 구현
- 생성 중 상태와 에러 상태 구현
- API 응답 JSON을 특허 문서처럼 읽히게 표시

### 받는 입력

- `docs/API_CONTRACT.md`
- 샘플 응답 JSON
- 디자인 톤: 진지한 특허 문서 + 살짝 유머러스한 입력 경험

### 산출물

- 입력 페이지
- 결과 미리보기 페이지 또는 컴포넌트
- API 연결 코드

## 3번: Backend & Agent - 이진중

### 책임

- FastAPI 서버 구현
- `/api/generate` 엔드포인트 구현
- 입력 검증, 에러 응답, fallback 응답 처리
- Agent 파이프라인 연결

### 받는 입력

- `docs/API_CONTRACT.md`
- `docs/PROMPT_GUIDE.md`
- RAG/search 모듈 함수 인터페이스

### 산출물

- FastAPI 서버
- 명세서 생성 API
- `.env.example`

## 4번: AI, RAG - 황현석

### 책임

- 프롬프트 설계
- 특허 문체 few-shot 예시 정리
- 검색 결과를 배경기술에 넣는 방식 설계
- LLM 출력 JSON 구조 안정화

### 받는 입력

- `docs/PROMPT_GUIDE.md`
- 필요한 출력 스키마

### 산출물

- 시스템 프롬프트
- 청구항 생성 프롬프트
- 검색/RAG 요약 함수
- 샘플 입력/출력 3개

## 5번: Playwright - 추웅재

### 책임

- 발표용 사용자 흐름 자동 테스트
- 입력-생성-결과 표시 E2E 테스트
- 데모 직전 regression 확인

### 받는 입력

- 프론트엔드 URL
- 발표용 입력 예시
- 성공 기준

### 산출물

- Playwright 테스트
- 스크린샷 또는 테스트 리포트
- 데모 체크리스트

