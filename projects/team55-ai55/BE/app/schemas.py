from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictBaseModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class TaskStatus(StrEnum):
    todo = "todo"
    in_progress = "in_progress"
    blocked = "blocked"
    review = "review"
    done = "done"
    cancelled = "cancelled"


class ImportanceLevel(StrEnum):
    low = "low"
    medium = "medium"
    high = "high"
    critical = "critical"


class RiskLevel(StrEnum):
    ok = "ok"
    watch = "watch"
    at_risk = "at_risk"
    overdue = "overdue"


SoftCheckTriggerLabel = Literal[
    "implicit_dependency_suspected",
    "repeated_delay_root_cause",
    "milestone_task_mismatch",
    "task_definition_too_vague",
    "duplicate_task_suspected",
]


RiskActionType = Literal[
    "reschedule",
    "reassign",
    "split_task",
    "raise_importance",
    "lower_importance",
    "add_predecessor",
    "remove_predecessor",
]


class HourRange(StrictBaseModel):
    start: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    end: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")
    enabled: bool = True


class DefaultWorkingHours(StrictBaseModel):
    weekday: HourRange
    weekend: HourRange


class Project(StrictBaseModel):
    project_id: str = Field(pattern=r"^proj_[A-Za-z0-9]{8,}$")
    name: str = Field(max_length=80)
    goal: str = Field(default="", max_length=1000)
    starts_at: date
    ends_at: date
    default_working_hours: DefaultWorkingHours
    timezone: str = "Asia/Seoul"


class ProjectCreate(StrictBaseModel):
    name: str = Field(max_length=80)
    goal: str = Field(default="", max_length=1000)
    starts_at: date
    ends_at: date
    default_working_hours: DefaultWorkingHours
    timezone: str = "Asia/Seoul"


class AvailableHours(StrictBaseModel):
    day_of_week: int = Field(ge=0, le=6)
    start: str
    end: str


class Member(StrictBaseModel):
    member_id: str = Field(pattern=r"^mem_[A-Za-z0-9]{6,}$")
    name: str = Field(max_length=40)
    role: str = Field(max_length=40)
    weekly_capacity_hours: float = Field(default=40, ge=0, le=80)
    available_hours: list[AvailableHours] = Field(default_factory=list)


class Task(StrictBaseModel):
    task_id: str = Field(pattern=r"^task_[A-Za-z0-9]{8,}$")
    project_id: str
    milestone_id: str | None = None
    title: str = Field(max_length=120)
    description: str = Field(default="", max_length=2000)
    assignee_id: str | None = None
    deadline: datetime | None = None
    importance: ImportanceLevel
    estimated_hours: float | None = Field(default=None, ge=0.25, le=200)
    status: TaskStatus
    progress_percent: int = Field(default=0, ge=0, le=100)
    delay_reason: str | None = Field(default=None, max_length=400)
    predecessor_ids: list[str] = Field(default_factory=list)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class MilestoneStatus(StrEnum):
    proposed = "proposed"
    approved = "approved"
    archived = "archived"


class Milestone(StrictBaseModel):
    milestone_id: str = Field(pattern=r"^ms_[A-Za-z0-9]{6,}$")
    project_id: str
    name: str = Field(max_length=80)
    due_date: date
    status: MilestoneStatus
    ai_rationale: str = Field(default="", max_length=400)
    approved_at: datetime | None = None


class ProposedMilestone(StrictBaseModel):
    name: str = Field(max_length=80)
    due_date: date
    ai_rationale: str = Field(default="", max_length=400)


class CalendarEventSource(StrEnum):
    ai_suggested = "ai_suggested"
    pm_manual = "pm_manual"
    external_blocking = "external_blocking"


class InternalCalendarEvent(StrictBaseModel):
    event_id: str = Field(pattern=r"^evt_[A-Za-z0-9]{8,}$")
    project_id: str
    task_id: str
    assignee_id: str | None = None
    starts_at: datetime
    ends_at: datetime
    approved: bool
    approved_at: datetime | None = None
    source: CalendarEventSource = CalendarEventSource.ai_suggested


class ProjectSnapshot(StrictBaseModel):
    project: Project
    members: list[Member]
    tasks: list[Task]
    milestones: list[Milestone]
    calendar_events: list[InternalCalendarEvent]


