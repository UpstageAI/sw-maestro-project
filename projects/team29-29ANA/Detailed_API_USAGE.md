# AI 면접 코치 FastAPI Orchestration API 사용 설명서

## 1. 개요

이 API는 AI 면접 코치 프로젝트의 백엔드 orchestration API입니다.  
작업을 시작한 뒤 `job_id`를 받아 `GET /api/jobs/{job_id}`를 주기적으로 polling합니다.

주요 흐름은 다음과 같습니다.

```text
1. PDF + 채용공고로 세션 생성 요청
2. API가 job_id 반환
3. 프론트가 /api/jobs/{job_id} polling
4. 첫 질문 수신
5. 사용자가 답변 제출
6. 답변 평가 job polling
7. 다음 질문 또는 리포트 가능 여부 수신
8. 리포트 생성 요청
9. 리포트 job polling 후 최종 report 표시
```

## 2. 기본 정보

| 항목 | 값 |
|---|---|
| Base URL | `http://localhost:8000` |
| API 문서 | `http://localhost:8000/docs` |
| 기본 응답 형식 | JSON |
| 파일 업로드 형식 | `multipart/form-data` |
| 답변/리포트 요청 형식 | `application/json` |
| 인증 | 현재 없음 |

## 3. 공통 Job 응답 구조

시간이 걸리는 API는 즉시 최종 결과를 반환하지 않고 `202 Accepted`와 함께 `job_id`를 반환합니다.

### Job 시작 응답

```json
{
  "job_id": "4208424a273943baa6456ba45b5f4496",
  "session_id": "365dcb5fc5d64c698a0f0ed6702f6d8e",
  "status_url": "/api/jobs/4208424a273943baa6456ba45b5f4496",
  "message": "리포트 생성 작업을 시작했습니다. status_url을 polling하세요."
}
```

| 필드 | 타입 | 설명 |
|---|---|---|
| `job_id` | string | 작업 ID |
| `session_id` | string \| null | 연결된 세션 ID |
| `status_url` | string | polling할 URL |
| `message` | string | 사용자 표시용 메시지 |

### Job 상태 응답

`GET /api/jobs/{job_id}` 응답입니다.

```json
{
  "job_id": "4208424a273943baa6456ba45b5f4496",
  "job_type": "generate_report",
  "session_id": "365dcb5fc5d64c698a0f0ed6702f6d8e",
  "status": "succeeded",
  "step": "done",
  "progress": 100,
  "message": "작업이 완료되었습니다.",
  "result": {},
  "error": null,
  "created_at": "2026-05-08T18:15:17.528864+00:00",
  "updated_at": "2026-05-08T18:15:23.463384+00:00"
}
```

| 필드 | 타입 | 설명 |
|---|---|---|
| `job_id` | string | 작업 ID |
| `job_type` | string | `start_session`, `process_answer`, `generate_report` 중 하나 |
| `session_id` | string \| null | 세션 ID |
| `status` | string | `queued`, `running`, `succeeded`, `failed` |
| `step` | string | 현재 처리 단계 |
| `progress` | number | 0~100 진행률 |
| `message` | string | 로딩바에 표시할 메시지 |
| `result` | object \| null | 완료 시 결과 데이터 |
| `error` | string \| null | 실패 시 에러 메시지 |
| `created_at` | string | 작업 생성 시각, ISO format |
| `updated_at` | string | 마지막 업데이트 시각, ISO format |

## 4. 공통 데이터 타입

### Question

```json
{
  "id": "3b443ede-9880-4999-bf1d-dcf4212bc865",
  "text": "PyTorch와 TensorFlow를 비교해본 경험을 설명해주세요.",
  "category": "역량",
  "difficulty": 3,
  "is_followup": false,
  "parent_id": null
}
```

