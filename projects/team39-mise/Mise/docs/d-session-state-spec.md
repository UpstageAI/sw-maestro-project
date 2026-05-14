# D 단계 — Streamlit Interaction UI 명세

C 단계(메인 화면) 담당이 D 컴포넌트를 통합할 때 참고할 문서. 키 이름과 콜백 인터페이스만 맞추면 동작한다.

## 모듈 구성

```
mise/
├── state.py                       # session_state 키 명세 + 헬퍼
├── components/
│   ├── scene_card.py              # 12요소 카드 (편집 가능)
│   ├── style_preset.py            # 스타일 라디오
│   ├── regenerate.py              # 재생성 버튼 + 카운터
│   └── history.py                 # 이미지 히스토리
└── app_d_demo.py                  # 단독 데모 페이지 (C 통합 전 시연용)
```

## session_state 키

키 상수는 `mise.state.Keys`에 정의되어 있다. 직접 문자열을 쓰지 말고 상수를 import 할 것.

| 키 (`Keys.*`) | 문자열 | 타입 | 설명 |
|---|---|---|---|
| `CURRENT_SCENE` | `d_current_scene` | `SceneSchema \| None` | 가장 최근 분석 결과 |
| `EDITED_ELEMENTS` | `d_edited_elements` | `dict \| None` | 사용자 편집 버퍼 (`SceneElements.model_dump()` 형식) |
| `STYLE_LABEL` | `d_style_label` | `str` | 라디오 위젯이 직접 바인딩 (한국어 라벨) |
| `REGEN_COUNT` | `d_regen_count` | `int` | 재생성 사용 횟수 (0 ~ 5) |
| `HISTORY` | `d_history` | `list[HistoryItem]` | 최근 5개 (인덱스 0이 최신) |
| `SELECTED_HISTORY_IDX` | `d_selected_history_idx` | `int \| None` | 펼쳐 볼 히스토리 인덱스 |
| `NOVEL_TEXT` | `d_novel_text` | `str` | 현재 분석 대상 원문 |

## 헬퍼 함수 (mise.state)

| 함수 | 호출 시점 |
|---|---|
| `init_state()` | 페이지 진입 직후 한 번 |
| `set_current_scene(scene, novel_text)` | 새 `SceneSchema`가 도착했을 때 (generate / regenerate 둘 다) |
| `update_edited_field(name, value)` | `scene_card`가 자동 호출 — C에서 신경 쓸 필요 없음 |
| `is_dirty()` | 편집 버퍼가 원본과 다른지 |
| `can_regenerate()` | 카운터가 한도 미만인지 |
| `increment_regen()` | `regenerate` 컴포넌트가 자동 호출 |
| `reset_regen_count()` | 새 원문으로 generate 호출 시 |
| `append_history(item)` | 이미지 생성 성공 직후 |
| `build_prev_scene_payload()` | `extract_scene(mode='regenerate', prev_scene=...)` 호출 직전 |
| `get_style_value()` | 백엔드로 넘길 영문 스타일 키워드가 필요할 때 |

## 스타일 프리셋 매핑

`mise.state.STYLE_PRESETS`:

| 라벨 (UI) | 값 (백엔드) |
|---|---|
| 시네마틱 | `cinematic` |
| 수채화 | `watercolor painting` |
| 픽셀아트 | `pixel art` |
| 웹툰풍 | `webtoon style` |

## HistoryItem 구조

```python
HistoryItem(
    novel_text: str,
    elements: dict,                  # SceneElements.model_dump()
    prompt: dict,                    # PromptResult.model_dump()
    style_label: str,                # 한국어 라벨
    image_bytes: bytes | None,       # PNG 직렬화 (PIL → encode_image_to_bytes 사용)
    mode: "generate" | "regenerate",
    created_at: datetime,            # 자동
)
```

PIL Image를 bytes로 변환하려면 `mise.components.history.encode_image_to_bytes(img)` 사용.

## C 단계 통합 패턴

```python
from mise.chains.scene_extractor import extract_scene
from mise.components.history import (
    encode_image_to_bytes,
    render_history_detail,
    render_history_strip,
)
from mise.components.regenerate import render_regenerate_button
from mise.components.scene_card import render_scene_cards, reset_card_widgets
from mise.components.style_preset import render_style_preset
from mise.state import (
    HistoryItem,
    Keys,
    append_history,
    build_prev_scene_payload,
    init_state,
    reset_regen_count,
    set_current_scene,
)

init_state()

# 1) 최초 시각화 (C 책임)
if st.button("시각화"):
    scene = extract_scene(novel_text, mode="generate")
    image = generate_image(scene.prompt.positive_prompt, scene.prompt.negative_prompt, scene.prompt.style)
    set_current_scene(scene, novel_text)
    reset_regen_count()
    reset_card_widgets()
    append_history(HistoryItem(
        novel_text=novel_text,
        elements=scene.elements.model_dump(),
        prompt=scene.prompt.model_dump(),
        style_label=st.session_state[Keys.STYLE_LABEL],
        image_bytes=encode_image_to_bytes(image),
        mode="generate",
    ))

# 2) 카드 + 스타일 + 재생성 (D 컴포넌트만 호출)
render_scene_cards()
render_style_preset()

def on_regenerate():
    prev = build_prev_scene_payload()
    scene = extract_scene(st.session_state[Keys.NOVEL_TEXT], mode="regenerate", prev_scene=prev)
    image = generate_image(scene.prompt.positive_prompt, scene.prompt.negative_prompt, scene.prompt.style)
    set_current_scene(scene, st.session_state[Keys.NOVEL_TEXT])
    reset_card_widgets()
    append_history(HistoryItem(
        novel_text=st.session_state[Keys.NOVEL_TEXT],
        elements=scene.elements.model_dump(),
        prompt=scene.prompt.model_dump(),
        style_label=st.session_state[Keys.STYLE_LABEL],
        image_bytes=encode_image_to_bytes(image),
        mode="regenerate",
    ))

render_regenerate_button(on_regenerate=on_regenerate)

# 3) 히스토리
render_history_strip()
render_history_detail()
```

## 제약 / 알려진 사항

- 재생성 한도 5회는 `mise.state.REGEN_LIMIT` 상수. 변경하면 카운터 표시·버튼 비활성 로직이 자동 반영됨.
- 히스토리 보관 한도 5개는 `HISTORY_LIMIT`. session 휘발성이므로 새로고침 시 사라진다 (기획서 MVP 제약).
- `SceneElements.objects`는 `list[str]`. `scene_card`는 콤마 구분 입력을 받아 자동으로 split/strip 한다.
- 편집된 카드 값은 다음 재생성 호출 때만 백엔드로 전달된다. 즉시 검증/반영 없음.
- `reset_card_widgets()`는 새 SceneSchema 적용 직후 한 번 호출해야 위젯 캐시가 새 값을 보여준다.

## 단독 실행

```bash
streamlit run mise/app_d_demo.py
```

더미 SceneSchema와 색상 placeholder 이미지로 카드 편집 → 재생성 → 히스토리 동작을 확인할 수 있다.
