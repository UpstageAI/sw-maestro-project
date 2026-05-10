# Streamlit Supervisor Demo Design

## Goal

Build a demo-oriented Streamlit UI for the persona review pipeline.

The demo flow should be:

1. User enters a service idea.
2. The graph parses the idea.
3. Two personas are selected.
4. Each persona agent gives a first opinion.
5. Each persona agent reviews the other persona's opinion.
6. A neutral supervisor agent synthesizes the opinions and cross reviews into a final product-planning review.
7. Streamlit displays the progress and results in a way that is easy to explain during a live demo.

## Current Code Context

The current graph is:

```text
START
  -> f0_parse
  -> select_personas
  -> route_opinions via Send[]
  -> generate_opinion x2
  -> collect_opinions
  -> route_reviews via Send[]
  -> generate_review x2
  -> END
```

Important files:

- `app.py` is currently a Streamlit stub.
- `graph.py` owns LangGraph topology.
- `scripts/test_pipeline.py` is the current terminal end-to-end runner.
- `data/personas/persona_cards.seed.json` is gitignored and may not exist locally.
- `scripts/generate_user_cards.py` can regenerate persona cards from raw seed personas.
- Streamlit is already installed in project dependencies.

## Scope

In scope:

- Add `f4_supervisor` node.
- Add a review fan-in point before supervisor execution.
- Add `final_review_text` to `ProjectState`.
- Add a reusable pipeline runner service for Streamlit and terminal use.
- Implement `app.py` as the demo UI.
- Show LangSmith tracing status and current project name.
- Provide sample input loading from `data/service_plans/sample_brief.seed.json`.
- Handle missing persona card seed with clear UI guidance.

Out of scope:

- N-person dynamic routing.
- Authentication or deployment.
- Long-term storage of runs.
- Custom Streamlit components.
- Full LangSmith project management from the UI.

## Architecture

### `nodes/f4_supervisor.py`

New node responsible for final synthesis.

It should not role-play as a persona. It acts as a neutral product review coordinator and produces a single `final_review_text`.

Inputs from state:

- `brief`
- `persona_a`
- `persona_b`
- `opinion_a`
- `opinion_b`
- `review_a`
- `review_b`

Output:

- `final_review_text`

The supervisor output should have stable sections:

```text
1. 종합 판단
2. 긍정 신호
3. 주요 우려
4. 페르소나 간 차이
5. 다음 검증 포인트
```

### `graph.py`

Add two nodes:

- `collect_reviews`
- `supervisor_finalize`

Update the tail of the graph from:

```text
generate_review -> END
```

to:

```text
generate_review -> collect_reviews -> supervisor_finalize -> END
```

`collect_reviews` is a no-op join point. It exists so the supervisor runs only after both `review_a` and `review_b` have been merged into state.

### `state.py`

Add:

```python
final_review_text: str
```

Keep the current A/B fixed-slot state. The demo should prioritize clarity over dynamic N-person generalization.

### `services/pipeline_runner.py`

New shared runtime helper.

Responsibilities:

- Load sample input.
- Check whether persona cards exist.
- Optionally regenerate persona cards.
- Stream graph updates.
- Accumulate final state.
- Provide node labels for both CLI and Streamlit.

This keeps Streamlit UI code focused on rendering and prevents copying the `graph.stream()` loop from `scripts/test_pipeline.py`.

Suggested public functions:

```python
def load_sample_raw_input() -> str: ...
def persona_cards_exist() -> bool: ...
def regenerate_persona_cards() -> None: ...
def stream_pipeline(raw_input: str) -> Iterator[PipelineEvent]: ...
```

`PipelineEvent` can be a simple dataclass:

```python
@dataclass
class PipelineEvent:
    node_name: str
    label: str
    update_keys: list[str]
    update: dict
```

### `app.py`

Streamlit should be the first screen, not a landing page.

Layout:

```text
Sidebar
  - Persona card status
  - LangSmith tracing status
  - LangSmith project
  - Regenerate persona cards button

Main
  - Service idea input
  - Load sample button
  - Run review button
  - Progress/status area
  - Results tabs
```

Result tabs:

- `기획안`: parsed brief summary
- `페르소나`: selected persona A/B cards
- `1차 의견`: A/B opinions side by side
- `교차 리뷰`: A -> B and B -> A reviews
- `최종 요약`: supervisor final review
- `Debug`: raw update keys and optional state preview

The UI should be dense and practical, not a marketing page. It is an internal demo tool.

## LangSmith Demo Behavior

Streamlit should display:

```text
LangSmith tracing: on/off
Project: <LANGSMITH_PROJECT or default>
```

It should not create or delete LangSmith projects. Project naming can still be automated externally with `scripts/run_demo_trace.ps1`, or users can set `LANGSMITH_PROJECT` in `.env`.

If LangSmith is enabled, Streamlit should make this visible before the run starts so the presenter can open the matching project in LangSmith.

## Demo Interaction Flow

1. Presenter opens Streamlit.
2. Sidebar confirms persona card status and LangSmith project.
3. Presenter clicks `샘플 입력 불러오기` or types a service idea.
4. Presenter clicks `리뷰 실행`.
5. Progress area updates as graph nodes complete:
   - `f0 기획안 파싱`
   - `f1 페르소나 선택`
   - `f2 의견 생성`
   - `의견 fan-in`
   - `f3 교차 리뷰 생성`
   - `리뷰 fan-in`
   - `f4 최종 요약`
6. Results tabs populate from the final state.
7. Presenter opens LangSmith project to show trace details.

## Error Handling

The UI should fail clearly:

- Missing `UPSTAGE_API_KEY`: show sidebar error and disable run button.
- Missing `persona_cards.seed.json`: show warning and offer regeneration.
- Persona regeneration failure: show exception text.
- Pipeline failure: show the failed stage if available and the exception.
- Missing LangSmith API key while tracing is enabled: show warning, but do not block non-traced pipeline runs.

## Verification

Minimum verification:

- `python -m unittest discover -s tests -v`
- `python -c "import graph; import app; print('imports ok')"`
- `ruff check . --no-cache`
- Manual Streamlit launch:

```powershell
.venv\Scripts\streamlit.exe run app.py
```

Manual demo verification:

- Load sample input.
- Run pipeline.
- Confirm all result tabs populate.
- Confirm final supervisor summary exists.
- If LangSmith env is set, confirm trace appears under the displayed project.

## Later Improvements

- Add `--auto-langsmith-project` behavior to Streamlit launch wrapper.
- Add N-person reducer-based routing.
- Add a richer final review schema instead of plain `final_review_text`.
- Add export to Markdown.
- Add side-by-side LangSmith trace link if run URL becomes available.