| 필드 | 타입 | 설명 |
|---|---|---|
| `id` | string | 질문 ID |
| `text` | string | 질문 본문 |
| `category` | string | `역량`, `경험`, `문제해결`, `협업`, `적합성` |
| `difficulty` | number | 난이도, 1~5 |
| `is_followup` | boolean | 꼬리질문 여부 |
| `parent_id` | string \| null | 꼬리질문일 경우 부모 질문 ID |

### Evaluation

```json
{
  "question": {},
  "user_answer": "사용자 답변 내용",
  "star_score": 4,
  "specificity_score": 4,
  "relevance_score": 4,
  "consistency_score": 4,
  "weakness_tags": ["정량 지표 부족", "기술 깊이 부족"],
  "feedback": "{...}",
  "feedback_json": {}
}
```

| 필드 | 타입 | 설명 |
|---|---|---|
| `question` | Question | 평가 대상 질문 |
| `user_answer` | string | 사용자 답변 |
| `star_score` | number | STAR 구조 점수, 1~5 |
| `specificity_score` | number | 구체성 점수, 1~5 |
| `relevance_score` | number | 직무 관련성 점수, 1~5 |
| `consistency_score` | number | 일관성 점수, 1~5 |
| `weakness_tags` | string[] | 약점 태그 목록 |
| `feedback` | string | evaluator가 만든 JSON 문자열 |
| `feedback_json` | object \| null | `feedback` 파싱 결과 |

### Session Summary

```json
{
  "session_id": "365dcb5fc5d64c698a0f0ed6702f6d8e",
  "status": "active",
  "is_active": true,
  "busy_job_id": null,
  "question_count": 5,
  "bundle_count": 3,
  "current_followup_depth": 0,
  "max_followup_depth": 3,
  "min_bundles_for_report": 3,
  "can_report": true,
  "job_family": "engineering",
  "current_question": {}
}
```

| 필드 | 타입 | 설명 |
|---|---|---|
| `session_id` | string | 세션 ID |
| `status` | string | `initializing`, `active`, `ended` |
| `is_active` | boolean | 세션 진행 여부 |
| `busy_job_id` | string \| null | 현재 진행 중인 job ID |
| `question_count` | number | 답변 완료된 전체 질문 수 |
| `bundle_count` | number | 완료된 메인 질문 묶음 수 |
| `current_followup_depth` | number | 현재 묶음의 꼬리질문 깊이 |
| `max_followup_depth` | number | 최대 꼬리질문 수 |
| `min_bundles_for_report` | number | 리포트 생성 최소 묶음 수 |
| `can_report` | boolean | 리포트 생성 가능 여부 |
| `job_family` | string | JD 기반 직무군, 예: `engineering` |
| `current_question` | Question \| null | 현재 답변해야 할 질문 |

### Report

```json
{
  "overall_score": 3.7,
  "category_scores": {
    "협업": 4.0,
    "적합성": 3.38,
    "경험": 3.88
  },
  "weakness_summary": [
    "정량 지표 부족",
    "기술 깊이 부족",
    "협업 설명 부족"
  ],
  "improvement_suggestions": "개선 제안 텍스트"
}
```

| 필드 | 타입 | 설명 |
|---|---|---|
| `overall_score` | number | 전체 평균 점수, 1~5 |
| `category_scores` | object | 카테고리별 평균 점수 |
| `weakness_summary` | string[] | 자주 나온 약점 태그 Top 5 |
| `improvement_suggestions` | string | 개선 제안 문장 |

## 5. 엔드포인트 상세

## 5.1 Health Check

서버가 실행 중인지 확인합니다.

```http
GET /health
```

### Request

없음.

### Response 200

```json
{
  "status": "ok"
}
```

---

## 5.2 세션 생성

PDF 파일과 채용공고를 업로드하여 면접 세션을 시작합니다.  
문서 인덱싱과 첫 질문 생성은 오래 걸릴 수 있으므로 job으로 처리됩니다.

```http
POST /api/sessions
Content-Type: multipart/form-data
```

