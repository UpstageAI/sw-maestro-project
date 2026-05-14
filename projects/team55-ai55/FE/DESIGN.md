---
version: alpha
name: Toss
description: >
  toss.im의 시각 디자인 시스템 (추출: 2026-05-08, 3개 페이지).
  단일 브랜드 블루(#3182f6)와 Toss Product Sans 전용 서체,
  8px 간격 시스템으로 신뢰·직관성을 구현한다.

colors:
  # Primary brand blue — CTA, UI 강조
  primary: "#3182f6"
  on-primary: "#f9fafb"
  primary-container: "#e8f3ff"
  on-primary-container: "#1b64da"
  primary-hover: "#2272eb"

  # Inline hyperlink (브랜드 블루와 구분되는 텍스트 링크용)
  link: "#007bff"

  # Surface
  surface: "#ffffff"
  surface-dim: "#f2f4f6"
  surface-container: "#f9fafb"

  # Text hierarchy (라이트 서페이스 위)
  on-surface: "#212529"
  on-surface-variant: "#4e5968"
  on-surface-muted: "#6b7684"
  on-surface-subtle: "#b0b8c1"

  # Inverse — 다크 GNB, 푸터, 다크 섹션
  inverse-surface: "#191f28"
  on-inverse-surface: "#ffffff"
  inverse-surface-hover: "#4e5968"

  # Borders
  outline: "#d1d6db"
  outline-variant: "#b0b8c1"

  # Error / Danger
  error: "#f04452"
  error-container: "#ffeeee"
  on-error-container: "#d22030"

typography:
  headline-display:
    fontFamily: "Toss Product Sans"
    fontSize: 80px
    fontWeight: "700"
    lineHeight: 1.30
    letterSpacing: "TBD"
  headline-xl:
    fontFamily: "Toss Product Sans"
    fontSize: 56px
    fontWeight: "700"
    lineHeight: 1.30
    letterSpacing: "TBD"
  headline-lg:
    fontFamily: "Toss Product Sans"
    fontSize: 36px
    fontWeight: "700"
    lineHeight: 1.30
    letterSpacing: "TBD"
  headline-md:
    fontFamily: "Toss Product Sans"
    fontSize: 24px
    fontWeight: "700"
    lineHeight: 1.60
    letterSpacing: "TBD"
  headline-sm:
    fontFamily: "Toss Product Sans"
    fontSize: 20px
    fontWeight: "600"
    lineHeight: 1.40
    letterSpacing: "TBD"
  body-lg:
    fontFamily: "Toss Product Sans"
    fontSize: 17px
    fontWeight: "400"
    lineHeight: 1.60
    letterSpacing: "TBD"
  body-md:
    fontFamily: "Toss Product Sans"
    fontSize: 16px
    fontWeight: "400"
    lineHeight: 1.00
    letterSpacing: "TBD"
  body-sm:
    fontFamily: "Toss Product Sans"
    fontSize: 15px
    fontWeight: "400"
    lineHeight: 1.33
    letterSpacing: "TBD"
  label-lg:
    fontFamily: "Toss Product Sans"
    fontSize: 17px
    fontWeight: "600"
    lineHeight: 1.06
    letterSpacing: "TBD"
  label-md:
    fontFamily: "Toss Product Sans"
    fontSize: 15px
    fontWeight: "600"
    lineHeight: 1.20
    letterSpacing: "TBD"
  label-sm:
    fontFamily: "Toss Product Sans"
    fontSize: 13px
    fontWeight: "400"
    lineHeight: 1.54
    letterSpacing: "TBD"

spacing:
  unit: 8px
  xs: 6px
  sm: 12px
  md: 24px
  lg: 40px
  xl: 60px
  xxl: 80px
  xxxl: 120px
  gutter: 24px
  container-max: "TBD"
  margin-mobile: "TBD"
  margin-desktop: "TBD"

rounded:
  xs: 4px
  sm: 7px
  md: 8px
  chip: 19px
  lg: 22px
  xl: 24px
  pill: 42px
  full: 9999px

components:
  button-default:
    backgroundColor: "rgba(0, 12, 30, 0.8)"
    textColor: "{colors.on-inverse-surface}"
    typography: "{typography.label-lg}"
    rounded: "{rounded.sm}"
    padding: "11px 16px 11px 14px"
  button-default-hover:
    backgroundColor: "{colors.inverse-surface-hover}"
    textColor: "{colors.on-inverse-surface}"
  button-primary:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.label-md}"
    rounded: "{rounded.sm}"
    padding: "11px 16px"
  button-primary-hover:
    backgroundColor: "{colors.primary-hover}"
    textColor: "{colors.on-primary}"
  button-primary-pill:
    backgroundColor: "{colors.primary}"
    textColor: "{colors.on-primary}"
    typography: "{typography.label-lg}"
    rounded: "18px"
    padding: "8.5px 16px"
  button-primary-pill-hover:
    backgroundColor: "{colors.primary-container}"
    textColor: "{colors.primary-hover}"
  button-secondary:
    backgroundColor: "{colors.primary-container}"
    textColor: "{colors.on-primary-container}"
    typography: "{typography.label-md}"
    rounded: "{rounded.sm}"
    padding: "11px 16px"
  button-ghost:
    backgroundColor: "{colors.surface-dim}"
    textColor: "{colors.on-surface-variant}"
    typography: "{typography.label-md}"
    rounded: "{rounded.sm}"
    padding: "11px 16px"
  badge:
    backgroundColor: "{colors.primary-container}"
    textColor: "{colors.primary-hover}"
    typography: "{typography.label-md}"
    rounded: "{rounded.chip}"
    padding: "6px 14px"
  input-default:
    backgroundColor: "{colors.surface}"
    textColor: "{colors.on-surface}"
    typography: "{typography.body-md}"
    rounded: "TBD"
    padding: "TBD"
    border: "rgba(0, 27, 55, 0.1)"
  input-disabled:
    backgroundColor: "{colors.surface-dim}"
    textColor: "{colors.on-surface-muted}"
    rounded: "TBD"
    padding: "TBD"
    border: "rgba(0, 23, 51, 0.02)"
