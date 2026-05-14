# ui:webex_summary

### Spec 참조

- SPEC §6.2
- API 설계 §2.2 `ChatUIBlock.webex_summary` / `WebexSummaryItem` (필드 미정 — F-1)
- frontEndSpec.md §3.1 (컴포넌트 매핑) / §3.2 (출처 렌더 규칙) / §5 시연 시나리오 5

### Path

- ChatUIBlock.webex_summary

### 설명

- Webex 요약. 비공식 배너 강제 노출 + 룸별 그룹핑.

---

### 구현 내용

#### 1. 사전 결정 (Pre-implementation Decisions)

| 항목 | 결정 | 이유 |
| --- | --- | --- |
| `WebexSummaryItem` 필드 | **잠정 컨트랙트로 정의 (F-1 미정 명시)** | API.md가 "sidecar PoC 후 확정"이라 비워둔 상태. UI를 막아둘 수 없으므로 시연에 충분한 최소 필드 세트로 진행하고, 백엔드 확정 시 본 파일 + mockChat 만 갱신하면 되도록 격리. |
| 비공식 배너 | **컴포넌트 최상단 강제 1회 노출** | SPEC "비공식 배너 강제 노출" 요건 + frontEndSpec §3.2 "회색 참고 배지". 사용자가 어떤 룸을 보고 있든 "Webex = 비공식"이라는 신호가 항상 시야 안에 있어야 함. |
| 룸별 그룹핑 | **`groupByRoom` 순수 함수로 분리** | 입력 순서를 보존(`order` 배열)하면서 같은 `roomId` 끼리 묶음. UI 컴포넌트는 그룹 결과만 그려서 테스트 용이성 확보. |
| 기존 `WebexThread` | **삭제** | 새 `WebexSummary`가 단일 메시지 나열 → 룸 그룹 → 클러스터 → 하이라이트 4계층을 모두 포함하므로 기존 단일 메시지 전용 컴포넌트는 더 이상 호출되지 않음. |
| `webex` mock kind | **`webex_summary`로 교체** | API.md가 정의한 정식 블록 이름과 일치시킴. discriminated union이라 마이그레이션 누락은 타입 컴파일에서 즉시 검출. |

#### 2. 파일 구조

```
lib/
  types/
    webex.ts                     (신규) WebexSummaryItem / WebexHighlight / groupWebexByRoom
  mockChat.ts                    (수정) webex → webex_summary kind, 2개 룸 / 3개 클러스터 데이터
components/
  chat/
    WebexSummary.tsx             (신규) 비공식 배너 + 룸 그룹 + 클러스터 카드 + 하이라이트
    WebexThread.tsx              (삭제)
    ChatMessage.tsx              (수정) kind 분기 webex → webex_summary
```

#### 3. 타입 컨트랙트 (잠정 — F-1 미정)

```ts
export type WebexHighlight = {
  id?: string;
  author: string;
  text: string;
  createdAt?: string;
};

export type WebexSummaryItem = {
  id: string;
  roomId: string;
  roomName: string;
  topic: string;       // 클러스터 주제
  summary: string;     // 본문 요약 (한국어)
  messageCount: number;
  participants: string[];
  startedAt?: string;
  endedAt?: string;
  highlights?: WebexHighlight[];
  rawRefs?: string[];
};
```

> 백엔드 sidecar PoC 결과로 필드가 확정되면 본 파일과 `lib/mockChat.ts` 만 갱신하면 되도록, 컴포넌트는 옵셔널 필드 부재를 모두 안전하게 처리한다 (`startedAt`/`endedAt`/`highlights`/`rawRefs` 모두 optional).

#### 4. UX 구조

```
WebexSummary
└─ [상단 1회] UnofficialBanner   ← role="note", 항상 노출
└─ RoomGroup × N
   ├─ Header: room icon + roomName + "N건" 칩
   └─ SummaryRow × M
      ├─ topic (h4) + summary (작은 본문)
      ├─ Highlight × K  (인용 박스, 작성자 + 상대 시간 + 본문)
      └─ Footer: 참여자 / 메시지 수 + 시간 범위 / "비공식" 라벨
```

**비공식 배너** (`UnofficialBanner`):
- `role="note"`, `aria-label="비공식 출처 안내"` — 시각/스크린리더 모두에 동일 신호.
- 색조 amber (`border-amber-200 bg-amber-50`) — 출처 칩의 비공식과 동일 톤으로 일관성 유지.
- 메시지 2단 구조: 헤더 강조 ("Webex 공유 스페이스 — 비공식 출처") + 본문 안내.

