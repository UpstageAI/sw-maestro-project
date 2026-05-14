# Dev Environment Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `persona-reviewer` 저장소의 main 브랜치에 환경 파일, 디렉터리 골격, seed 데이터를 셋업해서 5명 팀원이 같은 베이스에서 개발 시작 가능하게 한다.

**Architecture:** uv 기반 Python 3.11+ 가상환경 + LangGraph/LangChain/Streamlit 의존성. 코드 파일은 모두 placeholder(빈 파일 또는 한 줄 docstring) 상태로 두고, 실제 로직 구현은 별도 작업에서 채움. 단일 git 커밋으로 마무리.

**Tech Stack:** Python 3.11+, uv, LangGraph 0.2.74, LangChain 0.3.19, langchain-upstage 0.5.0, Pydantic 2.11.3, Streamlit 1.44.1, python-dotenv 1.1.0, datasets 3.5.0

**Source spec:** `docs/superpowers/specs/2026-05-04-dev-environment-setup-design.md`

**Key constraints:**
- 모든 작업 main 브랜치에서 직접 실행, 마지막에 단일 커밋
- 커밋 메시지는 Conventional Commits 스타일, **Co-Authored-By 라인 절대 포함하지 않음**
- 모든 파일은 UTF-8 (BOM 없음), LF 줄바꿈
- push는 사용자가 수동 실행

---

## File Structure

본 셋업이 만들어낼 파일 목록:

| 경로 | 종류 | 책임 |
|------|------|------|
| `.gitignore` | config | venv/캐시/IDE/OS 산출물 추적 제외 |
| `.env.example` | config | API 키 입력 형식 예시 |
| `requirements.txt` | config | 패키지 의존성 핀 (8개) |
| `README.md` | doc | 프로젝트 한 줄 소개 |
| `app.py` | code placeholder | Streamlit 진입점 (docstring만) |
| `graph.py` | code placeholder | LangGraph 빌드 (docstring만) |
| `schemas.py` | code placeholder | Pydantic 스키마 (docstring만, 전원 공유) |
| `state.py` | code placeholder | LangGraph State (docstring만, 전원 공유) |
| `nodes/__init__.py` | package marker | 빈 파일 |
| `nodes/f0_parse.py` | code placeholder | 빈 파일 |
| `nodes/f1_select.py` | code placeholder | 빈 파일 |
| `nodes/f2_opinion.py` | code placeholder | 빈 파일 |
| `nodes/f3_review.py` | code placeholder | 빈 파일 |
| `services/__init__.py` | package marker | 빈 파일 |
| `services/persona_repository.py` | code placeholder | 빈 파일 |
| `scripts/sample_hf_personas.py` | code placeholder | 빈 파일 |
| `scripts/generate_user_cards.py` | code placeholder | 빈 파일 |
| `data/personas/raw_personas.seed.json` | data | 2명 페르소나 seed (RawNemotronPersona) |

총 18개 파일 신규 생성. 단일 커밋.

---

## Task 1: Pre-flight environment check

**Files:** (검증만, 파일 변경 없음)

- [ ] **Step 1: Verify Python version ≥ 3.11**

PowerShell:
```powershell
python --version
```
Expected: `Python 3.11.x` 또는 그 이상. 3.10 이하면 중단하고 사용자에게 보고.

- [ ] **Step 2: Verify uv is installed**

PowerShell:
```powershell
uv --version
```
Expected: `uv 0.x.x` 출력. 명령을 찾을 수 없다는 에러가 나면 다음 Step으로 진행해서 설치, 그렇지 않으면 Step 4로 점프.

- [ ] **Step 3: Install uv (Step 2가 실패한 경우만)**

PowerShell:
```powershell
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```
설치 후 새 PowerShell 세션에서 다시 `uv --version`으로 확인. PATH 갱신을 위해 새 세션이 필요할 수 있음.

- [ ] **Step 4: Verify git state**

PowerShell:
```powershell
git status
git branch --show-current
```
Expected:
- working tree clean (uncommitted changes 없음)
- 현재 브랜치 `main`
- 만약 dirty하거나 다른 브랜치라면 사용자에게 보고하고 중단

