# 개발환경 세팅 가이드

> 5/5(월) 개발 시작 전까지 아래 세팅을 완료해주세요.
> 막히는 부분은 팀 채팅에 바로 공유해주세요.

---

## 1. Python 버전

```
Python 3.11 이상
```

버전 확인:
```bash
python --version
```

---

## 2. 패키지 매니저 선택

> `uv`는 Rust로 만든 패키지 매니저로 pip 대비 10~100배 빠릅니다.
> **uv 사용을 권장**하지만, pip으로 설치해도 동작은 동일합니다.

### ✅ 권장 — uv 사용

**uv 설치**
```bash
# Mac/Linux
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

**가상환경 생성 + 패키지 설치**
```bash
# 가상환경 생성
uv venv

# 활성화 (Mac/Linux)
source .venv/bin/activate

# 활성화 (Windows)
.venv\Scripts\activate

# 패키지 설치
uv pip install -r requirements.txt
```

### pip 사용 (uv 설치가 어려운 경우)

```bash
# 가상환경 생성
python -m venv .venv

# 활성화 (Mac/Linux)
source .venv/bin/activate

# 활성화 (Windows)
.venv\Scripts\activate

# 패키지 설치
pip install -r requirements.txt
```

---

## 3. 패키지 목록

**requirements.txt**
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

> 버전은 5/4 사전합의 때 최종 확정합니다.
> 그 전까지는 위 버전 기준으로 설치해주세요.

---

## 4. API 키 세팅

프로젝트 루트에 `.env` 파일 생성 후 아래 형식으로 작성:

```
UPSTAGE_API_KEY=your_api_key_here
```

> `.env` 파일은 절대 Git에 올리지 않습니다.
> `.gitignore`에 `.env` 포함 여부 반드시 확인해주세요.

---

## 5. .gitignore 확인

아래 항목이 포함되어 있는지 확인:

```
.env
.venv/
__pycache__/
*.pyc
```

---

## 6. 브랜치 세팅

```bash
# main 최신화
git checkout main
git pull origin main

# 개인 브랜치 생성 (5/5 개발 시작 때)
git checkout -b {이름}/f1-input-parsing
```

---

## 7. 설치 확인

아래 코드가 오류 없이 실행되면 세팅 완료입니다.

```python
import langgraph
import langchain
from langchain_upstage import ChatUpstage
from pydantic import BaseModel
import streamlit

print("✅ 세팅 완료!")
```

---

## ❓ 버전 관련 문의

5/4 사전합의 전에 설치하다가 버전 충돌 나면 팀 채팅에 공유해주세요.
`requirements.txt`는 5/4 합의 후 main에 최종 커밋합니다.