**룸 그룹** (`RoomGroup`):
- 카드형 컨테이너에 헤더(라운드 아이콘 + 룸명) + 우측 "N건" 카운트 칩.
- 같은 룸 안의 클러스터는 `<ul><li>` 로 의미화하고 `divide-y` 로 시각 분리.

**클러스터 본문** (`SummaryRow`):
- 굵은 topic + 짧은 summary 한국어 그대로(가공 금지, frontEndSpec §6.3).
- 하이라이트는 별도 작은 카드로 분리해 "본문 요약 vs 원문 인용" 차이를 시각적으로 구분.

**푸터**:
- 참여자: 처음 2명 + "외 N명" 형태로 축약.
- 시간: `endedAt` 기준 상대 시간 + 메시지 수. hover 시 절대 시각 범위(`startedAt – endedAt`)를 `title` 속성으로 노출.
- 우측 끝에 `ShieldOff` + "비공식" 라벨 — 카드 단위에서도 한 번 더 신호.

#### 5. 접근성

- `WebexSummary` 자체는 div이지만 그 안의 각 룸은 `<section aria-label="Webex 룸 ... 요약">` 로 영역 구분.
- 비공식 배너는 `role="note"` 로 보조 정보임을 명시(에러/알림 의미가 아님).
- 시간 표시는 본문(상대) + `title` 속성(절대) 조합. 스크린리더는 본문만 읽고, 시각 사용자는 호버로 절대 시각 확인.
- 아이콘은 모두 `lucide-react` 단순 SVG. 의미 있는 라벨이 텍스트로 별도 노출되어 있어 `aria-hidden`/별도 레이블링 불필요.

#### 6. 출처(SourceList)와의 관계

- frontEndSpec §3.2 규칙상 `webex_*` 출처는 항상 `official=false`.
- `webex_summary` 메시지 `sources` 에는 룸 단위 `webex_summary` 타입 출처 2건을 함께 부착해, 답변 하단에 회색 ‘참고’ 칩 그리드도 동시에 노출 → **카드 내부 비공식 배너 + 답변 하단 비공식 칩** 이중 신호.
- `rawRef` 는 `webex://room/...` URI 형태로 두어, 추후 클릭 시 클라이언트에서 직접 룸으로 점프하는 동작을 추가하기 쉬움.

#### 7. Mock 데이터 변경

- 룸 2개:
  - `r-be` "SOMA 5기 · 백엔드 채널" → 클러스터 2개 (AWS 환경변수 / Docker 가이드)
  - `r-general` "SOMA 5기 · 일반 채널" → 클러스터 1개 (워크숍 데모 일정)
- 각 클러스터에 `messageCount`, `participants`, 시간 범위, 1~2개 하이라이트 부착.
- 한 메시지 응답 안에서 **룸 그룹핑**(헤더 / 카운트), **클러스터별 요약·하이라이트**, **비공식 시그널 다중 노출** 모두 시연 가능.

#### 8. 검증

- `npx tsc --noEmit` 통과 — discriminated union의 `webex` → `webex_summary` 마이그레이션 누락 없음 확인.
- `npx eslint app components hooks lib` 통과 — React 16 신규 hook 룰 위반 없음.
- 수동 확인:
  - `/chat` 진입 → Webex 응답에서 amber 배너가 카드 최상단에 노출.
  - 백엔드 채널 카드: 두 클러스터(AWS·Docker)가 `divide-y` 로 분리되어 표시.
  - 일반 채널 카드: 워크숍 클러스터 1개 + 하이라이트 1개 + 12개 메시지 라벨.
  - 답변 하단의 회색 ‘참고 · Webex 요약’ 칩 2개도 동시에 노출되는지 확인.

#### 9. 후속 과제

- [ ] **F-1 확정 반영**: 백엔드가 `WebexSummaryItem` 필드를 확정하면 `lib/types/webex.ts` 1곳만 갱신. 옵셔널 필드 처리는 이미 안전.
- [ ] **룸 단위 접기/펼치기**: 클러스터 수가 많을 때 `<details>` 기반 접기 옵션. 기본 펼침으로 시작.
- [ ] **참여자 아바타**: `participants` 가 ID/이메일이 아닌 이름 문자열이라 현재는 텍스트만 노출. 이미지 URL 필드가 추가되면 head 그룹 컴포넌트로 교체.
- [ ] **하이라이트 클릭 → Webex 룸 직링크**: `rawRef` 가 `webex://...` 스킴이면 OS가 Webex 앱을 열어 줄 가능성. iOS/안드로이드 동작 검증 후 안전하면 링크화.
- [ ] **테스트**: `groupWebexByRoom` 의 순서 보존을 단위 테스트로 고정 (Vitest 도입 시 1번 후보).
