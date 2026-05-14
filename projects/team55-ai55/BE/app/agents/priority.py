from __future__ import annotations

import json
import re
from datetime import datetime

from app.agents.common import ACTIVE_STATUSES, clamp, find_cycle
from app.schemas import (
    AgentMeta,
    ImportanceLevel,
    Member,
    PriorityFactors,
    PriorityResponse,
    PriorityScore,
    ProjectSnapshot,
    Task,
    TaskAssignment,
    TaskStatus,
)
from app.services.llm_client import llm_client
from app.services.metrics import record_llm_call, record_llm_schema_result, record_policy_violation


IMPORTANCE_SCORE = {
    ImportanceLevel.low: 0.20,
    ImportanceLevel.medium: 0.50,
    ImportanceLevel.high: 0.75,
    ImportanceLevel.critical: 0.95,
}
FORBIDDEN_WORDS = ("매력", "호감", "인상", "성격", "잘생", "멋지", "게으", "느려", "의지", "무능", "책임감", "능력")
NUMBER_RE = re.compile(r"\d+(?:\.\d+)?")
ASSIGNABLE_STATUSES = {TaskStatus.todo, TaskStatus.in_progress}
ROLE_PROFILES = [
    (
        "frontend",
        ("frontend", "front-end", "front", "프론트", "ui engineer", "react"),
        ("frontend", "front-end", "front", "프론트", "ui", "ux", "react", "vite", "css", "component", "page", "화면", "페이지", "컴포넌트"),
    ),
    (
        "backend",
        ("backend", "back-end", "back", "server", "api", "백엔드", "서버"),
        ("backend", "back-end", "server", "api", "fastapi", "endpoint", "db", "database", "schema", "auth", "백엔드", "서버", "데이터베이스", "엔드포인트", "인증"),
    ),
    (
        "design",
        ("design", "designer", "ux", "ui", "디자인", "디자이너"),
        ("design", "designer", "figma", "wireframe", "prototype", "ux", "디자인", "피그마", "와이어프레임", "프로토타입"),
    ),
    (
        "qa",
        ("qa", "test", "tester", "quality", "검증", "테스트"),
        ("qa", "test", "testing", "tester", "quality", "검증", "테스트", "회귀", "품질"),
    ),
    (
        "data",
        ("data", "analytics", "analyst", "데이터", "분석"),
        ("data", "analytics", "metric", "report", "dashboard", "데이터", "분석", "지표", "리포트"),
    ),
]


def _deadline_pressure(task: Task, now: datetime) -> float:
    if task.deadline is None:
        return 0.20
    days_left = (task.deadline - now).total_seconds() / 86400
    if days_left <= 0:
        return 1.00
    if days_left < 1:
        return 0.95
    if days_left < 3:
        return 0.80
    if days_left < 7:
        return 0.60
    if days_left < 14:
        return 0.40
    if days_left < 30:
        return 0.20
    return 0.10


def _predecessor_pressure(task: Task, tasks_by_id: dict[str, Task]) -> float:
    preds = [tasks_by_id[task_id] for task_id in task.predecessor_ids if task_id in tasks_by_id]
    if not preds:
        return 0
    incomplete = sum(1 for pred in preds if pred.status not in (TaskStatus.done, TaskStatus.cancelled))
    return incomplete / len(preds)


def _progress_gap(task: Task, now: datetime) -> float:
    if task.deadline is None or task.created_at is None:
        return 0
    span = (task.deadline - task.created_at).total_seconds()
    if span <= 0:
        return 0
    elapsed = max(0, (now - task.created_at).total_seconds())
    expected = min(100, 100 * elapsed / span)
    if task.progress_percent >= expected:
        return 0
    return clamp((expected - task.progress_percent) / 100)


def _overload_penalty(task: Task, tasks: list[Task]) -> float:
    if task.assignee_id is None and task.status in ACTIVE_STATUSES:
        return 1
    if task.assignee_id is None:
        return 0
    active_count = sum(
        1
        for item in tasks
        if item.assignee_id == task.assignee_id and item.status in (TaskStatus.todo, TaskStatus.in_progress)
    )
    return clamp(active_count / 6)


def _normalized_text(*values: str | None) -> str:
    return " ".join(value for value in values if value).lower()


def _task_role_hint(task: Task) -> str | None:
    task_text = _normalized_text(task.title, task.description)
    for hint, _role_keywords, task_keywords in ROLE_PROFILES:
        if any(keyword in task_text for keyword in task_keywords):
            return hint
    return None


def _role_match_score(task: Task, member: Member) -> int:
    task_text = _normalized_text(task.title, task.description)
    member_role = _normalized_text(member.role)
    score = 0
    for _hint, role_keywords, task_keywords in ROLE_PROFILES:
        task_matches = [keyword for keyword in task_keywords if keyword in task_text]
        role_matches = [keyword for keyword in role_keywords if keyword in member_role]
        if task_matches and role_matches:
            score = max(score, 10 + min(len(task_matches), 5) + min(len(role_matches), 3))
    return score


