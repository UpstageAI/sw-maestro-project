# Backend README

Backend 담당자와 AI 코딩 도구는 이 폴더에서 FastAPI 서버와 Agent 파이프라인을 구현합니다.

## 목표

- `/health`로 서버 상태를 확인합니다.
- `/api/generate`로 특허 명세서 JSON을 생성합니다.
- LLM/search 실패 시 데모가 멈추지 않도록 fallback을 반환합니다.

## 추천 스택

- Python 3.11
- FastAPI
- Pydantic
- OpenAI 또는 Anthropic SDK
- Tavily SDK 또는 search fallback
- WeasyPrint는 후순위

## 최소 엔드포인트

```text
GET /health
POST /api/generate
```

## 구현 우선순위

1. `examples/sample_response.json`을 반환하는 mock API
2. 입력 검증
3. LLM 호출 연결
4. 검색/RAG 연결
5. PDF 또는 HTML print fallback

## Tools

backend Agent가 쓰는 외부 검색/RAG 도구는 `backend/app/tools/`에 둡니다.
특히 KIPRIS 특허 검색 도구를 수정하거나 연결할 때는 `backend/app/tools/README.md`를 먼저 읽습니다.

## AI에게 요청할 때

```text
backend/README.md, docs/API_CONTRACT.md, prompts/system_prompt.md를 읽고
FastAPI로 /health와 /api/generate를 구현해줘.
처음에는 examples/sample_response.json과 같은 구조를 반환하는 mock/fallback부터 만들어줘.
```

## 실행

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## 테스트

repo 루트에서 실행합니다.

```bash
python -m unittest discover -s backend/tests -t .
```
