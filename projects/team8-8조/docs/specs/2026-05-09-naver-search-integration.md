# Naver Search API 통합 스펙

작성일: 2026-05-09

## 배경

현재 daily-news-agent는 Google News RSS만 사용해 모든 키워드를 수집한다. 한국어 키워드의 경우 Naver Search API(news 엔드포인트)가 한국어 매체 커버리지와 응답 품질이 더 좋은 경우가 많다. 본 스펙은 한국어 키워드를 자동으로 Naver로 라우팅하고, 그 외 키워드는 기존 Google News RSS로 처리하는 라우터 기반 통합을 정의한다.

## 목표

- 한국어 키워드는 Naver Search API(news)로 수집한다.
- 비한국어 키워드는 기존 Google News RSS 흐름을 유지한다.
- Naver 자격증명이 없는 환경에서도 end-to-end 흐름이 깨지지 않게 한다.
- 외부 네트워크 없이 단위 테스트가 가능해야 한다.

## 비목표

- 관심 분야(`interest`) 다중 입력 지원은 본 스펙 범위 밖이다.
- 검색 키워드 한도(현재 3개) 변경은 다루지 않는다.
- Naver 블로그/카페/웹 검색 등 news 외 엔드포인트는 다루지 않는다.

## 요구사항

### 키워드별 라우팅

- 키워드 문자열에 한글(`[가-힣ㄱ-ㆎ]`)이 한 글자라도 포함되면 Naver를 사용한다.
- 그 외에는 Google News RSS를 사용한다.
- 한 키워드는 정상 경로에서 한 소스만 호출한다(중복 수집 방지).

### Fallback

| 상황 | 동작 |
|---|---|
| 한글 키워드 + `NAVER_CLIENT_ID`/`NAVER_CLIENT_SECRET` 둘 다 설정됨 | Naver 호출 |
| 한글 키워드 + Naver 키가 비어 있음 | `errors`에 경고 메시지 1회 기록 후 Google로 우회 |
| 한글 키워드 + Naver 호출 실패(`NaverNewsError`) | `errors`에 사유 기록 후 동일 키워드로 Google 재시도 |
| 비한글 키워드 | Google (변경 없음) |

같은 실행 안에서 "Naver 키 미설정" 경고는 한 번만 기록한다(키워드마다 반복 노출하지 않음).

### Naver Search News API

- 엔드포인트: `https://openapi.naver.com/v1/search/news.json`
- 헤더: `X-Naver-Client-Id`, `X-Naver-Client-Secret`
- 쿼리:
  - `query`: 키워드 원문
  - `display`: 요청 limit(1–100, 호출 시 limit 사용)
  - `sort`: `date`(최신순)
- 응답 매핑(`items[]` → `NewsArticle`):
  - `title` → `title` (HTML 태그 제거)
  - `originallink`(있으면) 또는 `link` → `link`
  - `description` → `summary` (HTML 태그 제거)
  - `pubDate` → `published_at`
  - 소스: `originallink`의 호스트 도메인을 추출, 실패 시 `"Naver News"`
  - `keyword`: 호출 키워드

### 오류 처리

- 네트워크/HTTP 오류, JSON 파싱 실패는 `NaverNewsError`로 래핑한다.
- `NaverNewsError`는 워크플로 라우터에서 잡아 `errors`에 메시지로 기록하고 Google fallback을 트리거한다.

## 아키텍처

### 모듈 구성

```text
daily_news_agent/
├── news_source.py     # GoogleNewsRssClient 유지, NewsRouter 추가
├── naver_news.py      # 신규: NaverNewsClient, NaverNewsError, parse_naver_news_response
├── preprocessor.py    # is_korean(keyword) 추가
├── config.py          # Settings에 naver_client_id, naver_client_secret 추가
└── workflow.py        # NewsRouter를 통해 키워드별 dispatch
```

### NewsRouter 인터페이스

```python
class NewsRouter:
    def __init__(
        self,
        google_client: GoogleNewsRssClient,
        naver_client: NaverNewsClient | None,  # 키 없으면 None
    ) -> None: ...

    def fetch(
        self,
        keyword: str,
        limit: int,
    ) -> tuple[list[NewsArticle], list[str]]:
        """기사 리스트와 (라우팅/우회) 메시지 리스트를 함께 반환."""
```

`workflow.collect_and_store`는 기존 `news_source.fetch(...)` 호출을 `news_router.fetch(...)`로 교체하고, 반환된 메시지를 `errors`에 누적한다(메시지는 사용자에게 정보 차원에서 노출).

### Settings

```python
@dataclass(frozen=True)
class Settings:
    ...
    naver_client_id: str
    naver_client_secret: str
```

`.env.example`에 다음 추가:

```env
NAVER_CLIENT_ID=
NAVER_CLIENT_SECRET=
```

`app.py`에서 `Settings`로부터 두 값이 모두 비어 있지 않으면 `NaverNewsClient`를 만들어 `NewsRouter`에 주입, 그렇지 않으면 `naver_client=None`.

## 테스트 계획

전부 외부 네트워크/실제 API 호출 없이 동작.

- `tests/test_naver_news.py` (신규)
  - 샘플 JSON 응답 → `NewsArticle` 매핑(필드/HTML 정제 검증)
  - `originallink` 비어 있을 때 `link` 사용
  - 빈 `items` → 빈 리스트
  - 깨진 JSON → `NaverNewsError`
  - HTTP 4xx → `NaverNewsError`(`requests` 모킹)

- `tests/test_preprocessor.py`
  - `is_korean("AI") == False`
  - `is_korean("반도체") == True`
  - `is_korean("AI 반도체") == True`(혼합)
  - `is_korean("") == False`

- `tests/test_workflow.py`
  - 한글 키워드 + Naver 클라이언트 있음 → Naver fake가 호출됨
  - 한글 키워드 + Naver 클라이언트 없음 → 경고 1건, Google fake 호출
  - 한글 키워드 + Naver 호출 예외 → 에러 기록 후 Google 재시도
  - 비한글 키워드 → Google fake만 호출
  - "Naver 키 미설정" 경고는 다회 키워드 호출에서도 1번만 errors에 추가

- `tests/test_config.py`
  - `NAVER_CLIENT_ID`/`NAVER_CLIENT_SECRET` 환경변수 → Settings에 반영
  - 미설정 시 빈 문자열

## 영향도

- `CollectionResult.errors`가 정상 흐름에서도 정보성 메시지를 담을 수 있게 됨(예: "Naver 키 미설정으로 Google News로 우회"). UI는 이미 `st.warning`으로 노출하므로 별도 변경 없음.
- `NewsArticle.source`는 Naver 결과의 경우 도메인(예: `chosun.com`) 또는 `Naver News`. 기존 UI에 그대로 표시됨.
- 사이드바에 한 줄 정보(`AI 모드` 옆에 `뉴스 소스: Naver+Google` / `Google only`) 추가.

## 작업 항목

1. `daily_news_agent/naver_news.py` 작성 + 단위 테스트.
2. `preprocessor.is_korean` + 테스트 추가.
3. `news_source.NewsRouter` 작성 + 워크플로 통합.
4. `Settings` 필드 추가 + `.env.example` 갱신 + 테스트.
5. `app.py`에서 NaverNewsClient/NewsRouter 주입 및 사이드바 표시.
6. README/AGENTS.md 갱신.
7. `python3 -m unittest discover -s tests`, `python3 -m compileall daily_news_agent app.py` 검증.