---

## Task 2: Create root configuration files

**Files:**
- Create: `.gitignore`
- Create: `.env.example`
- Create: `requirements.txt`
- Create: `README.md`

- [ ] **Step 1: Create `.gitignore`**

내용:
```
# Environment
.env
.venv/

# Python
__pycache__/
*.pyc
*.pyo

# Data 산출물 (스크립트로 생성될 변환본)
data/personas/persona_cards.seed.json

# IDE
.vscode/
.idea/
*.swp

# OS
.DS_Store
Thumbs.db
```

- [ ] **Step 2: Create `.env.example`**

내용:
```
UPSTAGE_API_KEY=your_api_key_here
```

- [ ] **Step 3: Create `requirements.txt`**

내용:
```
langgraph==0.2.74
langchain==0.3.19
langchain-upstage==0.5.0
langchain-core==0.3.51
pydantic==2.11.3
streamlit==1.44.1
python-dotenv==1.1.0
datasets==3.5.0
```

- [ ] **Step 4: Create `README.md`**

내용:
```markdown
# persona-reviewer

LangGraph 기반 페르소나 리뷰어. 자세한 내용은 `docs/setup.md`, `docs/structure.md` 참고.
```

- [ ] **Step 5: Verify all 4 files exist**

PowerShell:
```powershell
Test-Path .gitignore, .env.example, requirements.txt, README.md
```
Expected: 4번 모두 `True` 출력.

---

## Task 3: Create `nodes/` package

**Files:**
- Create: `nodes/__init__.py` (빈 파일)
- Create: `nodes/f0_parse.py` (빈 파일)
- Create: `nodes/f1_select.py` (빈 파일)
- Create: `nodes/f2_opinion.py` (빈 파일)
- Create: `nodes/f3_review.py` (빈 파일)

- [ ] **Step 1: Create `nodes/` directory**

PowerShell:
```powershell
New-Item -ItemType Directory -Path nodes -Force
```

- [ ] **Step 2: Create 5 empty files**

각각 0바이트 파일로 생성:
```powershell
New-Item -ItemType File -Path nodes/__init__.py -Force
New-Item -ItemType File -Path nodes/f0_parse.py -Force
New-Item -ItemType File -Path nodes/f1_select.py -Force
New-Item -ItemType File -Path nodes/f2_opinion.py -Force
New-Item -ItemType File -Path nodes/f3_review.py -Force
```

- [ ] **Step 3: Verify all files exist and are empty**

PowerShell:
```powershell
Get-ChildItem nodes/ | Select-Object Name, Length
```
Expected: 5개 파일 모두 표시되고 각 `Length` = 0.

---

## Task 4: Create `services/` package

**Files:**
- Create: `services/__init__.py` (빈 파일)
- Create: `services/persona_repository.py` (빈 파일)

- [ ] **Step 1: Create `services/` directory**

PowerShell:
```powershell
New-Item -ItemType Directory -Path services -Force
```

- [ ] **Step 2: Create 2 empty files**

```powershell
New-Item -ItemType File -Path services/__init__.py -Force
New-Item -ItemType File -Path services/persona_repository.py -Force
```

- [ ] **Step 3: Verify**

PowerShell:
```powershell
Get-ChildItem services/ | Select-Object Name, Length
```
Expected: 2개 파일, 모두 `Length` = 0.

---

## Task 5: Create `scripts/` directory

**Files:**
- Create: `scripts/sample_hf_personas.py` (빈 파일)
- Create: `scripts/generate_user_cards.py` (빈 파일)

> 주의: `scripts/`는 패키지가 아니므로 `__init__.py` 없음.

- [ ] **Step 1: Create `scripts/` directory**

PowerShell:
```powershell
New-Item -ItemType Directory -Path scripts -Force
```

- [ ] **Step 2: Create 2 empty files**

```powershell
New-Item -ItemType File -Path scripts/sample_hf_personas.py -Force
New-Item -ItemType File -Path scripts/generate_user_cards.py -Force
```

- [ ] **Step 3: Verify**

