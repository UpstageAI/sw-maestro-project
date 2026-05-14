---
name: git-workflow
description: "Mise 프로젝트 Git 워크플로우 규칙. 커밋, 푸시, 브랜치 생성, PR 생성 시 반드시 이 스킬을 따를 것. git commit, git push, git checkout, 브랜치 생성, PR 생성 요청 시 이 스킬을 사용."
---

# Git Workflow — GitHub Flow

이 프로젝트는 GitHub Flow 브랜치 전략을 사용한다. main 브랜치에 직접 커밋하지 않는다.

## 브랜치 규칙

1. **main에 직접 커밋/푸시 금지** — 항상 작업 브랜치에서 작업한다
2. **브랜치는 GitHub 이슈에서 생성** — 이슈 > "Create a branch" 버튼 사용
3. **브랜치명 형식:** `이슈번호/작업내용` (예: `2/image-generator`)

## 커밋 메시지 규칙

형식: `<타입>: <한글 설명>`

| 타입 | 사용 시기 |
|------|----------|
| `feat:` | 새 기능 추가 |
| `fix:` | 버그 수정 |
| `docs:` | 문서 수정 |
| `refactor:` | 코드 리팩토링 |
| `test:` | 테스트 추가/수정 |
| `chore:` | 설정, 빌드, 의존성 등 |

**예시:**
```
feat: 장면 요소 추출 체인 구현
fix: 1000자 초과 입력 검증 누락 수정
docs: README에 브랜치 전략 추가
```

## 커밋 전 체크리스트

커밋하기 전에 반드시 확인:
- [ ] 현재 브랜치가 main이 아닌지 확인 (`git branch`)
- [ ] main이면 작업 브랜치로 전환
- [ ] 커밋할 파일이 의도한 것만 포함되어 있는지 확인
- [ ] 커밋 메시지가 규칙에 맞는지 확인

## 금지 사항

- `git push origin main` — 절대 금지
- `git push --force` — 절대 금지
- `git reset --hard` — 확인 없이 실행 금지
- `git commit --amend` — 새 커밋으로 대체
- `.env` 파일 커밋 — API 키가 포함되어 있으므로 절대 금지

## PR 생성

push 후 PR 생성을 안내:
1. GitHub에서 "Compare & pull request" 버튼 클릭
2. PR 제목: `feat: 구현 내용 요약`
3. 내용에 `Closes #이슈번호` 포함
4. 리뷰어 지정
