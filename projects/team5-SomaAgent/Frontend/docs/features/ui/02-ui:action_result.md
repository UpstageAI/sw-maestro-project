# ui:action_result

### Spec 참조

- SPEC §6.2, §4.4
- API 설계 §2.2 `ChatUIBlock.action_result` / §3.1 `ActionExecutionResponse`
- frontEndSpec.md §3.1(컴포넌트 매핑), §3.3(액션 실행 흐름)

### Path

- ChatUIBlock.action_result

### 설명

- 액션 결과 배너 (성공/부분실패). 캘린더 실패 시 부분 실패 표시.

---

### 구현 내용

#### 1. 사전 결정 (Pre-implementation Decisions)

| 항목 | 결정 | 이유 |
| --- | --- | --- |
| 타입 위치 | `lib/types/action.ts` (별도 파일) | API.md §3.1과 1:1 매칭되는 단일 진실 소스. mock과 실제 응답이 동일 타입을 공유하도록 분리. |
| 톤 분기 | **`success` / `partial` / `failed` 3단계** | SPEC "캘린더 실패 시 부분 실패 표시" 요구를 그대로 표현. 파생 함수 `deriveActionResultTone` 으로 분기 일원화. |
| 409 `ACTION_CONFLICT` 표시 | **기본은 모달이 우선, 배너는 fallback** | frontEndSpec §3.3 "409는 모달로 표시" 규정에 따라 1차 노출은 호출 측(`MentoringCardList`)에서 모달/즉시 토스트로 처리. 다만 백엔드가 `200 OK + status:"failed" + error.code:"ACTION_CONFLICT"` 형태로 내려줄 가능성도 열어두므로, 본 배너의 `ErrorSummary` 는 일반 에러 처리 로직으로 그 케이스도 자연스럽게 흡수한다. |
| 출처(SourceChip) 노출 | `action_result` 블록 위에서는 **숨김** | 운영 결과 배너에 출처 칩이 같이 붙으면 혼란. 다른 agent kind에선 그대로 유지. |
| `requiresConfirmation` 모달 | 본 PR 범위 밖 | 카드/액션 버튼 → 모달 → `/actions/execute` 흐름 중 **응답 표시 단계만** 구현. 모달은 후속 PR에서 카드 컴포넌트와 함께 다룸. |

#### 2. 파일 구조

```
lib/
  types/
    action.ts                       (신규) ActionType / ApplicationData / CalendarInviteData / ActionResult / 톤 파생
  mockChat.ts                       (수정) action_result kind 추가 + 시연용 결과 2건
components/
  chat/
    ActionResultBanner.tsx          (신규) 배너 컴포넌트
    ChatMessage.tsx                 (수정) `kind === "action_result"` 분기
```

#### 3. 타입 컨트랙트 (API.md §3.1과 정합)

```ts
type ActionType = "MENTORING_APPLY" | "MENTORING_CANCEL";

type ActionResult = {
  actionType: ActionType;
  status: "success" | "failed";
  message: string;
  data?: {
    application?: ApplicationData;       // applySn / qustnrSn / mentoringId / title / sessionStartedAt
    calendarInvite?: CalendarInviteData; // status: created | skipped | failed
  };
  error?: { code: string; message: string; recoverable: boolean };
  traceId?: string;
};
```

`ChatUIBlock.action_result.results` 가 `ActionResult[]` 이므로 같은 타입을 그대로 import 해 mock에서도 사용. 백엔드 연결 시점에 `apiFetch<ActionResult>` 만 끼우면 된다.

#### 4. 톤 파생 규칙 (`deriveActionResultTone`)

```
status === "failed"                                  → "failed"
status === "success" && calendarInvite === "failed"  → "partial"
otherwise                                            → "success"
```

캘린더 invite는 보조 작용이므로 본 액션이 실패한 경우엔 캘린더 상태와 무관하게 `failed` 로 통일. 반대로 본 액션 성공 + 캘린더 실패는 SPEC 명시 그대로 `partial`.

#### 5. 배너 UX

| 톤 | 색상 | 상단 라벨 | 본문 강조 |
| --- | --- | --- | --- |
| `success` | emerald | "신청 완료" / "취소 완료" | 멘토링 정보 + 캘린더 등록 완료 한 줄 |
| `partial` | amber | "부분 완료" | 멘토링 정보 + 캘린더 실패 박스 (재시도 안내) |
| `failed` | rose | "실패" | `error.code`/`error.message` + recoverable 시 재시도 안내 |

세부:

- **헤더 영역**: 둥근 아이콘(✓ / ⚠ / ✕) + 액션 라벨(`신청 완료` 등) + `actionType` 칩(`멘토링 신청` / `멘토링 취소`).
- **본문**: `result.message` (백엔드가 한국어로 내려주는 사용자 노출 문구). frontEndSpec §6.3 "한국어 그대로 표시" 규칙 준수.
- **`ApplicationSummary`**: 멘토링 제목 / 시작 시각(있을 때만) / 접수번호(`#applySn`). `qustnrSn`은 사용자에게 의미 없으므로 미노출.
- **`CalendarSummary`**: `created` / `skipped` / `failed` 3분기 각각 별도 마이크로 컴포넌트. `failed` 메시지에는 SPEC §6.2가 요구하는 "신청은 완료됐지만 캘린더 등록 실패" 문구를 한국어로 명시.
- **`ErrorSummary`**: 코드(monospace 느낌) + 메시지 + `recoverable === true` 일 때 "잠시 후 다시 시도할 수 있어요" 안내.
- **시간 포맷**: 1번 PR에서 만든 `formatAbsoluteTime`을 재사용 (`sessionStartedAt`).

