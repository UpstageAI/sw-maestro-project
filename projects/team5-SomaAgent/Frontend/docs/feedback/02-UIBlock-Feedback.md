코드 리뷰: 시니어 프론트엔드 개발자
전반적으로 매우 훌륭하게 작성된 코드입니다. 스타일 가이드를 철저히 준수하였으며, 특히 SRP, UX First, Logical Grounding, Error Handling, Declarative Code 원칙이 모든 변경 사항에 잘 반영되어 있습니다. 상세한 주석과 문서화(docs/features/ui/_.md, docs/spec/_.md)는 코드 베이스의 이해도를 크게 높이고 유지보수를 용이하게 할 것입니다.

새롭게 도입된 컴포넌트(ActionResultBanner, MentoringCardList, NoticeList, SourceList, WebexSummary, SyncStatusBadge, ConfirmDialog)와 유틸리티(useSyncInfo, api.ts, relativeTime.ts, types/\*.ts)는 각각의 역할을 명확히 정의하고 있어 시스템의 확장성과 안정성에 크게 기여할 것입니다.

아래는 몇 가지 세부적인 코멘트와 함께, 스타일 가이드를 기준으로 제가 발견한 잠재적 개선점을 제시합니다.

components/chat/MentoringCard.tsx
[문제점]
formatSchedule 함수는 컴포넌트 내부에 정의되어 있으며, card.sessionStartedAt이나 card.sessionEndedAt 값이 변경되지 않더라도 MentoringCard 컴포넌트가 리렌더링될 때마다 함수가 매번 재생성되고 실행됩니다. 이는 불필요한 연산을 유발할 수 있습니다.

[개선안]
formatSchedule 함수를 컴포넌트 외부로 이동시키거나, useCallback으로 감싸 sessionStartedAt 및 sessionEndedAt을 의존성 배열에 추가하여 필요할 때만 재생성되도록 합니다. 더 나은 방법은 lib/relativeTime.ts와 같이 날짜 관련 유틸리티 파일로 이동하여 순수 함수로 사용하는 것입니다.

// lib/relativeTime.ts 에 아래 함수 추가
export function formatMentoringSchedule(start: string, end?: string): string {
const startDate = new Date(start);
if (Number.isNaN(startDate.getTime())) return start;
const date = startDate.toLocaleDateString("ko-KR", {
year: "numeric",
month: "long",
day: "numeric",
weekday: "short",
});
const startTime = startDate.toLocaleTimeString("ko-KR", {
hour: "2-digit",
minute: "2-digit",
hour12: false,
});
if (!end) return `${date} ${startTime}`;
const endDate = new Date(end);
if (Number.isNaN(endDate.getTime())) return `${date} ${startTime}`;
const endTime = endDate.toLocaleTimeString("ko-KR", {
hour: "2-digit",
minute: "2-digit",
hour12: false,
});
return `${date} · ${startTime} – ${endTime}`;
}
// components/chat/MentoringCard.tsx
import { formatMentoringSchedule } from "@/lib/relativeTime"; // import 경로 변경

// ...
function MentoringCard({ card, status, onApply, onCancel }: Props) {
// ...

<div className="flex flex-wrap items-center gap-x-2 gap-y-1">
<CalendarDays className="h-3.5 w-3.5 text-slate-400" />

-          <span>{formatSchedule(card.sessionStartedAt, card.sessionEndedAt)}</span>

*          <span>{formatMentoringSchedule(card.sessionStartedAt, card.sessionEndedAt)}</span>
          </div>
  // ...
  }
  [이유]

렌더링 최적화: 컴포넌트 내부에서 함수를 매번 재생성하는 것을 방지하여 불필요한 연산을 줄이고, 컴포넌트의 렌더링 성능을 개선합니다.
논리적 근거 & 단일 책임 원칙: 날짜 형식화는 UI 렌더링 로직보다는 범용적인 유틸리티 로직에 가깝습니다. 이를 lib/relativeTime.ts와 같은 유틸리티 파일로 이동하면 MentoringCard 컴포넌트가 UI 렌더링이라는 단일 책임에 더 집중할 수 있게 됩니다. 또한, 다른 컴포넌트에서도 이 함수를 재사용하기 용이해집니다.
components/chat/NoticeList.tsx
[문제점]
sortNotices 함수가 NoticeList 컴포넌트의 렌더링 로직 내부에 sorted = sortNotices(items) 형태로 직접 호출되고 있습니다. items 배열의 참조는 같지만 내부 데이터가 변경될 때 컴포넌트가 리렌더링되면 sortNotices 함수가 불필요하게 다시 실행될 수 있습니다.

