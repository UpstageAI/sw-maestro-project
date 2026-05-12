안녕하세요! 시니어 프론트엔드 개발자로서 변경된 코드를 리뷰하겠습니다. 전반적으로 코드 품질, 아키텍처, UX 및 에러 핸들링 측면에서 매우 높은 수준의 작업을 해주셨습니다. 특히 새로운 인증 시스템과 BFF 패턴 도입, 그리고 상세한 문서화는 프로젝트의 견고성을 크게 높였습니다. 스타일 가이드를 엄격히 준수하며 몇 가지 제안 사항을 드립니다.

app/login/page.tsx

1. isSubmitting 상태 관리 개선

[문제점] isSubmitting 상태가 로그인 성공 시 false로 재설정되지 않고 router.replace("/chat")가 호출됩니다. router.replace는 일반적으로 신뢰할 수 있는 클라이언트 사이드 동작이지만, 만약 이 단계에서 예외가 발생하거나(매우 드물겠지만) 또는 router.replace가 비동기적으로 지연되어 setIsSubmitting(false)가 누락될 경우, isSubmitting 상태가 true로 남아 사용자가 다시 로그인 시도를 할 수 없게 될 수 있습니다.

[개선안] handleSubmit 함수의 try...catch 블록에 finally 블록을 추가하여 isSubmitting 상태를 항상 false로 재설정하도록 변경합니다.

// app/login/page.tsx
const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
event.preventDefault();
if (isSubmitting) return;

setError(null);

const trimmedEmail = email.trim();
if (!trimmedEmail || !password) {
setError("이메일과 비밀번호를 모두 입력해 주세요.");
return;
}

setIsSubmitting(true);
try {
await login({ username: trimmedEmail, password });
setPassword("");
router.replace("/chat");
} catch (cause) {
const message =
cause instanceof Error
? cause.message
: "로그인에 실패했습니다. 잠시 후 다시 시도해 주세요.";
setError(message);
// setIsSubmitting(false); // 여기서는 제거
} finally {
setIsSubmitting(false); // 항상 실행되도록 finally 블록으로 이동
}
};
[이유] finally 블록은 try 블록에서 예외 발생 여부와 관계없이 항상 실행됨을 보장합니다. 이는 isSubmitting과 같은 UI 상태 플래그를 안정적으로 관리하여 사용자 경험의 일관성을 유지하고, 예상치 못한 상황에서도 컴포넌트의 상태가 비정상적으로 고착되는 것을 방지합니다. (핵심 원칙: UX First, 논리적 근거)

lib/contexts/AuthContext.tsx

1. refreshTriggerRef 패턴에 대한 보충 설명 (No Action Required)

