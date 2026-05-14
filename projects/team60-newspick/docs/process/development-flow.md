# 개발 워크플로우

이 프로젝트는 `progress.md`를 마스터 대시보드로 사용한다. `/project-review`와 `/step-implement`는 항상 루트 `progress.md`를 먼저 읽고, 트랙별 progress와 step metadata로 다음 작업과 dependency gate를 판단한다.

## 트랙

| 트랙 | 디렉터리 | 책임 |
|---|---|---|
| FE | `frontend/` | Next.js/React 화면, MSW mock-first 구현, 브라우저 검증 |
| BE | `backend/` | Spring REST/SSE API, DB access, Python AI proxy |
| AI | `ai/` | FastAPI, LangGraph pipeline, Solar/embedding/RAG |
| BOOT | 공통 | 계약, DB, 개발 환경 bootstrap |

## 문서 구조

| 파일 | 역할 |
|---|---|
| `progress.md` | milestone, 트랙별 진행률, 다음 step, dependency dashboard |
| `docs/progress/{track}.md` | 트랙별 step 체크리스트 |
| `docs/steps/{track}/{STEP_ID}.md` | 상세 step 명세와 YAML dependency metadata |
| `docs/contracts/` | FE/BE/AI 계약의 단일 진실원천 |

## Step 진입 규칙

1. `progress.md`를 읽어 현재 milestone과 다음 step 후보를 확인한다.
2. `docs/progress/{track}.md`에서 step 완료 상태를 확인한다.
3. `docs/steps/{track}/{STEP_ID}.md`를 읽는다.
4. M2~M6 범위의 step 파일이 없으면 문서 결함으로 보고하고 구현 전에 중단한다.
5. step 문서가 fixture, action, assertions, mock strategy를 결정하지 않았으면 문서 결함으로 중단한다.
6. `requires.completed`와 `requires.external.hard`가 미완료이면 구현 전에 중단한다.
7. `requires.external.mockable`만 미완료이면 mock-first로 진행하고, 완료 보고와 `progress.md`에 실제 통합 전 필요한 step을 남긴다.
8. FE mock-first step은 이전 live integration gate를 기다리지 않는다. 예를 들어 `FE-016`, `FE-022`, `FE-030`이 미완료여도 다음 FE mock-first 마일스톤은 fixture/MSW 기준 테스트와 브라우저 검증을 통과하도록 진행할 수 있다.

## FE Prototype Fidelity Gate

FE 화면 step은 원본 `prototype/` 파일을 디자인의 1차 진실원천으로 본다.

- 원본 우선순위는 `prototype/index.html`, `prototype/styles.css`, `prototype/script.js`, `prototype/report-variations.jsx`, `prototype/assets/*` 순서다.
- `docs/design.md`는 보조 색인이다. 문서와 원본 prototype이 충돌하면 원본 prototype을 따른다.
- FE 화면 step 문서에는 반드시 `## Prototype 기준`이 있어야 한다. 없으면 문서 결함으로 보고하고 구현 전에 중단한다.
- 구현 완료 조건은 텍스트, DOM 구조, 화면 배치, 색상, 간격, radius, shadow, 상태, 인터랙션을 prototype과 동일하게 맞추는 것이다.
- 임의 단순화, 다른 레이아웃 재해석, 텍스트 변경, 스타일 축약은 허용하지 않는다.

## TDD Cycle

여러 step을 입력받은 경우에도 아래 사이클은 step마다 독립적으로 수행한다. 한 step의 검증, progress sync, commit, push가 끝나기 전에는 다음 step을 시작하지 않는다. 중간 step이 실패하면 이후 step은 진행하지 않는다.

1. Red: step 문서의 테스트 명세대로 실패 테스트를 작성한다.
2. Green: step 문서의 파일 대상 안에서 최소 구현을 한다.
3. Test: 트랙별 자동 검증을 실행한다.
4. Verify: UI step은 브라우저에서 prototype과 구현 화면을 나란히 비교해 수동 검증 항목을 확인한다.
5. Progress sync: 트랙 progress와 루트 progress를 함께 갱신한다.
6. Commit/push: 현재 milestone branch에 step 단위 commit을 쌓고 원격에 push한다.
7. Next step/notice: 여러 step 입력에 남은 step이 있으면 최신 progress를 다시 읽고 다음 step dependency gate부터 재시작한다. 남은 step이 없으면 다음 가능한 step과 block된 step을 보고한다.

## Live Integration Gate

`FE-016`, `FE-022`, `FE-030`, `FE-037`은 hard-gated live step이다.

- hard dependency가 완료되기 전에는 구현하지 않는다.
- 기본 테스트는 fixture와 contract schema만 사용한다.
- 실제 서버 호출은 `RUN_LIVE_CONTRACT=true`에서만 실행한다.
- live 검증 준비 조건과 실패 기준은 각 step 문서에 적힌 값을 따른다.
- live step 미완료 상태는 다음 FE mock-first step의 진입을 막지 않는다. live 검증은 BE/AI hard dependency가 준비된 뒤 별도로 수행한다.

## Branch와 Commit

- milestone branch에서는 step마다 새 브랜치를 만들지 않고 현재 브랜치에 step 단위 commit을 쌓는다.
- step마다 PR을 만들지 않는다. milestone 완료 시점에 사용자가 원하면 PR을 만든다.
- `docs/contracts/` 변경이 필요하면 별도 contract-update step으로 분리한다.
