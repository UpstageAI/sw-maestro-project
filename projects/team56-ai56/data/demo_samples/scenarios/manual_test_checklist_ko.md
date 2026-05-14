# 수동 테스트 체크리스트

## 시나리오 A: 기본 성공 흐름

1. `jds/jd_backend_intern_ko.txt` 내용으로 채용 공고 생성
2. 기준 추천 결과를 그대로 확인하거나 일부 가중치 수정 후 확정
3. `candidates/candidate_backend_strong_ko.txt` 업로드
4. 확인 포인트
   - 마스킹 미리보기에서 이름/이메일/연락처가 토큰으로 바뀌는지
   - GitHub status가 `fetched` 또는 네트워크 상황에 따라 실패 사유가 기록되는지
   - ranking에 후보가 추가되는지
   - candidate detail에 evidence가 보이는지

## 시나리오 B: 비교 평가

1. 같은 JD에 아래 파일을 순서대로 추가
   - `candidates/candidate_backend_strong_ko.txt`
   - `candidates/candidate_backend_mixed_ko.txt`
   - `candidates/candidate_no_github_ko.txt`
2. 확인 포인트
   - strong 후보가 mixed/no_github 후보보다 대체로 높은 점수를 받는지
   - GitHub가 없는 후보는 status가 `skipped`인지
   - evidence 내용이 후보별로 달라지는지

## 시나리오 C: GitHub 실패 처리

1. `candidates/candidate_backend_github_fail_ko.txt` 업로드
2. 확인 포인트
   - GitHub status가 `failed`인지
   - failure reason이 저장되고 UI에 보이는지
   - 평가는 완전히 멈추지 않고 계속 진행되는지

## 시나리오 D: 마스킹 프리뷰 확인

1. `candidates/candidate_masking_focus_ko.txt` 업로드
2. 확인 포인트
   - `[NAME_001]`, `[EMAIL_001]`, `[PHONE_001]`, `[RRN_001]` 같은 토큰이 보이는지
   - token mappings 표에 원본과 토큰 매핑이 저장되는지

## 시나리오 E: 다수 후보 랭킹 데모

1. `scenarios/demo_seed_manifest.json` 기준으로 시드 스크립트 실행
2. 백엔드 포지션에서 상위권 후보와 하위권 후보를 비교
3. 확인 포인트
   - strong 계열 후보가 low_fit 계열보다 점수가 높은지
   - GitHub 실패 후보도 전체 파이프라인이 멈추지 않는지
   - 프론트엔드 JD에서는 프론트엔드 후보가 더 높은 점수를 받는지
