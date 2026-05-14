# AGENTS.md

이 파일은 Codex, Cursor, ChatGPT, Claude 등 AI 코딩 도구가 이 저장소에서 작업할 때 가장 먼저 읽어야 하는 공통 지시문입니다.

## 프로젝트 요약

`Brainrot Patent`는 황당한 한국어 발명 아이디어를 특허 명세서처럼 보이는 7개 섹션 문서로 변환하는 2주 MVP 데모 프로젝트입니다.

예시 입력:

```text
방구로 가는 자동차
```

예시 출력 방향:

```text
생체 가스 배출 압력을 이용한 친환경 추진 차량
```

이 프로젝트는 실제 특허 출원, 법률 자문, 신규성/진보성 판단을 제공하지 않습니다. 엔터테인먼트와 창작 보조 목적의 데모입니다.

## AI가 반드시 읽을 문서 순서

1. `README.md`
2. `docs/PROJECT_BRIEF.md`
3. `docs/MVP_SCOPE.md`
4. `docs/API_CONTRACT.md`
5. `docs/AI_DEV_RULES.md`
6. `TASKS.md`
7. 본인이 맡은 폴더의 `README.md`

## 절대 바꾸지 말아야 할 것

- API 응답 필드명은 `docs/API_CONTRACT.md`와 맞춥니다.
- MVP 범위를 넘는 로그인, 결제, DB, 다국어 기능을 추가하지 않습니다.
- 실제 법률 서비스처럼 보이는 문구를 추가하지 않습니다.
- 위험 주제의 구체적 제작법을 생성하지 않습니다.
- 한국어 입력/출력 중심으로 구현합니다.
- 발표용 데모 안정성을 기능 수보다 우선합니다.

## 역할별 작업 범위

### 1번 발표/기획

- `docs/**`, `README.md`, `TASKS.md`, `examples/**`를 주로 수정합니다.
- 기능 범위, 발표 흐름, 샘플 입력과 fallback 전략을 관리합니다.

### 2번 Frontend

- `frontend/**`를 주로 수정합니다.
- `docs/API_CONTRACT.md`와 `examples/sample_response.json`을 기준으로 UI를 구현합니다.
- API 필드명을 임의로 바꾸지 않습니다.

### 3번 Backend & Agent

- `backend/**`를 주로 수정합니다.
- `/api/generate`를 `docs/API_CONTRACT.md`에 맞게 구현합니다.
- LLM이나 검색 API 실패 시 `examples/sample_response.json` 형태의 fallback을 제공합니다.

### 4번 AI, RAG

- `prompts/**`, `examples/**`, backend의 AI 관련 모듈을 주로 수정합니다.
- 프롬프트는 JSON 출력 안정성을 최우선으로 설계합니다.
- 출처 URL을 지어내지 않습니다.

### 5번 Playwright

- `tests/**` 또는 `playwright/**`를 주로 수정합니다.
- 발표용 입력 3개가 입력-생성-결과표시 흐름을 통과하는지 확인합니다.

## AI 작업 요청 템플릿

팀원은 AI에게 다음 템플릿을 붙여넣고 작업을 시작합니다.

```text
이 저장소의 AGENTS.md, docs/API_CONTRACT.md, docs/MVP_SCOPE.md, TASKS.md를 먼저 읽어줘.
나는 [Frontend/Backend/AI/RAG/Playwright/기획] 담당이다.
내 작업 범위는 [폴더 또는 파일]이다.

요청:
[구체적인 작업]

제약:
- API contract를 바꾸지 말 것
- MVP 범위를 넘는 기능을 추가하지 말 것
- 변경한 파일과 검증 방법을 마지막에 요약할 것
```

## 작업 완료 기준

AI는 작업을 마치기 전에 다음을 확인해야 합니다.

- 변경이 본인 역할 범위를 벗어나지 않았는가?
- `docs/API_CONTRACT.md`와 충돌하지 않는가?
- 발표용 입력 예시로 동작을 설명할 수 있는가?
- 실패 시 사용자에게 보여줄 에러나 fallback이 있는가?
- 변경 파일 목록과 검증 방법을 팀원에게 설명했는가?

