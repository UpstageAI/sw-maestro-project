# HireProof

개인정보 노출을 줄이면서도 채용 담당자가 지원자를 비교·검토할 수 있도록 돕는 프라이버시 중심 채용 평가 보조 시스템입니다.

## 프로젝트 개요

HireProof는 채용 공고를 입력받아 평가 기준을 추천하고, 지원자 이력서를 분석한 뒤, 명시적인 개인정보를 마스킹하고, 아래 두 가지 관점의 점수를 생성합니다.

- JD 적합도 점수: 지원자가 채용 공고와 평가 기준에 얼마나 부합하는지
- 근거 정렬도 점수: 지원자의 주장과 GitHub 같은 공개 아티팩트가 얼마나 일치하는지

현재 버전은 시연과 검증을 위한 MVP입니다. 완벽한 자동 판정 시스템보다는, 평가 흐름을 구조화하고 근거를 남기는 데 초점을 두고 있습니다.

## 해결하려는 문제

초기 지원자 스크리닝 과정은 종종 다음과 같은 문제가 있습니다.

- 평가자마다 기준이 달라 일관성이 떨어짐
- 왜 이런 평가를 했는지 근거 추적이 어려움
- 이력서에 포함된 개인정보가 그대로 노출될 수 있음

HireProof는 이를 아래 단계로 구조화해 개선하려고 합니다.

1. 채용 공고 기반 평가 기준 생성
2. 지원자 이력서 수집 및 파싱
3. 개인정보 마스킹
4. 점수와 근거 생성
5. 감사 로그 저장

## 핵심 기능

- JD 기반 평가 기준 추천
- TXT, PDF, DOCX 이력서 업로드 지원
- 이름, 이메일, 전화번호 등 명시적 PII 마스킹
- 지원자 점수화 및 근거 제시
- GitHub 공개 프로필/저장소 스냅샷 수집
- 한국어/영어 Streamlit UI
- SQLite 기반 로컬 저장
- Mock 모드와 Upstage LLM 모드 지원

## 기술 스택

- Python 3.12
- FastAPI
- Streamlit
- SQLite
- LangGraph
- Requests
- Pydantic
- Upstage Solar 모델 연동

## 프로젝트 구조

```text
app/
  agent/      # 채팅형 워크플로우 및 오케스트레이션
  api/        # FastAPI 라우트
  core/       # 도메인 모델
  db/         # SQLite 저장소 계층
  scripts/    # 데모 데이터 적재 스크립트
  services/   # 파서, 마스킹, 평가기, GitHub, 파이프라인
  tests/      # 단위 테스트
  ui/         # Streamlit UI
data/
  demo_samples/   # 시연용 샘플 JD와 후보자
  uploads/        # 로컬 업로드 파일 저장
  artifacts/      # SQLite 및 체크포인트 저장
```

## 동작 방식

1. 사용자가 채용 공고 제목과 내용을 입력합니다.
2. 시스템이 평가 기준을 추천합니다.
3. 사용자가 기준을 검토하거나 수정한 뒤 확정합니다.
4. 지원자를 업로드하거나 텍스트로 입력합니다.
5. 시스템이 개인정보를 마스킹한 뒤 평가를 수행합니다.
6. JD 적합도와 근거 정렬도 점수를 생성합니다.
7. 근거 스니펫과 감사 로그를 저장합니다.

## 로컬 실행 방법

1. 가상환경 생성

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

2. 의존성 설치

```bash
pip install -e ".[dev]"
```

3. Streamlit 데모 UI 실행

```bash
python -m streamlit run app/ui/streamlit_app.py
```

4. 필요 시 FastAPI 서버 실행

```bash
python -m uvicorn app.main:app --reload
```

## 환경 변수 설정

Upstage 기반 평가기를 사용할 경우 `.env.example`을 참고해 `.env`를 구성합니다.

```bash
export HIREPROOF_EVALUATOR_MODE=upstage
export HIREPROOF_UPSTAGE_API_KEY=your_api_key_here
export HIREPROOF_UPSTAGE_MODEL=solar-pro3
export HIREPROOF_UPSTAGE_BASE_URL=https://api.upstage.ai/v1
```

환경 변수를 주지 않으면 로컬 개발에서는 mock 모드로 실행할 수 있습니다.

## 테스트

```bash
python -m pytest
```

## 데모 시나리오

시연용 샘플 데이터를 미리 적재하려면 아래 명령을 사용합니다.

```bash
python -m app.scripts.seed_demo --job-key backend
```

이 명령은 로컬 SQLite에 아래 데이터를 채워 넣습니다.

- 백엔드 채용 공고 1개
- 해당 공고에 대한 추천 평가 기준
- 여러 명의 샘플 지원자
- 지원자별 사전 계산된 평가 결과

## 현재 한계

- GitHub 검증은 공개 프로필 및 저장소 신호 기반의 휴리스틱에 가깝습니다.
- 점수 품질은 프롬프트 품질과 공개 근거의 양에 영향을 받습니다.
- 개인정보 마스킹은 규칙 기반이며, 완전한 NER 기반 익명화는 아닙니다.
- HWP 지원과 더 풍부한 외부 근거 연동은 아직 미구현 상태입니다.
- 현재 MVP는 채용 결정을 대신하는 시스템이 아니라, 평가 보조 도구를 목표로 합니다.

## 향후 계획

1. 근거 추출의 정확도와 인용 품질 개선
2. 한국어 특화 PII/NER 처리 강화
3. 포트폴리오와 추가 문서 소스 연동
4. 랭킹 및 리뷰어 피드백 플로우 개선
