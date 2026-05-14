# ui:sync_status_badge

### Spec 참조

- SPEC §6.6
- API 설계 §4.1 `GET /api/v1/system/sync-info`
- frontEndSpec.md §1.1 (P2: 동기화 시각 표시), §7 F-8 (폴링 주기·타임존 미정)

### 비고

- ChatUIBlock이 아닌 글로벌 UI 요소 (Header 등).

### 설명

- 동기화 시각 표시 배지/드롭다운. /system/sync-info 주기적 폴링.

---

### 구현 내용

#### 1. 결정 사항 (Pre-implementation Decisions)

| 항목 | 선택 | 이유 |
| ---- | ---- | ---- |
| 데이터 소스 | **실제 fetch만 시도, 백엔드 부재 시 에러 상태 노출** | 모킹은 추후 sidecar PoC 결과를 그대로 검증해야 하므로 별도 mock layer를 두지 않음. 에러 상태 자체도 1차 시연 자산. |
| 폴링 주기 | **60초** | 스펙 F-8 미정. sync 잡이 분 단위라 30초는 과해 트래픽만 늘고, 5분은 시연에서 정적으로 보일 위험. |
| 마운트 위치 | `ChatHeader` 우측 (프로필 좌측) | "글로벌 UI 요소(Header 등)" 비고 그대로. 로그인 페이지에는 노출되지 않음(인증 후 화면). |
| 서버 상태 라이브러리 | **도입하지 않음** | 단일 엔드포인트·단일 화면 사용. 01-UI Feedback에서 React Query/SWR 도입을 보류한 결정과 일관. |

#### 2. 파일 구조

```
lib/
  api.ts                    // 공통 fetch 래퍼 + ApiError 클래스
  syncInfo.ts               // SyncInfoResponse 타입 + fetchSyncInfo()
  relativeTime.ts           // formatRelativeTime / formatAbsoluteTime
hooks/
  useSyncInfo.ts            // 60초 폴링 + 백그라운드 일시정지 + abort
components/
  sync/
    SyncStatusBadge.tsx     // 배지 + 드롭다운(잡별 상태)
components/layout/
  ChatHeader.tsx            // 우측에 <SyncStatusBadge /> 마운트
```

API 컨트랙트(타입)는 `docs/spec/API.md` §4.1을 그대로 옮겼다.

```ts
type SyncJobStatus = {
  lastRunAt: string | null;
  lastSuccessAt: string | null;
  lastError: string | null;
};

type SyncInfoResponse = {
  jobs: Record<"notices_sync" | "mentorings_sync" | "webex_sync", SyncJobStatus>;
};
```

#### 3. 데이터 페칭 / 폴링 전략 (`useSyncInfo`)

- **공통 fetch 래퍼 `apiFetch<T>()`** 를 별도 분리: `NEXT_PUBLIC_API_BASE_URL` 합치기, JSON `{ code, message, details }` 표준 에러 파싱, `ApiError` 클래스 던짐. 추후 `/auth/login`, `/chat`, `/actions/execute` 도 같은 래퍼를 재사용.
- 60초 주기 `setTimeout` 체이닝(자기 재예약). `setInterval` 대신 사용한 이유:
  - 응답 지연이 폴링 간격보다 길어도 요청이 겹치지 않음.
  - 백그라운드 탭 진입 시 한 사이클을 그대로 미루고 다음 주기에 재예약하기 용이.
- `document.visibilityState === "hidden"` 인 동안 **실제 호출을 스킵**해 불필요 트래픽 차단. 탭이 다시 보이면 즉시 한 번 갱신 후 타이머 재정렬.
- 새 요청이 시작될 때 직전 요청 `AbortController`로 취소. 언마운트 시 모든 타이머와 인플라이트 요청 정리.
- React 16(App Router) hook 룰 `react-hooks/set-state-in-effect`를 만족시키기 위해 **첫 fetch도 `setTimeout(tick, 0)`**으로 macrotask 큐에 위임. `setState`가 effect 동기 본문에서 발생하지 않도록 했다.
- `refresh()`는 effect 내부의 `tick`을 호출하기 위해 `triggerRef`(ref 통로) 패턴을 사용. ref 노출은 hook 외부 API(`refresh`) 한 줄로 추상화.

#### 4. 배지 / 드롭다운 UX (`SyncStatusBadge`)

