# Frontend README

Frontend 담당자와 AI 코딩 도구는 이 폴더에서 Next.js UI를 구현합니다.

## 목표

- 사용자가 한국어 발명 아이디어를 입력할 수 있게 합니다.
- `/api/generate` 호출 결과를 특허 명세서처럼 보기 좋게 표시합니다.
- API 실패 시 fallback 또는 에러 메시지를 보여줍니다.

## 추천 스택

- Next.js 14 App Router
- TypeScript
- Tailwind CSS

## 구현 화면

1. 입력 영역
   - textarea
   - 생성 버튼
   - 엔터테인먼트 목적 디스클레이머

2. 생성 중 상태
   - loading spinner 또는 progress text
   - "특허 문체로 변환 중" 같은 짧은 문구

3. 결과 영역
   - 발명의 명칭
   - 기술분야
   - 배경기술
   - 해결하려는 과제
   - 발명의 구성
   - 청구항
   - 요약
   - sources
   - warnings

## AI에게 요청할 때

```text
frontend/README.md, docs/API_CONTRACT.md, examples/sample_response.json을 읽고
Next.js 14 + TypeScript + Tailwind CSS로 Brainrot Patent의 입력/결과 UI를 만들어줘.
API 필드명은 바꾸지 말고, sample_response.json으로 먼저 화면을 구성해줘.
```

## 실행

```bash
npm install
npm run dev
```

기본 Backend URL은 `http://localhost:8000`입니다. 필요하면 루트 `.env.example`을 참고해 `NEXT_PUBLIC_BACKEND_URL`을 설정합니다.
