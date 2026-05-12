# 회고: 운영 인프라 정보(IP·도메인·SSH key path) Git push 노출

**날짜**: 2026-05-10
**영향 범위**: GitHub 저장소(`soma17th-ai24/tail-quest`, **private**) 커밋 히스토리
**노출 시간**: 약 30분 (push → 사용자 알림 → 히스토리 재작성 완료)
**최종 결정**: 민감 정보 스크럽 + Git 히스토리 orphan reset + 옛 워크플로 run 삭제

---

## TL;DR

운영 환경의 EC2 퍼블릭 IP(`<EC2_PUBLIC_IP>`), 도메인(`<DOMAIN>`), SSH key 로컬 경로(`<LOCAL_PEM_PATH>`)를 README + TROUBLESHOOTING + POSTMORTEM 문서에 그대로 박아놓은 상태로 GitHub에 push했다. **저장소가 private**라 외부 노출은 0이었지만 팀원 외 협업자/감사 추적 리스크가 있어 ① 파일 스크럽 ② Git history orphan reset ③ 옛 SHA를 참조하는 워크플로 run 일괄 삭제로 대응했다. 다만 git의 force-push 한계상 14일 정도는 옛 SHA로 직접 fetch하면 접근 가능할 수 있어 **운영 IP·도메인 회전이 가장 안전한 후속 조치**다.

---

## 무엇이 어디에 노출됐나

| 정보 | 노출 위치 (커밋 기준) | 민감도 |
|---|---|---|
| 운영 EC2 퍼블릭 IP `<EC2_PUBLIC_IP>` | `README.md` 6-2 운영 EC2 접속 섹션, `TROUBLESHOOTING.md` 1번 항목, `POSTMORTEM-2026-05-10-disk-capacity.md` 검증 시나리오 | **높음** — 직접 SSH·HTTP 시도 가능 표적 |
| 도메인 `<DOMAIN>` | README 상단 "라이브 서비스" 표, TROUBLESHOOTING 검증 행, POSTMORTEM 검증 단계 | 중간 — 도메인 자체는 DNS로 누구나 조회 가능하나 운영 노출 사실 자체가 표적이 됨 |
| SSH 개인키 로컬 경로 `<LOCAL_PEM_PATH>` | README 6-2 / 6-3 ssh 명령 예시 | 낮음 — 경로일 뿐 키 내용 자체는 아님. 단 사용자명·디렉토리 구조 단서 |

> 키 파일(`<PEM_NAME>`)·`.env`·`UPSTAGE_API_KEY`·`JWT_SECRET`·`DOCKER_HUB_TOKEN` 등 **실제 시크릿 값은 push되지 않았다**. `.gitignore` + GitHub Secrets로 분리되어 있음.

---

## 발생 원인

### 1차 원인 — 운영 인프라 정보를 README에 직접 작성

데모 영상 녹화 직전 README를 "팀원이 보고 바로 운영 디버깅할 수 있게" 작성하면서 ssh 접속 명령, 라이브 URL, 디렉토리 경로 등을 **하드코딩**으로 박았다. README 작성 시점에 머릿속 우선순위가 "팀 사용성 ≫ 정보 노출 위험"이었다.

대표적인 라인:

```markdown
### 6-2. 운영 EC2 접속 (팀원용)

```powershell
ssh -i <LOCAL_PEM_PATH> ubuntu@<EC2_PUBLIC_IP>
```
```

### 2차 원인 — 푸시 직전 self-review 부재

`git add . && git commit && git push` 흐름에서 **diff 검토 없이** 진행했다. 변경 내역(README + 회고 합쳐 +752 라인)이 컸음에도 한 번도 `git diff` 하지 않았다.

### 3차 원인 — "private 저장소면 안전하다"는 안일함

저장소가 private라서 외부 노출은 0이지만:
- 팀원 외 collaborator 추가 시 즉시 공유됨
- 향후 public 전환 시(졸업과제 공개·포트폴리오 공개) 히스토리째 노출됨
- GitHub Support·DMCA 등의 제3자 접근 경로
- AI 학습 데이터로의 우발적 흡수(GitHub Copilot 학습 정책)