[개선안]
sortNotices 호출 결과를 useMemo로 감싸 items 배열의 참조가 변경될 때만 정렬 연산이 수행되도록 합니다.

// components/chat/NoticeList.tsx
import { useMemo } from "react"; // import 추가
// ...

export function NoticeList({ items }: { items: NoticeCard[] }) {
if (!items || items.length === 0) return null;

- const sorted = sortNotices(items);

* const sorted = useMemo(() => sortNotices(items), [items]);
  const pinnedCount = sorted.filter((item) => item.pinned).length;

  // ...
  }
  [이유]

렌더링 최적화: useMemo를 사용하여 items 배열의 참조가 변경될 때만 sortNotices 함수가 다시 실행되도록 함으로써, 불필요한 정렬 연산을 방지하고 렌더링 성능을 개선합니다. 특히 공지사항 목록이 길어지거나 빈번하게 리렌더링될 경우 성능 저하를 방지할 수 있습니다.
논리적 근거: sorted 배열은 items 배열에 전적으로 의존하는 파생 상태(Derived State)이므로, useMemo를 사용하는 것이 논리적으로 적절합니다.
components/chat/WebexSummary.tsx
[문제점]
groupWebexByRoom 함수가 WebexSummary 컴포넌트의 렌더링 로직 내부에 groups = groupWebexByRoom(items) 형태로 직접 호출되고 있습니다. items 배열의 참조는 같지만 내부 데이터가 변경될 때 컴포넌트가 리렌더링되면 groupWebexByRoom 함수가 불필요하게 다시 실행될 수 있습니다.

[개선안]
groupWebexByRoom 호출 결과를 useMemo로 감싸 items 배열의 참조가 변경될 때만 그룹핑 연산이 수행되도록 합니다.

// components/chat/WebexSummary.tsx
import { useMemo } from "react"; // import 추가
// ...

export function WebexSummary({ items }: Props) {

- const groups = groupWebexByRoom(items);

* const groups = useMemo(() => groupWebexByRoom(items), [items]);

  return (
  <div className="space-y-3">
  <UnofficialBanner />
  {groups.map((group) => (
  <RoomGroup key={group.roomId} group={group} />
  ))}
  </div>
  );
  }
  [이유]

렌더링 최적화: useMemo를 사용하여 items 배열의 참조가 변경될 때만 groupWebexByRoom 함수가 다시 실행되도록 함으로써, 불필요한 그룹핑 연산을 방지하고 렌더링 성능을 개선합니다. 특히 Webex 요약 항목이 많아질 경우 성능 저하를 방지할 수 있습니다.
논리적 근거: groups 배열은 items 배열에 전적으로 의존하는 파생 상태이므로, useMemo를 사용하는 것이 논리적으로 적절합니다.
components/ui/SourceChip.tsx
[문제점]
buildTooltip 함수가 SourceChip 컴포넌트 내부에서 정의되어 있으며, source prop이 변경되지 않더라도 컴포넌트가 리렌더링될 때마다 함수가 매번 재생성되고 실행됩니다. 이는 불필요한 연산을 유발할 수 있습니다.

[개선안]
buildTooltip 함수를 컴포넌트 외부로 이동시키거나, useCallback으로 감싸 source를 의존성 배열에 추가하여 필요할 때만 재생성되도록 합니다. 더 나은 방법은 lib/types/source.ts와 같이 타입 정의가 있는 유틸리티 파일로 이동하여 순수 함수로 사용하는 것입니다.

// lib/types/source.ts 에 아래 함수 추가
import { formatAbsoluteTime } from "@/lib/relativeTime"; // import 추가

