# AI 자동 개발 가이드라인

Claude Code 슬래시 커맨드를 통해 AI 에이전트가 자동으로 코드를 작성·테스트·커밋·PR 생성하는 개발 흐름을 설명한다.

---

## 핵심 개념

이 프로젝트는 사람이 직접 코드를 작성하는 대신, **슬래시 커맨드로 AI 에이전트에게 step 단위로 구현을 위임**한다.

- 사람의 역할: 방향 결정(어떤 step을 진행할지) + 검증(결과가 올바른지 확인)
- AI의 역할: 브랜치 생성 → 테스트 작성 → 구현 → 커밋 → PR 생성 전 과정 자동화

---

## 슬래시 커맨드 2종

### `/project-review`

세션 시작 시 가장 먼저 실행하는 명령. AI가 프로젝트 전체 상태를 읽고 현황을 보고한다.

- `docs/README.md`, `progress.md`, 트랙별 진행 파일을 병렬로 읽는다
- 각 트랙(FE/BE/AI/BOOT)의 미완료 step을 찾아 다음 진행 후보를 제시한다
- 최근 커밋 5개와 현재 브랜치 상태를 함께 보고한다
- **파일을 읽기만 한다. 어떤 수정도 하지 않는다.**

```
# 세션 시작할 때마다 실행
/project-review
```

보고 형식 예시:
```
BOOT: 0/1 (BOOT-000 미완료) ← 시작 전 필수
BE:   0/8
FE:   0/8
AI:   0/8

다음 step: /step-implement BOOT-000
```

---

### `/step-implement {STEP_ID}`

하나의 step을 TDD 사이클로 끝까지 자동 진행하는 명령. STEP_ID는 `BE-001`, `FE-003`, `AI-007`, `BOOT-000` 형식.

```
# 예시
/step-implement BOOT-000
/step-implement BE-001
/step-implement FE-003
```

---

## `/step-implement` 자동 실행 흐름

```
사용자: /step-implement BE-001
         │
         ▼
[Phase 1] docs/steps/be/BE-001.md 읽기
         파일 없으면 → 초안 작성 후 사용자 확인
         │
         ▼
[Phase 2] 사전 점검
         - 현재 브랜치가 main인지 확인
         - 선행 step 완료 여부 확인
         │
         ▼
[Phase 3] 브랜치 생성
         git checkout -b feat/be-001-flyway-init
         │
         ▼
[Phase 4] Red — 실패하는 테스트 작성
         step 명세의 "테스트 명세" 그대로 작성
         실행 → 반드시 실패해야 함
         │
         ▼
[Phase 5] Green — 최소 구현
         테스트가 통과하도록 최소한의 코드 작성
         최대 3회 재시도, 실패 시 사용자에게 보고
         │
         ▼
[Phase 6] Refactor
         가독성·중복 제거, 전체 테스트 재실행
         │
         ▼
[Phase 7] 사용자 검증 요청 ← 여기서 멈춤
         "검증 명령: curl localhost:8080/api/feed" 형식으로 제시
         │
         ├─ 사용자 "OK"
         │       ▼
         │   [Phase 8] 자동 Done
         │   git commit + git push + gh pr create
         │   docs/progress/be.md 에서 [ ] → [x]
         │   PR URL + 다음 step 후보 보고
         │
         └─ 사용자 거부 또는 수정 요청
                 ▼
             [Phase 10] git stash + 피드백 반영 후 재시도
```

---

## 사용자 워크플로우 (요약)

```
1. 세션 시작
   /project-review

2. 진행할 step 선택 후 실행
   /step-implement BOOT-000

3. AI가 자동으로:
   - 브랜치 생성
   - 실패 테스트 작성
   - 구현
   - 성공 테스트 확인
   - 리팩토링

4. AI가 검증 명령을 알려주고 멈춤
   "curl localhost:8080/api/health 실행해서 200 확인해주세요"

5. 사용자가 실행 후 "OK" 입력

6. AI가 자동으로:
   - git commit
   - git push
   - GitHub PR 생성
   - progress 체크박스 갱신

7. 사용자가 GitHub에서 PR merge

8. 다음 step으로 반복
```

---

## Step 명세 파일 구조

각 step은 `docs/steps/{track}/{ID}.md` 파일로 정의된다. AI가 이 파일을 읽고 구현한다.

```markdown
# BE-001 — Flyway V1 마이그레이션

## 목표
이 step이 달성하는 것을 한 문단으로.

## 사전 조건
- BOOT-000 완료

## 파일 대상
- backend/src/main/resources/db/migration/V1__init.sql
- backend/src/test/java/.../FlywayMigrationTest.java

## 테스트 명세
- given: 빈 DB
- when: 애플리케이션 시작
- then: article 테이블 존재

## 구현 힌트
docs/contracts/db-init.sql 의 DDL을 그대로 사용.

## 검증 방법
./gradlew :backend:test --tests FlywayMigrationTest
```

Step 파일이 없으면 AI가 `progress.md`의 한 줄 명세를 바탕으로 초안을 자동 작성하고 확인을 요청한다.

---

## 트랙 구조

| 트랙 | STEP ID | 디렉토리 | 테스트 도구 |
|------|---------|----------|------------|
| 공용 부트스트랩 | BOOT-000 | (프로젝트 루트) | — |
| 백엔드 | BE-001~008 | `backend/` | JUnit 5 + Testcontainers |
| 프론트엔드 | FE-001~008 | `frontend/` | Vitest + MSW |
| AI | AI-001~008 | `ai/` | pytest + httpx |

각 트랙은 **다른 트랙 파일을 절대 건드리지 않는다.** 트랙 간 의존은 모킹으로 해결한다.

---

## 브랜치 전략

```
main
├── feat/boot-000-bootstrap
├── feat/be-001-flyway-init
├── feat/be-002-article-entity
├── feat/fe-001-tailwind-setup
├── feat/ai-001-fastapi-skeleton
└── ...
```

- AI가 step 시작 시 자동으로 브랜치 생성
- step 완료(사용자 OK) 시 자동으로 commit + push + PR 생성
- **merge는 사람이 GitHub에서 직접 한다**
- merge 후 다음 step 시작

---

## 실패 처리

**테스트 3회 실패 시:**
1. AI가 `git stash`로 작업 보존
2. 시도한 접근법 3가지 + 막힌 지점 보고
3. 사용자가 힌트 추가 / step 분할 / 재정의 중 선택

**검증 거부 시:**
1. AI가 `git stash`로 보관
2. 피드백 수렴 후 처음부터 재시도
3. OK 시 stash 무시하고 새 변경으로 commit

---

## 주의사항

- `docs/contracts/` 파일은 BOOT-000 이후 **읽기 전용**. 수정 필요 시 AI가 사용자에게 알리고 별도 step 제안
- `--no-verify`, `--force`, `git reset --hard` 같은 파괴적 명령은 사용하지 않는다
- 테스트 없이 구현하지 않는다 (항상 Red → Green 순서)
- 사용자 OK 없이 commit/push 하지 않는다
