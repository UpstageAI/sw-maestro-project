# 계약 (Contracts)

본 폴더는 트랙 간 **단일 진실원천**. BOOT-000 단계에서 작성·동결된 뒤 **읽기 전용**으로 다룬다. 변경이 필요하면 별도 contract-update step 으로 한 사람이 처리.

## 파일

| 파일 | 내용 | 사용 트랙 |
|---|---|---|
| `openapi.yaml` | Spring REST API 스펙 (브라우저 ↔ Spring) | BE (구현), FE (소비) |
| `python-ai.yaml` | Python FastAPI 스펙 (Spring ↔ Python) | AI (구현), BE (소비) |
| `sse-events.md` | SSE 이벤트 스키마 (`step`/`done`/`warn`/`error`/`token`) | 3개 트랙 모두 |
| `db-init.sql` | 초기 Flyway V1 스키마 (DDL) | BE (Flyway 마이그레이션), AI (Testcontainers DDL) |
| `json-schemas/` | Article / Quiz / DailyReport / SseEvent JSON Schema | BE (응답 검증), FE (타입 자동 생성), AI (FastAPI Pydantic 모델 정합) |

## 변경 절차

1. 누구든 변경 필요성을 발견하면 GitHub Issue 로 contract-update 제안.
2. 사용자가 승인 → 한 사람이 `feat/contract-NNN-{slug}` 브랜치로 변경.
3. PR merge 후 모든 트랙이 main 을 pull 해서 새 계약을 받음.
4. 계약 변경 영향을 받는 step 들이 자동으로 invalidate — 영향받는 트랙은 해당 step 들을 재구현.

## BOOT-000 완료 후 본 폴더의 모든 파일은 frozen 상태로 시작.

> 본 README 는 가이드. 실제 계약 파일들은 BOOT-000 에서 채워진다.