PowerShell:
```powershell
Get-ChildItem scripts/ | Select-Object Name, Length
```
Expected: 2개 파일, 모두 `Length` = 0. `__init__.py`는 없어야 함.

---

## Task 6: Create top-level Python files with docstring placeholders

**Files:**
- Create: `app.py`
- Create: `graph.py`
- Create: `schemas.py`
- Create: `state.py`

- [ ] **Step 1: Create `app.py`**

내용 (한 줄 docstring + 줄바꿈):
```python
"""Streamlit 진입점. `streamlit run app.py`로 실행."""
```

- [ ] **Step 2: Create `graph.py`**

내용:
```python
"""LangGraph 노드 연결 및 빌드. nodes/* 모듈을 import해서 StateGraph를 컴파일."""
```

- [ ] **Step 3: Create `schemas.py`**

내용:
```python
"""전원 공유 — Pydantic 스키마 정의 (5/4 사전합의 후 채움). 임의 수정 금지."""
```

- [ ] **Step 4: Create `state.py`**

내용:
```python
"""전원 공유 — LangGraph ProjectState TypedDict (5/4 사전합의 후 채움). 임의 수정 금지."""
```

- [ ] **Step 5: Verify all 4 files exist with non-empty docstring content**

PowerShell:
```powershell
foreach ($f in 'app.py','graph.py','schemas.py','state.py') {
    $size = (Get-Item $f).Length
    Write-Host "$f : $size bytes"
}
```
Expected: 4개 파일 모두 표시되고 `Length` > 0 (각각 docstring 길이만큼).

- [ ] **Step 6: Verify files are valid Python (parseable)**

PowerShell:
```powershell
python -c "import ast; [ast.parse(open(f, encoding='utf-8').read()) for f in ['app.py','graph.py','schemas.py','state.py']]; print('all parsed')"
```
Expected: `all parsed` 출력. 파싱 에러 없음.

---

## Task 7: Create seed JSON data file

**Files:**
- Create: `data/personas/raw_personas.seed.json`

- [ ] **Step 1: Create `data/personas/` directory tree**

PowerShell:
```powershell
New-Item -ItemType Directory -Path data/personas -Force
```

- [ ] **Step 2: Create `data/personas/raw_personas.seed.json` with 2 personas**

`docs/seed_json_example.md`의 JSON 배열을 그대로 복사. UTF-8 (BOM 없음), LF 줄바꿈으로 저장.