#### 6. 접근성

- 컨테이너 `role`을 톤별로 분기:
  - `failed` → `role="alert" aria-live="assertive"` (실패는 즉시 인지)
  - 그 외(`success` / `partial`) → `role="status" aria-live="polite"` (스트리밍 중에도 방해되지 않게)
- 아이콘은 모두 `lucide-react` 단순 SVG, 텍스트 라벨이 별도로 있어 스크린리더에 의미 손실 없음.

#### 7. ChatMessage 통합

`message.kind === "action_result"` 분기를 추가하고, `results` 배열을 순회하며 배너를 렌더링.

```tsx
{message.kind === "action_result" && (
  <div className="space-y-2">
    {message.results.map((result, idx) => (
      <ActionResultBanner key={...} result={result} />
    ))}
  </div>
)}

{message.kind !== "action_result" && message.source && (
  <SourceChip source={message.source} />
)}
```

`results: ActionResult[]` 형태인 이유는 한 응답에 여러 액션 결과가 함께 올 수 있는 SPEC을 따른 것(예: `MENTORING_CANCEL` + 보충 안내).

#### 8. Mock 데이터 변경

기존 `system / status` 토스트는 본 컴포넌트로 대체했다.

- `ar-1`: **success** — `MENTORING_APPLY` + 캘린더 `created` (이벤트 ID prefix 표시).
- `ar-2`: **partial** — 신청은 성공이지만 `calendarInvite.status === "failed"` (Calendar API rate limit). 사용자에게 "캘린더 앱에서 직접 추가" 안내.

이 두 케이스로 SPEC §6.2 요구(`성공/부분실패`)를 시연 시나리오 1번 화면에서 그대로 확인 가능.

#### 9. 검증

- `npx tsc --noEmit` 통과 (discriminated union narrowing 정상).
- `npx eslint app components hooks lib` 통과.
- `npm run dev` 로 `/chat` 진입 시:
  - 마이크로서비스 멘토링 신청 → 초록 ✓ "신청 완료" + 캘린더 등록 완료 라인
  - 데이터베이스 멘토링 신청 → 주황 ⚠ "부분 완료" + 캘린더 실패 박스 + 재시도 안내
- 키보드/스크린리더 테스트는 macOS VoiceOver로 `failed` 케이스가 즉시 읽히는지 확인 (현재 mock에는 failed 케이스가 없어 컴포넌트 단위로만 확인).

#### 10. 후속 과제

- [ ] **확인 모달**: 카드 "신청"/"취소" 버튼 → confirm modal → `/actions/execute` 흐름 (frontEndSpec §3.3).
- [ ] **409 ACTION_CONFLICT** 모달: "이미 신청됨/마감됨" 등 상태 충돌을 별도 모달로 표시 (배너 아님).
- [ ] **trace 토글 (Cmd+Shift+T)**: SPEC §6.4 디버그 모드에서 `traceId` 노출 (현재는 props에만 보관).
- [ ] **`MENTORING_CANCEL` 매핑 실패** 시 카피 (F-7 미정 항목) — `error.code` 기반 분기 카피 정의.
- [ ] **카드 상태 갱신 연동**: `/actions/execute` 응답 도착 시 같은 mentoringId 카드의 `status` 를 `applied`/`cancelled` 로 갱신하는 상위 상태 머신 (다음 PR).

---

#### 11. 후속 PR 반영 (2026-05-07 코드 리뷰)

리뷰에서 "결과는 채팅 메시지 히스토리의 한 줄로 남는 것이 UX First 관점에 맞다" 는 의견이 있었고, `05-ui:mentoring_cards` 의 인라인 결과 배너를 `action_result` 메시지로 승격하는 후속 PR 에서 본 컴포넌트가 다음과 같이 활용되도록 정착됐다.

- 카드 신청/취소 → 확인 모달 → `/actions/execute` 호출.
- 응답이 도착하면 `MentoringCardList` 가 `ChatMessagesContext.appendMessage` 를 통해 `kind: "action_result"` 메시지를 채팅 메시지 배열에 push.
- 그 메시지는 `ChatMessage` 의 기존 분기에서 `ActionResultBanner` 로 렌더 — 본 PR 에서 만든 컴포넌트가 그대로 사용된다.
- 실패 케이스(예: 백엔드 부재로 인한 네트워크 오류)는 `MentoringCardList` 가 클라이언트 측에서 `ActionResult { status: "failed", error }` 를 합성하여 동일 흐름으로 push. `ErrorSummary` 가 그대로 표시한다.

따라서 본 PR 의 "응답에 들어온 결과만 렌더링" 책임 범위는 그대로 유지되고, 모달/카드 상태 머신은 호출 측이 책임지는 구조가 명확해졌다.
