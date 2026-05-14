# Scripts

운영용 셸 스크립트. Git 동기화(Codex 전용)와 개발 서버 실행 스크립트.

## 개발 서버 실행

### 백엔드 (FastAPI + LangGraph)

```powershell
.\scripts\run-backend.ps1
```

> PowerShell 실행 정책 에러("스크립트 실행 사용 안 함")가 뜨면 아래 `.cmd` 래퍼를 사용하거나 한 번만 정책을 풀어두세요(맨 아래 *실행 정책 안내* 참조).
>
> ```powershell
> .\scripts\run-backend.cmd
> ```

**기본값은 `LLM_PROVIDER=upstage`** — 별도 설정 없이 실제 Solar 모델로 동작합니다 (스크립트에 기본 API 키 포함).

빠른 mock 테스트가 필요하면 실행 전에 환경변수 덮어쓰기:

```powershell
$env:LLM_PROVIDER = 'mock'
.\scripts\run-backend.cmd
```

- 의존성 미설치 시 자동으로 `pip install -r backend\requirements.txt` 수행
- 포트 8000 점유 시 종료 옵션(y/N) 안내 후 자동 정리 가능
- http://localhost:8000

### 프론트엔드 (Next.js 15)

```powershell
.\scripts\run-frontend.ps1
```

> PowerShell 실행 정책 에러가 뜨면:
>
> ```powershell
> .\scripts\run-frontend.cmd
> ```

- 시스템 Node가 없으면 `%USERPROFILE%\node-portable\node-v20.18.1-win-x64` 포터블 Node를 PATH에 자동 끼움
- `frontend\node_modules`가 없으면 자동으로 `npm ci`
- http://localhost:3000

---

## 실행 정책 안내

Windows PowerShell의 기본 정책이 `Restricted`라 `.ps1` 직접 실행이 막혀 있을 수 있습니다.

**옵션 A — `.cmd` 래퍼 사용 (권장, 변경 없음)**

```powershell
.\scripts\run-backend.cmd
.\scripts\run-frontend.cmd
```

`.cmd`는 내부적으로 `powershell.exe -ExecutionPolicy Bypass`로 `.ps1`을 호출하므로 정책 변경 없이 한 번만 실행됩니다.

**옵션 B — 현재 사용자에 한해 정책 풀기 (한 번만)**

관리자 권한 없이 한 번만 실행:

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

이후부터는 `.\scripts\run-*.ps1` 직접 실행 가능합니다.

**옵션 C — 1회용**

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run-backend.ps1
```

---

## Git Sync (Codex 전용)

Git synchronization helpers for Codex sessions.

## Start Sync

Run this at the beginning of a Codex task:

```powershell
.\scripts\codex-git-start.ps1
```

It records the current dirty working tree state in `.codex/` and then tries to fetch and pull the current branch with `--rebase --autostash`.

## Finish Sync

Run this at the end of a Codex task:

```powershell
.\scripts\codex-git-finish.ps1
```

This pushes already committed local work.

To also commit task changes before pushing:

```powershell
.\scripts\codex-git-finish.ps1 -CommitAll -CommitMessage "docs: update project plan"
```

The finish script uses the baseline saved by the start script to avoid automatically staging files that were already dirty before the task started.

For a one-time initial repository commit, use:

```powershell
.\scripts\codex-git-finish.ps1 -CommitAll -IgnoreBaseline -CommitMessage "chore: initial project setup"
```
