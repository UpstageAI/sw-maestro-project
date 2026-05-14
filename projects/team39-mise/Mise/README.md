# Mise — 소설 속 장면을 이미지로

LLM과 이미지 생성 AI를 결합하여 소설 속 텍스트 묘사를 시각화하는 서비스.

## 팀 구성

| 담당 | 이름 | 역할 |
|------|------|------|
| Scene Extraction | 심종한 | 소설 텍스트 → 12개 장면 요소 추출 → 이미지 프롬프트 생성 |
| 이미지 생성 | 임세희 | 생성된 프롬프트 기반 Gemini 이미지 생성 API 연동 |
| 프론트엔드 | 정이현 | Streamlit core UI 구현 |
| 프론트엔드 | 이준혁 | Streamlit interaction UI 구현|
| QA / 통합 | 강현준 | 통합 테스트 및 품질 검증 |

## 빠른 시작

### 1. 저장소 클론

```bash
git clone <repo-url>
cd asm-39-mise
```

### 2. 가상환경 생성 및 패키지 설치

```bash
python -m venv .venv
source .venv/bin/activate  # macOS/Linux
pip install -r requirements.txt
```

### 3. 환경 변수 설정

```bash
cp mise/.env.example mise/.env
```

`mise/.env` 파일을 열어 실제 Gemini API 키를 입력:

```
GOOGLE_API_KEY=AIzaSy...본인의키...
```

API 키 발급: https://aistudio.google.com/apikey (무료, 일일 1500회)

### 4. 테스트 실행

```bash
# 단위 테스트 (API 키 불필요)
GOOGLE_API_KEY=test .venv/bin/python -m pytest tests/ -v --ignore=tests/test_integration.py

# 통합 테스트 (실제 API 호출)
.venv/bin/python -m pytest tests/test_integration.py -v
```

## 프로젝트 구조

```
mise/
├── config.py                     # 환경 변수, 모델 설정
├── models/
│   └── scene_schema.py           # Pydantic 데이터 모델 (4종)
├── prompts/
│   ├── extraction_prompt.py      # Call 1: 소설 → 12개 요소 추출 프롬프트
│   └── prompt_generator.py       # Call 2: 요소 → 영문 프롬프트 생성 프롬프트
├── chains/
│   └── scene_extractor.py        # 핵심 파이프라인 (extract_scene 함수)
└── .env.example                  # API 키 템플릿

tests/
├── test_scene_schema.py          # Pydantic 모델 테스트 (7개)
├── test_extraction_prompt.py     # Call 1 프롬프트 테스트 (3개)
├── test_prompt_generator.py      # Call 2 프롬프트 테스트 (3개)
├── test_scene_extractor.py       # 파이프라인 단위 테스트 (9개, mock)
├── test_integration.py           # 실제 API 통합 테스트 (5개)
└── samples.py                    # 테스트용 한국어 소설 샘플
```

## 다른 팀원이 이어받아 작업하는 방법

### 프론트엔드 담당자

`mise/chains/scene_extractor.py`의 `extract_scene()` 함수를 호출하면 됩니다:

```python
from mise.chains.scene_extractor import extract_scene

# 최초 생성
result = extract_scene("붉은 노을 아래 무너진 성벽 너머로 거대한 마법진이 떠오르고 있었다...")

# 결과 구조
result.elements.character    # "검은 갑옷을 입은 기사" (한국어)
result.elements.background   # "폐허가 된 성벽"
result.prompt.positive_prompt # "cinematic, a knight in black armor..." (영문)
result.prompt.negative_prompt # "excessive gore, explicit content, blurry..."
result.source_type           # {"character": "original", "lighting": "inferred"}

# 사용자가 요소 수정 후 재생성
prev = {"elements": result.elements.model_dump(), "source_type": result.source_type}
modified = extract_scene("...", mode="regenerate", prev_scene=prev)
```

**주의사항:**
- `extract_scene()` 호출 시 `.env`에 `GOOGLE_API_KEY`가 설정되어 있어야 함
- 1회 호출에 Gemini API 2회 소모 (약 10-15초 소요)
- 입력 텍스트는 최대 1000자
- `mise/.env` 파일은 `.gitignore`에 포함되어 있으니 각자 로컬에 생성