### Request Form Data

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `files` | File[] | 필수 | 자소서/이력서 PDF 파일. 1개 이상 |
| `job_description` | string | 필수 | 채용공고 전문 |
| `company_name` | string | 선택 | 회사명. 비우면 Tavily 검색 생략 |
| `company_culture` | string | 선택 | 사용자가 직접 보강한 회사 문화/인재상 |

### curl 예시

```bash
curl -X POST http://localhost:8000/api/sessions \
  -F "files=@./resume.pdf" \
  -F "job_description=Machine Learning Engineer 채용공고 예시. Python, PyTorch, TensorFlow, scikit-learn 기반 모델 개발 경험을 우대합니다. 추천 시스템, NLP, Computer Vision, MLOps, 모델 배포 경험을 중요하게 봅니다." \
  -F "company_name=" \
  -F "company_culture="
```

### Response 202

```json
{
  "job_id": "8f14e45fceea4a7bbefc0f4a7d7c2e19",
  "session_id": "365dcb5fc5d64c698a0f0ed6702f6d8e",
  "status_url": "/api/jobs/8f14e45fceea4a7bbefc0f4a7d7c2e19",
  "message": "세션 생성 작업을 시작했습니다. status_url을 polling하세요."
}
```

### Polling 성공 결과 예시

`GET /api/jobs/{job_id}`의 `status`가 `succeeded`가 되면 `result`에 세션 정보와 첫 질문이 들어옵니다.

```json
{
  "status": "succeeded",
  "progress": 100,
  "result": {
    "session": {
      "session_id": "365dcb5fc5d64c698a0f0ed6702f6d8e",
      "status": "active",
      "is_active": true,
      "busy_job_id": null,
      "question_count": 0,
      "bundle_count": 0,
      "current_followup_depth": 0,
      "max_followup_depth": 3,
      "min_bundles_for_report": 3,
      "can_report": false,
      "job_family": "engineering",
      "current_question": {
        "id": "q-1",
        "text": "첫 질문 내용",
        "category": "역량",
        "difficulty": 3,
        "is_followup": false,
        "parent_id": null
      }
    },
    "question": {
      "id": "q-1",
      "text": "첫 질문 내용",
      "category": "역량",
      "difficulty": 3,
      "is_followup": false,
      "parent_id": null
    }
  }
}
```

---

## 5.3 Job 상태 조회

작업 진행률과 결과를 조회합니다. 프론트 loading bar는 이 API를 polling해서 표시합니다.

```http
GET /api/jobs/{job_id}
```

### Path Parameters

| 이름 | 타입 | 설명 |
|---|---|---|
| `job_id` | string | 조회할 job ID |

### Response 200 - running

```json
{
  "job_id": "8f14e45fceea4a7bbefc0f4a7d7c2e19",
  "job_type": "start_session",
  "session_id": "365dcb5fc5d64c698a0f0ed6702f6d8e",
  "status": "running",
  "step": "indexing_documents",
  "progress": 10,
  "message": "PDF 문서를 파싱하고 ChromaDB에 인덱싱하는 중입니다.",
  "result": null,
  "error": null,
  "created_at": "2026-05-08T18:15:17.528864+00:00",
  "updated_at": "2026-05-08T18:15:18.528864+00:00"
}
```

### Response 200 - failed

```json
{
  "job_id": "8f14e45fceea4a7bbefc0f4a7d7c2e19",
  "job_type": "start_session",
  "session_id": "365dcb5fc5d64c698a0f0ed6702f6d8e",
  "status": "failed",
  "step": "failed",
  "progress": 100,
  "message": "작업 중 오류가 발생했습니다.",
  "result": null,
  "error": "에러 메시지와 traceback",
  "created_at": "2026-05-08T18:15:17.528864+00:00",
  "updated_at": "2026-05-08T18:15:23.528864+00:00"
}
```

---

## 5.4 세션 상태 조회

현재 세션 상태와 현재 질문을 조회합니다.

```http
GET /api/sessions/{session_id}
```

### Path Parameters

| 이름 | 타입 | 설명 |
|---|---|---|
| `session_id` | string | 세션 ID |

