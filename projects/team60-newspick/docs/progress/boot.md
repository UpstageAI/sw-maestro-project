# BOOT 진행 (공용 부트스트랩)

본 트랙은 BOOT-000 1개 step 으로 끝난다. 완료 후 BE/FE/AI 가 병렬 개발 가능.

## 체크리스트

- [x] **BOOT-000** 공용 셋업 — [docs/steps/boot/BOOT-000.md](../steps/boot/BOOT-000.md)
  - `docker-compose.yml` 작성
  - `.env.example` 작성 (4개 영역: 루트/backend/ai/frontend)
  - `docs/contracts/` 동결 (openapi.yaml / python-ai.yaml / sse-events.md / db-init.sql / json-schemas/)
  - 각 트랙 디렉토리 초기화 (`backend/`, `frontend/`, `ai/`) — Spring Initializr / create-next-app / uv init 결과만 커밋
  - 루트 `README.md` 작성 (셋업 절차)
  - `.gitignore`, `.editorconfig` 등 공용 파일

## 완료 기준

- `docker compose up -d` → DB healthy
- 각 트랙 디렉토리에서 빌드/lint 통과 (`./gradlew build`, `pnpm install`, `uv sync`)
- `docs/contracts/openapi.yaml` 와 `python-ai.yaml` validation 통과