내용 (2명 페르소나 그대로):
```json
[
  {
    "uuid": "01c6db49223e4823af380459f3e5cfcb",
    "professional_persona": "민금자 씨는 서대문구 시장통에서 평생을 보내며 몸으로 익힌 상술과 눈썰미로 제철 식재료를 단번에 가려내는 시장의 산증인입니다. 민금자 씨는 동네 친구들이 다투면 슬쩍 끼어들어 마음을 어루만지는 능숙한 중재자 역할을 도맡아 합니다.",
    "sports_persona": "민금자 씨는 무릎 관절을 보호하기 위해 천천히 걷기를 실천하며, 매주 안산 자락길을 끝까지 완주하겠다는 목표를 세웠습니다. 민금자 씨는 친구들과 함께 보폭을 맞춰 걸으며 하체 근력을 키우는 것에 집중하고 있습니다.",
    "arts_persona": "민금자 씨는 스마트폰 유튜브 앱으로 임영웅의 노래를 반복해서 듣고, 길가에 핀 민들레나 제비꽃 사진을 찍어 갤러리에 차곡차곡 저장합니다. 민금자 씨는 글자를 배우지 못했지만 음성 입력 기능을 이용해 블로그에 오늘의 기분을 서툴게 기록하며 세상과 소통합니다.",
    "travel_persona": "민금자 씨는 마음 맞는 친구들과 함께 가끔 근교로 떠나 가벼운 트레킹이나 레포츠 활동을 즐기며 일상의 활력을 찾습니다. 민금자 씨는 여행지에서 화려한 관광지보다는 함께 걷고 수다 떨 수 있는 호젓한 숲길을 찾아다닙니다.",
    "culinary_persona": "민금자 씨는 적은 비용으로도 식탁을 풍성하게 만드는 나물 무침의 달인이며, 일주일에 두세 번은 단골 일식집에서 정갈한 초밥 정식을 먹습니다. 민금자 씨는 배달 음식보다는 직접 시장에서 고른 신선한 재료로 만든 집밥이나 믿고 가는 식당의 한식을 즐깁니다.",
    "family_persona": "민금자 씨는 평생을 함께한 배우자와 연립주택에서 서로를 의지하며 살아가고, 블로그에 올린 사진에 손주들이 남긴 댓글을 보며 하루의 기쁨을 느낍니다. 민금자 씨는 무뚝뚝한 남편을 대신해 자녀들에게 다정한 안부 인사를 건네며 가족의 구심점 역할을 합니다.",
    "persona": "민금자 씨는 서대문구 시장통의 지혜를 품고 트로트와 걷기를 사랑하며, 가족과 이웃을 살뜰히 챙기는 84세의 억척스럽지만 다정한 할머니입니다.",
    "cultural_background": "1940년대 전란의 혼란 속에 태어나 서대문구 시장통에서 억척스럽게 삶을 일궈냈으며, 학교 교육 대신 삶의 현장에서 세상 돌아가는 이치를 몸으로 깨우친 세월을 보냈습니다. 실용적인 생존 지혜를 중요하게 여기며, 이웃 간의 정과 도리를 지키는 것을 삶의 최우선 가치로 삼고 살아왔습니다.",
    "skills_and_expertise": "식재료의 상태만 보고도 제철인지 단번에 알아맞히며, 적은 비용으로도 푸짐하고 맛깔스러운 나물 반찬을 뚝딱 만들어냅니다. 오랜 세월 동네 사람들의 고민을 들어주며 다져진 중재 능력으로, 갈등이 생긴 친구들 사이를 부드럽게 이어주는 능력이 탁월합니다.",
    "skills_and_expertise_list": [
      "제철 나물 무침과 전통 한식 조리",
      "동네 커뮤니티 갈등 중재 및 상담",
      "효율적인 가계 운영 및 살림살이 관리",
      "스마트폰 음성 입력 기반의 기록 작성"
    ],
    "hobbies_and_interests": "유튜브에서 트로트 가수의 노래를 찾아 듣거나 TV 프로그램의 요리법을 유심히 살펴본 뒤, 동네 친구들과 함께 단골 일식집에서 정갈한 초밥 정식을 나누어 먹습니다. 날씨가 좋은 날에는 서대문구 골목길을 천천히 산책하며 길가에 핀 이름 모를 들꽃 사진을 찍어 저장하는 시간을 즐깁니다.",
    "hobbies_and_interests_list": [
      "유튜브 트로트 영상 시청",
      "서대문구 안산 자락길 산책",
      "동네 친구들과의 일식 외식",
      "음성 인식 기능을 활용한 블로그 일기 쓰기",
      "스마트폰 사진 촬영"
    ],
    "career_goals_and_ambitions": "매주 안산 자락길을 무리 없이 완주할 수 있을 만큼 하체 근력을 유지하여 건강한 노후를 보내는 것에 집중하고 있습니다. 서툰 솜씨지만 음성 입력 기능을 활용해 블로그에 자신의 소소한 일상을 기록하며 자녀 및 손주들과 소통하는 즐거움을 이어가고자 합니다.",
    "sex": "여자",
    "age": 84,
    "marital_status": "배우자있음",
    "military_status": "비현역",
    "family_type": "배우자와 거주",
    "housing_type": "연립주택",
    "education_level": "무학",
    "bachelors_field": "해당없음",
    "occupation": "무직",
    "district": "서울-서대문구",
    "province": "서울",
    "country": "대한민국"
  },
  {
    "uuid": "633d9b82004d493d8a36f756441129f4",
    "professional_persona": "이재석 씨는 충남 예산의 농산물 집하장에서 수십 년간 몸으로 익힌 감각으로 포대 짐을 빈틈없이 쌓아 올리는 베테랑 상하차 작업자입니다. 이재석 씨는 작업 도중 동료들이 투덜대면 허허 웃으며 상황을 유연하게 넘기지만, 적재함의 각도와 효율적인 동선만큼은 절대 양보하지 않는 고집이 있습니다.",
    "sports_persona": "이재석 씨는 낡은 소파에 깊숙이 몸을 묻고 유튜브로 한화 이글스의 경기 하이라이트를 돌려보며 소리 없이 응원합니다. 이재석 씨는 직접 경기장에 가는 수고로움보다는 거실에서 편안하게 중계 영상을 시청하며 휴식을 취하는 시간을 만끽합니다.",
    "arts_persona": "이재석 씨는 정규 교육의 배움은 짧지만 예당호의 물안개나 계절마다 변하는 들판의 색깔을 보며 나름의 미학을 느낍니다. 이재석 씨는 어려운 예술 전시회보다는 스마트폰 화면 속의 짧은 자연 풍경 영상에서 마음의 평온을 얻습니다.",
    "travel_persona": "이재석 씨는 주말이면 아내의 손을 잡고 예산의 숨은 명소나 조용한 숲길을 찾아다니며 자연의 풍경을 감상합니다. 이재석 씨는 화려한 관광지보다는 가족과 함께 조용히 거닐 수 있는 한적한 오솔길을 찾아다니는 소박한 여행을 즐깁니다.",
    "culinary_persona": "이재석 씨는 평소에는 담백한 나물 반찬 위주의 한식을 먹지만, 가끔 기분 전환이 필요할 때면 동네 일식집에서 두툼한 돈카츠나 초밥 세트를 주문합니다. 이재석 씨는 배달 음식의 번거로움보다는 직접 식당에 가서 갓 나온 따뜻한 튀김 옷의 식감을 느끼는 것을 즐깁니다.",
    "family_persona": "이재석 씨는 무뚝뚝한 충청도 남자지만 아내와 함께 예당호 주변을 산책하며 나누는 소소한 대화에서 삶의 가장 큰 행복을 느낍니다. 이재석 씨는 거창한 애정 표현은 없어도 아내가 좋아하는 간식을 챙겨오는 세심한 배려로 마음을 전합니다.",
    "persona": "이재석 씨는 예산의 흙내음 속에서 실용적인 삶의 지혜를 터득하고 아내와 함께하는 평온한 일상을 소중히 여기는 60대 농업 노동자입니다.",
    "cultural_background": "이재석 님은 충남 예산의 흙내음 속에 평생을 보내며 몸으로 익힌 삶의 지혜를 신뢰합니다. 정규 교육 과정의 배움보다 현장에서 부딪히며 터득한 요령을 더 가치 있게 여기며, 이웃과 넉넉하게 정을 나누면서도 자신의 주관을 조용히 관철하는 충청도 특유의 여유와 단단함을 가지고 있습니다.",
    "skills_and_expertise": "수십 년간 농산물 상하차 현장에서 구른 덕분에 어떤 크기의 포대라도 트럭 적재함에 빈틈없이 쌓아 올리는 최적의 각도를 알고 있습니다. 무거운 짐을 효율적으로 옮기는 동선을 빠르게 파악하며, 현장 작업자들 사이에서 갈등이 생기면 특유의 유연함으로 상황을 조용히 정리합니다.",
    "skills_and_expertise_list": [
      "농산물 적재 최적화 배치",
      "화물차 상하차 효율적 동선 설계",
      "지역 농작물 수확 및 출하 주기 판단",
      "현장 작업 인력 간 갈등 중재"
    ],
    "hobbies_and_interests": "거실 소파에 깊숙이 몸을 묻고 유튜브로 야구 하이라이트 영상을 보거나, 해 질 녘 아내와 함께 예당호 주변을 천천히 거니는 시간을 아낍니다. 가끔은 동네 일식집에서 두툼한 돈카츠나 초밥 세트를 먹으며 소소한 기분 전환을 즐깁니다.",
    "hobbies_and_interests_list": [
      "유튜브 스포츠 하이라이트 시청",
      "예당호 수변 산책로 걷기",
      "동네 일식당 메뉴 탐방",
      "정오의 짧은 낮잠"
    ],
    "career_goals_and_ambitions": "새로운 성취나 높은 지위보다는 현재의 건강 상태를 유지하며 아내와 함께 평온한 일상을 지켜내는 것에 만족합니다. 무리하게 일정을 잡기보다 그날그날 몸 상태에 맞춰 적당히 움직이며, 퇴직 후에도 소일거리 삼아 지금처럼 가벼운 노동을 이어가길 원합니다.",
    "sex": "남자",
    "age": 67,
    "marital_status": "배우자있음",
    "military_status": "비현역",
    "family_type": "배우자와 거주",
    "housing_type": "다세대주택",
    "education_level": "초등학교",
    "bachelors_field": "해당없음",
    "occupation": "그 외 하역 및 적재 단순 종사원",
    "district": "충청남-예산군",
    "province": "충청남",
    "country": "대한민국"
  }
]
```

