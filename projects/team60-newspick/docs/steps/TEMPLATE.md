# Step Definition Standard v2

모든 step 문서는 에이전트가 추가 의사결정 없이 red test를 작성하고 구현할 수 있을 만큼 결정된 상태여야 한다.

## 필수 YAML Metadata

```yaml
---
id: FE-031
milestone: M6
requires:
  completed: [FE-030]
  external:
    mockable: [BE-018, AI-024]
    hard: []
---
```

- `id`: canonical step id만 사용한다. 예: `FE-031`.
- `milestone`: `M1`~`M6` 중 하나를 쓴다.
- `requires.completed`: 같은 트랙 직전 step 또는 bootstrap 선행 step을 명시한다.
- `requires.external.mockable`: fixture, MSW, WireMock, fake repository로 대체 가능한 외부 step을 둔다.
- `requires.external.hard`: 미완료 상태에서 구현 전에 중단해야 하는 외부 step을 둔다.

## 필수 섹션

1. `# {STEP_ID} - {제목}`
2. `## 목표`
3. `## 사전 조건`
4. `## 파일 대상`
5. `## 테스트 명세`
6. `## 구현 기준`
7. `## 검증 방법`
8. FE 화면 step은 `## Prototype 기준`과 `## 수동 브라우저 검증`을 추가한다.

## 파일 대상 규칙

`파일 대상`에는 실제로 만들거나 수정할 파일만 적는다.

```text
[신규] frontend/src/features/chat/ChatShell.tsx
[수정] frontend/src/features/chat/ChatShell.test.tsx
```

읽기 전용 계약서, schema, 참조 fixture는 `검증 대상` 섹션에 따로 적는다.

## 테스트 명세 규칙

각 테스트 명세는 다음 항목을 모두 포함한다.

- **테스트 파일**: 실행할 테스트 파일 경로
- **테스트 이름**: 만들 테스트 함수 또는 test case 이름
- **fixture**: 사용할 입력 데이터, MSW 응답, WireMock 응답, fake Solar 응답, DB seed를 구체적으로 적는다.
- **action**: 사용자가 하는 동작, API 호출, graph/node 실행, service method 호출을 하나로 고정한다.
- **assertions**: HTTP status, JSON path, role/name, DB row, state shape 등 검증할 값을 bullet로 나열한다.
- **mock strategy**: MSW, WireMock, Mockito, fake repository, Testcontainers, VCR 중 무엇을 쓰는지 하나로 고정한다.
- **out of scope**: 이 step에서 만들지 않는 기능을 명시한다.

## 문서 결함으로 중단하는 경우

- 입력 fixture가 구체적인 파일명, 응답 JSON, DB seed, fake 응답 없이 일반 설명에 머무른다.
- action이 실제 호출 대상이나 사용자 조작을 특정하지 않는다.
- assertions가 화면 텍스트, role/name, JSON path, DB row, state field를 특정하지 않는다.
- mock strategy가 여러 선택지 사이에서 결정되지 않았다.
- 파일 대상에 실제 변경 파일과 읽기 전용 참조 파일이 섞여 있다.
- FE 화면 step에 `## Prototype 기준`이 없다.
- FE 화면 step의 `## Prototype 기준`이 참조할 prototype 파일, 섹션, class를 특정하지 않는다.

## FE Prototype Fidelity 규칙

FE 화면 step은 원본 `prototype/` 파일을 1차 진실원천으로 삼는다. `docs/design.md`는 보조 색인이며, 충돌 시 원본 prototype을 따른다.

`## Prototype 기준`에는 다음을 반드시 적는다.

- 참조할 원본 파일: `prototype/index.html`, `prototype/styles.css`, `prototype/script.js`, `prototype/report-variations.jsx`, `prototype/assets/*` 중 해당 항목
- 참조할 prototype 섹션 또는 class: 예: `.inline-quiz#inlineQuiz`, `.app-page.chat-page`, `VariantCPlus`
- 동일하게 맞출 범위: 텍스트, 구조, 색상, 간격, radius, shadow, 상태, 인터랙션

`## 수동 브라우저 검증`에는 prototype과 구현 화면을 나란히 열고 확인할 체크리스트를 둔다. 불일치가 남아 있으면 step 완료로 처리하지 않는다.

## Live Gate 규칙

`FE-016`, `FE-022`, `FE-030`, `FE-037`은 live integration gate다.

- hard dependency가 미완료이면 구현 전에 중단한다.
- 기본 `pnpm test`는 fixture와 contract schema만 사용한다.
- 실제 FE/BE/AI 서버 호출은 `RUN_LIVE_CONTRACT=true`일 때만 실행한다.
- live step 문서는 FE/BE/AI URL, seed 준비 조건, 실패 기준을 반드시 포함한다.