### Response 200

```json
{
  "session_id": "365dcb5fc5d64c698a0f0ed6702f6d8e",
  "status": "active",
  "is_active": true,
  "busy_job_id": null,
  "question_count": 5,
  "bundle_count": 3,
  "current_followup_depth": 0,
  "max_followup_depth": 3,
  "min_bundles_for_report": 3,
  "can_report": true,
  "job_family": "engineering",
  "current_question": {
    "id": "3b443ede-9880-4999-bf1d-dcf4212bc865",
    "text": "PyTorch와 TensorFlow 둘 다 사용해본 경험이 있는 걸로 보이는데, 두 프레임워크를 비교하면서 어떤 상황에서 어떤 도구를 선택했는지 구체적인 사례를 하나 들려주실 수 있나요?",
    "category": "역량",
    "difficulty": 3,
    "is_followup": false,
    "parent_id": null
  }
}
```

---

## 5.5 답변 제출

현재 질문에 대한 사용자 답변을 제출합니다.  
답변 평가와 다음 질문 생성은 job으로 처리됩니다.

```http
POST /api/sessions/{session_id}/answers
Content-Type: application/json
```

### Path Parameters

| 이름 | 타입 | 설명 |
|---|---|---|
| `session_id` | string | 세션 ID |

### Request Body

```json
{
  "question_id": "3b443ede-9880-4999-bf1d-dcf4212bc865",
  "answer": "저는 머신러닝 프로젝트에서 데이터 불균형 문제를 해결한 경험이 있습니다..."
}
```

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `answer` | string | 필수 | 사용자 답변. 최소 1자. 단, 50자 이하면 retry action 반환 |
| `question_id` | string \| null | 선택 | 프론트가 보고 있는 현재 질문 ID. 불일치하면 409 반환 |

### Response 202

```json
{
  "job_id": "2dc6cd12200b4021a1813a5f2037fb",
  "session_id": "365dcb5fc5d64c698a0f0ed6702f6d8e",
  "status_url": "/api/jobs/2dc6cd12200b4021a1813a5f2037fb",
  "message": "답변 평가 작업을 시작했습니다. status_url을 polling하세요."
}
```

### Polling 성공 결과 예시 - 다음 질문

```json
{
  "status": "succeeded",
  "result": {
    "action": "next_question",
    "evaluation": {
      "question": {},
      "user_answer": "사용자 답변",
      "star_score": 4,
      "specificity_score": 4,
      "relevance_score": 4,
      "consistency_score": 4,
      "weakness_tags": [],
      "feedback": "{...}",
      "feedback_json": {}
    },
    "question": {
      "id": "next-question-id",
      "text": "다음 질문 내용",
      "category": "경험",
      "difficulty": 3,
      "is_followup": false,
      "parent_id": null
    },
    "can_report": false,
    "session": {}
  }
}
```

### Polling 성공 결과 예시 - 꼬리질문

```json
{
  "status": "succeeded",
  "result": {
    "action": "followup",
    "evaluation": {
      "star_score": 3,
      "specificity_score": 2,
      "relevance_score": 4,
      "consistency_score": 4,
      "weakness_tags": ["정량 지표 부족", "행동 구체성 부족"]
    },
    "question": {
      "id": "followup-question-id",
      "text": "그 결과를 수치로 설명할 수 있나요?",
      "category": "경험",
      "difficulty": 3,
      "is_followup": true,
      "parent_id": "parent-question-id"
    },
    "can_report": false,
    "session": {}
  }
}
```

### Polling 성공 결과 예시 - 리포트 가능

```json
{
  "status": "succeeded",
  "result": {
    "action": "can_report",
    "evaluation": {
      "star_score": 4,
      "specificity_score": 4,
      "relevance_score": 4,
      "consistency_score": 4,
      "weakness_tags": []
    },
    "question": {
      "id": "next-question-id",
      "text": "다음 질문 내용",
      "category": "역량",
      "difficulty": 3,
      "is_followup": false,
      "parent_id": null
    },
    "can_report": true,
    "session": {
      "can_report": true,
      "question_count": 5,
      "bundle_count": 3
    }
  }
}
```