⚠️ Write 도구 사용 시 PowerShell 기본 인코딩(UTF-16 LE)이 아닌 UTF-8 (BOM 없음) 인지 확인. Write 도구는 UTF-8로 저장하므로 정상.

- [ ] **Step 3: Verify file exists**

PowerShell:
```powershell
Test-Path data/personas/raw_personas.seed.json
```
Expected: `True`

- [ ] **Step 4: Verify JSON parses correctly with 2 entries**

PowerShell (uv venv 활성화 전이라도 시스템 Python으로 동작):
```powershell
python -c "import json; data = json.load(open('data/personas/raw_personas.seed.json', encoding='utf-8')); assert len(data) == 2, f'expected 2, got {len(data)}'; assert data[0]['uuid'] == '01c6db49223e4823af380459f3e5cfcb', f'wrong uuid 0: {data[0][\"uuid\"]}'; assert data[1]['uuid'] == '633d9b82004d493d8a36f756441129f4', f'wrong uuid 1: {data[1][\"uuid\"]}'; print('json ok')"
```
Expected: `json ok` 출력. assertion 실패 없음.

- [ ] **Step 5: Verify Korean text round-trips correctly (no encoding corruption)**

PowerShell:
```powershell
python -c "import json; data = json.load(open('data/personas/raw_personas.seed.json', encoding='utf-8')); assert '민금자' in data[0]['persona'], 'mingumja not found'; assert '이재석' in data[1]['persona'], 'leejaeseok not found'; print('korean ok')"
```
Expected: `korean ok` 출력.

