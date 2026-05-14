# 냥멍일기

반려동물 사진과 키워드를 입력하면 AI가 1인칭 시점 일기를 생성해 아카이빙하는 사이드 프로젝트.

> 배포: https://cat-dog-diary-web.vercel.app

## 기능

- Google OAuth 로그인
- 펫 등록·수정·소프트 삭제 (호칭/종/성별)
- 사진 + 키워드 → 1인칭 일기 자동 생성 (OpenAI gpt-4o-mini Vision)
- 결과가 마음에 안 들면 피드백을 곁들여 재생성 (세션당 최대 3회)
- 채택한 일기는 펫별 캐러셀에 보관, 상세 모달에서 본문 확인·삭제 가능
- 일일 한도: 신규 5회 + 재생성 3회 (KST 자정 리셋)
- 모든 LLM 호출 LangSmith로 trace

## 아키텍처

```
[Browser]
    │
    ▼
[Vercel]   Next.js (App Router + BFF)
    │      supabase-js (auth · storage · RLS query)
    │
    ▼      X-Internal-Secret + Bearer JWT
[Railway]  FastAPI + LangGraph
    │      Vision 추론 → safety check → (필요 시 재시도)
    ▼
[OpenAI]   gpt-4o-mini Vision
```

- **Auth**: Supabase Auth (Google OAuth)
- **DB / Storage**: Supabase Postgres + Storage. 모든 테이블 owner 기반 RLS, 사진은 1시간 TTL 서명 URL
- **BFF (Vercel)**: Next.js Route Handlers — 한도 검증, signed URL 발급, Gateway 호출
- **Gateway (Railway)**: FastAPI + LangGraph. BFF→Gateway 신뢰는 X-Internal-Secret + Supabase JWT(JWKS) 이중 검증
- **관측**: LangSmith (session_id, seq, owner_id_hash 메타데이터)
