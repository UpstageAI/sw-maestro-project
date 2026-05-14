# Contributing

이 문서는 팀원들이 같은 방식으로 작업하고 충돌을 줄이기 위한 협업 규칙입니다.

## 기본 원칙

- `main` 브랜치는 발표 가능한 상태로 유지합니다.
- 각자 작업은 개인 브랜치에서 진행한 뒤 PR로 합칩니다.
- API 형식은 `docs/API_CONTRACT.md`를 기준으로 합니다.
- 기능을 늘리기보다 데모가 안정적으로 돌아가는 것을 우선합니다.

## 추천 브랜치 이름

| 역할 | 브랜치 예시 |
| --- | --- |
| 발표/기획 | `docs/planning-update` |
| Frontend | `feature/frontend-preview` |
| Backend | `feature/backend-generate-api` |
| AI/RAG | `feature/ai-prompts-rag` |
| Playwright | `test/playwright-demo-flow` |

## 작업 시작 전

```bash
git checkout main
git pull origin main
git checkout -b feature/my-task
```

## 커밋 메시지 예시

```text
Add generate API contract
Implement result preview UI
Tune patent claim prompt
Add demo flow test
```

## PR 규칙

PR에는 다음 내용을 적습니다.

- 무엇을 바꿨는지
- 왜 바꿨는지
- 어떤 입력으로 확인했는지
- 아직 남은 위험이나 TODO가 있는지

## 충돌 방지 규칙

- Frontend 담당자는 가능하면 `frontend/**` 안에서 작업합니다.
- Backend 담당자는 가능하면 `backend/**` 안에서 작업합니다.
- AI/RAG 담당자는 가능하면 `prompts/**`, `examples/**`, backend의 AI 관련 파일만 수정합니다.
- Playwright 담당자는 가능하면 `tests/**` 또는 `playwright/**` 안에서 작업합니다.
- 공통 문서나 API contract를 바꿀 때는 팀 채팅에 먼저 공유합니다.

## Merge 전 체크리스트

- `docs/API_CONTRACT.md`와 응답 구조가 맞는가?
- `examples/sample_inputs.md`의 입력 중 최소 1개로 확인했는가?
- 에러 상황 또는 fallback이 있는가?
- 발표 범위를 벗어난 기능을 추가하지 않았는가?