배지 자체는 5가지 톤을 가진다.

| 톤 | 트리거 | 라벨 예시 |
| --- | --- | --- |
| `loading` | 첫 응답 도착 전 | "동기화 확인 중" |
| `error` | fetch 실패 (네트워크/4xx/5xx 모두) | "동기화 확인 실패" |
| `empty` | jobs 객체가 비어 있음 | "동기화 정보 없음" |
| `warn` | 어떤 잡이라도 `lastError` 보유 또는 `lastSuccessAt` 전부 null | "일부 실패 · 30분 전 동기화" / "동기화 이력 없음" |
| `ok` | 모든 잡 정상 + 최소 1건 성공 이력 | "방금 전 동기화" / "30분 전 동기화" |

라벨은 가장 최근 `lastSuccessAt`을 기준으로 `formatRelativeTime`이 `방금 전 / N분 전 / N시간 전 / N일 전 / 절대 날짜`까지 단계 변환.

드롭다운(클릭 토글)에서는:

- 헤더 라인에 **마지막 fetch 확인 시각**과 **수동 새로고침** 버튼(`RefreshCw`, 로딩 중에는 회전).
- 에러 상태일 때 별도 빨간 배너로 `error.message`를 노출(접근성: `role="alert"` 사용은 인라인 알림에만 적용, 드롭다운 내부는 `role="dialog"`).
- 잡 목록은 항상 3개(`notices_sync`, `mentorings_sync`, `webex_sync`) 고정 순서로 노출. 응답에서 빠진 잡은 "정보 없음"으로 표시.
- 각 잡 행에 **마지막 성공 / 마지막 실행** 두 줄을 상대 시간으로 보여주고, 호버 `title` 속성으로 절대 시각 노출(F-8 타임존은 일단 사용자 로케일 준수).
- `lastError`가 있으면 노란 배너에 raw 메시지를 그대로 노출(SPEC §3.2 출처 렌더 규칙과 별개로, 운영 디버깅 용도라 마스킹 안 함).
- 푸터에 **"매 60초마다 자동 갱신 · /api/v1/system/sync-info"** 명시 — 시연 시 어떤 엔드포인트인지 한눈에.

접근성:

- 토글 버튼 `aria-haspopup="true"`, `aria-expanded`, `aria-label` 모두 부여.
- ESC 키 / 외부 클릭으로 닫힘 (`mousedown` + `keydown` 리스너, 드롭다운 열린 동안만 등록 후 정리).

#### 5. 인증/세션과의 관계

- `/system/sync-info`는 스펙상 **인증 불필요**. 따라서 현재 구현은 헤더에 `X-Soma-Session`을 넣지 않는다.
- `apiFetch`는 옵션을 그대로 통과시켜 추후 인증 필요한 엔드포인트가 같은 래퍼를 재사용할 수 있게 했다.

#### 6. 검증

- `npx tsc --noEmit` 통과.
- `npx eslint app components hooks lib` 통과 — 특히 React 16 신규 룰 `react-hooks/set-state-in-effect`, `react-hooks/immutability` 모두 위반 없음.
- 백엔드 미배포 상태에서 `/chat` 진입 시 **동기화 확인 실패** 빨간 톤 배지가 정상 노출, 60초 후 재시도 확인.
- 드롭다운에서 새로고침 버튼 클릭 시 즉시 재요청 → 실패 메시지 갱신.
- 탭 전환 후 복귀 시 즉시 재요청되는지 `visibilitychange` 동작 확인.

#### 7. 후속 과제

- [ ] **F-8 결정 반영:** 폴링 주기·타임존 표시 정책 확정 시 `useSyncInfo(intervalMs)` 인자와 `formatAbsoluteTime` 옵션으로 손쉽게 교체 가능하도록 이미 추상화 완료.
- [ ] **시각적 폴링 인디케이터:** 배경 폴링 중에는 배지 라벨 옆 미세 펄스(`animate-pulse`) 추가 검토 — UX와 트래픽 시각성 트레이드오프.
- [ ] **운영자 모드:** `lastError` 본문이 길 경우(e.g. stack trace) 토스트로 별도 노출 / 운영 권한에서만 raw 노출.
- [ ] **테스트:** `useSyncInfo`의 폴링/abort 동작은 `vitest` + `MSW` 도입 시 1번째 후보.
