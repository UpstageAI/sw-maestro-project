# ui:mentoring_cards

### Spec 참조

- SPEC §6.2

### Path

- ChatUIBlock.mentoring_cards

### 비고

- MentoringCard 정확 필드 스키마는 sidecar PoC 후 확정 (F-1).

### 설명

- 멘토링 카드 리스트. 신청/취소 액션 버튼 트리거 위치.

---

### 구현 내용

#### 1. 사전 결정 사항

- **타입 위치 (`lib/types/mentoring.ts`)**: F-1 로 표기된 "MentoringCard 필드 미정"을 풀기 위해 시연용 잠정 컨트랙트를 별도 파일로 두었다. 백엔드 sidecar PoC 가 끝나면 이 파일과 `lib/mockChat.ts` 두 곳만 갱신하면 UI 코드 수정이 거의 없도록 설계했다.
- **API 호출 정책**: `sync_status_badge` 와 동일한 정책으로 "처음부터 실제 fetch만 시도" 하기로 결정. `lib/api/actions.ts` 에서 `apiFetch` 를 통해 `/api/v1/actions/execute` 로 POST 한다. 백엔드가 아직 없는 동안에는 클릭 → 모달 → 확인 시 네트워크 에러가 발생하고, 카드 리스트의 인라인 결과 배너에 사용자 친화적 메시지 (예: 409 → "이미 신청되었거나 마감된 멘토링이에요.") 가 노출된다.
- **확인 모달 강제 (frontEndSpec §3.3)**: `requiresConfirmation` 플래그와 무관하게 신청/취소 버튼 클릭 시 항상 `ConfirmDialog` 를 거치도록 했다. 의도하지 않은 신청/취소를 막기 위한 안전장치.
- **카드 상태 머신 위치**: 카드 단일 컴포넌트가 아니라 리스트 래퍼 (`MentoringCardList`) 가 상태 맵을 들고 있다. 이유는 (1) 모달이 한 번에 하나만 떠야 하며, (2) 응답 결과 배너가 카드 리스트 단위로 노출되는 게 더 자연스럽고, (3) 추후 한 메시지 내 여러 카드 간 상태 전이 (예: capacity 갱신) 를 통합 관리하기 쉽기 때문.
- **결과 표시 방식**: 신청/취소 결과를 별도 `ChatMessage(action_result)` 로 추가하지 않고, 카드 리스트 내부에 인라인 배너로 노출했다. 채팅 흐름 상위 (페이지) 의 메시지 배열을 카드에서 직접 변경하면 결합도가 높아지므로, 일단 카드 리스트 자체 책임 범위 안에서 닫았다. 별도 `action_result` 메시지 추가는 후속 PR 로 미룬다.

#### 2. 파일 구조

```
lib/
  types/
    mentoring.ts            # 잠정 MentoringCard 컨트랙트 (F-1)
  api/
    actions.ts              # POST /api/v1/actions/execute 래퍼
components/
  ui/
    ConfirmDialog.tsx       # 모달 (ESC, 백드롭 클릭 닫기, busy 잠금)
  chat/
    MentoringCard.tsx       # 단일 카드 표시 (props-only, 콜백 호출)
    MentoringCardList.tsx   # 상태 머신 + 모달 + 결과 배너 (client)
```

#### 3. 잠정 타입 컨트랙트

`MentoringCard` 의 필드는 sidecar PoC 결과에 따라 변할 가능성이 있어, 다음과 같이 합의 가능한 최소 집합만 우선 정의했다.

```ts
type MentoringStatus = "open" | "applied" | "closed";

type MentoringCard = {
  id: string; // mentoringId
  title: string;
  mentor: { name: string; organization?: string; photoUrl?: string };
  tags: string[];
  description?: string;
  sessionStartedAt: string;
  sessionEndedAt?: string;
  location?: { type: "online" } | { type: "offline"; place: string };
  capacity?: { current: number; max: number };
  status: MentoringStatus;
  applySn?: number;
  qustnrSn?: number;
};
```

UI 단에서는 위 `status` 위에 클라이언트 로컬 상태 (`applying`, `cancelling`) 를 얹어 `MentoringCardLocalStatus` 로 다룬다 (`MentoringCard.tsx`).

#### 4. 카드 UX

- **헤더**: 제목 + 우측 status 배지. 상태별 색·아이콘 차등.
  - `open` 파랑 "신청 가능", `applied` 초록 "신청 완료" + 체크 아이콘, `closed` 회색 "마감", `applying`/`cancelling` 동일 톤 + 스피너.
- **본문**: 멘토(이름/소속) → 일정(`formatSchedule`로 한국어 포맷) → 장소(온/오프라인) → 태그 칩.
- **정원 바 (`CapacityBar`)**: `current/max` 와 백분율 표기. `<80%` 초록, `80~99%` 앰버, `100%` 로즈. `role="progressbar"` + `aria-valuenow/aria-valuemax` 부착.
- **부가 정보**: `applied` 일 때 "접수번호 #N · 시작 30분 전 알림" 가이드 문구 노출. `applying` 일 때 `aria-live="polite"` 안내 문구 노출.
- **액션 버튼 분기**:
  - `applied` → ghost "신청 취소하기" / `cancelling` 중에는 스피너 + 잠금.
  - `closed` → 비활성 "신청 마감".
  - `open` 인데 정원 마감 (`isCapacityFull`) → 비활성 "정원 마감".
  - 그 외 `open` → primary "이 멘토링 신청하기" / `applying` 중에는 스피너 + 잠금.

