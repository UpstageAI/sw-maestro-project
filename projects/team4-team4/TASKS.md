# Tasks

2주 MVP에서 각 담당자가 AI와 함께 작업할 수 있도록 쪼갠 TODO입니다.

## 공통

- [ ] `AGENTS.md`와 `docs/API_CONTRACT.md`를 읽고 본인 역할 범위 확인
- [ ] 발표용 입력 3개를 기준으로 동작 확인
- [ ] API 필드명 변경이 필요하면 팀에 먼저 공유

## 1번 발표/기획 - 임준현

- [ ] 발표용 문제 정의 30초 버전 작성
- [ ] 발표용 입력 3개 확정
- [ ] 실패 대비 샘플 결과 고정
- [ ] 최종 데모 흐름을 `docs/DEMO_SCRIPT.md`에 반영
- [ ] scope creep이 생기면 `docs/MVP_SCOPE.md` 기준으로 정리

## 2번 Frontend - 박서연

- [ ] `frontend/README.md` 기준으로 Next.js 프로젝트 생성
- [ ] 아이디어 입력 화면 구현
- [ ] 생성 중 loading 상태 구현
- [ ] `examples/sample_response.json` 기반 결과 미리보기 UI 구현
- [ ] `/api/generate` 호출 연결
- [ ] 오류 메시지와 fallback 결과 표시 처리

## 3번 Backend & Agent - 이진중

- [ ] `backend/README.md` 기준으로 FastAPI 프로젝트 생성
- [ ] `/health` 엔드포인트 구현
- [ ] `/api/generate` 엔드포인트 구현
- [ ] 입력 검증 구현
- [ ] LLM 호출 실패 시 sample response fallback 구현
- [ ] Frontend에서 호출 가능하도록 CORS 설정

## 4번 AI, RAG - 황현석

- [ ] `prompts/system_prompt.md`를 LLM 호출에 연결
- [ ] `prompts/claim_prompt.md`로 청구항 생성 품질 개선
- [ ] 검색 결과를 title, url, snippet 구조로 정리
- [ ] 출처가 없을 때 URL을 지어내지 않도록 프롬프트 보강
- [ ] 발표용 입력 3개에 대한 샘플 결과 생성

## 5번 Playwright - 추웅재

- [ ] Playwright 설치 및 기본 테스트 생성
- [ ] 입력창에 발표용 입력을 넣는 테스트 작성
- [ ] 생성 버튼 클릭 후 결과 제목이 보이는지 확인
- [ ] 오류 발생 시 fallback 메시지가 보이는지 확인
- [ ] 데모 직전 실행할 체크리스트 작성

## 통합 마일스톤

- [ ] Day 3: 단일 LLM 또는 fallback으로 JSON 생성 성공
- [ ] Day 5: Frontend와 Backend 연결 성공
- [ ] Day 7: 발표용 입력 1개 end-to-end 성공
- [ ] Day 10: 검색/RAG 또는 샘플 근거 표시 성공
- [ ] Day 12: Playwright 데모 흐름 통과
- [ ] Day 14: 발표 리허설 완료