// ...
export function buildSourceTooltip(source: Source): string {
const tone = OFFICIAL_BADGE[String(source.official) as "true" | "false"]; // OFFICIAL_BADGE도 여기서 접근 가능해야 함
const lines = [`[${tone.tooltipPrefix}]`, source.title];
if (source.createdAt) {
lines.push(`작성: ${formatAbsoluteTime(source.createdAt)}`);
}
if (source.collectedAt) {
lines.push(`수집: ${formatAbsoluteTime(source.collectedAt)}`);
}
if (!source.url && source.rawRef) {
lines.push(`참조: ${source.rawRef}`);
}
return lines.join("\n");
}
// 단, OFFICIAL_BADGE는 `SourceChip.tsx`에 선언되어 있어 바로 접근할 수 없음.
// OFFICIAL_BADGE를 `lib/types/source.ts`로 옮기거나, `buildSourceTooltip`에 인자로 전달해야 합니다.
// 현재는 `SourceChip` 내부에서 `useMemo`로 감싸는 것이 가장 합리적입니다.
// components/ui/SourceChip.tsx
import { useMemo } from "react"; // import 추가
// ...

export function SourceChip({ source }: { source: Source }) {
const tone = OFFICIAL_BADGE[String(source.official) as "true" | "false"];
const TypeIcon = TYPE_ICON[source.type] ?? Link2;
const isLink = Boolean(source.url);

- const tooltip = buildTooltip(source);

* const tooltip = useMemo(() => buildTooltip(source), [source]); // source 객체 변경 시에만 재생성

// ...
function buildTooltip(source: Source): string {
const lines = [`[${tone.tooltipPrefix}]`, source.title];
if (source.createdAt) {
lines.push(`작성: ${formatAbsoluteTime(source.createdAt)}`);
}
if (source.collectedAt) {
lines.push(`수집: ${formatAbsoluteTime(source.collectedAt)}`);
}
if (!source.url && source.rawRef) {
lines.push(`참조: ${source.rawRef}`);
}
return lines.join("\n");
}
// ...
}
[이유]

렌더링 최적화: 컴포넌트 내부에서 함수를 매번 재생성하고 실행하는 것을 방지하고, source 객체의 참조가 변경될 때만 buildTooltip 함수가 다시 실행되도록 함으로써 불필요한 연산을 줄여 렌더링 성능을 개선합니다.
논리적 근거: tooltip 문자열은 source 객체에 전적으로 의존하는 파생 상태이므로, useMemo를 사용하는 것이 논리적으로 적절합니다.
lib/mockChat.ts
[문제점]
AgentBase 타입 정의에서 role: "agent"가 명시되어 있지만, 이후에 정의되는 구체적인 에이전트 메시지 타입들(예: { kind: "text"; text: string; }, { kind: "mentoring"; intro: string; cards: MentoringCard[]; })은 AgentBase를 & 연산자로 조합하는 대신 직접 id: string; role: "agent";를 포함하고 있습니다.

[개선안]
각 에이전트 메시지 타입이 AgentBase를 명시적으로 상속받도록 하여 중복을 제거합니다.

// lib/mockChat.ts
// ...
type AgentBase = {
id: string; // id가 AgentBase에 포함되어야 함
role: "agent";
sources?: Source[];
};

export type ChatMessage =
| {
id: string;
role: "user";
text: string;
}
| (AgentBase & {
kind: "text";
text: string;
})
| (AgentBase & {
kind: "mentoring";
intro: string;
cards: MentoringCard[];
})
| (AgentBase & {
kind: "notice";
intro: string;
items: NoticeCard[];
})
| (AgentBase & {
kind: "webex_summary";
intro: string;
items: WebexSummaryItem[];
})
| {
id: string; // action_result는 AgentBase를 상속받지 않는 특수 케이스로 처리
role: "agent";
kind: "action_result";
results: ActionResult[];
}
| {
id: string;
role: "system";
kind: "status"; // 이 메시지 타입은 제거되었으므로 해당 코드가 없어야 함
text: string;
detail: string;
};
[이유]

논리적 근거 & 단일 책임 원칙: id와 role: "agent"는 모든 에이전트 메시지 타입에 공통적으로 포함되는 속성이므로 AgentBase로 추상화하는 것이 타입 정의의 일관성과 재사용성을 높입니다. 이를 통해 타입 정의의 중복을 줄이고, mockChat.ts가 더욱 선언적인 코드가 되도록 기여합니다.
유지보수성: 공통 속성이 변경될 경우 한 곳만 수정하면 되므로 유지보수성이 향상됩니다.
스타일 가이드 준수: '논리적 근거' 원칙에 따라 중복을 피하고 명확한 논리적 계층을 구축합니다.
lib/relativeTime.ts
[문제점]
formatRelativeTime 함수에서 diffMs < 0인 경우 "방금 전"을 반환하도록 되어 있습니다. 이는 미래 시간을 의미하며, "방금 전"이라는 표현은 과거 시간과 현재 시간에만 적합합니다. 미래 시간의 경우 "미정" 또는 다른 표현이 더 적절할 수 있습니다.

