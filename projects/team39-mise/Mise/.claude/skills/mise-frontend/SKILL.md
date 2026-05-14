---
name: mise-frontend
description: "Mise 프론트엔드 구현 스킬. Streamlit UI 레이아웃, 세션 상태 관리, 장면 요소 카드, 프롬프트 미리보기, 이미지 표시, 스타일 프리셋, 보정/재생성 UI 구현. Streamlit 화면, UI 컴포넌트, 사용자 인터랙션 요청 시 반드시 이 스킬을 사용."
---

# Mise Frontend — Streamlit UI 구현 가이드

소설 이미지 생성 서비스 Mise의 Streamlit 기반 사용자 인터페이스를 구현하는 방법을 안내한다.

## 화면 레이아웃

```
┌─────────────────────────────────────────────┐
│  🔮 Mise — 소설 속 장면을 이미지로          │
├─────────────────────────────────────────────┤
│                                             │
│  [텍스트 입력 영역]                          │
│  text_area (max_chars=1000)                 │
│  글자 수: 0 / 1000                          │
│                                             │
│  스타일: [시네마틱 ▼]  포커스: [균형형 ▼]    │
│                                             │
│  [✨ 시각화] 버튼                            │
│                                             │
├─────────────────────────────────────────────┤
│  장면 분석 결과                              │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐       │
│  │인물  │ │배경  │ │시간  │ │장소  │       │
│  │(원문) │ │(원문) │ │(추론)│ │(원문) │       │
│  └──────┘ └──────┘ └──────┘ └──────┘       │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐       │
│  │사물  │ │행동  │ │감정  │ │분위기│       │
│  └──────┘ └──────┘ └──────┘ └──────┘       │
│  ┌──────┐ ┌──────┐ ┌──────┐ ┌──────┐       │
│  │색감  │ │조명  │ │시점  │ │구도  │       │
│  └──────┘ └──────┘ └──────┘ └──────┘       │
│                                             │
│  ▸ 프롬프트 미리보기                         │
│  Positive: ...                              │
│  Negative: ...                              │
├─────────────────────────────────────────────┤
│  생성된 이미지                               │
│  ┌─────────────────────────────────┐        │
│  │                                 │        │
│  │         [이미지]                 │        │
│  │                                 │        │
│  └─────────────────────────────────┘        │
│                                             │
│  [🔄 재생성]  [💾 저장]                      │
├─────────────────────────────────────────────┤
│  이전 결과 (최대 5개)                        │
│  [결과1] [결과2] [결과3] ...                 │
└─────────────────────────────────────────────┘
```

## Session State 구조

```python
# 세션 상태 초기화
def init_session_state():
    if "results" not in st.session_state:
        st.session_state.results = []  # 최대 5개 결과 유지
    if "current_input" not in st.session_state:
        st.session_state.current_input = ""
    if "current_style" not in st.session_state:
        st.session_state.current_style = "cinematic"
    if "current_focus" not in st.session_state:
        st.session_state.current_focus = "balanced"

# 결과 추가 (최대 5개)
def add_result(result):
    st.session_state.results.append(result)
    if len(st.session_state.results) > 5:
        st.session_state.results = st.session_state.results[-5:]
```

## 핵심 컴포넌트

### 1. 텍스트 입력 영역

```python
col1, col2 = st.columns([4, 1])
with col1:
    novel_text = st.text_area(
        "소설 텍스트를 입력하세요",
        height=200,
        max_chars=1000,
        placeholder="소설의 장면 묘사를 붙여넣으세요..."
    )
with col2:
    char_count = len(novel_text) if novel_text else 0
    st.metric("글자 수", f"{char_count}/1000")
```

### 2. 장면 요소 카드

각 요소를 `st.container` 카드로 표시한다. 원문 기반 정보는 파란색 배지, 추론 정보는 주황색 배지로 구분한다.

```python
def render_element_card(label, value, source_type):
    with st.container():
        st.markdown(f"**{label}**")
        st.write(value)
        badge = "📘 원문" if source_type == "original" else "🟠 추론"
        st.caption(badge)
```

### 3. 스타일 프리셋

```python
STYLE_PRESETS = {
    "시네마틱": "cinematic, dramatic lighting, film grain, 35mm photography",
    "수채화": "watercolor painting, soft edges, flowing colors, artistic",
    "픽셀아트": "pixel art, 16-bit style, retro game aesthetic",
    "애니메이션": "anime style, cel shading, vibrant colors, studio quality",
    "판타지 일러스트": "fantasy illustration, detailed, rich colors, concept art",
}
```

### 4. 로딩 상태

분석 진행 중에는 `st.spinner`와 진행 상태 단계를 표시한다:
- "장면 분석 중..." (Gemini 호출)
- "프롬프트 생성 중..."
- "이미지 생성 중..." (Gemini 이미지 생성 호출)

## 사용자 워크플로우 구현

1. **입력 단계:** 텍스트 입력 → 스타일/포커스 선택 → "시각화" 클릭
2. **분석 단계:** spinner 표시 → 장면 요소 카드 표시
3. **프롬프트 미리보기:** expander로 Positive/Negative 프롬프트 공개
4. **이미지 표시:** 생성된 이미지를 화면에 렌더링
5. **보정 분기:** 카드 값 수정 또는 스타일 변경 → "재생성"
6. **이전 결과:** 하단에 탭 또는 컬럼으로 최대 5개 결과 표시

## 에러 UI

- 이미지 생성 실패: `st.warning`으로 프롬프트만 표시 + "재시도" 버튼
- API 오류: `st.error`로 사용자 친화적 메시지
- 입력 없음: 버튼 비활성화 또는 경고
