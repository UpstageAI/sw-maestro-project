# SW Maestro Project

SW 마에스트로 프로젝트 제출 저장소입니다.

## 팀 폴더 네이밍 규칙

팀 폴더명은 반드시 아래 형식을 따라주세요:

```
team{번호}-{팀이름}
```

**예시:**
- `team1-newscatcher` (팀1 - 뉴스캐처)
- `team15-budgetbuddy` (팀15 - 버짓버디)
- `team42-studybot` (팀42 - 스터디봇)

**규칙:**
- `team` + 팀 번호를 반드시 접두사로 사용 (team1 ~ team60)
- 하이픈(`-`) 뒤에 팀 이름을 영문 소문자로 작성
- 팀 이름에 공백, 특수문자, 한글은 사용하지 마세요

## Repository Structure

```
sw-maestro-project/
├── README.md
└── projects/
    ├── team1-newscatcher/
    ├── team2-budgetbuddy/
    ├── team3-studybot/
    └── ...
```

각 팀은 `projects/` 아래 자신의 팀 폴더에 프로젝트를 제출합니다.

## 프로젝트 제출 방법

### 1. Fork this repository

GitHub 페이지 우측 상단의 **Fork** 버튼을 클릭하여 자신의 GitHub 계정으로 Fork합니다.

### 2. Clone your fork

```bash
git clone https://github.com/<your-github-username>/sw-maestro-project.git
cd sw-maestro-project
```

### 3. 팀 폴더를 만들고 프로젝트를 복사하세요

```bash
mkdir -p projects/team1-myteamname
cp -r /path/to/your-project/* projects/team1-myteamname/
```

> `team1-myteamname` 부분을 자신의 팀 번호와 팀 이름으로 변경하세요.

### 4. Commit and push

```bash
git add .
git commit -m "[Team 1] 프로젝트 제출 - myteamname"
git push origin main
```

### 5. Create a Pull Request

1. GitHub에서 자신의 Fork 저장소로 이동합니다.
2. **Contribute** → **Open pull request** 를 클릭합니다.
3. PR 제목을 `[Team N] 프로젝트 제출 - 팀이름` 형식으로 작성합니다.
4. 제출 완료!

> PR이 머지되기 전까지 리뷰가 진행될 수 있습니다.

## 주의사항

- **자신의 팀 폴더에만 작업하세요.** 다른 팀의 폴더를 수정하지 마세요.
- **반드시 Pull Request를 통해 제출하세요.** 직접 push는 허용되지 않습니다.
- **팀 폴더 네이밍 규칙을 반드시 지켜주세요.** (`team{번호}-{팀이름}`)
- PR 제출 전 자신의 Fork에서 프로젝트가 정상적으로 포함되었는지 확인하세요.
