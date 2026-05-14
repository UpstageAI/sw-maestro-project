# Daily News Agent 로컬 MVP 스펙

작성일: 2026-05-04

## 목표

사용자가 로컬 PC에서 관심 분야와 검색 키워드를 입력하면, 최근 하루 뉴스 샘플을 수집하고 Vector DB에 저장한 뒤 관련 기사를 선별해 뉴스 브리핑 결과물을 확인할 수 있게 한다.

## 배경

코치 피드백에 따라 초기 구현 범위를 줄인다. 뉴스 수집 소스는 하나로 고정하고, 관심 키워드 3개 수준의 샘플 데이터로 end-to-end 동작을 먼저 확인한다. 이후 결과물을 기반으로 데이터 수집, 필터링, 요약 품질을 개선한다.

## MVP 범위

- 로컬 Streamlit UI를 제공한다.
- 뉴스 소스는 Google News RSS만 사용한다.
- 검색 키워드는 최대 3개를 입력받는다.
- 키워드별 최근 하루 뉴스만 수집한다.
- 기사 데이터는 제목, 요약, 링크, 출처, 발행일, 검색 키워드로 정제한다.
- 중복 링크는 제거한다.
- 정제된 기사는 Chroma 로컬 Vector DB에 저장한다.
- 관심 분야 문장을 query embedding으로 변환해 similarity search를 수행한다.
- 상위 기사만 브리핑 생성 단계에 전달한다.
- Upstage API key가 있으면 Upstage embedding/chat 모델을 사용한다.
- Upstage API key가 없으면 demo AI 모드로 전체 흐름과 출력 형태를 확인할 수 있게 한다.

## MVP에서 제외하는 범위

- 웹크롤러 직접 구현
- Naver Search API 연동
- 여러 뉴스 소스 통합
- 로그인/회원가입
- 배포 환경 구성
- 매일 자동 실행 스케줄러
- 고도화된 자동 태깅 파이프라인
- 사용자별 장기 기억 관리
- FE/BE/DE/AI workflow의 완전 분리

## 사용자 흐름

1. 사용자가 Streamlit 앱을 실행한다.
2. 관심 분야를 입력한다.
3. 검색 키워드 최대 3개를 입력한다.
4. 사용자가 `뉴스 수집 및 브리핑 생성` 버튼을 누른다.
5. 시스템이 Google News RSS에서 키워드별 뉴스를 수집한다.
6. 시스템이 기사를 정제하고 중복을 제거한다.
7. 시스템이 기사를 Vector DB에 저장한다.
8. 시스템이 관심 분야 기준으로 관련 기사를 검색한다.
9. 시스템이 선별된 기사로 브리핑을 생성한다.
10. 사용자가 브리핑과 선별된 기사 목록을 확인한다.

## 시스템 흐름

```text
관심 분야 입력
→ 검색 키워드 정규화
→ Google News RSS URL 생성
→ RSS XML 파싱
→ 기사 필드 정제
→ 중복 링크 제거
→ document embedding 생성
→ Chroma upsert
→ query embedding 생성
→ Chroma similarity search
→ Top-K 기사 선택
→ 브리핑 markdown 생성
→ Streamlit 출력
```

## 데이터 모델

기사 1개는 아래 필드를 가진다.

```text
title: 기사 제목
summary: RSS description 정제 결과
link: 원문 또는 Google News 링크
source: 언론사명
published_at: RSS pubDate
keyword: 수집에 사용한 검색 키워드
```

Vector DB 저장 시 document text는 `title + summary`를 사용한다. metadata에는 위 필드를 그대로 저장한다.

## AI 동작

### Demo 모드

`UPSTAGE_API_KEY`가 없을 때 사용한다.

- 결정적 hash 기반 embedding을 생성한다.
- LLM 호출 없이 고정된 markdown 브리핑을 만든다.
- 목적은 요약 품질이 아니라 end-to-end 동작 확인이다.

### Upstage 모드

`UPSTAGE_API_KEY`가 있을 때 사용한다.

- 문서 embedding: `solar-embedding-1-large-passage`
- query embedding: `solar-embedding-1-large-query`
- 브리핑 생성: `solar-pro3`
- model 이름은 `.env`에서 변경 가능하다.

## 오류 처리

- RSS 요청 실패 시 키워드별 오류를 `errors`에 기록한다.
- 검색 결과가 없어도 앱이 중단되지 않고 빈 브리핑을 출력한다.
- 필수 입력인 관심 분야와 키워드가 모두 비어 있으면 사용자에게 오류를 보여준다.
- 외부 API key는 `.env`에서만 읽고 repository에 저장하지 않는다.

## 검증 기준

아래 기준을 만족하면 로컬 MVP가 동작한다고 본다.

- 단위 테스트가 통과한다.
- Python compile check가 통과한다.
- Streamlit 앱이 실행된다.
- 실제 Google News RSS 호출로 기사 수집이 된다.
- 수집된 기사가 Chroma에 저장된다.
- 관심 분야 기준으로 Top-K 기사가 조회된다.
- 브리핑 markdown이 화면에 출력된다.

## 다음 개선 계획

1. LLM으로 관심 분야를 검색 키워드 3~5개로 확장한다.
2. Naver Search API를 추가해 한국어 뉴스 품질을 비교한다.
3. 기사 자동 태깅을 추가한다.
4. 날짜, 출처, 키워드 기반 metadata filtering을 강화한다.
5. 하루 1회 자동 수집 workflow를 추가한다.
6. 팀 작업이 본격화되면 FE, BE, DE, AI workflow를 분리한다.

## 2026-05-05 개선 스펙

### 목표

실제 Upstage API 사용 시 버튼 클릭 후 오래 기다리는 문제를 줄이고, 사용자가 어느 단계에서 시간이 걸리는지 알 수 있게 한다. 또한 이후 품질 개선을 위해 검색 기준과 평가 기준을 문서화한다.

### 변경 범위

- 기본 수집 기사 수를 키워드당 10개에서 3개로 줄인다.
- 기본 요약 기사 수를 8개에서 5개로 줄인다.
- 이미 Chroma에 저장된 기사 링크는 다시 embedding하지 않는다.
- 뉴스 수집/저장 단계와 브리핑 생성 단계를 UI에서 분리한다.
- Streamlit에 단계별 진행 상태를 표시한다.
- 관련 기사 검색 시 키워드 metadata filter를 먼저 적용하고, 결과가 없으면 전체 collection similarity search로 fallback한다.
- 브리핑 품질 평가 체크리스트 문서를 추가한다.

### 검증 기준

- 중복 링크가 이미 저장되어 있으면 Upstage embedding 호출 대상에서 제외된다.
- query 시 검색 키워드 metadata filter가 Chroma에 전달된다.
- 기본 설정값은 `PER_KEYWORD_LIMIT=3`, `TOP_K=5`다.
- 사용자는 UI에서 수집/저장과 브리핑 생성을 따로 실행할 수 있다.
- 단위 테스트, Python compile check, 실제 Upstage 기반 workflow 검증이 통과한다.