[개선안]
미래 시간에 대한 처리를 명확히 분리합니다. 예를 들어, "미정" 또는 "N분 후" 등으로 표시하거나, 해당 케이스가 발생하지 않음을 가정하고 에러를 던질 수 있습니다. 현재 시나리오에서는 "기록 없음"과 동일하게 처리하는 것도 방법입니다.

// lib/relativeTime.ts
export function formatRelativeTime(
iso: string | null | undefined,
now: Date = new Date(),
): string {
if (!iso) return "기록 없음";

const target = new Date(iso);
const diffMs = now.getTime() - target.getTime();
if (Number.isNaN(diffMs)) return "기록 없음";

- if (diffMs < 0) return "방금 전"; // 미래 시간 처리

* if (diffMs < 0) return "미래 시각"; // 또는 "기록 없음" 또는 에러 처리

const minutes = Math.floor(diffMs / 60_000);
if (minutes < 1) return "방금 전";
if (minutes < 60) return `${minutes}분 전`;

const hours = Math.floor(minutes / 60);
if (hours < 24) return `${hours}시간 전`;

const days = Math.floor(hours / 24);
if (days < 7) return `${days}일 전`;

return target.toLocaleDateString("ko-KR", {
year: "numeric",
month: "long",
day: "numeric",
});
}
[이유]

UX First: 사용자 경험을 고려할 때, 미래 시간을 "방금 전"으로 표시하는 것은 혼란을 줄 수 있습니다. 시각 정보의 정확성을 높여 사용자가 올바르게 정보를 인지할 수 있도록 합니다.
논리적 근거: diffMs < 0은 대상 시각이 현재 시각보다 미래임을 의미하므로, "방금 전"이라는 표현은 논리적으로 맞지 않습니다.
docs/features/ui/01-ui:sync_status_badge.md
[문제점]
문서에 React 16(App Router) hook 룰 react-hooks/set-state-in-effect를 만족시키기 위해 **첫 fetch도 setTimeout(tick, 0)**으로 macrotask 큐에 위임. setState가 effect 동기 본문에서 발생하지 않도록 했다.는 설명이 있습니다. 그러나 React 18 (Next.js 13/14의 App Router는 React 18 기반)부터는 useEffect의 동기적 실행 중에 setState를 호출하는 것이 대부분의 경우 안전하며, 특히 초기 마운트 시에는 흔한 패턴입니다. setTimeout(tick, 0) 패턴은 불필요할 수 있습니다.

[개선안]
setTimeout(tick, 0) 대신 tick()을 직접 호출하도록 변경하고, react-hooks/set-state-in-effect 룰의 필요성을 재평가합니다. 만약 이 룰이 특정 컨텍스트에서 여전히 필요하다고 판단된다면 그 이유를 명확히 문서화해야 합니다.

--- a/hooks/useSyncInfo.ts
+++ b/hooks/useSyncInfo.ts
@@ -73,8 +73,7 @@ export function useSyncInfo(
};

     // 첫 실행은 macrotask 큐에 올려 effect 동기 setState 회피.

- timer = setTimeout(tick, 0);
-

