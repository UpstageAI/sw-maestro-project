# ui:source_list

### Spec 참조

- SPEC §6.2
- API 설계 §2.2 `Source` 타입 / `ChatUIBlock.source_list`
- frontEndSpec.md §3.1 (컴포넌트 매핑) / §3.2 (출처 렌더 규칙)

### Path

- ChatUIBlock.source_list

### 설명

- 출처 칩 목록. official=true → 공식 배지, false → 참고 배지. 답변 하단 공통.

---

### 구현 내용

#### 1. 사전 결정 (Pre-implementation Decisions)

| 항목 | 결정 | 이유 |
| --- | --- | --- |
| 타입 위치 | `lib/types/source.ts` (별도 파일) | API.md §2.2 `Source` 와 1:1 매핑되는 단일 진실 소스. `lib/types/action.ts` 와 같은 패턴. |
| 데이터 부착 위치 | **`ChatMessage`(agent kind) 내부 `sources?: Source[]`** | API.md 응답이 `sources` 필드를 메시지 레벨로 가지고 있으며, 별도 `source_list` UI 블록도 같은 컴포넌트(`<SourceChips />`)로 렌더링됨. 메시지에 부착해 두면 두 경로 모두 자연스럽게 흡수. |
| 칩 레이아웃 | **`flex-wrap` 그리드** | frontEndSpec §3.1 "답변 하단 칩 그리드" 표현 그대로. 줄바꿈은 자연스럽게. |
| 비공식 출처 안내 | **칩 색 변경 + 리스트 하단 한 줄 안내 + 칩 hover 툴팁** | frontEndSpec §3.2 "비공식 출처 안내 툴팁" 요건. 시각/스크린리더/마우스 호버 3중으로 신호. |
| 링크 처리 | `url` 있으면 `<a target="_blank">`, 없으면 `<span>` + `rawRef` 툴팁 | frontEndSpec §3.2 규칙 그대로. |
| 시간 포맷 | `formatRelativeTime(createdAt)` 노출 + hover 시 절대 시각 (`title` 속성) | frontEndSpec §3.2 "상대 시간 + 호버 절대 시간". 별도 라이브러리 없이 1번 PR의 유틸 재사용. |

#### 2. 파일 구조

```
lib/
  types/
    source.ts                       (신규) Source / SourceType / SOURCE_TYPE_LABEL
  mockChat.ts                       (수정) ChatSource → Source[] 컨트랙트 교체
components/
  ui/
    SourceChip.tsx                  (재작성) 새 Source 컨트랙트 + 공식/참고 배지 + 타입 아이콘
  chat/
    SourceList.tsx                  (신규) 칩 그리드 + 비공식 안내 배너
    ChatMessage.tsx                 (수정) `sources?` → <SourceList /> 렌더링
```

#### 3. 타입 컨트랙트 (API.md §2.2와 정합)

```ts
type SourceType =
  | "notice" | "notice_pdf"
  | "mentoring"
  | "application"
  | "webex_message" | "webex_summary"
  | "calendar"
  | "other";

type Source = {
  id?: string;
  type: SourceType;
  title: string;
  url?: string;
  createdAt?: string;   // ISO 8601
  collectedAt?: string; // ISO 8601
  official: boolean;    // OpenSoma=true, Webex=false
  rawRef?: string;
};
```

`SOURCE_TYPE_LABEL` 매핑을 함께 제공해 칩에 한국어 라벨(`공지`, `멘토링`, `Webex 메시지` …)을 표시.

#### 4. 출처 렌더 규칙 (frontEndSpec §3.2 매핑)

| 규칙 | 구현 |
| --- | --- |
| `official=true` → 파란 "공식" 배지 | `bg-blue-600 text-white` 라운드 배지 + `ShieldCheck` 아이콘. 칩 자체는 `bg-blue-50 border-blue-200`. |
| `official=false` → 회색 "참고" 배지 + 비공식 툴팁 | `bg-slate-500 text-white` 배지. 칩 hover 툴팁 첫 줄에 `[비공식 출처 — 답변에 참고했지만 공식 채널은 아닙니다]` 명시. 리스트 하단에는 별도 한 줄 안내. |
| `url` 있으면 새 탭, 없으면 텍스트 | `<a href target="_blank" rel="noreferrer">` vs `<span>`. URL 없는 경우 툴팁에 `참조: ${rawRef}` 동봉. |
| `createdAt` 상대 시간 + 호버 절대 시간 | 칩 본문에 `· 3일 전`, 칩 `title` 속성에 `작성: YYYY-MM-DD HH:mm` + `수집: …` 추가. |

타입별 아이콘 (`lucide-react`):

| `type` | 아이콘 |
| --- | --- |
| `notice`, `notice_pdf` | `FileText` |
| `mentoring` | `Users` |
| `application` | `Inbox` |
| `webex_message`, `webex_summary` | `MessagesSquare` |
| `calendar` | `CalendarDays` |
| `other` | `Link2` |