### 이미지 생성 담당자

`result.prompt.positive_prompt`와 `result.prompt.negative_prompt`를 받아서 Gemini 이미지 생성 API를 호출하면 됩니다. 프롬프트는 이미 영문으로 변환되어 있습니다.

```python
result = extract_scene(novel_text)
positive = result.prompt.positive_prompt   # 영문 프롬프트
negative = result.prompt.negative_prompt   # 제외할 요소
style = result.prompt.style                # "cinematic"
```

### 프롬프트 튜닝 담당자

수정할 파일:
- `mise/prompts/extraction_prompt.py` → `EXTRACTION_SYSTEM_PROMPT` (Call 1)
- `mise/prompts/prompt_generator.py` → `PROMPT_GENERATOR_SYSTEM_PROMPT` (Call 2)

수정 후 테스트:
```bash
GOOGLE_API_KEY=test .venv/bin/python -m pytest tests/test_extraction_prompt.py tests/test_prompt_generator.py -v
```

## Git 브랜치 전략 (GitHub Flow)

> **Claude Code 사용자 필수:** 이 프로젝트에는 `.claude/skills/git-workflow` 스킬이 등록되어 있습니다. Claude Code로 작업할 때 커밋, 푸시, 브랜치 관련 작업을 요청하면 이 규칙이 자동으로 적용됩니다. 스킬이 없는 환경에서 작업할 때는 아래 규칙을 직접 따라주세요.

**main 브랜치에 직접 커밋하지 않습니다.** 모든 작업은 이슈 → 브랜치 → PR → 머지 순서로 진행합니다.

### 작업 흐름

```
1. GitHub에서 이슈 생성
2. 이슈에서 "Create a branch" 버튼 클릭 → 브랜치 자동 생성
3. 로컬에서 브랜치 받아서 작업
4. Push 후 PR 생성
5. 리뷰 후 main에 머지
```

### 규칙

**1. GitHub에서 이슈를 생성한다**

1. 리포지토리 페이지 → **Issues** 탭 → **New issue**
2. 제목과 내용을 작성 (예: 제목 `이미지 생성 API 연동`)
3. **Submit new issue** 클릭

**2. 이슈에서 브랜치를 만든다**

1. 생성된 이슈 페이지 오른쪽 사이드바에서 **"Create a branch"** 버튼 클릭
2. 브랜치 이름 확인 후 **"Create branch"** 클릭
3. 브랜치가 자동으로 생성되고 이슈와 연결됨

**3. 로컬에서 작업한다**

```bash
# 원격의 새 브랜치를 가져옴
git fetch origin
git checkout <생성된 브랜치명>

# 작업 후 커밋
git add <수정한 파일>
git commit -m "feat: 구현 내용"

# 원격에 push
git push origin <브랜치명>
```

**4. PR 생성 시**

push 후 GitHub에서 **"Compare & pull request"** 버튼이 나타나면 클릭:
- PR 제목: `feat: 구현 내용 요약`
- PR 내용에 이슈가 자동 연결됨 (`Closes #이슈번호`)
- 리뷰어 지정 후 **Create pull request**

**5. 커밋 메시지 규칙**

```
<타입>: <한글 설명>

타입:
feat:     새 기능 추가
fix:      버그 수정
docs:     문서 수정
refactor: 코드 리팩토링
test:     테스트 추가/수정
chore:    설정, 빌드 등 기타 작업
```

### 절대 하면 안 되는 것

- `main` 브랜치에 직접 `git push` 금지
- `git push --force` 금지
- 다른 사람의 브랜치에 함부로 커밋하지 않기

## 기술 스택

| 구분 | 기술 |
|------|------|
| 언어 | Python 3.9+ |
| LLM 프레임워크 | LangChain + langchain-google-genai |
| LLM 모델 | Gemini 2.5 Flash |
| 데이터 검증 | Pydantic v2 |
| 테스트 | pytest |
| UI (예정) | Streamlit |