def _member_active_load(member: Member, tasks: list[Task]) -> tuple[float, int, float]:
    active = [
        task
        for task in tasks
        if task.assignee_id == member.member_id and task.status in ASSIGNABLE_STATUSES
    ]
    hours = sum(task.estimated_hours or 1 for task in active)
    capacity = member.weekly_capacity_hours or 40
    utilization = hours / capacity if capacity else hours
    return utilization, len(active), hours


def _best_member_for_task(task: Task, snapshot: ProjectSnapshot) -> tuple[Member | None, list[str]]:
    if not snapshot.members:
        return None, ["배정 가능한 member가 없습니다."]
    role_hint = _task_role_hint(task) or "none"
    ranked = []
    for member in snapshot.members:
        role_score = _role_match_score(task, member)
        utilization, active_count, active_hours = _member_active_load(member, snapshot.tasks)
        ranked.append((role_score, utilization, active_count, active_hours, member))
    role_score, utilization, active_count, active_hours, member = min(
        ranked,
        key=lambda item: (-item[0], item[1], item[2], item[4].member_id),
    )
    rationale_facts = [
        f"Task 텍스트 role_hint={role_hint}",
        f"선택 member role={member.role}",
        f"role_match_score={role_score}",
        f"활성 Task {active_count}건 / 추정 {active_hours:g}h / capacity {member.weekly_capacity_hours:g}h",
        f"load_utilization={utilization:.2f}",
    ]
    return member, rationale_facts


def _assign_missing_assignees(snapshot: ProjectSnapshot) -> list[TaskAssignment]:
    assignments: list[TaskAssignment] = []
    for task in snapshot.tasks:
        if task.assignee_id is not None or task.status not in ASSIGNABLE_STATUSES:
            continue
        member, rationale_facts = _best_member_for_task(task, snapshot)
        if member is None:
            continue
        task.assignee_id = member.member_id
        assignments.append(
            TaskAssignment(
                task_id=task.task_id,
                assignee_id=member.member_id,
                rationale_facts=rationale_facts,
                rationale=f"{member.name}({member.role})에게 역할 단서와 현재 부하를 기준으로 배정했습니다.",
            )
        )
    return assignments


def _facts(task: Task, factors: PriorityFactors, now: datetime) -> list[str]:
    if task.deadline:
        days = round((task.deadline - now).total_seconds() / 86400, 1)
        deadline_fact = f"마감까지 D={days}일"
    else:
        deadline_fact = "마감일 없음"
    pred_total = len(task.predecessor_ids)
    pred_incomplete = round(factors.predecessor_pressure * pred_total)
    progress_fact = (
        "기대 대비 진척 지연"
        if factors.progress_gap > 0
        else f"진척률 {task.progress_percent}%로 기대 대비 양호"
    )
    assignment_fact = (
        f"담당자 미지정 감점 {factors.overload_penalty:.2f}"
        if task.assignee_id is None
        else f"담당자 배정됨, 활성 업무 부하 감점 {factors.overload_penalty:.2f}"
    )
    return [
        f"{deadline_fact} (deadline_pressure={factors.deadline_pressure:.2f})",
        f"중요도={task.importance.value} (점수 {factors.importance:.2f})",
        f"미완 선행 {pred_incomplete}/{pred_total}건",
        progress_fact,
        assignment_fact,
    ]


def _rationale(score: int, facts: list[str]) -> str:
    return f"우선순위 {score}점입니다. {facts[0]}와 {facts[1]}가 주요 근거입니다."


def _has_forbidden_words(text: str) -> bool:
    found = any(word in text for word in FORBIDDEN_WORDS)
    if found:
        record_policy_violation("forbidden_word")
    return found


def _number_tokens(text: str) -> set[str]:
    tokens = set()
    for value in NUMBER_RE.findall(text):
        tokens.add(value)
        try:
            tokens.add(f"{float(value):g}")
        except ValueError:
            pass
    return tokens


def _uses_only_allowed_numbers(text: str, allowed_text: str) -> bool:
    used = _number_tokens(text)
    if not used:
        return True
    allowed = _number_tokens(allowed_text)
    ok = used.issubset(allowed)
    if not ok:
        record_policy_violation("invented_number")
    return ok