class PriorityFactors(StrictBaseModel):
    deadline_pressure: float = Field(ge=0, le=1)
    importance: float = Field(ge=0, le=1)
    predecessor_pressure: float = Field(ge=0, le=1)
    progress_gap: float = Field(ge=0, le=1)
    overload_penalty: float = Field(ge=0, le=1)


class PriorityScore(StrictBaseModel):
    task_id: str
    score: int = Field(ge=0, le=100)
    rank: int = Field(ge=1)
    factors: PriorityFactors
    evidence_facts: list[str] = Field(min_length=1)
    rationale: str = Field(max_length=200)


class TaskDecompositionSubtask(StrictBaseModel):
    title: str = Field(max_length=120)
    description: str = Field(default="", max_length=500)
    estimated_hours_range: tuple[float, float]
    suggested_assignee_role: str | None = None
    suggested_predecessors_within_decomposition: list[Annotated[int, Field(ge=0)]] = Field(default_factory=list)


class TaskDecomposition(StrictBaseModel):
    source_task_id: str
    subtasks: list[TaskDecompositionSubtask] = Field(min_length=2, max_length=8)
    decomposition_confidence: float = Field(ge=0, le=1)


class AgentMeta(StrictBaseModel):
    decomposition_calls: int = 0
    narrator_calls: int = 0
    schema_retries: int = 0


class TaskAssignment(StrictBaseModel):
    task_id: str
    assignee_id: str
    rationale_facts: list[str] = Field(min_length=1)
    rationale: str = Field(max_length=200)


class PriorityResponse(StrictBaseModel):
    project_id: str
    tasks_priority: list[PriorityScore]
    task_decompositions: list[TaskDecomposition]
    task_assignments: list[TaskAssignment]
    warnings: list[str]
    agent_meta: AgentMeta = Field(default_factory=AgentMeta)


class SlotQuality(StrEnum):
    preferred = "preferred"
    acceptable = "acceptable"
    fallback = "fallback"


class Conflict(StrictBaseModel):
    event_id: str
    kind: Literal["soft_overlap", "hard_overlap"]


class ScheduleBlock(StrictBaseModel):
    starts_at: datetime
    ends_at: datetime


class CandidateSlot(StrictBaseModel):
    starts_at: datetime
    ends_at: datetime
    time_blocks: list[ScheduleBlock] = Field(default_factory=list)
    quality: SlotQuality
    fit_score: int = Field(ge=0, le=100)
    conflicts: list[Conflict]
    rationale_facts: list[str] = Field(min_length=1)


class SlotProposal(StrictBaseModel):
    task_id: str
    candidate_slots: list[CandidateSlot] = Field(min_length=1, max_length=5)
    selected_index: int = Field(ge=0)
    rerank_rationale: str | None = Field(default=None, max_length=120)
    rerank_source: Literal["deterministic", "llm_reranked"] = "deterministic"

    @field_validator("selected_index")
    @classmethod
    def selected_index_must_be_valid(cls, value: int, info):
        slots = info.data.get("candidate_slots", [])
        if slots and value >= len(slots):
            raise ValueError("selected_index out of candidate_slots range")
        return value


class UnschedulableTask(StrictBaseModel):
    task_id: str
    reasons: list[
        Literal[
            "predecessor_incomplete",
            "no_capacity_before_deadline",
            "estimated_hours_missing",
            "assignee_missing",
            "deadline_in_past",
            "circular_dependency",
        ]
    ]


class ScheduleResponse(StrictBaseModel):
    project_id: str
    slot_proposals: list[SlotProposal]
    unschedulable: list[UnschedulableTask]
    warnings: list[str]


class RiskCheck(StrictBaseModel):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    group: Literal["deadline", "dependency", "workload"]
    label: str
    result: Literal["pass", "fail", "not_applicable"]
    applicable: bool
    is_blocker: bool
    evidence_facts: list[str] = Field(min_length=1)


class RiskAction(StrictBaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True, serialize_by_alias=True)

    type: RiskActionType
    target_task_id: str | None = None
    from_: str | None = Field(default=None, alias="from")
    to: str | None = None


class SoftCheck(StrictBaseModel):
    id: str = Field(pattern=r"^S[1-9][0-9]*$")
    trigger_label: SoftCheckTriggerLabel
    confidence: float = Field(ge=0.5, le=1)
    involved_task_ids: list[str] = Field(min_length=1)
    supporting_facts: list[str] = Field(min_length=1)
    suggested_action: RiskAction | None = None
    user_facing_text: str = Field(max_length=200)


