# [design] 개발 환경 셋업

> 작성일: 2026-05-04
> 대상 저장소: `persona-reviewer`
> 입력 문서: `docs/setup.md`, `docs/structure.md`, `docs/schema_example.md`, `docs/seed_json_example.md`

## 1. 목표와 범위

### 목표

5/5(화) 본격 개발 시작 전에, 5명 팀원 모두가 같은 베이스에서 출발할 수 있도록
`persona-reviewer` 저장소의 환경 파일과 디렉터리 골격을 main 브랜치에 셋업한다.

### 범위에 포함

- Python 가상환경 (uv 사용)
- 환경 파일: `requirements.txt`, `.gitignore`, `.env.example`, `README.md`(한 줄 골격)
- 디렉터리 골격 + 빈 모듈 파일:
  - `nodes/` 패키지 (`__init__.py`, `f0_parse.py`, `f1_select.py`, `f2_opinion.py`, `f3_review.py`) — 빈 파일
  - `services/` 패키지 (`__init__.py`, `persona_repository.py`) — 빈 파일
  - `scripts/` 디렉터리 (`sample_hf_personas.py`, `generate_user_cards.py`) — 빈 파일
- 최상위 Python 파일 (`app.py`, `graph.py`, `schemas.py`, `state.py`) — **한 줄 docstring placeholder만**
- seed 데이터: `data/personas/raw_personas.seed.json` (`seed_json_example.md`의 2명 그대로)

### 범위에서 제외

- 로직 코드 (노드 함수 본문, 서비스 구현, 스크립트 구현, 그래프 빌드, Streamlit UI)
- `schemas.py`/`state.py`의 실제 스키마/State 정의 — 5/4 사전합의 후 별도 커밋으로 채움
- `app.py`/`graph.py`의 실제 구현 — 5/8 통합 단계에서 채움
- `data/personas/persona_cards.seed.json`
  — `RawNemotronPersona` → `TargetUserPersonaCard` 변환은 LLM 가공 의도가 강한 별도 작업
- 실제 `.env` 파일 (각 팀원이 로컬에서 자기 키로 생성)
- DB 셋업 — `schema_example.md` MVP 범위에서 명시적으로 제외(`pgvector DB ❌, seed JSON으로 대체`)

### 성공 기준

`git pull` 받은 팀원이 `setup.md` 7번 "설치 확인" 절차(`import langgraph`, `import streamlit` 등)를
오류 없이 실행할 수 있다.

---

## 2. 최종 파일/디렉터리 구조

셋업 완료 시점의 저장소 상태:

```
persona-reviewer/
├── .git/
├── .gitignore                          # 신규
├── .env.example                        # 신규
├── .venv/                              # uv venv 산출물 (gitignore)
├── README.md                           # 신규 (한 줄 골격)
├── requirements.txt                    # 신규
│
├── app.py                              # 한 줄 docstring placeholder
├── graph.py                            # 한 줄 docstring placeholder
├── schemas.py                          # 한 줄 docstring placeholder (전원 공유)
├── state.py                            # 한 줄 docstring placeholder (전원 공유)
│
├── docs/                               # 기존
│   ├── setup.md
│   ├── structure.md
│   ├── schema_example.md
│   ├── seed_json_example.md
│   └── superpowers/specs/
│       └── 2026-05-04-dev-environment-setup-design.md  # 본 문서
│
├── nodes/
│   ├── __init__.py                     # 빈 파일
│   ├── f0_parse.py                     # 빈 파일
│   ├── f1_select.py                    # 빈 파일
│   ├── f2_opinion.py                   # 빈 파일
│   └── f3_review.py                    # 빈 파일
│
├── services/
│   ├── __init__.py                     # 빈 파일
│   └── persona_repository.py           # 빈 파일
│
├── data/
│   └── personas/
│       └── raw_personas.seed.json      # 2명 (민금자 / 이재석)
│
└── scripts/
    ├── sample_hf_personas.py           # 빈 파일
    └── generate_user_cards.py          # 빈 파일
```

**디렉터리 성격:**
- `nodes/`, `services/` — Python 패키지 (`__init__.py` 포함, import 대상)
- `scripts/` — 실행 스크립트 모음 (패키지 아님, `__init__.py` 없음)
- `data/` — 데이터 디렉터리 (패키지 아님)

