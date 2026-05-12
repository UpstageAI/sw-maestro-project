# Two-Person Supervisor Review Flow Design

## Goal

The immediate goal is to finish a working two-person persona review pipeline:

1. Parse a user's raw service idea into a structured brief.
2. Select two personas.
3. Generate one opinion from each persona in parallel.
4. Let each persona review the other persona's opinion.
5. Add a supervisor node that reads the brief, selected personas, first opinions, and cross reviews, then produces one final review text for the user.

This keeps the current A/B state model for now. The purpose is to make the existing LangGraph flow complete and easy to inspect before moving to dynamic N-person routing.

## Current Blocker

`data/personas/persona_cards.seed.json` does not match `schemas.py`.

`TargetUserPersonaCard` currently expects these fields as `list[str]`:

- `user_goals`
- `pain_points`
- `positive_triggers`
- `negative_triggers`

The current seed JSON stores each item as an object with `text`, `source_field`, and `evidence`. Because of this, `load_personas()` fails during Pydantic validation before the graph can reach persona selection.

For this iteration, regenerate `persona_cards.seed.json` to match the current schema instead of expanding the schema.

## Scope

In scope:

- Regenerate persona cards so the current schema loads successfully.
- Keep the two-person A/B flow.
- Keep `Send` API and conditional edges for parallel opinion and review dispatch.
- Add a supervisor/finalization node after both cross reviews complete.
- Return a final user-facing review text.
- Add a focused script-level verification path.

Out of scope for this iteration:

- N-person dynamic persona selection.
- Reducer-based state such as `Annotated[list[Opinion], operator.add]`.
- All-to-all review routing.
- Streamlit UI completion.
- PersonaSignal schema with evidence tracking.

## State Design

Keep the current explicit A/B state keys:

```python
class ProjectState(TypedDict, total=False):
    raw_input: str
    brief: ServicePlanInput
    persona_a: TargetUserPersonaCard
    persona_b: TargetUserPersonaCard
    opinion_a: Opinion
    opinion_b: Opinion
    review_a: Review
    review_b: Review
    final_review_text: str
```

`final_review_text` is intentionally a string for this iteration. A structured `FinalReview` schema can be introduced later if the output needs sections, scores, or machine-readable decisions.

## Graph Design

The graph should end with a supervisor node:

```text
START
  -> f0_parse
  -> select_personas
  -> route_opinions via conditional edge
      -> generate_opinion for persona_a
      -> generate_opinion for persona_b
  -> collect_opinions
  -> route_reviews via conditional edge
      -> generate_review by persona_a on opinion_b
      -> generate_review by persona_b on opinion_a
  -> collect_reviews
  -> supervisor_finalize
  -> END
```

`collect_reviews` is a no-op join point, just like `collect_opinions`. It makes the graph boundary explicit: the supervisor only runs after both `review_a` and `review_b` exist.

## Node Responsibilities

### `f0_parse`

Converts `raw_input` into `ServicePlanInput`.

No design change.

### `select_personas`

Loads regenerated persona cards and selects exactly two personas.

No design change except that regenerated JSON must match `TargetUserPersonaCard`.

### `generate_opinion`

Runs once per persona through `Send`.

No design change. It writes to `opinion_a` or `opinion_b` based on the `slot` in the sub-state.

### `generate_review`

Runs once per reviewer through `Send`.

No design change. It writes to `review_a` or `review_b` based on the `slot` in the sub-state.

### `supervisor_finalize`

New node.

Inputs:

- `brief`
- `persona_a`, `persona_b`
- `opinion_a`, `opinion_b`
- `review_a`, `review_b`

Output:

- `final_review_text`

The supervisor should not role-play as either persona. It should act as a neutral product review coordinator and synthesize:

- where both personas agree
- where their reactions differ
- the most important positive signals
- the most important adoption risks
- whether the service idea looks promising for the selected target
- what should be changed or validated next

The final text should be readable by a product planner, not by another internal agent.

## Final Review Text Shape

The supervisor output should use a stable text structure:

```text
최종 리뷰

1. 종합 판단
...

2. 긍정 신호
...

3. 주요 우려
...

4. 페르소나 간 차이
...

5. 다음 검증 포인트
...
```

This is plain text for now. It keeps the final user experience simple and avoids adding a new shared schema before the pipeline is stable.

## Verification

Minimum verification for this iteration:

- `persona_cards.seed.json` loads through `load_personas()`.
- `import graph` succeeds.
- The graph streams through these stages:
  - `f0_parse`
  - `select_personas`
  - `generate_opinion`
  - `collect_opinions`
  - `generate_review`
  - `collect_reviews`
  - `supervisor_finalize`
- The final result contains `final_review_text`.
- `ruff check .` has no new errors from the edited files.

Full end-to-end verification requires a valid `UPSTAGE_API_KEY`.

## Later Expansion Plan

After this two-person flow works, migrate to dynamic N-person routing:

```python
class ProjectState(TypedDict, total=False):
    raw_input: str
    brief: ServicePlanInput
    selected_personas: list[TargetUserPersonaCard]
    opinions: Annotated[list[Opinion], operator.add]
    reviews: Annotated[list[Review], operator.add]
    final_review_text: str
```

The next design should replace fixed A/B keys with reducer-backed collections, then update routing in two steps:

1. `route_opinions`: dispatch one `generate_opinion` per selected persona.
2. `route_reviews`: start with round-robin review routing, then consider all-to-all reviews if cost and latency are acceptable.

The current two-person supervisor should be written so its prompt can later accept a list of opinions and reviews.
