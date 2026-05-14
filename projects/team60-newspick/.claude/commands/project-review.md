---
description: 세션 시작 시 NewPick 프로젝트 컨텍스트를 로드한다. progress.md를 마스터 대시보드로 읽고 트랙별 현황, 의존성, 다음 step 후보를 보고한다.
allowed-tools: Read, Glob, Grep, Bash
---

# /project-review

NewPick 프로젝트의 현재 상태를 빠르게 파악한다. 세션이 시작될 때 가장 먼저 호출하는 명령.

## 핵심 원칙

- 루트 `progress.md`가 전체 milestone/트랙/의존성 상태의 첫 진입점이다.
- `docs/progress/{track}.md`는 step 체크박스의 상세 출처다.
- `docs/steps/{track}/{STEP_ID}.md`는 상세 명세와 dependency metadata의 단일 진실원천이다.
- 보고 시 "바로 진행 가능", "mock-first 가능", "hard dependency 대기"를 구분한다.

## 수행 절차

### 1. 마스터 대시보드 읽기

가장 먼저 `progress.md`를 읽는다.

확인 항목:
- 현재 Phase
- milestone 체크 상태
- 트랙별 진행률과 다음 step
- Dependency Dashboard의 진행 가능/대기 목록

### 2. 트랙별 진행 상황 읽기

병렬로:
- `Read` `docs/progress/boot.md`
- `Read` `docs/progress/be.md`
- `Read` `docs/progress/fe.md`
- `Read` `docs/progress/ai.md`

각 트랙의 미완료(`[ ]`) step 중 가장 ID가 낮은 것이 기본 다음 후보다.
루트 `progress.md`의 진행률과 트랙별 체크박스가 어긋나면 보고서에 `progress.md 갱신 필요`로 표시한다.

### 3. 다음 step metadata 확인

다음 후보 step의 `docs/steps/{track}/{STEP_ID}.md`가 있으면 읽는다.

확인 항목:
- `milestone`
- `requires.completed`
- `requires.external.mockable`
- `requires.external.hard`

step 파일이 없으면 `docs/progress/{track}.md`의 한 줄 설명만 기준으로 후보를 표시하고, `/step-implement`가 명세를 작성한다고 안내한다.

### 4. 계약 동결 상태 확인

`Glob` `docs/contracts/**/*` 로 파일 목록 확인. README, openapi.yaml, python-ai.yaml, sse-events.md, db-init.sql, json-schemas/* 가 모두 존재해야 한다.

### 5. 최근 git 활동

`Bash`:
```bash
git log --oneline -5
git status --short
git branch --show-current
```

현재 브랜치가 `main`인지, 작업 중인 milestone 브랜치가 있는지 보고한다.

## 보고서 형식

사용자에게 한 메시지로 요약한다.

```markdown
## NewPick 프로젝트 현황

**현재 단계**: Phase C — 실제 코드 구현
**현재 브랜치**: <branch>
**마스터 대시보드**: progress.md 기준 <정상/갱신 필요>

**Milestone**
- M1: 완료
- M2: FE 완료, BE/AI 대기
- M3~M6: 계획/진행 상태 요약

**트랙별 진행률**
- BOOT: 1/1, 다음 없음
- BE: 0/8, 다음 BE-001
- FE: 8/8, 다음 FE-009 계획 필요
- AI: 0/8, 다음 AI-001

**다음 진행 가능**
- 바로 가능: BE-001, AI-001
- mock-first 가능: <step 목록 또는 없음>
- hard dependency 대기: <step -> 필요한 step 목록>

**최근 커밋 5개**
- abc1234 feat(...): ...

**추천 작업**
- `/step-implement BE-001`
```

## 추가 컨텍스트가 필요한 경우

사용자가 다음 step을 명시하면, 그 트랙의 도메인 문서를 추가로 읽기:
- BE step 시작 → `docs/backend/*.md` 4~5개
- FE step 시작 → `docs/frontend/*.md` + `docs/design.md`
- AI step 시작 → `docs/ai/*.md` 6개 + `docs/architecture/pipeline-design.md`

이는 `/project-review`가 아니라 `/step-implement`가 필요 시 자동으로 한다.

## 주의

- 본 명령은 읽기만 한다. 어떤 파일도 생성·수정·삭제하지 않는다.
- 루트 `progress.md`가 stale해 보여도 project-review에서는 수정하지 않고 보고만 한다.
- 보고서는 간결하게 유지하되, 사용자가 지금 무엇을 할 수 있고 무엇이 막혔는지 분명히 보여준다.