---

## Overview

Toss의 디자인은 **신뢰와 단순함**에서 출발한다. 금융 서비스에서 신뢰는 가장 중요한 감정적 자산이므로, 시각적 복잡성을 최소화하고 행동 동선을 명확히 하는 데 모든 토큰이 수렴한다.

단일 브랜드 블루(`primary: #3182f6`)가 UI 전체의 주요 행동을 안내하고, 4단계 텍스트 팔레트(`on-surface` 계열)가 정보 계층을 만든다. 핵심 기조는 **Less Chrome, More Signal** — 불필요한 장식 없이 콘텐츠와 행동만 남긴다.

프레임워크: PrimeReact (129개 Prime 컴포넌트 감지). 아이콘 시스템: SVG 인라인.

---

## Colors

### Primary (브랜드 블루)

`#3182f6`는 Toss의 유일한 브랜드 컬러다. 모든 주요 CTA와 인터랙티브 강조에 이 색상 하나만 사용한다.

| 토큰 | 값 | 역할 |
|---|---|---|
| `primary` | `#3182f6` | CTA 버튼, 탭 인디케이터, 아이콘 강조 |
| `on-primary` | `#f9fafb` | `primary` 배경 위 텍스트·아이콘 |
| `primary-container` | `#e8f3ff` | Secondary 버튼 배경, 뱃지·칩 배경 (낮은 강도) |
| `on-primary-container` | `#1b64da` | `primary-container` 위 텍스트, 포커스 링 색상 |
| `primary-hover` | `#2272eb` | `primary` 및 `primary-container` 호버·액티브 상태 |
| `link` | `#007bff` | 본문 내 인라인 텍스트 링크 (버튼과 구분) |

`primary`와 `primary-container`를 같은 뷰에 동시에 사용할 수 있지만, 동일한 행동 계층에 두면 안 된다. 대표 CTA는 `primary`(솔리드 블루), 보조 CTA는 `primary-container`(연파란 틴트)로 위계를 유지한다.

### Surface (배경 계층)

| 토큰 | 값 | 역할 |
|---|---|---|
| `surface` | `#ffffff` | 기본 페이지 배경, 카드 배경, 인풋 배경 |
| `surface-dim` | `#f2f4f6` | 비활성 인풋 배경, Ghost 버튼 배경 |
| `surface-container` | `#f9fafb` | 낮은 강조도의 컨테이너 배경 |

### Text Hierarchy (온-서페이스)

4단계 명도 계층으로 정보 중요도를 표현한다.

| 토큰 | 값 | 용도 |
|---|---|---|
| `on-surface` | `#212529` | 본문 제목, 주요 텍스트 — WCAG AA 적합 |
| `on-surface-variant` | `#4e5968` | 부제목, 레이블, 보조 정보 — WCAG AA 적합 |
| `on-surface-muted` | `#6b7684` | Placeholder, 비활성 텍스트 |
| `on-surface-subtle` | `#b0b8c1` | 구분선, 비활성 아이콘, 캡션 |