---

## 3. 환경 파일 내용

### `requirements.txt`

`setup.md`의 8개 패키지를 정확히 그대로:

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

### `.gitignore`

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

> 주의: `data/personas/raw_personas.seed.json`은 **추적 대상**이므로 와일드카드(`*.json`) 패턴 사용하지 않음.

### `.env.example`

```
UPSTAGE_API_KEY=your_api_key_here
```

### `README.md`

```markdown
# persona-reviewer

LangGraph 기반 페르소나 리뷰어. 자세한 내용은 `docs/setup.md`, `docs/structure.md` 참고.
```

### `data/personas/raw_personas.seed.json`

`seed_json_example.md`의 JSON 배열 그대로 (2개 페르소나):
- `uuid: 01c6db49223e4823af380459f3e5cfcb` — 민금자 (84세 여성, 서대문구, 무직)
- `uuid: 633d9b82004d493d8a36f756441129f4` — 이재석 (67세 남성, 예산, 하역 단순 종사원)

### 최상위 Python 파일 (docstring placeholder)

각 파일은 한 줄 docstring만 가지고 다른 코드는 없음.

`app.py`:
```python
"""Streamlit 진입점. `streamlit run app.py`로 실행."""
```

`graph.py`:
```python
"""LangGraph 노드 연결 및 빌드. nodes/* 모듈을 import해서 StateGraph를 컴파일."""
```

`schemas.py`:
```python
"""전원 공유 — Pydantic 스키마 정의 (5/4 사전합의 후 채움). 임의 수정 금지."""
```

`state.py`:
```python
"""전원 공유 — LangGraph ProjectState TypedDict (5/4 사전합의 후 채움). 임의 수정 금지."""
```

---

## 4. 실행 시퀀스

main 브랜치에서 단계별 실행:

### 단계 1 — 환경 사전 점검

```powershell
python --version          # 3.11 이상 확인
uv --version              # 미설치면: powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
git status                # main, clean 확인
git branch --show-current # main 확인
```

### 단계 2 — 환경 파일 생성

다음 파일 작성:
- `.gitignore`
- `.env.example`
- `requirements.txt`
- `README.md`

### 단계 3 — 디렉터리 + 빈 파일 생성

다음 빈 파일 생성 (모두 0바이트):
- `nodes/__init__.py`
- `nodes/f0_parse.py`
- `nodes/f1_select.py`
- `nodes/f2_opinion.py`
- `nodes/f3_review.py`
- `services/__init__.py`
- `services/persona_repository.py`
- `scripts/sample_hf_personas.py`
- `scripts/generate_user_cards.py`

### 단계 3-2 — 최상위 Python 파일 생성 (docstring placeholder)

저장소 루트에 다음 4개 파일을 Section 3 "최상위 Python 파일" 항목에 명시된 한 줄 docstring 그대로 작성:
- `app.py`
- `graph.py`
- `schemas.py`
- `state.py`

### 단계 4 — seed JSON 생성

`data/personas/raw_personas.seed.json` 작성:
`seed_json_example.md`의 JSON 배열 부분(2명 페르소나)을 그대로 복사.
설명/코멘트 텍스트(`## why?` 섹션 등)는 포함하지 않음.

- 파일 인코딩: **UTF-8 (BOM 없음)** — 한글 페르소나 텍스트가 그대로 보여야 함
- 줄바꿈: LF (Windows에서 작성하더라도 LF로 저장)
- JSON 자체는 valid해야 함 (`json.load`로 파싱 시 에러 없음)

### 단계 5 — uv 가상환경 + 패키지 설치

```powershell
uv venv
.venv\Scripts\activate
uv pip install -r requirements.txt
```

### 단계 6 — 설치 검증

`setup.md` 7번 스크립트 실행:

```python
import langgraph
import langchain
from langchain_upstage import ChatUpstage
from pydantic import BaseModel
import streamlit
print("✅ 세팅 완료!")
```

출력 `✅ 세팅 완료!` 확인.

### 단계 7 — git 커밋

