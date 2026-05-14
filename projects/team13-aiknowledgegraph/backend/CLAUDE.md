## 커밋 메시지 규칙

- 형식: `<type>: <한국어 요약>`
- type 종류: `feat`, `fix`, `docs`, `refactor`, `test`, `chore` 등

## PR 규칙

- PR 생성 전에 반드시 `/swagger-check` 스킬을 실행하여 Swagger/OpenAPI 명세 누락 여부를 확인한다.
- PR 제목 형식: `<type>: <한국어 요약>`
- type 종류는 커밋 메시지 규칙과 동일하게 `feat`, `fix`, `docs`, `refactor`, `test`, `chore` 등을 사용한다.
- PR을 올릴 때는 `.github/pull_request_template.md` 템플릿을 따른다.
- PR 본문에는 변경 요약, 변경 이유, 영향 범위, 검증 결과를 명확히 작성한다.

## 프로젝트 기획

- 전체 기획은 `docs/plan.md`를 기준으로 한다.
- `docs/plan.md`는 최신 상태가 아닐 수 있으므로 갱신이 필요할 수 있다.

## docs/plan.md 수정 규칙

- `docs/plan.md`를 수정할 때는 반드시 수정안을 먼저 제시하고 유저의 확인을 받은 후 반영한다.
- `docs/plan.md`의 기존 양식(마크다운 구조, 표 형식 등)을 절대로 변경하지 않는다.

## API 명세 규칙

- API를 구현하거나 수정할 때는 Swagger/OpenAPI 문서에서 요청, 응답, 경로 변수, 쿼리 파라미터, 에러 응답을 자세히 파악할 수 있도록 명세한다.