[문제점] refreshTriggerRef를 사용하여 useEffect 내의 비동기 로직(run 함수)을 외부에서 호출하는 패턴은 특정 상황에서 유용하지만, useCallback과 useState를 활용한 명시적인 상태 관리 패턴에 비해 직관성이 떨어질 수 있습니다. 예를 들어, run 함수가 의존성 배열에 복잡한 객체나 함수를 포함하게 되면, 이 패턴의 장점이 상쇄되거나 디버깅이 어려워질 가능성도 있습니다.
[개선안] 현재 코드의 패턴은 useEffect의 react-hooks/exhaustive-deps 룰을 회피하면서도 비동기 로직의 재실행 및 클린업을 안정적으로 관리하는 유효한 방법입니다. 따라서 당장은 수정이 필요 없습니다. 다만, 향후 인증 로직이 더 복잡해지거나 React Query와 같은 전용 라이브러리를 도입하게 된다면, 해당 패턴의 유지 여부를 재고할 필요가 있습니다.
[이유] 이 패턴은 useEffect 내부에서 정의된 비동기 함수를 컴포넌트 라이프사이클 외부에서 안전하게 트리거하고 싶을 때 사용됩니다. AbortController와 cancelled 플래그를 함께 사용하여 메모리 누수를 방지하고 중복 호출을 처리하는 등 안정적인 구현을 보여줍니다. (React & Next.js Best Practices: State Management) 현재는 "에러/로딩 처리가 완벽한지 검토하세요"라는 가이드에 부합하는 자체 구현으로 볼 수 있습니다.
전반적인 코드 품질
UX First: 로그인/로그아웃 시 로딩 상태, 에러 메시지, 자동 리디렉션, 비밀번호 메모리 폐기, 서버 상태와 클라이언트 상태 동기화 (세션 만료 시 쿠키 자동 폐기) 등 사용자 경험을 최우선으로 고려한 흔적이 돋보입니다. /chat 페이지의 세션 확인 중… 로딩 UI 처리도 훌륭합니다.
Logical Grounding: BFF 패턴을 도입한 이유, httpOnly 쿠키 사용, SomaApiError를 통한 에러 응답 정규화, 그리고 docs/features/api/auth.md 문서에 기술된 상세한 아키텍처와 흐름 설명은 모든 기술적 결정이 명확한 논리에 기반하고 있음을 보여줍니다.
Declarative Code: loginUser, logoutUser, fetchWhoami와 같은 함수명과 AuthContext의 명확한 인터페이스는 코드가 "무엇을" 하는지 명확하게 드러냅니다.
React & Next.js Best Practices:
State Management: AuthContext는 서버 상태(BFF 호출)와 클라이언트 상태(로딩, 인증 여부)를 잘 분리하고 관리하고 있습니다. React Query 등의 라이브러리 대신 직접 구현했음에도 로딩/에러 처리가 완벽하여 가이드라인을 충족합니다.
Rendering Optimization: AuthContext에서 useMemo를 사용하여 context value의 불필요한 재생성을 막은 점이 좋습니다.
Component Structure: \_helpers.ts, lib/auth.ts, lib/contexts/AuthContext.tsx, lib/server/somaApi.ts 등 기능별로 파일과 폴더를 명확하게 분리하여 단일 책임 원칙을 잘 지켰습니다.
Naming Conventions: camelCase, PascalCase, handle 프리픽스 등 명명 규칙이 일관되게 잘 적용되어 있습니다.
Error Handling: somaApi.ts의 SomaApiError와 parseErrorBody 구현, Route Handler들의 errorResponse/unexpectedErrorResponse 활용, AuthContext의 extractMessage 유틸리티까지 매우 견고하고 사용자 친화적인 에러 처리 로직을 갖추고 있습니다. 조용히 넘어가는 에러는 없습니다.
결론적으로, 이번 변경사항은 프로젝트의 인증 시스템을 매우 안정적이고 사용자 친화적으로 개선했으며, 스타일 가이드의 모든 핵심 원칙과 베스트 프랙티스를 훌륭하게 준수하고 있습니다. 제안 드린 isSubmitting 상태 관리 개선을 반영하시면 더욱 완벽한 코드가 될 것입니다.

수고 많으셨습니다!

---

## 반영 내역 (구현 측 기록)

아래는 위 리뷰를 코드에 반영한 결과를 정리한 것이다. 원문 리뷰는 보존하고, 이 섹션만 이후에 갱신하면 된다.

### 1. `app/login/page.tsx` — `isSubmitting` 상태 관리

| 구분 | 내용 |
| --- | --- |
| **상태** | 반영 완료 |
| **조치** | `handleSubmit`의 `try`/`catch`에 **`finally` 블록 추가**. 항상 `setIsSubmitting(false)`를 호출해, 성공 경로에서 `router.replace("/chat")` 직후 비정상 종료가 나거나(극히 드묾), `catch`에서만 `false`를 두던 경우에 비해 **버튼·입력이 잠긴 채로 남는 고착(stuck) 리스크를 제거**했다. |
| **코드** | `setIsSubmitting(true)` 직후 `try { await login(...); setPassword(""); router.replace("/chat"); } catch { setError(...) } finally { setIsSubmitting(false); }` |
| **비고** | 조기 반환(이메일/비밀번호 미입력) 분기에서는 `setIsSubmitting(true)` 이전에 `return`하므로 기존과 동일하게 동작한다. |

### 2. `lib/contexts/AuthContext.tsx` — `refreshTriggerRef` 패턴

| 구분 | 내용 |
| --- | --- |
| **상태** | 조치 없음 (리뷰어 권고: No Action Required) |
| **사유** | `react-hooks/set-state-in-effect` 등 ESLint 규칙과 맞추면서 mount 시 `whoami` 실행·AbortController 클린업을 유지하는 현재 패턴을 유지한다. React Query 도입 시에는 리뷰에서 제안한 대로 패턴 재검토 예정. |

### 3. 그 외 항목

전반적인 칭찬·가이드 라인 준수 코멘트는 **추가 코드 변경 없이** 참고용으로만 둔다.