#### 5. 컴포넌트 책임 분리

- **`SourceChip`** (atomic): 단일 출처 1건 렌더. 링크 여부에 따라 `<a>` vs `<span>` 분기, 공식/참고 배지·타입 라벨·제목·상대시간·외부 링크 아이콘 5요소를 한 줄에 배치. 제목은 `max-w-[180px] truncate` 로 길이 폭주 방지.
- **`SourceList`** (= 스펙의 `<SourceChips />`): 다중 칩을 `flex-wrap`으로 그리드 배치 + 헤더(`출처 · N건`) + 비공식이 섞여 있을 때 하단 안내 1줄. `aria-label="출처"` 로 영역 의미 부여.

스펙은 컴포넌트 이름을 `<SourceChips />` 로 적었지만, 본 구현에서는 **칩 자체(`SourceChip`)와 그것을 묶는 리스트(`SourceList`)** 로 책임을 명확히 나눴다.

#### 6. 접근성

- `SourceList` 는 `<section aria-label="출처">` 로 감싸고 내부를 `<ul>/<li>` 로 의미화.
- `SourceChip` 의 공식/참고 배지에 `aria-label="공식 출처" | "참고 출처"`. 시각 라벨이 짧지만 스크린리더로는 정확히 읽힘.
- 타입 라벨(아이콘+한국어)은 `aria-hidden="true"` 처리 — 칩 `aria-label` 에 이미 `공식 출처: <title>` 형태로 핵심 정보가 들어가므로 중복 방지.
- hover 툴팁(`title`) 은 마우스 사용자만 보지만, 모든 정보가 `aria-label` 또는 본문에 이미 노출돼 있어 보조 정보 역할만 한다.

#### 7. ChatMessage 통합

- 기존 `message.source?: ChatSource` 필드 → `message.sources?: Source[]` 로 교체.
- agent kind가 `text/mentoring/notice/webex` 일 때 공통적으로 `sources` 가 있으면 하단에 `<SourceList />` 렌더링.
- `kind === "action_result"` 는 출처 노출 대상이 아니라 분기에서 명시적으로 제외 (이전 PR과 동일 정책).

```tsx
{message.kind !== "action_result" &&
  message.sources &&
  message.sources.length > 0 && (
    <SourceList sources={message.sources} />
  )}
```

타입 시스템상 `AgentBase` 인터섹션을 도입해 `sources?: Source[]` 를 4개 kind에 한 번에 부여 — 중복 선언 제거.

#### 8. Mock 데이터 변경

| 메시지 | 출처 구성 |
| --- | --- |
| `a-1` 멘토링 응답 | `mentoring` (공식, OpenSoma URL) 1건 |
| `a-2` 공지 요약 | `notice` + `notice_pdf` 2건 (둘 다 공식) — 다중 칩 그리드 시연 |
| `a-3` Webex 검색 | `webex_message` 2건 (둘 다 비공식, `rawRef` 만 보유) — 회색 배지 + URL 없음 툴팁 흐름 시연 |

이로써 `/chat` 한 화면에서 다음을 모두 확인 가능:
- 단일 공식 출처
- 복수 공식 출처(타입 다른 두 가지)
- 복수 비공식 출처 + URL 부재 + 하단 안내 배너

#### 9. 검증

- `npx tsc --noEmit` 통과 — discriminated union narrowing 정상.
- `npx eslint app components hooks lib` 통과.
- 수동 확인:
  - 멘토링 응답 하단에 파란 ‘공식’ + 멘토링 아이콘 칩 1개.
  - 공지 응답 하단에 ‘공식 · 공지’와 ‘공식 · 공지 PDF’ 두 칩이 줄바꿈 없이 나란히.
  - Webex 응답 하단에 회색 ‘참고’ 칩 두 개 + “참고(회색) 출처는 공식 채널이 아닙니다…” 안내 1줄.
  - 칩 hover 시 brower native tooltip 으로 `[공식 출처]` / `[비공식 출처 — …]` + 제목·작성·수집 시각 노출.

#### 10. 후속 과제

- [ ] **F-5 결정 반영**: OpenSoma 페이지 직접 링크 가능 여부 확정 시, `official=true` 칩의 `url` 정책(인증 우회/리다이렉트 등) 단일화.
- [ ] **별도 `source_list` UI 블록 분기**: API 응답에서 `ui[].type === "source_list"` 로 별도 블록이 오는 경우, 메시지 본문과 분리된 카드 스타일이 필요하면 `<SourceList variant="block" />` 옵션 추가.
- [ ] **테스트**: `SourceChip`/`SourceList` 의 공식/비공식 분기를 RTL + jest-axe 로 a11y snapshot 작성 (Vitest 도입 시).
- [ ] **번역**: i18n 도입 시 `SOURCE_TYPE_LABEL` 을 자원 파일로 분리.