→ private도 결국 "지금 외부에 안 보일 뿐"의 임시 안전이지 영구 안전이 아니다.

---

## 영향 평가

### 실제 발생한 노출

| 채널 | 노출 여부 |
|---|---|
| 외부 인터넷 (검색·인덱싱) | **0** — private 저장소, 검색 엔진 크롤링 불가 |
| 팀 내 협업자 | **있음** — 현재 협업자 5명이 README/회고 열람 가능했음 |
| GitHub 직원 / DMCA / 법적 절차 | 이론상 접근 가능, 실제 사례 없음 |
| AI 학습 데이터 | private 저장소는 학습 미사용 (GitHub Copilot 정책상) |

### 잠재적 공격 표면 (IP·도메인이 알려졌다고 가정)

| 위험 | 차단 여부 |
|---|---|
| SSH 무차별 접속 | **차단** — 비밀번호 인증 비활성화, key-only |
| HTTPS 일반 트래픽 | **공개 의도** — 라이브 서비스 자체가 공개 운영 중 |
| API endpoint 엿보기 | `/health`만 무인증, 비즈니스 API는 모두 JWT 게이팅 |
| DDoS / 스팸 트래픽 | nginx + EC2 t2.micro의 한정된 처리량 — 표적 시 영향 가능 |

→ **현재 즉시 위협 수준은 낮음**. 단 IP가 알려진 상태로 운영을 계속하면 누적 위험이 증가.

---

## 해결 방법

### 1단계 — 파일 스크럽 (즉시 효과)

3개 파일에서 IP·도메인·pem path 일괄 제거:
- `README.md` — 사용자 요청에 따라 섹션 4(인증 격리) / 5(CI/CD) / 9(디자인) / 10(변경이력) / 11(비범위) 일괄 삭제. 상단 카드에서 "라이브 서비스" / "인프라" 행 제거
- `TROUBLESHOOTING.md` — 1번 항목 헤더 + 검증 행에서 IP·도메인 삭제
- `POSTMORTEM-2026-05-10-disk-capacity.md` — 검증 단계의 라이브 URL 제거

### 2단계 — Git 히스토리 재작성 (force push)

```bash
git checkout --orphan fresh-main
git commit -m "Initial commit: tail-question..."
git branch -D main
git branch -m main
git push --force-with-lease origin main
```

결과: `main` 브랜치가 단일 커밋(`026e54c`)만 가리킨다. 옛 SHA들(`e94394e`, `ce801c6`, `9023efc`, `d1fd4f6`, `cb38113`, `688b528` 등)은 **unreachable** 상태가 되어 GitHub의 garbage collector가 ~14일 내에 자동 회수한다.

### 3단계 — 워크플로 run 캐시 삭제

GitHub Actions의 `runs` 항목은 옛 commit SHA를 참조해 표시되며, 일부 메타데이터를 캐시한다. 옛 SHA를 참조하는 25건의 run을 `gh run delete`로 일괄 삭제. 잔존 run은 새 SHA `026e54c` 기준 3건뿐.

### 4단계 — 한계 인식 + 후속 조치 권고

force-push의 보안적 한계:
- 옛 SHA를 **직접 안다면** `git fetch origin <sha>` 로 14일 내 접근 가능 (private 레포 collaborator 한정)
- 옛 SHA를 이미 fork·clone한 사람의 로컬에는 그대로 남음 — 통제 불가
- GitHub 내부 백업·감사 로그는 force-push와 무관하게 보존될 수 있음

→ 코드 차원에서 할 수 있는 일은 했지만, **운영 IP·도메인 자체를 회전하는 것이 진짜 해결**이라는 결론.

---

## 교훈

### 잘한 점

1. **빠른 알림·빠른 대응**: 사용자가 push 후 즉시 인지해 신고했고, 30분 안에 history 재작성까지 완료했다.
2. **민감도별 분리**: 실제 시크릿(`.env`, `.pem` 내용, JWT_SECRET, API 키)은 처음부터 `.gitignore` + GitHub Secrets로 분리되어 있어 **이번 사고에서 시크릿 값 자체는 노출되지 않았다**. README의 노출은 "운영 위치 정보"에 한정.
3. **private 저장소 정책**: 적어도 외부 검색 엔진·AI 학습 데이터로 흘러갈 가능성은 차단됨.

