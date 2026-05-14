---
name: "source-command-step-implement"
description: "한 step의 TDD 사이클(red -> green -> test -> verify -> commit/push -> progress sync -> next notice)을 자율 수행한다."
---

# source-command-step-implement

Use this skill when the user asks to run the migrated source command `step-implement`.

## Command Template

# /step-implement {STEP_ID}

지정한 step 하나를 끝까지 수행한다. 기본 흐름은 **step 명세 로드 -> dependency gate -> red test -> green 구현 -> 검증 -> progress sync -> commit/push -> 다음 단계 고지**다.

`M6-FE-031`처럼 milestone prefix가 붙은 입력은 canonical ID `FE-031`로 정규화한다. 한 번에 여러 step을 구현하지 않는다.

## 시작 전에 반드시 읽을 파일

1. `progress.md`
2. `docs/progress/boot.md`
3. `docs/progress/be.md`
4. `docs/progress/fe.md`
5. `docs/progress/ai.md`
6. `docs/steps/{track}/{STEP_ID}.md`

## Step 명세 정책

- `docs/steps/{track}/{STEP_ID}.md`가 단일 진실원천이다.
- M2~M6 범위에서 step 파일이 없으면 문서 결함으로 보고하고 구현 전에 중단한다.
- M7 이후 범위에서 step 파일이 없으면 `docs/steps/TEMPLATE.md` 기준으로 먼저 작성한 뒤 같은 사이클에서 구현한다.
- step 문서에 generic 테스트 문구가 남아 있으면 구현 전에 중단하고 `step 명세 보강 필요`로 보고한다.
- 금지 문구 판정은 `docs/steps/TEMPLATE.md`의 Step Definition Standard v2를 따른다.

## Dependency Gate

step YAML metadata를 읽어 gate를 판정한다.

```yaml
requires:
  completed: [FE-030]
  external:
    mockable: [BE-018, AI-024]
    hard: []
```

- `requires.completed`: 미완료이면 구현 전에 중단한다.
- `requires.external.hard`: 미완료이면 구현 전에 중단한다.
- `requires.external.mockable`: 미완료여도 MSW, WireMock, fake repository, fake graph, fixture로 진행한다.
- hard dependency 중단 메시지는 다음 형식을 따른다.

```text
FE-037은 hard dependency가 완료되지 않아 진행할 수 없습니다. 먼저 BE-023, AI-029를 완료해야 합니다.
```

## Live Integration Gate

`FE-016`, `FE-022`, `FE-030`, `FE-037`은 live integration gate다.

- hard dependency가 미완료이면 구현하지 않는다.
- 기본 `pnpm test`는 fixture와 contract schema만 사용한다.
- 실제 FE/BE/AI 서버 호출은 `RUN_LIVE_CONTRACT=true`일 때만 수행한다.
- live 검증을 실행할 때는 step 문서에 적힌 FE/BE/AI URL, seed 준비 조건, 실패 기준을 그대로 따른다.

## TDD 사이클

1. Red: step 문서의 테스트 명세대로 실패하는 테스트를 먼저 작성한다.
2. Green: step 문서의 파일 대상 안에서 최소 구현으로 테스트를 통과시킨다.
3. Test: 해당 track의 명령을 실행한다.
   - FE: `pnpm test`, `pnpm lint`
   - BE: Gradle 테스트
   - AI: pytest
4. Verify: UI step이면 브라우저에서 step 문서의 수동 검증 항목을 확인한다.
5. Progress sync: `docs/progress/{track}.md`와 루트 `progress.md`를 갱신한다.
6. Commit/push: 이번 step과 직접 관련된 파일만 stage하고 commit/push한다.
7. Next notice: 다음 가능한 step, mock-first 잔여 의존성, hard dependency 대기 항목을 보고한다.

## Progress Sync 규칙

- 완료한 step은 `docs/progress/{track}.md`에서 `[x]`로 바꾼다.
- 루트 `progress.md`의 track 진행률, 다음 step, dependency dashboard를 갱신한다.
- mockable dependency가 미완료인 상태로 완료했다면 `progress.md`에 실제 통합 전 필요한 step을 남긴다.
- milestone 마지막 step이 완료되면 milestone 체크 상태도 갱신한다.

## 안전 규칙

- 요청받은 step 범위를 넘는 리팩터링은 하지 않는다.
- `docs/contracts/` 변경이 필요하면 별도 contract-update step으로 분리한다.
- 사용자가 만든 변경이나 이번 step과 무관한 변경은 되돌리지 않는다.
- `git reset --hard`, `git checkout --`, `git push --force`, `--no-verify`는 사용하지 않는다.
- `git add .` 대신 이번 step과 직접 관련된 파일만 명시적으로 stage한다.