### Polling 성공 결과 예시 - 답변이 너무 짧음

답변이 50자 이하이면 평가하지 않고 같은 질문에 다시 답변하도록 유도합니다.

```json
{
  "status": "succeeded",
  "result": {
    "action": "retry",
    "message": "답변이 너무 짧습니다. 50자 이상으로 더 구체적으로 답해주세요.",
    "question": {
      "id": "current-question-id",
      "text": "현재 질문 내용",
      "category": "역량",
      "difficulty": 3,
      "is_followup": false,
      "parent_id": null
    }
  }
}
```

---

## 5.6 히스토리 조회

현재까지 평가된 질문/답변/평가 결과를 조회합니다.

```http
GET /api/sessions/{session_id}/history
```

### Path Parameters

| 이름 | 타입 | 설명 |
|---|---|---|
| `session_id` | string | 세션 ID |

### Response 200

```json
{
  "session_id": "365dcb5fc5d64c698a0f0ed6702f6d8e",
  "count": 2,
  "history": [
    {
      "question": {
        "id": "q-1",
        "text": "질문 내용",
        "category": "경험",
        "difficulty": 3,
        "is_followup": false,
        "parent_id": null
      },
      "evaluation": {
        "question": {},
        "user_answer": "사용자 답변",
        "star_score": 4,
        "specificity_score": 4,
        "relevance_score": 5,
        "consistency_score": 4,
        "weakness_tags": ["정량 지표 부족"],
        "feedback": "{...}",
        "feedback_json": {}
      }
    }
  ]
}
```

---

## 5.7 리포트 생성

현재까지의 평가 결과를 바탕으로 종합 리포트를 생성합니다.

```http
POST /api/sessions/{session_id}/report
Content-Type: application/json
```

### Path Parameters

| 이름 | 타입 | 설명 |
|---|---|---|
| `session_id` | string | 세션 ID |

### Request Body

```json
{
  "force": true
}
```

| 필드 | 타입 | 필수 | 설명 |
|---|---|---|---|
| `force` | boolean | 선택 | `true`면 최소 묶음 수 조건을 만족하지 않아도 현재 history로 리포트 생성. 기본값 `false` |

### Response 202

```json
{
  "job_id": "4208424a273943baa6456ba45b5f4496",
  "session_id": "365dcb5fc5d64c698a0f0ed6702f6d8e",
  "status_url": "/api/jobs/4208424a273943baa6456ba45b5f4496",
  "message": "리포트 생성 작업을 시작했습니다. status_url을 polling하세요."
}
```

### Polling 성공 결과 예시

```json
{
  "job_id": "4208424a273943baa6456ba45b5f4496",
  "job_type": "generate_report",
  "session_id": "365dcb5fc5d64c698a0f0ed6702f6d8e",
  "status": "succeeded",
  "step": "done",
  "progress": 100,
  "message": "작업이 완료되었습니다.",
  "result": {
    "session": {
      "session_id": "365dcb5fc5d64c698a0f0ed6702f6d8e",
      "status": "ended",
      "is_active": false,
      "busy_job_id": null,
      "question_count": 5,
      "bundle_count": 3,
      "can_report": true,
      "job_family": "engineering",
      "current_question": {}
    },
    "report": {
      "overall_score": 3.7,
      "category_scores": {
        "협업": 4.0,
        "적합성": 3.38,
        "경험": 3.88
      },
      "weakness_summary": [
        "정량 지표 부족",
        "기술 깊이 부족",
        "협업 설명 부족",
        "행동 구체성 부족",
        "근거 부족"
      ],
      "improvement_suggestions": "MLOps 관점에서 모델 모니터링 및 재학습 파이프라인을 설명할 때는..."
    }
  },
  "error": null,
  "created_at": "2026-05-08T18:15:17.528864+00:00",
  "updated_at": "2026-05-08T18:15:23.463384+00:00"
}
```