- 단일 커밋 (모든 변경이 환경 셋업이라는 단일 의도)
- Conventional Commits 스타일 사용
- 커밋 메시지 (예시): `chore: initial dev environment setup (deps, structure, raw seed)`
- `Co-Authored-By:` 라인 **포함하지 않음**
- `.venv/`는 `.gitignore`에 의해 자동 제외됨
- main에 직접 커밋
- **push는 사용자가 수동으로 별도 실행** (셋업 자동화에 push 포함하지 않음)

---

## 5. 검증 기준 (Definition of Done)

> 모든 검증은 **저장소 루트(`persona-reviewer/`)에서 venv가 활성화된 PowerShell 세션** 기준으로 실행한다.

### 5.1. 파일 시스템 검증

- 환경 파일 존재: `requirements.txt`, `.gitignore`, `.env.example`, `README.md`
- 최상위 Python 파일 존재 (각각 한 줄 docstring): `app.py`, `graph.py`, `schemas.py`, `state.py`
- 디렉터리/빈 파일 모두 존재 (Section 2의 트리 그대로)
- seed 데이터: `data/personas/raw_personas.seed.json` 존재 및 2개 페르소나 JSON 배열

### 5.2. Python 패키지 import 검증

`setup.md` 7번 스크립트 실행 → `✅ 세팅 완료!` 출력.

### 5.3. import 경로 검증

```python
from nodes import f0_parse, f1_select, f2_opinion, f3_review
from services import persona_repository
```

빈 모듈이지만 import는 성공해야 함 (패키지 구조 정상 확인).

### 5.4. seed JSON 파싱 검증

```python
import json
data = json.load(open("data/personas/raw_personas.seed.json", encoding="utf-8"))
assert len(data) == 2
assert data[0]["uuid"] == "01c6db49223e4823af380459f3e5cfcb"
assert data[1]["uuid"] == "633d9b82004d493d8a36f756441129f4"
```

### 5.5. git 검증

- `git status` → working tree clean
- `git log -1 --oneline` → 환경 셋업 커밋 표시
- `git ls-files` 결과에 `.env`, `.venv/`, `__pycache__/` 미포함 확인

### 5.6. 비범위 (검증 대상 아님)

- LangGraph 그래프 빌드 (graph.py 없음)
- Streamlit 앱 실행 (app.py 없음)
- Upstage API 실호출 (실제 `.env`/API 키는 각자 로컬에서)
- `persona_cards.seed.json` 로드 (별도 작업으로 미뤄짐)

---

## 6. 영향 및 후속 작업

### 본 셋업 직후 가능해지는 작업

- 각 팀원이 `git pull` 후 동일한 venv/패키지 환경 구성
- 각 팀원의 개인 브랜치(`{번호}/feature/...`) 생성
- 노드 개발 시작 (단, `schemas.py`/`state.py` 별도 커밋 후)

### 본 셋업과 별개로 진행되어야 할 후속 작업 (이번 범위 외)

본 셋업의 placeholder 파일들에 실제 내용을 채우는 작업:

1. **`schemas.py` / `state.py` 채우기 (main 직접 커밋)** — placeholder docstring을 유지하면서 실제 스키마/State 정의 추가. `schema_example.md`의 코멘트(`// 제거`, `// 변수로 빼서` 등) 정리 필요
2. **`scripts/sample_hf_personas.py` 구현** — HuggingFace `nvidia/Nemotron-Personas-Korea` 샘플링
3. **`scripts/generate_user_cards.py` 구현** — `RawNemotronPersona` → `TargetUserPersonaCard` LLM 변환
4. **`data/personas/persona_cards.seed.json` 생성** — 위 3번 스크립트 실행 산출물 또는 수동 작성
5. **각 노드 함수(`f0_parse`/`f1_select`/`f2_opinion_a/b`/`f3_review_a/b`) 구현** — 개인 브랜치에서
6. **`services/persona_repository.py` 구현** — `persona_cards.seed.json` 로드
7. **`graph.py` 채우기** — 5/8 통합 시 전원 함께. placeholder docstring 유지하면서 StateGraph 빌드 코드 추가
8. **`app.py` 채우기** — Streamlit UI 단계. placeholder docstring 유지하면서 진입점 코드 추가
