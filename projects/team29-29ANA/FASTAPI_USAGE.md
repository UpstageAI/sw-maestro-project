# FastAPI Orchestration API 실행/연동 가이드

## 1. 실행

```bash
cd Coach
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

export UPSTAGE_API_KEY="YOUR_KEY"
export SOLAR_BASE_URL="https://api.upstage.ai/v1"
export LLM_MODEL="solar-pro3"
# 회사 검색을 쓸 때만 필요
export TAVILY_API_KEY="YOUR_KEY"

uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

API 문서는 브라우저에서 확인할 수 있습니다.

```text
http://localhost:8000/docs
```

## 2. 프론트엔드 polling 흐름

모든 오래 걸리는 작업은 `202 Accepted`와 함께 `job_id`, `status_url`을 반환합니다.
프론트는 `status_url`을 1~2초 주기로 polling합니다.

```ts
async function pollJob(statusUrl: string) {
  while (true) {
    const res = await fetch(`http://localhost:8000${statusUrl}`);
    const job = await res.json();

    // loading bar
    console.log(job.progress, job.step, job.message);

    if (job.status === "succeeded") return job.result;
    if (job.status === "failed") throw new Error(job.error ?? "job failed");

    await new Promise((resolve) => setTimeout(resolve, 1500));
  }
}
```

## 3. 세션 시작

```bash
curl -X POST http://localhost:8000/api/sessions \
  -F "files=@./resume.pdf" \
  -F "job_description=Machine Learning Engineer 채용공고 ..." \
  -F "company_name="
```

응답 예시:

```json
{
  "job_id": "...",
  "session_id": "...",
  "status_url": "/api/jobs/...",
  "message": "세션 생성 작업을 시작했습니다. status_url을 polling하세요."
}
```

`GET /api/jobs/{job_id}`가 `succeeded`가 되면 `result.question`에 첫 질문이 들어 있습니다.

## 4. 답변 제출

```bash
curl -X POST http://localhost:8000/api/sessions/{session_id}/answers \
  -H "Content-Type: application/json" \
  -d '{"question_id":"현재_질문_id", "answer":"50자 이상의 답변 ..."}'
```

완료 결과의 `action` 값:

| action | 의미 |
|---|---|
| `retry` | 답변이 50자 미만. 같은 질문에 다시 답변 |
| `followup` | 꼬리질문 생성 |
| `next_question` | 다음 메인 질문 생성 |
| `can_report` | 리포트 생성 가능. 계속 진행하거나 리포트 요청 가능 |
| `force_end` | 최대 질문 수 도달로 리포트 생성 후 종료 |

## 5. 리포트 생성

최소 묶음 수 조건을 만족한 경우:

```bash
curl -X POST http://localhost:8000/api/sessions/{session_id}/report \
  -H "Content-Type: application/json" \
  -d '{"force": false}'
```

중간에 바로 리포트를 보고 싶은 경우:

```bash
curl -X POST http://localhost:8000/api/sessions/{session_id}/report \
  -H "Content-Type: application/json" \
  -d '{"force": true}'
```

## 6. 주요 엔드포인트

| Method | Path | 설명 |
|---|---|---|
| GET | `/health` | 서버 상태 확인 |
| POST | `/api/sessions` | PDF/JD로 면접 세션 시작 |
| GET | `/api/jobs/{job_id}` | polling용 작업 상태 조회 |
| GET | `/api/sessions/{session_id}` | 세션 요약 조회 |
| POST | `/api/sessions/{session_id}/answers` | 답변 제출 및 평가 작업 시작 |
| GET | `/api/sessions/{session_id}/history` | 누적 질문/평가 조회 |
| POST | `/api/sessions/{session_id}/report` | 리포트 생성 |
| DELETE | `/api/sessions/{session_id}` | 세션 업로드 파일 및 메모리 상태 삭제 |