주의: 리포트를 생성하면 세션의 `status`가 `ended`, `is_active`가 `false`가 됩니다. 같은 세션으로 면접을 계속 진행하지 않는 것을 권장합니다.

---

## 5.8 세션 삭제

데모용 세션 데이터와 업로드 파일을 삭제합니다.

```http
DELETE /api/sessions/{session_id}
```

### Path Parameters

| 이름 | 타입 | 설명 |
|---|---|---|
| `session_id` | string | 세션 ID |

### Response 200

```json
{
  "status": "deleted",
  "session_id": "365dcb5fc5d64c698a0f0ed6702f6d8e"
}
```

## 6. 주요 에러 응답

FastAPI 기본 에러 포맷은 아래 형태입니다.

```json
{
  "detail": "에러 메시지"
}
```

또는 상세 정보가 object로 올 수 있습니다.

```json
{
  "detail": {
    "message": "이미 진행 중인 작업이 있습니다.",
    "busy_job_id": "abc123",
    "status_url": "/api/jobs/abc123"
  }
}
```

| HTTP Status | 발생 상황 | 대응 |
|---|---|---|
| 400 | PDF가 아닌 파일 업로드, 파일 없음 | 파일 형식 확인 |
| 404 | 존재하지 않는 `job_id` 또는 `session_id` | ID 확인 |
| 409 | 세션 초기화 전 접근 | 세션 생성 job polling 완료 후 재요청 |
| 409 | 이미 진행 중인 job 있음 | `busy_job_id` polling 완료 후 재요청 |
| 409 | 요청 `question_id`와 현재 질문 ID 불일치 | 최신 세션 상태 조회 후 현재 질문 ID로 재요청 |
| 409 | `force=false`인데 최소 묶음 수 미달 | 계속 질문 진행하거나 `force=true`로 요청 |
| 422 | JSON/body/form 필드 누락 또는 타입 불일치 | request body 확인 |

## 7. Loading Bar 표시 기준

`GET /api/jobs/{job_id}` 응답의 아래 필드를 사용합니다.

```json
{
  "status": "running",
  "step": "evaluating_answer",
  "progress": 20,
  "message": "답변을 STAR·구체성·직무 관련성·일관성 기준으로 평가하는 중입니다."
}
```

| 필드 | 프론트 사용법 |
|---|---|
| `status` | `running`이면 로딩 표시, `succeeded`면 결과 화면, `failed`면 에러 화면 |
| `progress` | loading bar width 값으로 사용 |
| `message` | loading bar 하단/상단 안내 문구 |
| `step` | 개발자 디버깅 또는 세부 상태 표시 |

현재 progress는 실제 초 단위 진행률이 아니라 단계별 진행률입니다.  
더 부드러운 UI가 필요하면 프론트에서 `running` 상태일 때 90%까지만 가짜 진행률을 보정하고, `succeeded`가 오면 100%로 채우면 됩니다.

## 10. 실행 예시 요약

```bash
# 서버 실행
uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

# Health check
curl http://localhost:8000/health

# 세션 생성
curl -X POST http://localhost:8000/api/sessions \
  -F "files=@./resume.pdf" \
  -F "job_description=Machine Learning Engineer 채용공고 예시. Python, PyTorch, MLOps 경험을 우대합니다." \
  -F "company_name=" \
  -F "company_culture="

# Job polling
curl http://localhost:8000/api/jobs/{job_id}

# 답변 제출
curl -X POST http://localhost:8000/api/sessions/{session_id}/answers \
  -H "Content-Type: application/json" \
  -d '{"question_id":"{question_id}","answer":"50자 이상의 답변을 입력합니다."}'

# 리포트 생성
curl -X POST http://localhost:8000/api/sessions/{session_id}/report \
  -H "Content-Type: application/json" \
  -d '{"force":true}'
```
