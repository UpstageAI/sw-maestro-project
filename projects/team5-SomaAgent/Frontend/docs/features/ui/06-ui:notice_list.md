# ui:notice_list

### Spec 참조

- SPEC §6.2

### Path

- ChatUIBlock.notice_list

### 비고

- 접수 내역에 재사용할지 별도 블록 신설할지 미정 (F-2).

### 설명

- 공지 리스트. 제목·작성자·작성일 + 첨부 표시.

---

### 구현 내용

#### 1. 사전 결정 사항

- **타입 위치 (`lib/types/notice.ts`)**: F-1 ("NoticeCard 정확 필드 미정") 을 풀기 위해 시연용 잠정 컨트랙트를 별도 파일로 분리. 백엔드 sidecar PoC 결과로 필드가 확정되면 본 파일과 `lib/mockChat.ts` 두 곳만 갱신하면 컴포넌트는 그대로 둘 수 있다.
- **F-2 (접수 내역 재사용 vs 별도 블록)**: 본 PR 에서는 **별도 블록을 신설하지 않고** `notice_list` 자체를 충분히 풍부하게 만들어 두는 방향으로 결정. `NoticeCard` 의 `category` 필드를 통해 `"평가" | "운영" | "워크숍" | "시스템" | "기타"` 와 같은 도메인 구분을 표현할 수 있고, 추후 `ApplicationHistory` 응답을 동일 구조로 매핑하면 별도 컴포넌트 추가 없이 흡수할 수 있다. 백엔드 응답 형태가 확정될 때 다시 검토.
- **컴포넌트 이름 (`NoticeList`)**: 기존 임시 컴포넌트는 `NoticeBlock` 으로 단순 bullet list 였는데, `frontEndSpec.md §3.1` 의 컴포넌트 매핑 표에 `<NoticeList />` 로 명시되어 있어 이름을 맞췄다. 단순 텍스트 리스트가 아닌 "공지 카드 리스트" 라는 의미를 더 잘 전달한다.
- **레이아웃 결정**: 멘토링과 동일한 카드 그리드로 갈지, 단일 박스 + 내부 구분선의 리스트로 갈지 고민. 스펙이 "리스트형" 으로 명시했고, 한 메시지에 3건 이상 자주 나올 가능성이 있어 **단일 컨테이너 + `divide-y` 내부 구분선** 패턴을 채택. 시각적 무게가 멘토링 카드와 분리된다.
- **첨부 표현**: 최소 1건의 PDF/링크 첨부가 일반적이라 가정하고, 본문 하단에 `AttachmentChip` 칩 그리드로 노출. 타입(pdf/image/doc/link/other)별 아이콘과 톤을 다르게 줘서 한눈에 형식을 식별할 수 있다.

#### 2. 파일 구조

```
lib/
  types/
    notice.ts             # 잠정 NoticeCard + NoticeAttachment 컨트랙트 (F-1)
                          # formatFileSize, sortNotices 유틸 포함
components/
  chat/
    NoticeList.tsx        # 컨테이너 + 헤더 + NoticeRow + AttachmentChip
    NoticeBlock.tsx       # 삭제 (구 임시 구현)
```

#### 3. 잠정 타입 컨트랙트

```ts
type NoticeAttachmentType = "pdf" | "image" | "doc" | "link" | "other";

type NoticeAttachment = {
  id?: string;
  type: NoticeAttachmentType;
  name: string;
  url?: string;
  sizeBytes?: number;
};

type NoticeCategory = "운영" | "평가" | "워크숍" | "시스템" | "기타";

type NoticeCard = {
  id: string;
  title: string;
  author: string;
  createdAt: string; // ISO 8601
  url?: string; // 원본 공지 링크 (OpenSoma)
  summary?: string;
  category?: NoticeCategory;
  pinned?: boolean;
  unread?: boolean;
  attachments?: NoticeAttachment[];
};
```

`pinned` / `createdAt` 정렬은 컴포넌트가 `sortNotices(items)` 헬퍼로 처리한다. 백엔드가 이미 정렬해서 내려주더라도 결과가 달라지지 않도록 멱등.

#### 4. 컴포넌트 책임 분리

- **`NoticeList` (export)**: 헤더("공지 N건" + "필독 N건" 배지) + `<ol>` 컨테이너 렌더. 정렬은 여기서 한 번만 수행. 빈 배열이면 `null` 반환.
- **`NoticeRow` (내부)**: 단일 공지 한 줄. 메타라인 → 제목 → 요약 → 첨부 칩 순서.
  - 메타라인: `[필독]` 칩 → `category` 칩 → 작성자 → `·` → 상대 시간(`<time>` 태그 + `dateTime` 속성, 호버 시 절대 시간 툴팁).
  - 제목: `url` 이 있으면 `<a target="_blank">` + 외부 링크 아이콘, 없으면 `<span>`.
  - 요약: `line-clamp-2` 로 2줄 클램프.
  - 미열람(`unread`) 일 때 메타라인 끝에 작은 파란 dot 표시.
