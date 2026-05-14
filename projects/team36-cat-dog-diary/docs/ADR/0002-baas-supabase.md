# ADR-0002: BaaS로 Supabase 채택

- **상태**: Accepted
- **날짜**: 2026-05-01

## Context

MVP 단계에서 다음 인프라 컴포넌트를 빠르게 구축해야 함:
- 사용자 인증 (Google OAuth)
- 관계형 DB (반려동물 프로필, 일기, 사용량)
- 파일 스토리지 (반려동물 사진)
- 향후 RAG 확장 대비 벡터 검색

리소스(시간/인력)가 제한적이므로 자체 구축보다 Managed BaaS 선호.

## Decision

**Supabase를 단일 BaaS로 채택한다.**

- Auth: Supabase Auth (Google OAuth provider)
- DB: Supabase Postgres + RLS
- Storage: Supabase Storage (private bucket + 서명 URL)
- 벡터 검색: Postgres `pgvector` 확장 (RAG 단계에서 활성화)

## Rationale

- Auth/DB/Storage/Vector 한 벤더에서 일관 처리 — 통합 인증/권한이 자연스러움
- RLS로 권한을 DB 레이어에 두면 Next.js BFF 코드가 단순해짐
- pgvector가 같은 DB 안에 있어서 RAG 전환 시 별도 벡터 DB 도입 불필요
- 무료 티어로 MVP 충분
- TypeScript SDK + Python SDK 모두 안정적

## Alternatives Considered

### Firebase
- Auth/Storage는 좋지만 RDB가 아님 (Firestore = 문서 DB)
- **탈락 이유**: 일기 피드 페이지네이션, 일일 사용량 카운트 같은 관계형 쿼리에 부적합

### AWS Cognito + RDS + S3
- 가장 유연
- **탈락 이유**: MVP에 과한 운영 부담. IAM, VPC 설정만으로 며칠 소비

### 자체 Postgres + Auth.js + S3 호환 스토리지
- 통제력 최대
- **탈락 이유**: 인증 구축 시간이 비용. RLS와 동등한 권한 추상화 직접 짜야 함

## Consequences

### Pros
- MVP 부트스트랩 1주 가능
- RLS로 보안 누락 방지
- pgvector 사전 활성화로 RAG 마이그레이션 무중단

### Cons
- Vendor lock-in (RLS, Storage 정책 등 Supabase 특화 코드)
- Postgres 외 DB 엔진 선택 불가
- Edge Function 콜드 스타트 이슈 (사용 시)

### 후속 조치
- **모든 테이블에 RLS 활성화 + owner-based 정책** 의무 (`.claude/rules/rls-policy.md`)
- Storage 버킷은 **private + 서명 URL**만 사용 (public bucket 금지)
- 일정 규모 이상 확장 시 Postgres 마이그레이션 경로 검토 (Supabase → Neon/RDS)
