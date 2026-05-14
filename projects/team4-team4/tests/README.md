# Tests README

Playwright 담당자는 이 폴더에서 발표용 E2E 테스트를 관리합니다.

## 목표

- 사용자가 아이디어를 입력합니다.
- 생성 버튼을 누릅니다.
- 결과 제목과 청구항이 화면에 표시되는지 확인합니다.
- API 실패 시 fallback 메시지 또는 샘플 결과가 표시되는지 확인합니다.

## 발표용 테스트 입력

`examples/sample_inputs.md`의 1순위 입력을 기본으로 사용합니다.

```text
방구로 가는 자동차
```

## AI에게 요청할 때

```text
tests/README.md와 examples/sample_inputs.md를 읽고
Playwright로 Brainrot Patent의 입력-생성-결과 표시 E2E 테스트를 작성해줘.
테스트는 발표용 입력 "방구로 가는 자동차"를 사용해야 해.
```

## 실행

Frontend와 Backend를 먼저 켠 뒤 실행합니다.

```bash
npm install
npx playwright test
```