#### 5. 상태 머신 & 모달 흐름 (`MentoringCardList`)

```
open ──[click 신청]──▶ pending(MENTORING_APPLY) → confirm
       ├─ ok    → status: applying → success → status: applied + 결과 배너(success)
       └─ fail                           → status: 원복(open) + 결과 배너(error)

applied ──[click 취소]──▶ pending(MENTORING_CANCEL) → confirm
        ├─ ok   → status: cancelling → success → status: open + 결과 배너(success)
        └─ fail                            → status: 원복(applied) + 결과 배너(error)
```

- 모달이 떠 있는 동안 (`busy` 인 동안) ESC, 백드롭 클릭, 닫기 버튼은 모두 잠긴다. 더블클릭/중복 요청을 막기 위해 카드 버튼도 `applying`/`cancelling` 동안 disabled.
- 실패 시 `describeError` 가 `ApiError.status` 별로 분기하여 401(세션 만료), 409(중복/마감) 메시지를 사람 말로 풀어낸다. 그 외에는 서버가 내려준 `message` 를 우선 사용한다.

#### 6. ConfirmDialog 디자인

- `role="dialog" aria-modal="true" aria-labelledby aria-describedby` 부착.
- 백드롭은 시각적으로는 `bg-slate-900/40 backdrop-blur-sm`, 의미적으로는 별도 `<button aria-label="모달 닫기">` 으로 두어 클릭 시 닫힘. 키보드 포커스에서는 `tabIndex={-1}` 로 빠지게 함.
- 마운트 시 confirm 버튼으로 `focus()` 이동, ESC 누를 시 `onCancel`. busy 일 때는 모든 닫기 경로가 잠긴다.
- `tone` 으로 신청 (`primary` 파랑) / 취소 (`danger` 로즈) 버튼 색 차등.

#### 7. ChatMessage 통합

`ChatMessage.tsx` 의 `mentoring` 분기는 단순 카드 그리드에서 `MentoringCardList` 호출로 단순화했다. 카드 단위 상태/모달은 모두 리스트 컴포넌트가 캡슐화한다.

```tsx
{message.kind === "mentoring" && (
  <div className="...">
    <p>{message.intro}</p>
    <MentoringCardList items={message.cards} />
  </div>
)}
```

#### 8. Mock 데이터

`lib/mockChat.ts` 의 멘토링 메시지를 새 컨트랙트에 맞춰 4 카드로 확장하여 모든 시각 분기를 한 번에 시연할 수 있게 했다.

| ID  | 시연 의도                        | status    | capacity |
| --- | -------------------------------- | --------- | -------- |
| m-1 | 일반 신청 가능 (기본 흐름)       | `open`    | 8/12     |
| m-2 | 이미 신청한 카드 → 취소 흐름     | `applied` | 11/12    |
| m-3 | 정원 마감 (`open` + capacity 100%) | `open`    | 12/12    |
| m-4 | 운영자가 닫은 마감               | `closed`  | 12/12    |

#### 9. 검증

- `npx tsc --noEmit`: 통과.
- `npx eslint app components hooks lib`: 통과.
- 시각 확인 (수동): `/chat` 페이지에서 4 카드 렌더, 신청 클릭 → 모달 → 확인 시 (백엔드 부재로) 네트워크 에러 → 인라인 에러 배너 노출, 카드 상태는 원복됨.

#### 10. 후속 작업 (Follow-up)

- **F-1 확정 반영**: 백엔드 sidecar PoC 결과로 `MentoringCard` 필드가 확정되면 `lib/types/mentoring.ts` 와 mock 만 갱신.
- **결과를 `action_result` 메시지로 승격**: 현재는 카드 리스트 내부 인라인 배너이지만, 채팅 히스토리 보존을 위해 성공 시 `kind: "action_result"` 메시지를 메시지 배열에 push 하는 흐름이 더 적합. 페이지/스토어 단 상태 머신과 함께 도입.
- **Optimistic UI vs server-truth**: 현재는 응답이 와야 카드 상태를 바꾼다. 응답 지연 (>1s) 이 잦으면 optimistic `applied` 처리 후 실패 시 롤백하는 패턴으로 전환 검토.
- **모달 포커스 트랩**: 현재는 confirm 버튼 자동 포커스만 적용. tab 키로 모달 밖으로 빠지는 문제는 별도 PR 에서 focus-trap 라이브러리 또는 자체 구현으로 보강 예정.
- **취소 후 capacity 동기화**: 취소 성공 시 클라이언트가 `capacity.current` 를 -1 처리하지 않는다 (서버 truth 우선). 추후 응답 payload 에 신규 capacity 가 포함되면 즉시 반영.