### 못한 점

1. **README 작성 시 self-review 부재**: "팀 편의 ≫ 위험"이라는 우선순위 판단의 결과지만, 동일한 정보를 노출 없이도 전달할 수 있는 방법(아래 "패턴" 참고)을 사용하지 않았다.
2. **diff 미확인**: `git diff --staged` 한 줄이면 IP가 박혔다는 사실을 발견할 수 있었다.
3. **노출 가능성 매트릭스 사전 검토 부재**: "private = 안전"으로 판단했지만 그 가정의 한계(향후 public 전환·collaborator 추가·법적 절차)를 미리 따져보지 않았다.

### 안전한 README 작성 패턴

| 위험 | 안전한 표현 |
|---|---|
| `ssh -i C:\path\key.pem ubuntu@1.2.3.4` | `ssh -i <ssh-key-path> ubuntu@<EC2_HOST>` + "값은 팀 내부 secret manager / 1Password 참조" 안내 |
| `https://realdomain.com` | `<운영 URL은 별도 채널에서 공유>` 또는 placeholder `https://your-app.example.com` |
| `/home/ubuntu/myapp/...` 절대 경로 | `<APP_ROOT>/...` 변수 형태 |
| 운영 EC2 인스턴스 ID·VPC ID | README에 절대 작성 안 함, infra-as-code 레포에만 |

---

## 후속 액션 아이템

| 우선순위 | 항목 | 담당 / 기한 |
|---|---|---|
| **높음** | 운영 EC2 EIP 회전 — 새 EIP 할당 + DNS A 레코드 갱신 + 보안 그룹 재검토 | 인프라 담당, 24시간 내 |
| **높음** | 팀원 모두 로컬에 clone된 `.git/` 디렉토리 정리 — `git fetch --prune` + `git gc --aggressive --prune=now` 또는 fresh clone | 팀 전원, 안내 후 즉시 |
| 중간 | README 표준 템플릿 정의 — "운영 정보는 별도 secret manager 참조" 패턴 강제 | 팀장, 다음 sprint |
| 중간 | `pre-commit` hook 도입 — `gitleaks` / `detect-secrets`로 IP·이메일·키 패턴 차단 | 팀장 또는 보안 담당, 1주일 내 |
| 낮음 | GitHub 저장소 secret scanning + push protection 활성화 (Settings → Code security) | 팀장, 즉시 |
| 낮음 | 향후 public 전환 시 체크리스트 만들기 (history 전수 검토 + EIP·도메인 prior rotation 등) | 졸업 시점 전 |

---

## 부록 — 사용한 명령어 모음

복기·교육용:

```bash
# 1. 노출된 정보가 어느 파일에 있는지 전수 확인
git ls-files | xargs grep -l -E "13\.125\.177\.165|waitzero\.site|tail-request\.pem"

# 2. 파일 내용 스크럽 (Edit 툴 또는 sed)
# (생략 — README/TROUBLESHOOTING/POSTMORTEM 직접 편집)

# 3. orphan branch로 history 완전 재작성
git checkout --orphan fresh-main
git commit -m "Initial commit: ..."
git branch -D main
git branch -m main
git push --force-with-lease origin main

# 4. 옛 SHA 참조하는 워크플로 run 삭제
gh run list --limit 50 --json databaseId,headSha \
  | jq -r '.[] | select(.headSha != "<NEW_SHA>") | .databaseId' \
  | xargs -I {} gh run delete {}

# 5. 검증 — 잔존물 0 확인
git log --all --oneline   # 1줄만 나와야 함
git ls-remote origin       # main만 새 SHA
```

---

## 부록 — 관련 commit

| Commit | 내용 |
|---|---|
| `e94394e` (재작성으로 unreachable) | README 최신화 + 옛 IP/도메인 박힌 시점 |
| `026e54c` (현재 main) | 모든 민감 정보 제거 후 orphan reset |
