# Presentation Kit — review-ops-agent

SOMA 17기 57조 발표용 4개 콘텐츠 파일. **이미 준비된 발표 양식 슬라이드에 본문만 옮겨 사용** 하는 용도.

## 파일 구성

| 파일 | 내용 | 활용 |
|---|---|---|
| [`slides.md`](./slides.md) | 7장 슬라이드 본문 (총 310s ≈ 5분 10초) | 발표 양식 슬라이드 각 페이지에 본문 paste |
| [`poster.md`](./poster.md) | 1장 포스터 본문 (5 zone 레이아웃) | 포스터 양식의 해당 zone 에 paste |
| [`speaker-notes.md`](./speaker-notes.md) | 슬라이드별 발표 멘트 + 강조 + 전환 | 리허설 / 발표 시 옆에 배치 |
| [`qa.md`](./qa.md) | 예상 Q&A 10문 + 라이브 데모 사고 대응 | 발표 직전 훑기 / Q&A 시간 대응 |

---

## 슬라이드 구성 (7장)

발표 순서는 사용자 지정 4개 섹션을 그대로 매핑:

| # | 슬라이드 | 시간 | 사용자 지정 섹션 |
|---|---|---|---|
| 1 | 표지 | 15s | — |
| 2 | 왜 이 서비스인가 | 45s | ① 서비스 선정 배경 |
| 3 | 핵심 가치 (차별점 3) | 40s | ① + 핵심 가치 |
| 4 | 서비스 핵심 기능 (일상 / 회고 / 대화) | 50s | ② 서비스 핵심 기능 |
| 5 | Workflow — 왜 LangGraph 인가 | 40s | ③ Agent Workflow 기획 |
| 6 | Workflow — 3 graph 한눈에 (mermaid) | 60s | ③ + Workflow 구성 |
| 7 | Workflow 시연 (4 시나리오 압축, 마무리 포함) | 60s | ④ Agent Workflow 시연 |

총 310s. 3~5분 발표 budget 안.

---

## 사용 흐름

1. 발표 양식 슬라이드를 연다 (이미 준비된 SOMA 발표 템플릿 등).
2. `slides.md` 의 슬라이드별 본문을 *각 페이지에 옮겨 붙임*:
   - H1 = 페이지 제목
   - bullet / 표 / mermaid = 페이지 본문 영역
   - HTML 주석 (`<!-- 시간: ... -->`) 은 무시 (메타 정보)
3. mermaid 다이어그램 (Slide 6) 은:
   - 발표 양식이 mermaid 렌더링을 지원하면 그대로 paste
   - 지원 안 하면 [mermaid.live](https://mermaid.live) 에서 PNG export 후 이미지로 삽입
4. 포스터 양식이 별도면 `poster.md` 의 5 zone 본문을 zone 별로 옮김.

발표 양식이 없으면 일반 PPT / Google Slides / Keynote 어디든 같은 방식으로 적용 가능.

---

## Speaker notes 활용

[`speaker-notes.md`](./speaker-notes.md) 은 슬라이드별로:

- 시간 예산 (15s ~ 60s)
- 멘트 (한국어 발표어, 분당 ~280자 페이싱)
- 강조 포인트 (어떤 단어 / 숫자에 힘 줄지)
- 다음 슬라이드 전환 문구

발표 리허설 시 슬라이드 옆에 두고 stopwatch 로 페이싱 확인. 페이싱 표가 문서 끝에 있음.

5분 발표면 §5 (기획) 또는 §6 (구성) 에서 10초 압축 가능. 3분 빠른 발표면 §5 제거 + §6 단축 권장.

---

## 발표 시나리오 매핑

`slides.md` 의 슬라이드 7 (시연) 은 [`docs/demo/scenarios.md`](../demo/scenarios.md) 의 3 시나리오를 압축한 것. 영상 데모를 함께 보여줄 경우 [`docs/demo/script.md`](../demo/script.md) 의 4분 영상을 슬라이드 6 끝에서 cut-in 가능.

## Checklist (발표 D-1)

- [ ] 발표 양식 슬라이드에 `slides.md` 본문 7장 적용 완료
- [ ] mermaid 다이어그램 (Slide 6) 렌더링 또는 이미지 삽입 확인
- [ ] 표지 슬라이드의 *로고 / 팀 학번* placeholder 교체
- [ ] 포스터 zone 5개에 `poster.md` 본문 적용
- [ ] `speaker-notes.md` 인쇄본 또는 태블릿
- [ ] 5분 stopwatch 리허설 2회
- [ ] 발표 PC 에서 시각 효과 (mermaid · 표) 렌더 확인