* tick(); // 첫 실행 시 즉시 호출
  const onVisibility = () => {
  if (cancelled) return;
  if (document.visibilityState === "visible") {
  [이유]

논리적 근거 & 선언적 코드: React 18에서는 useEffect 내부에서 setState를 직접 호출하는 것이 일반적이며, 오히려 setTimeout(0)을 사용하는 것은 코드의 흐름을 복잡하게 만들고 디버깅을 어렵게 할 수 있습니다. useEffect의 디자인 자체가 부수 효과(side effect)와 상태 업데이트를 안전하게 처리하기 위함입니다. 초기 데이터 페칭 및 상태 업데이트는 useEffect의 일반적인 사용 사례에 해당합니다.
성능: setTimeout(0)은 비록 0ms이지만, 태스크 큐에 추가되므로 아주 미세하게 지연이 발생합니다. 직접 호출하면 이러한 오버헤드를 줄일 수 있습니다.
docs/features/ui/02-ui:action_result.md
[문제점]
문서에 409 ACTION_CONFLICT는 모달로 표시 및 본 컴포넌트는 /actions/execute **응답에 들어온 결과만** 렌더링. 이라는 설명이 있습니다. 이는 ActionResultBanner 컴포넌트가 /actions/execute 호출 시 발생하는 409 ACTION_CONFLICT 에러를 직접 처리하지 않고, 상위 컴포넌트(MentoringCardList)에서 모달로 처리함을 명확히 합니다. 그러나 ActionResultBanner의 ErrorSummary 컴포넌트에서 error.code를 표시하고 recoverable 여부에 따라 재시도 안내를 하는 로직은 모든 종류의 에러에 대해 일반적인 처리를 제공합니다. ACTION_CONFLICT 에러가 ActionResultBanner에 도달할 수도 있다는 가능성을 열어두는 것이 좋습니다.

[개선안]
ActionResultBanner는 action_result UI 블록의 결과로만 렌더링되므로, 이 컴포넌트가 ACTION_CONFLICT를 직접 수신할 가능성은 낮다는 점을 문서를 통해 명확히 하거나, ErrorSummary 내부에 ACTION_CONFLICT에 대한 특정 UI 피드백 로직을 추가하지 않는다면, 현재 로직을 그대로 유지하되 문서에서 해당 부분의 해석을 좀 더 유연하게 합니다. 현재 코드는 일반적인 에러 처리를 잘 따르고 있어, 굳이 수정할 필요는 없습니다. 다만, 만약 ACTION_CONFLICT 에러가 action_result UI 블록의 형태로 오게 된다면 ErrorSummary에서 이를 특별히 처리하는 것이 UX First 원칙에 부합할 것입니다.

// docs/features/ui/02-ui:action_result.md
// ...

#### 1. 사전 결정 (Pre-implementation Decisions)

| 항목                       | 결정                       | 이유                                                                                                                                                                                                                                                                                                                                                                                                                     |
| -------------------------- | -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 409 `ACTION_CONFLICT` 표시 | **배너에서는 다루지 않음** | frontEndSpec §3.3 "409는 모달로 표시" 규정. 본 컴포넌트는 `/actions/execute` **응답에 들어온 결과만** 렌더링하며, `ACTION_CONFLICT`는 일반적으로 응답의 `status`가 `failed`로 오는 대신 HTTP 409 응답 코드로 바로 반환되므로, 이 배너가 직접 렌더링될 경우는 드뭅니다. 단, 만약 백엔드가 `action_result` 블록 내부에 `error.code: ACTION_CONFLICT`를 포함하여 응답한다면 `ErrorSummary`에서 일반 에러로 처리될 것입니다. |

// ...
[이유]

논리적 근거: API 설계에 따르면 ACTION_CONFLICT는 HTTP 409 응답 코드로 반환되며, ActionExecutionResponse의 status: "failed" 필드를 통해 전달되지 않을 가능성이 높습니다. 따라서 ActionResultBanner가 이를 직접 error prop으로 받을 경우는 드물지만, 만약을 위해 문서에서 이러한 동작을 명확히 하는 것이 좋습니다. ErrorSummary는 일반적인 에러 처리에 충실하고 있으므로 컴포넌트 자체의 수정은 불필요합니다.
docs/features/ui/05-ui:mentoring_cards.md
[문제점]
결과 표시 방식 항목에서 "신청/취소 결과를 별도 ChatMessage(action_result) 로 추가하지 않고, 카드 리스트 내부에 인라인 배너로 노출했다. 채팅 흐름 상위 (페이지) 의 메시지 배열을 카드에서 직접 변경하면 결합도가 높아지므로, 일단 카드 리스트 자체 책임 범위 안에서 닫았다. 별도 action_result 메시지 추가는 후속 PR 로 미룬다."고 설명하고 있습니다.
하지만, 이전 PR (docs/features/ui/02-ui:action_result.md)에서는 action_result UI 블록이 /actions/execute 응답을 렌더링하는 역할로 도입되었으며, mock 데이터에도 action_result 메시지가 포함되어 있습니다. MentoringCardList에서 API 응답을 받자마자 이를 페이지의 메시지 목록에 action_result 타입으로 추가하는 것이 초기 action_result UI 블록의 도입 의도와 더 부합합니다.

[개선안]
MentoringCardList에서 executeAction 호출 후 받은 ActionResult를 상위 컴포넌트(ChatMessage 또는 그 상위)로 전달하여, 채팅 메시지 목록에 새로운 kind: "action_result" 메시지로 추가하는 방식으로 변경하는 것을 고려합니다. 이는 docs/features/ui/02-ui:action_result.md의 ChatMessage 통합 섹션과도 일관성을 유지할 수 있습니다.

[이유]

논리적 근거 & 선언적 코드: action_result UI 블록은 채팅 메시지의 한 종류로, 사용자에게 어떤 액션이 수행되었는지에 대한 히스토리와 결과를 명확하게 보여주는 역할을 합니다. 인라인 배너는 일시적인 피드백으로 유용하지만, 채팅 메시지 히스토리의 일부로 남는 것이 UX First 관점에서 더 중요합니다. 즉, '액션의 결과'라는 하나의 '메시지'가 독립적인 UI 블록으로 존재해야 합니다.
단일 책임 원칙: MentoringCardList는 멘토링 카드 목록의 관리와 액션 실행을 담당하고, ChatMessage (또는 페이지 스토어)는 전체 메시지 흐름을 관리하는 것이 좋습니다. 액션 결과를 메시지 흐름에 추가하는 책임은 ChatMessage 상위 로직에 두는 것이 더 적절합니다.
UX First: 액션 결과가 메시지 히스토리에 명확히 기록되면 사용자가 나중에 자신의 행동 결과를 다시 확인할 때 편리합니다.
총평:

이 PR은 매우 높은 수준의 품질을 보여주며, 코드 품질 유지를 위한 핵심 원칙들을 훌륭하게 준수했습니다. 위에서 제시한 개선안들은 대부분 사소한 최적화나 명확성 제고에 초점을 맞추었으며, 전반적인 코드의 완성도와 설계 우수성은 매우 돋보입니다. 훌륭한 작업에 감사드립니다.

---

## 반영 결과 (Follow-up)

리뷰 9건을 모두 검토하고, 7건은 그대로 반영, 1건은 검증 후 다른 방식으로 반영, 1건은 사실 관계 확인 후 변경 없이 종료했습니다.

| #   | 항목                                                | 상태       | 처리 방식                                                                                                                                                                                                                                                                                                |
| --- | --------------------------------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `MentoringCard.formatSchedule` → 유틸로 이동        | ✅ 적용     | `lib/relativeTime.ts` 에 `formatMentoringSchedule(start, end)` 추가, 컴포넌트 내부 함수 제거.                                                                                                                                                                                                            |
| 2   | `NoticeList.sortNotices` → `useMemo`                | ✅ 적용     | `"use client"` 추가하고 `sortNotices(items)` / `pinnedCount` 둘 다 `useMemo([items])` 로 감쌈. items 참조가 같으면 정렬 비용 없음.                                                                                                                                                                       |
| 3   | `WebexSummary.groupWebexByRoom` → `useMemo`         | ✅ 적용     | `"use client"` 추가하고 `groupWebexByRoom(items)` 결과를 `useMemo([items])` 로 캐시.                                                                                                                                                                                                                     |
| 4   | `SourceChip.buildTooltip` → `useMemo`               | ✅ 적용     | 리뷰가 가장 합리적이라고 명시한 path 그대로 — `"use client"` 추가하고 `buildTooltip(source)` 호출을 `useMemo([source])` 로 감쌈. `OFFICIAL_BADGE` 는 모듈 레벨 상수라 굳이 옮길 필요 없음.                                                                                                                |
| 5   | `mockChat` `AgentBase` 일관성                       | ⏭ 변경 없음 | 현재 코드를 다시 확인 — agent 메시지(text/mentoring/notice/webex_summary)는 모두 이미 `AgentBase &` 로 상속, `action_result` 와 `system/status` 는 의도적으로 별도 (리뷰가 권장한 형태와 동일). 추가 리팩터링 없음.                                                                                       |
| 6   | `formatRelativeTime` 미래시간 처리                  | ✅ 적용     | 단순 "방금 전" 대신 **clock-skew 60초 허용 + 그보다 더 미래는 "예정"** 으로 분리. 서버↔클라이언트 시각 차이는 흡수하면서, 명백한 미래값은 사용자에게 잘못된 정보(방금 전)를 주지 않도록 함.                                                                                                                |
| 7   | `useSyncInfo` 직접 `tick()` 호출                    | ✅ 적용     | 직접 `void tick()` 호출로 변경하고 `npx eslint hooks/useSyncInfo.ts` 로 검증 — 본 프로젝트 룰셋(Next.js 16 / React Compiler 환경)에서 통과 확인. `setTimeout(tick, 0)` 우회 모두 제거. 첫 실행/refresh/visibility-resume 모두 동일 패턴으로 단순화.                                                         |
| 8   | `02-ui:action_result.md` 문서 표현 보강             | ✅ 적용     | "409는 배너에서 다루지 않음" → "**기본은 모달, 배너는 fallback**" 으로 표현 완화. 백엔드가 200 OK + `error.code:"ACTION_CONFLICT"` 로 내려주는 케이스도 `ErrorSummary` 가 자연스럽게 흡수한다는 점 명시. 후속 PR(인라인 배너 → action_result 메시지 승격) 반영 결과도 §11 로 추가.                       |
| 9   | 멘토링 결과를 `action_result` 메시지로 승격         | ✅ 적용     | 신규 `lib/contexts/ChatMessagesContext.tsx` 도입. `app/chat/page.tsx` 가 Provider 로 메시지 배열을 들고, `MentoringCardList` 가 `useChatMessages().appendMessage` 를 통해 성공/실패 모두 `kind:"action_result"` 메시지로 채팅 흐름에 push. 인라인 결과 배너 제거 (히스토리 보존 + 결합도 감소). |

### 변경된 파일

- 추가
  - `lib/contexts/ChatMessagesContext.tsx` — `messages` 배열 + `appendMessage` 를 노출하는 클라이언트 Provider/Hook.
- 수정
  - `lib/relativeTime.ts` — `formatMentoringSchedule` 추가, 미래시간 클럭 스큐 처리.
  - `components/chat/MentoringCard.tsx` — 내부 `formatSchedule` 제거, 유틸 사용.
  - `components/chat/MentoringCardList.tsx` — 인라인 결과 배너 제거. 성공/실패 모두 `appendMessage` 로 `action_result` 메시지를 chat 으로 승격. 실패 시 클라이언트 합성 `ActionResult` 생성 (`buildSyntheticFailureResult`).
  - `components/chat/NoticeList.tsx` — `"use client"` + `sortNotices`/`pinnedCount` 메모.
  - `components/chat/WebexSummary.tsx` — `"use client"` + `groupWebexByRoom` 메모.
  - `components/ui/SourceChip.tsx` — `"use client"` + `buildTooltip` 메모.
  - `hooks/useSyncInfo.ts` — `setTimeout(tick, 0)` 패턴을 모두 제거하고 `void tick()` 직접 호출.
  - `app/chat/page.tsx` — `ChatMessagesProvider` 로 감싸고, 자식이 컨텍스트의 `messages` 를 사용하도록 분리.
  - `docs/features/ui/02-ui:action_result.md` — 409 처리 표현 보강 + §11 후속 PR 반영 결과 추가.

### 거절/보류 사항 사유

- **#5 `mockChat` AgentBase**: 리뷰의 의도(공통 속성 상속)는 이미 적용되어 있는 상태. `action_result` / `system.status` 가 `AgentBase` 를 상속하지 않는 것은 의도된 분리이며, 리뷰의 제안 코드도 그대로 유지를 권장하므로 추가 변경 없음. 단, 리뷰가 "이 메시지 타입은 제거되었으므로 해당 코드가 없어야 함" 으로 언급한 `kind: "status"` 는 mock 데이터에서는 빠졌으나 `StatusToast` 컴포넌트와 함께 타입은 향후 시스템 알림 용도로 유지(예: 동기화 실패 인라인 알림). 사용처가 영구적으로 사라지면 후속 정리.

### 검증

- `npx tsc --noEmit`: 통과.
- `npx eslint app components hooks lib`: 통과.
- `useSyncInfo` 단독 lint: 통과 (직접 `tick()` 호출 안전 확인).
- 시각 확인(수동): `/chat` 페이지에서 멘토링 신청 → 모달 → 확인 → (백엔드 부재로) 실패 → 채팅 흐름 맨 아래에 빨간 `ActionResultBanner` 가 새 메시지로 추가되며 자동 스크롤. 카드 상태는 `open` 으로 원복.