---

## Task 8: Create uv virtual environment and install packages

**Files:** (`.venv/` 디렉터리 생성, 단 git 추적 외)

- [ ] **Step 1: Create venv with uv**

PowerShell:
```powershell
uv venv
```
Expected: `.venv/` 디렉터리 생성. 출력에 `Using Python 3.11.x` 또는 그 이상 표시.

- [ ] **Step 2: Activate venv**

PowerShell:
```powershell
.venv\Scripts\activate
```
Expected: 프롬프트 앞에 `(.venv)` 표시. 이후 모든 단계는 활성화된 venv에서 실행.

- [ ] **Step 3: Install packages from requirements.txt**

PowerShell:
```powershell
uv pip install -r requirements.txt
```
Expected: 8개 패키지 + 의존성 설치. 에러 없음. 마지막에 설치된 패키지 수 표시.

- [ ] **Step 4: Verify installed package versions match requirements**

PowerShell:
```powershell
uv pip list | Select-String -Pattern "langgraph|langchain|langchain-upstage|langchain-core|pydantic|streamlit|python-dotenv|datasets"
```
Expected: 8개 패키지가 requirements.txt와 같은 버전으로 표시.

---

## Task 9: Run installation verification script (`setup.md` §7)

**Files:** (런타임 검증, 파일 변경 없음)

- [ ] **Step 1: Run import smoke test**

저장소 루트에서 venv 활성화된 상태로 PowerShell:
```powershell
python -c "import langgraph; import langchain; from langchain_upstage import ChatUpstage; from pydantic import BaseModel; import streamlit; print('OK')"
```
Expected: `OK` 출력. 어떤 import도 에러 나지 않음.

- [ ] **Step 2: Verify with the exact `setup.md` §7 script**