- **`AttachmentChip` (내부)**: 단일 첨부 칩. 타입별 아이콘/톤 매핑.
  - `pdf` 로즈, `image` 블루, `doc/link/other` 슬레이트.
  - `sizeBytes` 가 있으면 `formatFileSize` 로 사람 읽기 좋게 변환 (`1.2 MB`, `320 KB` 등).
  - `url` 있으면 `<a target="_blank">`, 없으면 `<span>` 으로 표시 (백엔드가 다운로드 URL 미내려줄 케이스 대비).

#### 5. 정렬 규칙

```
1. pinned 가 true 인 항목 우선
2. 같은 그룹 안에서는 createdAt 내림차순(최신순)
```

`sortNotices` 는 입력 배열을 변형하지 않고 새 배열을 반환한다 (`[...items].sort(...)`).

#### 6. 접근성 (a11y)

- 컨테이너에 `aria-label="공지 N건"` 부여로 스크린리더가 섹션 단위로 인식.
- 각 공지의 시간을 `<time dateTime={iso}>` 으로 마킹하여 보조기기가 정확한 시각을 읽을 수 있게 함. 시각적으로는 "30분 전", 호버 시 "2026.05.04 10:00" 절대 시간이 표시 (`title` 속성).
- 첨부 칩은 `aria-label` 에 "PDF 첨부: 파일명" 형식으로 명확히 표기. 단순 아이콘은 `aria-hidden="true"`.
- 링크는 `target="_blank" rel="noreferrer"` 로 새 탭에서 열리며, 시각 단서로 외부 링크 아이콘 동봉.
- `unread` dot 은 시각 정보만으로 끝나지 않게 `aria-label="미열람"` + `title="미열람"` 부가.

#### 7. ChatMessage 통합

`ChatMessage.tsx` 의 기존 `kind: "notice"` 분기가 `NoticeBlock` → `NoticeList` 로 교체되었고, 데이터 필드는 단순 `{ id, text }` → 풍부한 `NoticeCard` 로 갈아끼웠다.

```tsx
{message.kind === "notice" && (
  <div className="...">
    <p>{message.intro}</p>
    <NoticeList items={message.items} />
  </div>
)}
```

`message.kind` 는 그대로 `"notice"` 유지 (스펙의 UI 블록 키 `notice_list` 와는 별개의 프론트 내부 메시지 종류). 추후 ChatMessage 디스패치 매핑을 정리할 때 함께 재명명 검토.

#### 8. Mock 데이터 시연 매트릭스

| ID  | 시연 의도                          | category | pinned | 첨부              |
| --- | ---------------------------------- | -------- | ------ | ----------------- |
| n-1 | 필독 + 평가 + 미열람 + 첨부 2건    | `평가`   | ✓      | PDF 1.2 MB + DOC  |
| n-2 | 일반 워크숍 공지 + 외부 링크 첨부  | `워크숍` |        | PDF 2.8 MB + LINK |
| n-3 | 시스템 점검 공지 (요약만, 첨부 없음) | `시스템` |        | —                 |

`source_list` 와의 결합도 함께 확인하기 위해 동일 메시지의 `sources` 배열에는 `notice` + `notice_pdf` 두 종류의 출처가 포함되어 있다 (이전 PR 의 출처 칩이 그대로 활용됨).

#### 9. 검증

- `npx tsc --noEmit`: 통과.
- `npx eslint app components hooks lib`: 통과.
- 시각 확인 (수동): `/chat` 페이지 — "이번 주 공지사항 요약해줘" 메시지 응답에서 필독이 맨 위로 정렬되고, 카테고리/시간/첨부 칩이 의도대로 표시.
- 다크 모드/모바일 폭은 본 PR 범위 외. 후속 검토.

#### 10. 후속 작업 (Follow-up)

- **F-1 확정 반영**: 백엔드에서 `NoticeCard` 필드가 확정되면 `lib/types/notice.ts` 와 mock 만 갱신.
- **F-2 접수 내역 (`ApplicationHistory`) 처리**: 백엔드가 같은 `notice_list` 구조로 내려주면 `category` 만 추가/매핑하면 끝. 별도 응답 형태로 내려주면 `ApplicationHistoryCard` 컴포넌트를 신설하되, 본 `NoticeList` 의 행 패턴(메타 → 제목 → 요약 → 칩)을 재사용 가능한 베이스 컴포넌트로 빼는 리팩터링을 함께 고려.
- **읽음 처리 (`unread`) 인터랙션**: 현재는 표시만. 클릭 시 서버에 mark-as-read 호출 + 로컬 상태 갱신 흐름은 별도 PR.
- **첨부 미리보기**: PDF 클릭 시 새 탭이 아니라 인라인 PDF 미리보기 (모달) 제공 옵션을 사용자 피드백 보고 결정.
- **카테고리 확장**: 현재 5종은 잠정. 백엔드 카테고리 enum 이 확정되면 `CATEGORY_TONE` 매핑을 그에 맞춰 정리.
- **F-5 (출처 직접 링크 인증)**: `notice.url` 클릭 시 OpenSoma 로그인이 필요할 수 있다는 사실은 본 컴포넌트가 모름. 인증 안내 토스트나 인터셉트 처리는 라우팅 상위에서 별도 다룰 예정.
