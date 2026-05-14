# AGENTS.md

이 repository에서 작업하는 agent와 개발자는 아래 규칙을 따른다.

## 기본 원칙

- 모든 응답과 문서는 한국어로 작성한다.
- 기능을 추가하거나 동작을 바꿀 때는 먼저 `docs/specs/` 아래에 스펙 문서를 작성하거나 기존 스펙을 갱신한다.
- 구현 후에는 테스트와 실행 검증을 double check한다.
- API key, `.env`, Chroma DB 파일, 로컬 실행 산출물은 커밋하지 않는다.
- MVP 단계에서는 과도한 추상화보다 로컬에서 end-to-end 결과물을 확인하는 것을 우선한다.

## 현재 MVP 방향

- 뉴스 소스는 키워드별로 Naver Search News API(한글) 또는 Google News RSS(그 외)로 라우팅한다.
- 관심 키워드는 최대 3개를 사용한다.
- 수집 범위는 최근 하루 뉴스로 제한한다.
- Vector DB는 로컬 Chroma를 사용한다.
- Upstage API key가 있으면 Upstage embedding/chat 모델을 사용한다.
- Upstage API key가 없으면 demo AI 모드로 end-to-end 흐름을 확인할 수 있어야 한다.
- Naver Client ID/Secret이 없으면 한글 키워드도 Google News RSS로 자동 우회한다.

## 작업 전 확인

- `git status --short`로 작업 트리 상태를 확인한다.
- 관련 스펙 문서가 있는지 확인한다.
- 스펙이 없거나 현재 구현과 다르면 먼저 스펙을 추가/수정한다.
- 기존 사용자 변경사항을 되돌리지 않는다.

## 구현 규칙

- 외부 네트워크나 API key 없이 검증 가능한 로직은 단위 테스트를 먼저 작성한다.
- 뉴스 수집, 정제, Vector DB, AI client, workflow 책임을 섞지 않는다.
- 로컬 데모에서 실패해도 사용자가 원인을 알 수 있도록 오류 메시지를 남긴다.
- Upstage API 연동 코드는 `.env` 기반으로만 동작하게 한다.

## 검증 명령

작업 후 최소한 아래 명령을 실행한다.

```bash
python3 -m unittest discover -s tests
python3 -m compileall daily_news_agent app.py
```

의존성 설치 후 로컬 데모를 확인할 때는 아래 명령을 사용한다.

```bash
streamlit run app.py
```

실제 RSS 수집이 포함된 end-to-end 확인은 네트워크 상태에 따라 실패할 수 있다. 실패 시 단순히 성공으로 간주하지 말고, 오류 원인을 기록한다.

## Pull Request 작성

- Pull Request를 작성할 때는 `.github/pull_request_template.md` 또는 `.github/PULL_REQUEST_TEMPLATE/`가 있는지 먼저 확인한다.
- PR template가 존재하면 반드시 그 양식을 따른다.
- template가 없으면 변경 요약, 검증 결과, 남은 위험을 포함해 작성한다.