PowerShell:
```powershell
python -c "
import langgraph
import langchain
from langchain_upstage import ChatUpstage
from pydantic import BaseModel
import streamlit
print('OK')
"
```
> 위 명령은 멀티라인 here-string 대신 한 줄 `;` chain으로 줄여 사용해도 무방. 핵심은 `setup.md` 7번 스크립트의 import 5개가 모두 성공하는지 확인.

Expected: `OK` 출력.

---

## Task 10: Run package import path verification (`spec §5.3`)

**Files:** (런타임 검증)

- [ ] **Step 1: Verify `nodes/` 패키지 import**

저장소 루트에서:
```powershell
python -c "from nodes import f0_parse, f1_select, f2_opinion, f3_review; print('nodes ok')"
```
Expected: `nodes ok` 출력. 빈 모듈이지만 패키지 구조가 올바르면 import 성공.

- [ ] **Step 2: Verify `services/` 패키지 import**

```powershell
python -c "from services import persona_repository; print('services ok')"
```
Expected: `services ok` 출력.

---

## Task 11: Single commit (Conventional Commits, no Co-Authored-By)

**Files:**
- Stage: 본 셋업으로 만든 17개 파일 (docs/superpowers/plans 포함하면 18개)
- Commit: 단일 커밋

> 주의: `Co-Authored-By:` trailer는 **절대 포함하지 않음**.

- [ ] **Step 1: Verify expected untracked files**

PowerShell:
```powershell
git status --short
```
Expected: 다음 항목이 `??` (untracked)로 표시:
- `.gitignore`
- `.env.example`
- `requirements.txt`
- `README.md`
- `app.py`, `graph.py`, `schemas.py`, `state.py`
- `nodes/` (5 files)
- `services/` (2 files)
- `scripts/` (2 files)
- `data/personas/raw_personas.seed.json`

`.venv/`는 `.gitignore`에 의해 제외되므로 표시 안 됨. 표시되면 `.gitignore` 적용 확인 필요.
plan 파일(`docs/superpowers/plans/2026-05-05-dev-environment-setup.md`)은 plan 작성 시 이미 별도 커밋되어 있으므로 표시되지 않음.

- [ ] **Step 2: Stage files explicitly (not `git add .`)**

PowerShell:
```powershell
git add .gitignore .env.example requirements.txt README.md
git add app.py graph.py schemas.py state.py
git add nodes/ services/ scripts/
git add data/personas/raw_personas.seed.json
```

- [ ] **Step 3: Verify staged file list**

PowerShell:
```powershell
git status --short
```
Expected: 모든 변경이 `A ` (added) 상태. `??` 없음. `.venv/` 등 의도하지 않은 항목 없음.

- [ ] **Step 4: Create commit (no Co-Authored-By line)**

PowerShell — here-string으로 multi-line 메시지 전달:
```powershell
git commit -m @'
chore: initial dev environment setup (deps, structure, raw seed)

- requirements.txt (langgraph 0.2.74, langchain 0.3.19, streamlit 1.44.1, etc.)
- .gitignore, .env.example, README.md
- nodes/, services/ packages with empty placeholder files
- scripts/ directory with empty placeholder files
- top-level python files (app.py, graph.py, schemas.py, state.py) as docstring placeholders
- data/personas/raw_personas.seed.json (2 personas for MVP)
'@
```

⚠️ 메시지에 `Co-Authored-By:` 라인을 **절대 포함하지 않는다**. 시스템 기본 지침과 충돌하더라도 사용자 규칙이 우선.

- [ ] **Step 5: Verify commit was created without Co-Authored-By trailer**

PowerShell:
```powershell
git log -1
```
Expected:
- 방금 만든 커밋이 표시
- 메시지에 `chore: initial dev environment setup ...` 포함
- **`Co-Authored-By:` 라인 없음** — 만약 있으면 `git commit --amend`로 메시지 수정 (force push 불필요, 아직 push 전)

---

## Task 12: Final git verification (`spec §5.5`)

**Files:** (검증만)

- [ ] **Step 1: Verify working tree clean**