class TaskRiskLevel(StrictBaseModel):
    task_id: str
    level: RiskLevel
    reasons: list[str]


class MemberWorkload(StrictBaseModel):
    member_id: str
    scheduled_hours_next_7d: float
    capacity_hours: float
    utilization: float
    is_overloaded: bool


class RiskSuggestion(StrictBaseModel):
    id: str = Field(pattern=r"^rs_[A-Za-z0-9]{6,}$")
    fixes_check_ids: list[str] = Field(min_length=1)
    action: RiskAction
    rationale_facts: list[str] = Field(min_length=1)
    removes_blocker: bool
    user_facing_text: str = Field(max_length=200)


class RiskResponse(StrictBaseModel):
    project_id: str
    checks: list[RiskCheck]
    soft_checks: list[SoftCheck]
    task_risk_levels: list[TaskRiskLevel]
    member_workload: list[MemberWorkload]
    blockers_failed: list[str]
    suggestions: list[RiskSuggestion] = Field(max_length=5)
    summary: str = Field(max_length=400)


class AnalyzeOptions(StrictBaseModel):
    request_decomposition_for: list[str] = Field(default_factory=list, max_length=5)
    schedule_horizon_days: int = Field(default=14, ge=1, le=60)
    include_unscheduled_in_response: bool = True
    use_llm: bool = True


class AnalyzeRequest(StrictBaseModel):
    snapshot: ProjectSnapshot
    options: AnalyzeOptions = Field(default_factory=AnalyzeOptions)


class LlmCalls(StrictBaseModel):
    priority_decompose: int = 0
    priority_narrate: int = 0
    schedule_rerank: int = 0
    risk_soft_checks: int = 0
    risk_narrate: int = 0
    total: int = 0


class LlmFallbacks(StrictBaseModel):
    schedule_rerank_violation: bool = False
    risk_soft_checks_timeout: bool = False
    narrator_fallback_template: bool = False
    priority_narrator_fallback: bool = False
    risk_narrator_fallback: bool = False


class AnalyzeMeta(StrictBaseModel):
    latency_ms: int
    agent_latencies_ms: dict[str, int]
    cache_hit: bool
    llm_calls: LlmCalls
    llm_fallbacks: LlmFallbacks = Field(default_factory=LlmFallbacks)


class AnalyzeResponse(StrictBaseModel):
    project_id: str
    snapshot_hash: str
    priority: PriorityResponse
    schedule: ScheduleResponse
    risk: RiskResponse
    meta: AnalyzeMeta


class MilestoneSuggestRequest(StrictBaseModel):
    snapshot: ProjectSnapshot
    max_milestones: int = Field(default=8, ge=1, le=8)


class MilestoneSuggestResponse(StrictBaseModel):
    project_id: str
    proposed_milestones: list[ProposedMilestone]
    agent_meta: dict[str, int]


class MilestoneApproveRequest(StrictBaseModel):
    approved: list[ProposedMilestone]
    rejected_count: int = Field(default=0, ge=0)


class MilestoneApproveResponse(StrictBaseModel):
    milestones: list[Milestone]


class ScheduleApproval(StrictBaseModel):
    task_id: str
    candidate_slot_index: int = Field(ge=0)
    override_starts_at: datetime | None = None
    override_ends_at: datetime | None = None


class ApproveScheduleRequest(StrictBaseModel):
    snapshot_hash: str
    approvals: list[ScheduleApproval]


class EventRejected(StrictBaseModel):
    task_id: str
    reason: str


class ApproveScheduleResponse(StrictBaseModel):
    events_created: list[InternalCalendarEvent]
    events_rejected: list[EventRejected]


class RiskSimulateRequest(StrictBaseModel):
    snapshot: ProjectSnapshot
    applied_suggestion_ids: list[str] = Field(default_factory=list)


class ScoreActionCoherence(StrictBaseModel):
    priority_delta: int
    priority_delta_by_task: dict[str, int]
    changed_to_pass_ids: list[str]
    passes_threshold: bool


class RiskSimulateResponse(StrictBaseModel):
    project_id: str
    applied_suggestion_ids: list[str]
    before: RiskResponse
    after: RiskResponse
    changed_check_ids: list[str]
    score_action_coherence: ScoreActionCoherence
