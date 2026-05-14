# ADR-0009: 사진 업로드 흐름 — 클라이언트 직접 업로드 + Storage RLS

- **상태**: Accepted
- **날짜**: 2026-05-03

## Context

기획 §1: 사진 JPG/PNG ≤10MB. Vercel 함수 페이로드 한도(4.5MB hobby)와 충돌. AI Gateway에 사진을 어떻게 전달할지도 결정 필요.

## Decision

### a — 브라우저가 supabase-js로 Storage에 직접 PUT

- Storage 버킷: `pet-photos` (private)
- path 규칙: `{owner_id}/diaries/{yyyy}/{mm}/{uuid}.{ext}`
- Storage RLS — **모든 op (SELECT / INSERT / UPDATE / DELETE)** 동일 정책:
  - `(storage.foldername(name))[1] = auth.uid()::text` (path 첫 segment = owner_id)
  - DELETE 정책 포함: 일기 삭제 시 BFF가 사용자 JWT로 storage object 동반 제거
- 클라이언트 리사이즈: long edge 1024px (Canvas API)
- 업로드 후 path를 BFF에 전달 (예: `/api/diaries/generate` body `photo_path`)

### Vision API 전달

- BFF가 사용자 JWT로 short-lived signed URL(TTL 1h) 발급
- Gateway에 payload로 동봉 → Gateway는 OpenAI Vision에 그대로 forward
- DB(`diaries.photo_path`)에는 path만 저장. 피드 조회 시 BFF가 매번 새 signed URL 발급.

### MIME / 크기 검증

- 클라이언트 1차 (JPG/PNG, ≤10MB).
- BFF 2차 (Storage object metadata HEAD로 type·size 확인). 클라이언트 신뢰 X.

## Rationale

- **Supabase 표준 패턴** — supabase-js + Storage + RLS는 가장 다듬어진 경로.
- **10MB 한도 충족** — Vercel 함수 페이로드 한도 우회.
- **β(JWT) 정합** — RLS로 owner-bound path 강제.
- **단일 방향 흐름** — Gateway는 signing 책임 없음.

## Alternatives Considered

### b — Browser → BFF (multipart) → Storage
- **탈락 이유**: Vercel 함수 페이로드 한도(4.5MB hobby)로 10MB 사진 사실상 불가.

### c — BFF presigned URL 발급 → 클라이언트 PUT
- **탈락 이유**: step 1개 추가, 사전 검증 가치는 `/generate` 시점 검증으로 대체 가능.

## Consequences

### Pros
- 단순 + 표준 패턴.
- RLS만으로 안전.
- Vercel 페이로드 한도 우회.

### Cons
- 클라이언트 supabase-js 의존성 +1.
- 클라이언트 Canvas 리사이즈 코드 필요.

### 후속 조치
- 마이그레이션: `storage.buckets` insert + RLS 정책.
- 클라이언트 Canvas 리사이즈 유틸.
- BFF에서 path → signed URL 발급 유틸.
- 미사용 사진 cleanup (저장 안 된 채 업로드된 사진) — MVP 외, 미래 ADR.