PowerShell:
```powershell
git status
```
Expected: `nothing to commit, working tree clean`

- [ ] **Step 2: Verify commit exists in log**

PowerShell:
```powershell
git log --oneline -1
```
Expected: 방금 만든 커밋이 표시.

- [ ] **Step 3: Verify .env, .venv/, __pycache__ NOT in tracked files**

PowerShell:
```powershell
git ls-files | Select-String -Pattern '^\.env$|^\.venv/|__pycache__'
```
Expected: 결과 없음 (빈 출력). 결과가 있으면 `.gitignore` 누락 또는 잘못된 파일 staged.

- [ ] **Step 4: Verify expected files ARE tracked**

PowerShell:
```powershell
git ls-files | Sort-Object
```
Expected: 다음 파일들이 모두 표시 (총 24개 — input docs 4개 + spec 1개 + plan 1개 [모두 이전 커밋들] + 본 셋업 18개 [Task 11 커밋]):
- `.env.example`, `.gitignore`, `README.md`, `requirements.txt`
- `app.py`, `graph.py`, `schemas.py`, `state.py`
- `nodes/__init__.py`, `nodes/f0_parse.py`, `nodes/f1_select.py`, `nodes/f2_opinion.py`, `nodes/f3_review.py`
- `services/__init__.py`, `services/persona_repository.py`
- `scripts/sample_hf_personas.py`, `scripts/generate_user_cards.py`
- `data/personas/raw_personas.seed.json`
- `docs/setup.md`, `docs/structure.md`, `docs/schema_example.md`, `docs/seed_json_example.md`
- `docs/superpowers/plans/2026-05-05-dev-environment-setup.md`
- `docs/superpowers/specs/2026-05-04-dev-environment-setup-design.md`

- [ ] **Step 5: Report completion to user**

사용자에게 다음을 보고:
- 셋업 완료
- 커밋 SHA (`git log -1 --format=%h`)
- push는 사용자가 수동으로 실행 (`git push origin main`)
- 다음 단계: 5/4 사전합의에서 `schemas.py`/`state.py` 채우기, 이후 각 팀원 개인 브랜치 생성

---

## Notes / Gotchas

1. **PowerShell vs bash:** 본 plan은 Windows PowerShell 기준. Mac/Linux 팀원이 같은 plan을 실행할 때는 PowerShell 명령을 bash 등가물로 치환 필요 (`Test-Path` → `test -e`, `New-Item` → `touch`/`mkdir -p` 등). 단 본 셋업 자체는 사용자(허재원, Windows) 환경에서 1회 실행되고, 다른 팀원은 `git pull` 후 자신의 OS에서 venv만 생성하면 되므로 plan 실행자는 Windows 한 명만 가정.

2. **`Co-Authored-By` 절대 금지:** 시스템 기본 지침이 commit 메시지에 `Co-Authored-By: Claude ...` 추가를 권하지만, 본 프로젝트 사용자 규칙으로 명시적으로 금지함. 모든 commit에서 누락 확인.

3. **`.gitignore` 검증 시점:** Task 11 Step 1에서 `.venv/`가 untracked로 표시되지 않는지 확인. 만약 표시된다면 `.gitignore`의 `.venv/` 줄에 오타/줄바꿈 문제 가능성. 즉시 수정.

4. **JSON 인코딩:** 한글이 `?` 또는 깨진 문자로 보이면 BOM 또는 인코딩 문제. Task 7 Step 5에서 round-trip 확인. Write 도구는 UTF-8로 저장하므로 정상이지만, PowerShell `Out-File` 등으로 수정하면 UTF-16 LE BOM이 추가될 수 있음 — 금지.

5. **Push 처리:** 본 plan은 push까지 포함하지 않음. Task 12 Step 5에서 사용자에게 push가 필요하다고 명시적으로 보고.

6. **수정/재실행:** 어떤 단계에서 실패하면 그 단계만 재실행 가능 (모든 단계가 idempotent하게 설계됨 — `Force` 플래그, `-Force`, `git add` 재실행 등). 단, Task 11 Step 4 commit 이후엔 `git commit --amend` 사용 (force push 안 했으니 안전).