async def _llm_rationales(scores: list[PriorityScore]) -> tuple[dict[str, str], int, int]:
    if not llm_client.configured or not scores:
        return {}, 0, 0
    calls = 0
    schema_retries = 0
    valid_task_ids = {item.task_id for item in scores[:10]}
    user_payload = json.dumps(
        [
            {
                "task_id": item.task_id,
                "rank": item.rank,
                "score": item.score,
                "evidence_facts": item.evidence_facts,
            }
            for item in scores[:10]
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    )
    for attempt in range(2):
        record_llm_call("priority_narrate")
        payload = await llm_client.chat_json(
            system=(
                "You receive deterministic priority scores and evidence facts. "
                "Return JSON only: {\"rationales\":[{\"task_id\":\"...\",\"text\":\"...\"}]}. "
                "Return exactly one rationale per supplied task_id and copy task_id exactly. "
                "Write Korean text <=200 chars using only the supplied rank, score, and evidence_facts. "
                "Copy numeric tokens exactly from the supplied score/evidence_facts when numbers are needed. "
                "Do not round, convert, estimate, add ordinal or rank numbers, or invent counts/dates/hours. "
                "Do not add ordinal or rank numbers unless copying the supplied rank exactly. "
                "Do not judge people."
            ),
            user=user_payload,
            purpose="priority_narrate",
            temperature=0,
            max_tokens=900,
        )
        calls += 1
        rationales: dict[str, str] = {}
        violation = False
        items = (payload or {}).get("rationales")
        if not isinstance(items, list):
            violation = True
        else:
            score_by_task_id = {score.task_id: score for score in scores}
            for item in items:
                if not isinstance(item, dict):
                    violation = True
                    continue
                task_id = item.get("task_id")
                text = item.get("text")
                score_item = score_by_task_id.get(task_id) if isinstance(task_id, str) else None
                if (
                    not isinstance(task_id, str)
                    or task_id not in valid_task_ids
                    or not isinstance(text, str)
                    or len(text) > 200
                    or _has_forbidden_words(text)
                    or score_item is None
                    or not _uses_only_allowed_numbers(
                        text,
                        str(
                            {
                                "rank": score_item.rank,
                                "score": score_item.score,
                                "evidence_facts": score_item.evidence_facts,
                            }
                        ),
                    )
                ):
                    violation = True
                    continue
                rationales[task_id] = text
        if rationales:
            record_llm_schema_result("priority_narrate", True)
            return rationales, calls, schema_retries
        if not violation:
            record_llm_schema_result("priority_narrate", True)
            return rationales, calls, schema_retries
        record_llm_schema_result("priority_narrate", False)
        if attempt == 0:
            schema_retries += 1
    return {}, calls, schema_retries


async def _llm_decompose(task: Task, snapshot: ProjectSnapshot):
    if not llm_client.configured or task.estimated_hours is None:
        return None, 0, 0
    calls = 0
    schema_retries = 0
    for attempt in range(2):
        record_llm_call("priority_decompose")
        payload = await llm_client.chat_json(
            system=(
                "Decompose a task into 2 to 8 Korean subtasks. Output JSON only: "
                "{\"subtasks\":[{\"title\":\"...\",\"description\":\"...\",\"estimated_hours_range\":[1,2],"
                "\"suggested_assignee_role\":\"...\",\"suggested_predecessors_within_decomposition\":[]}],"
                "\"decomposition_confidence\":0.7}. "
                "estimated_hours_range must be two positive numbers [min,max] with max >= min. "
                "suggested_predecessors_within_decomposition must contain only zero-based subtask indexes. "
                "Use only supplied task/project facts. Do not infer importance, deadline, or assignee."
            ),
            user=json.dumps(
                {"task": task.model_dump(mode="json"), "project_goal": snapshot.project.goal},
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            purpose="priority_decompose",
            temperature=0,
            max_tokens=1000,
        )
        calls += 1
        subtasks = (payload or {}).get("subtasks")
        verified = _verify_decomposition_payload(subtasks, task)
        if verified is not None:
            record_llm_schema_result("priority_decompose", True)
            return {
                "source_task_id": task.task_id,
                "subtasks": verified,
                "decomposition_confidence": float((payload or {}).get("decomposition_confidence", 0.6)),
            }, calls, schema_retries
        record_llm_schema_result("priority_decompose", False)
        if attempt == 0:
            schema_retries += 1
    return None, calls, schema_retries


def _verify_decomposition_payload(subtasks, source_task: Task) -> list[dict] | None:
    if not isinstance(subtasks, list) or not (2 <= len(subtasks) <= 8):
        return None
    verified: list[dict] = []
    total_min = 0.0
    total_max = 0.0
    for index, item in enumerate(subtasks):
        if not isinstance(item, dict):
            return None
        title = item.get("title")
        hours = item.get("estimated_hours_range")
        predecessors = item.get("suggested_predecessors_within_decomposition", [])
        if not isinstance(title, str) or not title.strip() or _has_forbidden_words(title):
            return None
        if not isinstance(hours, list) or len(hours) != 2:
            return None
        try:
            min_hours = float(hours[0])
            max_hours = float(hours[1])
        except (TypeError, ValueError):
            return None
        if min_hours <= 0 or max_hours < min_hours:
            return None
        if not isinstance(predecessors, list) or any(
            not isinstance(pred, int) or pred < 0 or pred >= len(subtasks) or pred == index
            for pred in predecessors
        ):
            return None
        description = item.get("description", "")
        if isinstance(description, str) and _has_forbidden_words(description):
            return None
        total_min += min_hours
        total_max += max_hours
        verified.append(
            {
                **item,
                "title": title.strip(),
                "description": description if isinstance(description, str) else "",
                "estimated_hours_range": [min_hours, max_hours],
                "suggested_predecessors_within_decomposition": predecessors,
            }
        )
    if source_task.estimated_hours is None:
        return None
    if total_min > source_task.estimated_hours * 1.3:
        return None
    if total_max < source_task.estimated_hours * 0.7:
        return None
    return verified


async def run_priority(
    snapshot: ProjectSnapshot,
    now: datetime,
    request_decomposition_for: list[str] | None = None,
    use_llm: bool = True,
) -> PriorityResponse:
    warnings: list[str] = []
    task_assignments = _assign_missing_assignees(snapshot)
    cycle = find_cycle(snapshot.tasks)
    if cycle:
        warnings.append(f"circular_dependency:{'->'.join(cycle)}")

    tasks_by_id = {task.task_id: task for task in snapshot.tasks}
    scores: list[PriorityScore] = []
    for task in snapshot.tasks:
        factors = PriorityFactors(
            deadline_pressure=_deadline_pressure(task, now),
            importance=IMPORTANCE_SCORE[task.importance],
            predecessor_pressure=_predecessor_pressure(task, tasks_by_id),
            progress_gap=_progress_gap(task, now),
            overload_penalty=_overload_penalty(task, snapshot.tasks),
        )
        raw = (
            0.35 * factors.deadline_pressure
            + 0.25 * factors.importance
            + 0.15 * factors.predecessor_pressure
            + 0.15 * factors.progress_gap
            - 0.10 * factors.overload_penalty
        )
        score = round(clamp(raw, 0, 1) * 100)
        facts = _facts(task, factors, now)
        scores.append(
            PriorityScore(
                task_id=task.task_id,
                score=score,
                rank=1,
                factors=factors,
                evidence_facts=facts,
                rationale=_rationale(score, facts),
            )
        )

    scores.sort(key=lambda item: (-item.score, item.task_id))
    ranked = [item.model_copy(update={"rank": index}) for index, item in enumerate(scores, start=1)]
    rationales, narrator_calls, narrator_retries = await _llm_rationales(ranked) if use_llm else ({}, 0, 0)
    if rationales:
        ranked = [item.model_copy(update={"rationale": rationales.get(item.task_id, item.rationale)}) for item in ranked]
    elif narrator_calls > 0:
        warnings.append("narrator_fallback_template")
    request_decomposition_for = request_decomposition_for or []
    if len(request_decomposition_for) > 5:
        warnings.append("decomposition_request_limit_exceeded")
        request_decomposition_for = request_decomposition_for[:5]
    decompositions = []
    decomposition_calls = 0
    schema_retries = narrator_retries
    for task_id in request_decomposition_for:
        task = tasks_by_id.get(task_id)
        if task is None:
            warnings.append(f"decomposition_task_not_found:{task_id}")
            continue
        if not use_llm:
            warnings.append(f"decomposition_llm_disabled:{task_id}")
            continue
        decomp, calls, retries = await _llm_decompose(task, snapshot)
        decomposition_calls += calls
        schema_retries += retries
        if decomp:
            decompositions.append(decomp)
        elif calls > 0:
            warnings.append(f"decomposition_schema_violation:{task_id}")

    return PriorityResponse(
        project_id=snapshot.project.project_id,
        tasks_priority=ranked,
        task_decompositions=decompositions,
        task_assignments=task_assignments,
        warnings=warnings,
        agent_meta=AgentMeta(
            decomposition_calls=decomposition_calls,
            narrator_calls=narrator_calls,
            schema_retries=schema_retries,
        ),
    )


class _SequentialPriorityGraph:
    async def ainvoke(self, state: dict):
        return {
            "priority": await run_priority(
                state["snapshot"],
                state["now"],
                state.get("request_decomposition_for", []),
                state.get("use_llm", True),
            )
        }


def _build_priority_subgraph():
    try:
        from langgraph.graph import END, START, StateGraph
    except ModuleNotFoundError:
        return _SequentialPriorityGraph()

    async def run_node(state: dict):
        return await _SequentialPriorityGraph().ainvoke(state)

    graph = StateGraph(dict)
    graph.add_node("run_priority", run_node)
    graph.add_edge(START, "run_priority")
    graph.add_edge("run_priority", END)
    return graph.compile()


priority_subgraph = _build_priority_subgraph()