`on-surface-muted`(#6b7684)는 흰 배경에서 WCAG AA(4.5:1) 미달이므로 일반 본문에 쓰지 않는다. Placeholder나 보조 힌트에만 허용한다.

### Inverse Surface (다크 패널)

GNB, 푸터, 특정 프로모션 섹션의 다크 배경에 사용한다.

| 토큰 | 값 | 역할 |
|---|---|---|
| `inverse-surface` | `#191f28` | 다크 패널 기본 배경 |
| `on-inverse-surface` | `#ffffff` | 다크 배경 위 텍스트·아이콘 |
| `inverse-surface-hover` | `#4e5968` | 다크 배경 위 버튼 호버 배경 |

다크 패널에서 `button-default`(반투명 네이비)는 호버 시 `inverse-surface-hover`(#4e5968)로 전환되어 상태를 표현한다. `primary`(#3182f6)를 다크 배경 위에 그대로 얹으면 대비가 부족할 수 있으므로 주의한다.

### Borders

- `outline`: `#d1d6db` — 탭 비활성 언더라인, 구분선
- `outline-variant`: `#b0b8c1` — 약한 구분선
- 인풋 보더는 CSS 변수 `rgba(0, 27, 55, 0.1)` (반투명 적응형)을 사용한다. 배경색에 따라 시각적 무게가 자동 조정된다.

### Error / Danger

| 토큰 | 값 | 역할 |
|---|---|---|
| `error` | `#f04452` | 위험·삭제 주요 액션 버튼 배경 (`--btn-danger-bg`) |
| `error-container` | `#ffeeee` | 오류 상태 소프트 배경 (`--btn-danger-weak-bg: #fee`) |
| `on-error-container` | `#d22030` | 오류 컨테이너 위 텍스트 (`--btn-danger-weak-color`) |

---

## Typography

Toss Product Sans는 Toss 전용 커스텀 서체다 (Google Fonts · Adobe Fonts 미사용, 가변 폰트 미사용). 외부 프로젝트 폴백 스택:

```
"Toss Product Sans", Tossface, -apple-system, BlinkMacSystemFont,
"Noto Sans KR", "Apple SD Gothic Neo", Roboto, "Helvetica Neue", Arial, sans-serif
```

`letterSpacing`은 추출되지 않아 모든 토큰이 **TBD**다. 실제 적용 시 TDS(Toss Design System) 공식 문서를 참조한다.

### Headline 계열 (weight 700 / 600)

대형 헤드라인은 line-height 1.30으로 타이트하게 유지해 인상적인 밀도를 만든다. 크기가 내려올수록 line-height가 1.40~1.60으로 열린다.

| 토큰 | 크기 | Weight | Line-height | 용도 |
|---|---|---|---|---|
| `headline-display` | 80px | 700 | 1.30 | 히어로 최상위 슬로건 (페이지 당 1회) |
| `headline-xl` | 56px | 700 | 1.30 | 대형 섹션 대표 카피 |
| `headline-lg` | 36px | 700 | 1.30 | 섹션 제목 |
| `headline-md` | 24px | 700 | 1.60 | 카드·모달 제목 |
| `headline-sm` | 20px | 600 | 1.40 | 서브 섹션 제목, 강조 항목 |

`headline-display`와 `headline-xl`은 line-height 1.30으로 설정되어 있어 다행 처리 시 줄 간격이 매우 좁다. 단행 슬로건에만 사용하고, 줄이 바뀌는 경우 `headline-lg`(36px)로 내린다.

### Body 계열 (weight 400)

| 토큰 | 크기 | Weight | Line-height | 용도 |
|---|---|---|---|---|
| `body-lg` | 17px | 400 | 1.60 | 주요 본문, 설명 문단 |
| `body-md` | 16px | 400 | 1.00 | 네비게이션 링크, 단행 인라인 텍스트 |
| `body-sm` | 15px | 400 | 1.33 | 보조 설명, 약관, 부가 정보 |

`body-md`의 line-height 1.00은 단일 행 컨텍스트(네비게이션, 버튼 내 텍스트)에서 관측된 값이다. 다행 본문에는 반드시 `body-lg`(1.60)를 사용한다.

### Label 계열 (weight 600 / 400)

버튼, 탭, 칩, 링크 등 인터랙티브 요소의 레이블에 사용한다.

| 토큰 | 크기 | Weight | Line-height | 용도 |
|---|---|---|---|---|
| `label-lg` | 17px | 600 | 1.06 | 대형 버튼 텍스트, 강조 링크 |
| `label-md` | 15px | 600 | 1.20 | 표준 버튼·탭·칩 텍스트 |
| `label-sm` | 13px | 400 | 1.54 | 메타 정보, 태그, 날짜, 캡션 |

`label-lg`와 `label-md`는 모두 weight 600이다. 버튼에서 weight를 400으로 낮추면 브랜드 일관성이 무너진다.

---

## Layout & Spacing

기본 단위는 **8px**이다. `xs`(6px)는 8px 격자의 예외값이지만, 칩 내부 패딩처럼 매우 작은 공간에서 자주 관측되었다.

| 토큰 | 값 | 대표 사용처 |
|---|---|---|
| `xs` | 6px | 칩·뱃지 수직 패딩, 아이콘-텍스트 간격 |
| `sm` | 12px | 리스트 행 간격, 인라인 요소 수평 간격 |
| `md` | 24px | 섹션 내 컴포넌트 간격, 컨테이너 gutter |
| `lg` | 40px | 섹션 상단 여백 |
| `xl` | 60px | 섹션 간 구분 여백 |
| `xxl` | 80px | 히어로 영역 상하 패딩 |
| `xxxl` | 120px | 대형 섹션 분리 |

`container-max`, `margin-mobile`, `margin-desktop`은 추출되지 않아 **TBD**다.

**반응형 브레이크포인트** (추출값):

| 브레이크포인트 | 값 | 용도 추정 |
|---|---|---|
| Desktop | ≥ 1024px | 풀 레이아웃 |
| Tablet-L | 840px | 중간 뷰포트 |
| Tablet-S | 640px | 태블릿 세로 / 모바일 가로 |
| Mobile | ≤ 639px | 모바일 (기준 360px) |

---

## Elevation & Depth

추출된 그림자는 단 하나다:

```
rgba(0, 27, 55, 0.1) 0px 2px 30px 0px
```

이 그림자는 드롭다운, 카드, 플로팅 패널 등 부유 요소에 적용한다. 반투명 네이비 컬러가 흰 배경에 자연스럽게 스며들어 Toss 특유의 차분한 깊이감을 만든다.

Toss UI는 그림자를 최소화하고 컬러·여백으로 계층을 표현하는 방식을 선호한다. 추가 elevation 레벨(e.g., 모달 오버레이)은 **TBD**.

---

## Shapes

모서리는 **목적별 반경**으로 구분된다.

| 토큰 | 값 | 적용 요소 |
|---|---|---|
| `rounded.xs` | 4px | 소형 보조 버튼 |
| `rounded.sm` | 7px | **기본 버튼, 인풋** (가장 많이 관측, 8회) |
| `rounded.md` | 8px | 앵커·링크 포커스 아웃라인 |
| `rounded.chip` | 19px | 칩·뱃지 (Pill 형태에 가까운 소형 컴포넌트) |
| `rounded.lg` | 22px | 이미지 컨테이너, 카드 썸네일 |
| `rounded.xl` | 24px | 대형 카드, 패널 |
| `rounded.pill` | 42px | 대형 Pill 형태 컨테이너 |
| `rounded.full` | 9999px | 아바타, SNS 아이콘 버튼 (50% 원형) |

`rounded.sm`(7px)이 버튼과 인풋의 표준이다. 같은 컨텍스트에서 `rounded.sm`과 `rounded.lg` 이상을 혼용하지 않는다 — 이미지·카드 영역(lg 이상)과 액션 요소(sm)는 반경 차이로 시각적으로 구분된다.

---

## Components

### Buttons

모든 버튼은 `font-weight: 600`, `border: 0px solid transparent`이며, PrimeReact의 `p-button` 클래스 기반이다.

#### button-default (다크 네이비)

다크 GNB나 다크 섹션의 CTA에 사용한다. 배경이 반투명(`rgba(0, 12, 30, 0.8)`)이므로 뒤 배경에 따라 보이는 색상이 달라진다.

- 배경: `rgba(0, 12, 30, 0.8)` (다크 네이비 80% 불투명도)
- 텍스트: `{colors.on-inverse-surface}` (#ffffff)
- 패딩: `11px 16px 11px 14px` (좌측이 좁음 — 아이콘 공간 없이도 시각적 균형 유지)
- 반경: `{rounded.sm}` (7px)
- **호버**: 배경 `{colors.inverse-surface-hover}` (#4e5968)

#### button-primary (브랜드 블루 CTA)

페이지 당 가장 중요한 단일 행동에만 사용한다.

- 배경: `{colors.primary}` (#3182f6)
- 텍스트: `{colors.on-primary}` (#f9fafb)
- 패딩: `11px 16px`
- 반경: `{rounded.sm}` (7px)
- **호버**: 배경 `{colors.primary-hover}` (#2272eb)

#### button-primary-pill (Pill 형태 CTA)

`button-primary`의 Pill 변형. 반경이 18px로 더 둥글며, 호버 시 색상이 역전된다.

- 배경: `{colors.primary}` (#3182f6)
- 텍스트: `{colors.on-primary}` (#f9fafb)
- 패딩: `8.5px 16px`
- 반경: `18px`
- **호버**: 배경 `{colors.primary-container}` (#e8f3ff), 텍스트 `{colors.primary-hover}` (#2272eb)

#### button-secondary (연파란 보조 CTA)

`button-primary`와 같은 레이아웃에서 보조 행동에 사용한다.

- 배경: `{colors.primary-container}` (#e8f3ff)
- 텍스트: `{colors.on-primary-container}` (#1b64da)
- 패딩: `11px 16px`
- 반경: `{rounded.sm}` (7px)

#### button-ghost (중립 보조)

낮은 강조도의 보조 액션. 배경이 `surface-dim`으로 튀지 않는다.

- 배경: `{colors.surface-dim}` (#f2f4f6)
- 텍스트: `{colors.on-surface-variant}` (#4e5968)
- 패딩: `11px 16px`
- 반경: `{rounded.sm}` (7px)

---

### Badge / Chip

추출된 단일 변형 (`p-chip` 클래스).

- 배경: `{colors.primary-container}` (#e8f3ff)
- 텍스트: `{colors.primary-hover}` (#2272eb)
- 패딩: `6px 14px`
- 반경: `{rounded.chip}` (19px) — Pill에 가까운 형태
- 폰트: `{typography.label-md}` (15px / 600)
- 보더: `1px solid transparent`

---

### Input

`text`, `checkbox`, `radio`, `select` 컴포넌트의 상세 값은 추출되지 않아 **TBD**다.
CSS 변수에서 다음 값이 확인되었다:

| 상태 | 배경 | 보더 |
|---|---|---|
| 기본 | `{colors.surface}` (#ffffff) | `rgba(0, 27, 55, 0.1)` |
| 비활성 | `{colors.surface-dim}` (#f2f4f6) | `rgba(0, 23, 51, 0.02)` |

인풋 보더가 반투명(`rgba`) 값인 이유: 다크/라이트 배경 모두에서 동일한 CSS 변수를 적용하기 위한 적응형 설계다.

---

### Links

링크는 `text-decoration: none`으로 밑줄 없이 색상만으로 역할을 표현한다.

| 변형 | 색상 | Weight | 용도 |
|---|---|---|---|
| 기본 텍스트 링크 | `{colors.link}` (#007bff) | 400 | 본문 내 하이퍼링크 |
| 서브 링크 | `{colors.on-surface-variant}` (#4e5968) | 400 | 네비게이션, 푸터 링크 |
| 강조 링크 | `{colors.on-primary-container}` (#1b64da) | 600 | 주요 인라인 CTA 링크 |
| 역전 링크 | `{colors.on-inverse-surface}` (#ffffff) | 600 | 다크 배경 위 링크 |
| 주 브랜드 링크 | `{colors.primary}` (#3182f6) | 500 | 파란 강조 링크 |

---

## Do's and Don'ts

- **Do** `primary`(#3182f6) 버튼은 화면당 하나만. 복수 CTA가 필요하면 `button-secondary` · `button-ghost`를 조합한다.
- **Do** 텍스트는 `on-surface` → `on-surface-variant` → `on-surface-muted` 순으로 계층을 내린다. 단계를 건너뛰지 않는다.
- **Do** 버튼·인풋의 반경은 `rounded.sm`(7px)으로 통일한다.
- **Do** `body-md`(16px/lh 1.00)는 단행 컨텍스트(네비게이션, 버튼 레이블)에만. 본문 문단은 `body-lg`(17px/lh 1.60)를 쓴다.
- **Don't** `rounded.sm`(7px) 버튼과 `rounded.lg`(22px) 이미지를 같은 카드 내에 혼용하지 않는다. 목적 계층이 혼란스러워진다.
- **Don't** `on-surface-muted`(#6b7684)를 흰 배경 위 일반 본문에 쓰지 않는다 — WCAG AA(4.5:1) 미달.
- **Don't** `letterSpacing` 값은 TBD이므로 임의 값을 넣지 않는다.
- **Don't** `primary`(#3182f6)와 `link`(#007bff)를 같은 문장 안에 혼용하지 않는다 — 사용자가 두 파란색의 의미를 구분하지 못한다.
