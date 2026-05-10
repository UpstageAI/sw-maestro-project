# docs/ — 팀 문서 인덱스

> **담당**: 전원. 본인 슬라이스에 영향 가는 변경은 PR로만 (인터페이스 변경은 `[interface-change]` 태그 + 5명 react).

루트 `CLAUDE.md`(코드와 협업 룰의 진실)와 별개로, **계획·스펙·디자인 자료**를 카테고리별로 모아둠.

## 디렉토리

```
docs/
├── planning/   # 분담·일정·시작 가이드·사람별 플랜
│   ├── plan.md                 ★ 분담 원본
│   ├── dev_plan.md             일자별 카드 (5/4~5/10)
│   ├── 킥오프_5월4일.md          5/4 비동기 시작 체크리스트 (회의 없음)
│   └── people/                 사람별 맞춤 플랜
│       ├── A_노준영.md         (Flutter Web 프론트)
│       ├── B_박장우.md         (Chat UI + 프로토콜)
│       ├── C_이유준.md         (LangGraph Agent)
│       ├── D_박영준.md         (CRUD calendar/workouts + Tech Lead)
│       └── E_신승민.md         (CRUD health + 시나리오/튜닝 주도)
├── spec/       # 기능·제품 스펙
│   ├── feature_spec.md         F1~F7 사용자 행동·수용 기준
│   └── 프로젝트 기획서 양식_*.md   소마톤 제출 원본 기획서 (불변)
└── design/     # 시각 자료
    ├── flow.html               시스템 플로우 Mermaid 도식 (브라우저로 열기)
    └── ChatGPT Image *.png     메인 화면 디자인 레퍼런스
```

## 어떤 문서를 언제 보나

| 상황 | 문서 |
|---|---|
| "**내가** 오늘/내일 뭐 해야 하지?" | `docs/planning/people/<나>.md` ← 가장 먼저 |
| "내 담당이 뭐였지?" | `docs/planning/plan.md` (원본) → 루트 `CLAUDE.md` 1번 표 |
| "전체 일정 카드는?" | `docs/planning/dev_plan.md` |
| "5/4에 뭐부터 해야 하지?" | `docs/planning/킥오프_5월4일.md` (비동기 시작 체크리스트) |
| "F4가 뭘 보여주기로 했지?" | `docs/spec/feature_spec.md` |
| "기획서 원안이 뭐였지?" | `docs/spec/프로젝트 기획서 양식_*.md` |
| "전체 시스템 흐름이 어떻게 생겼지?" | `docs/design/flow.html` |
| "메인 화면 톤이 어땠지?" | `docs/design/ChatGPT Image *.png` |

## 갱신 규칙

- `plan.md`, 기획서 원본은 **합의된 내용만** 담음 — 단독 수정 금지.
- `dev_plan.md`, `킥오프_5월4일.md`, `feature_spec.md`, `flow.html`은 **인터페이스/일정/기능이 바뀌면 함께 갱신**. `[interface-change]` PR로.
- 코드/디렉토리 구조 진실은 항상 **루트 `CLAUDE.md`** + 각 디렉토리 `CLAUDE.md`. docs/와 충돌 시 코드 쪽 CLAUDE.md가 우선.
