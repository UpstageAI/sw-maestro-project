# Tailwind v4

## 사용 범위

- 모든 스타일링. UI 컴포넌트 라이브러리 도입하지 않고 **Tailwind 유틸리티만으로 prototype CSS 1대1 포팅**.
- prototype 의 토큰을 Tailwind v4 의 `@theme` 디렉티브로 옮겨 클래스명을 그대로 쓸 수 있게 한다.

## 버전

| 항목 | 값 |
|---|---|
| Tailwind | v4.x |
| 설정 위치 | `app/globals.css` (config 파일 X) |

## v4 설정 방식

v4 는 `tailwind.config.js` 가 사라지고 CSS 안에서 토큰을 정의한다.

```css
/* app/globals.css */
@import "tailwindcss";

@theme {
  /* prototype 의 CSS 변수 1대1 매핑 */
  --color-bg: #f2f4f6;
  --color-surface: #ffffff;
  --color-ink: #191f28;
  --color-muted: #6b7684;
  --color-hint: #8b95a1;
  --color-line: #e5e8eb;
  --color-chip: #f2f4f6;

  --color-brand-50: #fff0e7;     /* var(--blue-soft) */
  --color-brand-500: #ff8a3d;    /* var(--blue) */
  --color-brand-600: #f97821;    /* var(--blue-pressed) */

  /* 카테고리 색 */
  --color-economy: #4f9cf9;
  --color-social: #9b7cf8;

  /* 폰트 */
  --font-sans: "Pretendard", "Inter", "ui-sans-serif", "system-ui", "-apple-system", "BlinkMacSystemFont", "Segoe UI", sans-serif;

  /* 라운드 */
  --radius-phone: 32px;
  --radius-card: 20px;
}
```

> 변수 prefix(`--color-*`, `--font-*`, `--radius-*`)는 v4 의 약속된 네임스페이스. 이렇게 두면 자동으로 `bg-bg`, `text-ink`, `bg-brand-500`, `font-sans`, `rounded-phone` 같은 유틸리티가 활성화된다.

## prototype 토큰 → Tailwind 매핑 표

| prototype 변수 | Tailwind 클래스 |
|---|---|
| `--bg` `#f2f4f6` | `bg-bg` |
| `--surface` `#ffffff` | `bg-surface` |
| `--ink` `#191f28` | `text-ink` |
| `--muted` `#6b7684` | `text-muted` |
| `--hint` `#8b95a1` | `text-hint` |
| `--line` `#e5e8eb` | `border-line` / `bg-line` |
| `--chip` `#f2f4f6` | `bg-chip` |
| `--blue` `#ff8a3d` | `bg-brand-500` / `text-brand-500` |
| `--blue-pressed` `#f97821` | `active:bg-brand-600` |
| `--blue-soft` `#fff0e7` | `bg-brand-50` / `text-brand-50` |
| `--c:#4f9cf9` (경제 카테고리) | `text-economy` / `bg-economy` |
| `--c:#9b7cf8` (이슈 카테고리) | `text-social` / `bg-social` |

## 폰트

Pretendard 는 CDN woff2 를 `@font-face` 로 globals.css 에 정의. Next.js `next/font` 는 사용하지 않는다 (Pretendard 는 next/font 의 Google/Local 카탈로그에 없음).

```css
@font-face {
  font-family: "Pretendard";
  font-weight: 45 920;
  font-style: normal;
  font-display: swap;
  src: url("https://cdn.jsdelivr.net/gh/orioncactus/pretendard/dist/web/variable/woff2/PretendardVariable.woff2")
    format("woff2-variations");
}
```

## 다크모드

prototype 은 light only. Tailwind 의 `dark:` variant 는 활성화하지 않는다 (`@variant dark` 정의 안 함).

## 컴포넌트 스타일링 패턴

prototype 의 클래스명(예: `.news-card`, `.tl-card`, `.chat-bubble--ai`) 은 React 컴포넌트로 흡수하고, 안에서 Tailwind 유틸리티를 조합한다. 클래스명 그대로 보존하지 않음.

### 예: 뉴스 카드

```tsx
// app/(app)/feed/_components/NewsCard.tsx
export function NewsCard({ article }: { article: Article }) {
  return (
    <article className="grid gap-3 rounded-2xl border border-line bg-surface p-[18px] shadow-[0_10px_24px_rgba(25,31,40,0.05)]">
      <div className="grid grid-cols-[auto_1fr_auto] items-center gap-2">
        <span className="inline-flex min-h-6 items-center rounded-full bg-brand-50 px-[9px] text-xs font-extrabold text-brand-500">
          {article.category}
        </span>
        <span className="truncate text-xs font-bold text-hint">{article.source}</span>
        <time className="text-xs font-bold text-hint">{article.publishedAt}</time>
      </div>
      <h3 className="text-lg font-extrabold leading-[1.38] text-ink break-keep">
        {article.title}
      </h3>
      {/* ... */}
    </article>
  );
}
```

> 그림자 같은 정확 값은 임의 값(`shadow-[...]`)으로. 자주 쓰이면 `@theme` 에 `--shadow-card` 추가.

## 유틸리티 확장

prototype 에서 자주 쓰는 패턴은 `@utility` 로 등록:

```css
@utility break-keep { word-break: keep-all; }
@utility text-balance-pretty { text-wrap: pretty; }
```

## 성능

- v4 는 oxidation 기반 빌드로 v3 대비 빌드 시간 ~10x 빠름.
- 프로덕션 빌드 시 사용 안 한 클래스 자동 제거.

## 주의점

- v4 는 출시 직후라 일부 IDE 플러그인(VS Code Tailwind IntelliSense) 호환성 확인 필요.
- shadcn/ui 같은 라이브러리는 v4 지원 시작 단계 — 본 프로젝트는 도입 안 하므로 무관.
- v4 의 `@theme` 안 변수명은 **케밥-케이스 + namespace prefix** 필수. (`--color-foo-500` ✅, `--brand` ❌)

## 레퍼런스

- Tailwind v4: https://tailwindcss.com/docs (v4 release notes)
- Pretendard: https://github.com/orioncactus/pretendard
- prototype 토큰 정의 원본: [design.md](../design.md) §2
