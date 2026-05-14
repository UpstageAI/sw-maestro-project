# 07. Data Contracts — 단일 진실 소스

> 이 문서는 모든 역할이 공유하는 **JSON 스키마 / API 계약** 단일 진실 소스다.
> 변경 시 모든 역할 담당자에게 PR 리뷰가 강제된다 (CODEOWNERS, `08-roles-and-handoffs.md §3.3`).

## 1. 공통 enum

### 1.1 task_status
```typescript
type TaskStatus =
  | "todo"
  | "in_progress"
  | "blocked"
  | "review"
  | "done"
  | "cancelled";
```

### 1.2 importance_level
PM이 직접 입력. Agent가 추정하지 않는다.
```typescript
type ImportanceLevel = "low" | "medium" | "high" | "critical";
// 점수 환산: low=20, medium=50, high=75, critical=95
```

### 1.3 risk_level
```typescript
type RiskLevel = "ok" | "watch" | "at_risk" | "overdue";
// ok=0, watch=1, at_risk=2, overdue=3 (정수 등급)
```

### 1.4 risk_check_group
```typescript
type RiskCheckGroup =
  | "deadline"     // 마감
  | "dependency"   // 선후행
  | "workload";    // 담당자 부하
```

### 1.5 suggestion_action_type
```typescript
type SuggestionAction =
  | "reschedule"        // 슬롯 변경
  | "reassign"          // 담당자 변경
  | "split_task"        // Task 분해
  | "raise_importance"  // 중요도 상향
  | "lower_importance"
  | "add_predecessor"
  | "remove_predecessor";
```

### 1.6 schedule_slot_quality
```typescript
type SlotQuality = "preferred" | "acceptable" | "fallback";
// preferred: 근무가능시간 + 마감 여유 > 50% + 충돌 없음
// acceptable: 근무가능시간 + 마감 여유 > 0% + 충돌 없음
// fallback: 근무가능시간 외이거나 마감 임박 (사용자 경고 표시)
```

### 1.7 approval_gate
```typescript
type ApprovalGate = "G1_milestone" | "G2_schedule" | "G3_core_field";
```

### 1.8 milestone_status
```typescript
type MilestoneStatus = "proposed" | "approved" | "archived";
```

## 2. 핵심 도메인 객체

### 2.1 Project
```json
{
  "type": "object",
  "required": ["project_id", "name", "starts_at", "ends_at", "default_working_hours"],
  "properties": {
    "project_id": {"type": "string", "pattern": "^proj_[A-Za-z0-9]{8,}$"},
    "name": {"type": "string", "maxLength": 80},
    "goal": {"type": "string", "maxLength": 1000, "description": "PM 자유 입력 — 마일스톤 LLM 제안 시 입력"},
    "starts_at": {"type": "string", "format": "date"},
    "ends_at": {"type": "string", "format": "date"},
    "default_working_hours": {
      "type": "object",
      "required": ["weekday", "weekend"],
      "properties": {
        "weekday": {"$ref": "#/$defs/HourRange"},
        "weekend": {"$ref": "#/$defs/HourRange"}
      }
    },
    "timezone": {"type": "string", "default": "Asia/Seoul"}
  },
  "$defs": {
    "HourRange": {
      "type": "object",
      "properties": {
        "start": {"type": "string", "pattern": "^([01]\\d|2[0-3]):[0-5]\\d$"},
        "end":   {"type": "string", "pattern": "^([01]\\d|2[0-3]):[0-5]\\d$"},
        "enabled": {"type": "boolean", "default": true}
      }
    }
  }
}
```

### 2.2 Member
```json
{
  "type": "object",
  "required": ["member_id", "name", "role"],
  "properties": {
    "member_id": {"type": "string", "pattern": "^mem_[A-Za-z0-9]{6,}$"},
    "name": {"type": "string", "maxLength": 40},
    "role": {"type": "string", "maxLength": 40, "description": "프론트엔드, 디자이너, 등"},
    "weekly_capacity_hours": {"type": "number", "minimum": 0, "maximum": 80, "default": 40},
    "available_hours": {
      "type": "array",
      "description": "요일별 가능 시간 윈도우 (없으면 default_working_hours 사용)",
      "items": {
        "type": "object",
        "required": ["day_of_week", "start", "end"],
        "properties": {
          "day_of_week": {"type": "integer", "minimum": 0, "maximum": 6},
          "start": {"type": "string"},
          "end":   {"type": "string"}
        }
      }
    }
  }
}
```

### 2.3 Task
원본 기획서 §3 "Task 입력 항목"을 모두 포함한다.

```json
{
  "type": "object",
  "required": ["task_id", "project_id", "title", "importance", "status"],
  "properties": {
    "task_id": {"type": "string", "pattern": "^task_[A-Za-z0-9]{8,}$"},
    "project_id": {"type": "string"},
    "milestone_id": {"type": ["string", "null"]},
    "title": {"type": "string", "maxLength": 120},
    "description": {"type": "string", "maxLength": 2000},
    "assignee_id": {"type": ["string", "null"], "description": "member_id"},
    "deadline": {"type": ["string", "null"], "format": "date-time"},
    "importance": {"enum": ["low", "medium", "high", "critical"]},
    "estimated_hours": {"type": ["number", "null"], "minimum": 0.25, "maximum": 200},
    "status": {"enum": ["todo", "in_progress", "blocked", "review", "done", "cancelled"]},
    "progress_percent": {"type": "integer", "minimum": 0, "maximum": 100, "default": 0},
    "delay_reason": {"type": ["string", "null"], "maxLength": 400},
    "predecessor_ids": {
      "type": "array",
      "items": {"type": "string"},
      "description": "선행 task_id 목록. DAG 검증 강제."
    },
    "created_at": {"type": "string", "format": "date-time"},
    "updated_at": {"type": "string", "format": "date-time"}
  }
}
```

### 2.4 Milestone
```json
{
  "type": "object",
  "required": ["milestone_id", "project_id", "name", "due_date", "status"],
  "properties": {
    "milestone_id": {"type": "string", "pattern": "^ms_[A-Za-z0-9]{6,}$"},
    "project_id": {"type": "string"},
    "name": {"type": "string", "maxLength": 80},
    "due_date": {"type": "string", "format": "date"},
    "status": {"enum": ["proposed", "approved", "archived"]},
    "ai_rationale": {"type": "string", "maxLength": 400, "description": "AI 제안 근거 (proposed 상태에서만)"},
    "approved_at": {"type": ["string", "null"], "format": "date-time"}
  }
}
```

### 2.5 InternalCalendarEvent
**내부 캘린더만**. Google Calendar 이벤트 객체를 흉내내지 않는다 (혼동 방지).
```json
{
  "type": "object",
  "required": ["event_id", "project_id", "task_id", "starts_at", "ends_at", "approved"],
  "properties": {
    "event_id": {"type": "string", "pattern": "^evt_[A-Za-z0-9]{8,}$"},
    "project_id": {"type": "string"},
    "task_id": {"type": "string"},
    "assignee_id": {"type": ["string", "null"]},
    "starts_at": {"type": "string", "format": "date-time"},
    "ends_at": {"type": "string", "format": "date-time"},
    "approved": {"type": "boolean", "description": "PM G2 승인 여부. false면 캘린더에 표시되지 않음."},
    "approved_at": {"type": ["string", "null"], "format": "date-time"},
    "source": {"enum": ["ai_suggested", "pm_manual", "external_blocking"], "description": "external_blocking은 내부 캘린더에 PM이 수동 입력한 회의 등 충돌 검사 대상"}
  }
}
```

### 2.6 ProjectSnapshot
모든 분석 요청은 이 스냅샷을 본문으로 보낸다 (서버 stateless).
```json
{
  "type": "object",
  "required": ["project", "members", "tasks", "milestones", "calendar_events"],
  "properties": {
    "project":         {"$ref": "Project"},
    "members":         {"type": "array", "items": {"$ref": "Member"}},
    "tasks":           {"type": "array", "items": {"$ref": "Task"}},
    "milestones":      {"type": "array", "items": {"$ref": "Milestone"}},
    "calendar_events": {"type": "array", "items": {"$ref": "InternalCalendarEvent"}, "description": "approved=true인 이벤트만 충돌 검사. external_blocking은 항상 충돌 검사."}
  }
}
```

## 3. Priority Agent 출력 (PriorityResponse)

```json
{
  "type": "object",
  "required": ["project_id", "tasks_priority", "task_decompositions", "task_assignments", "warnings", "agent_meta"],
  "properties": {
    "project_id": {"type": "string"},
    "tasks_priority": {
      "type": "array",
      "items": {"$ref": "#/$defs/PriorityScore"}
    },
    "task_decompositions": {
      "type": "array",
      "description": "AI가 제안한 세부 Task 분해 (PM이 승인해야 실제 Task로 생성). 분해 요청한 task만 포함.",
      "items": {"$ref": "#/$defs/TaskDecomposition"}
    },
    "task_assignments": {
      "type": "array",
      "description": "Priority Agent가 assignee_id=null인 active Task에 실제 반영한 담당자 배정 결과.",
      "items": {"$ref": "#/$defs/TaskAssignment"}
    },
    "warnings": {"type": "array", "items": {"type": "string"}},
    "agent_meta": {
      "type": "object",
      "properties": {
        "decomposition_calls": {"type": "integer"},
        "narrator_calls": {"type": "integer"},
        "schema_retries": {"type": "integer"}
      }
    }
  },
  "$defs": {
    "PriorityScore": {
      "type": "object",
      "required": ["task_id", "score", "rank", "factors", "evidence_facts", "rationale"],
      "properties": {
        "task_id": {"type": "string"},
        "score": {"type": "integer", "minimum": 0, "maximum": 100},
        "rank": {"type": "integer", "minimum": 1, "description": "1이 가장 시급"},
        "factors": {
          "type": "object",
          "required": ["deadline_pressure", "importance", "predecessor_pressure", "progress_gap", "overload_penalty"],
          "properties": {
            "deadline_pressure":    {"type": "number", "minimum": 0, "maximum": 1},
            "importance":           {"type": "number", "minimum": 0, "maximum": 1},
            "predecessor_pressure": {"type": "number", "minimum": 0, "maximum": 1},
            "progress_gap":         {"type": "number", "minimum": 0, "maximum": 1},
            "overload_penalty":     {"type": "number", "minimum": 0, "maximum": 1}
          }
        },
        "evidence_facts": {
          "type": "array",
          "items": {"type": "string"},
          "minItems": 1,
          "description": "결정적 사실 목록. LLM Narrator는 이 facts만 인용 가능."
        },
        "rationale": {
          "type": "string",
          "maxLength": 200,
          "description": "LLM Narrator의 한국어 자연어 설명. facts/숫자만 인용."
        }
      }
    },
    "TaskDecomposition": {
      "type": "object",
      "required": ["source_task_id", "subtasks", "decomposition_confidence"],
      "properties": {
        "source_task_id": {"type": "string"},
        "subtasks": {
          "type": "array",
          "minItems": 2,
          "maxItems": 8,
          "items": {
            "type": "object",
            "required": ["title", "estimated_hours_range"],
            "properties": {
              "title": {"type": "string", "maxLength": 120},
              "description": {"type": "string", "maxLength": 500},
              "estimated_hours_range": {
                "type": "array",
                "items": {"type": "number"},
                "minItems": 2, "maxItems": 2,
                "description": "[min, max] 시간 추정. 단일 값이 아님 (LLM 추정의 불확실성 반영)."
              },
              "suggested_assignee_role": {"type": "string"},
              "suggested_predecessors_within_decomposition": {
                "type": "array", "items": {"type": "integer"},
                "description": "이 분해 안의 다른 subtask 인덱스 (0-based). 외부 task ID 금지."
              }
            }
          }
        },
        "decomposition_confidence": {"type": "number", "minimum": 0, "maximum": 1}
      }
    },
    "TaskAssignment": {
      "type": "object",
      "required": ["task_id", "assignee_id", "rationale_facts", "rationale"],
      "properties": {
        "task_id": {"type": "string"},
        "assignee_id": {"type": "string"},
        "rationale_facts": {
          "type": "array",
          "items": {"type": "string"},
          "minItems": 1,
          "description": "역할 단서, member role, 현재 부하 등 결정적 배정 근거."
        },
        "rationale": {
          "type": "string",
          "maxLength": 200,
          "description": "담당자 배정 근거를 PM에게 설명하는 한국어 문장."
        }
      }
    }
  }
}
```

## 4. Schedule Agent 출력 (ScheduleResponse)

```json
{
  "type": "object",
  "required": ["project_id", "slot_proposals", "unschedulable", "warnings"],
  "properties": {
    "project_id": {"type": "string"},
    "slot_proposals": {
      "type": "array",
      "description": "Task별 후보 슬롯. PM이 1개 선택하거나 기각.",
      "items": {"$ref": "#/$defs/SlotProposal"}
    },
    "unschedulable": {
      "type": "array",
      "description": "근무가능시간/마감 안에서 슬롯을 못 찾은 Task ID + 이유",
      "items": {
        "type": "object",
        "required": ["task_id", "reasons"],
        "properties": {
          "task_id": {"type": "string"},
          "reasons": {"type": "array", "items": {"enum": [
            "predecessor_incomplete",
            "no_capacity_before_deadline",
            "estimated_hours_missing",
            "assignee_missing",
            "deadline_in_past",
            "circular_dependency"
          ]}}
        }
      }
    },
    "warnings": {"type": "array", "items": {"type": "string"}}
  },
  "$defs": {
    "SlotProposal": {
      "type": "object",
      "required": ["task_id", "candidate_slots", "selected_index"],
      "properties": {
        "task_id": {"type": "string"},
        "candidate_slots": {
          "type": "array",
          "minItems": 1,
          "maxItems": 5,
          "items": {"$ref": "#/$defs/CandidateSlot"}
        },
        "selected_index": {
          "type": "integer", "minimum": 0,
          "description": "Agent가 추천하는 candidate_slots의 인덱스 (PM이 변경 가능). LLM Reranker가 변경 가능, verify_rerank 통과 보장."
        },
        "rerank_rationale": {
          "type": ["string", "null"], "maxLength": 120,
          "description": "LLM Reranker의 1문장 한국어 설명. fallback 시 null."
        },
        "rerank_source": {
          "enum": ["deterministic", "llm_reranked"],
          "description": "최종 selected_index의 결정 출처. verify_rerank 위반 시 deterministic."
        }
      }
    },
    "CandidateSlot": {
      "type": "object",
      "required": ["starts_at", "ends_at", "quality", "fit_score", "conflicts", "rationale_facts"],
      "properties": {
        "starts_at": {"type": "string", "format": "date-time"},
        "ends_at":   {"type": "string", "format": "date-time"},
        "quality":   {"enum": ["preferred", "acceptable", "fallback"]},
        "fit_score": {
          "type": "integer", "minimum": 0, "maximum": 100,
          "description": "결정적 점수 = 0.5*마감 여유 + 0.3*근무가능시간 적합도 + 0.2*담당자 부하 역수"
        },
        "conflicts": {
          "type": "array",
          "items": {
            "type": "object",
            "required": ["event_id", "kind"],
            "properties": {
              "event_id": {"type": "string"},
              "kind": {"enum": ["soft_overlap", "hard_overlap"]}
            }
          }
        },
        "rationale_facts": {
          "type": "array",
          "items": {"type": "string"},
          "minItems": 1
        }
      }
    }
  }
}
```

## 5. Risk Agent 출력 (RiskResponse)

```json
{
  "type": "object",
  "required": ["project_id", "checks", "soft_checks", "task_risk_levels", "member_workload", "blockers_failed", "suggestions", "summary"],
  "properties": {
    "project_id": {"type": "string"},
    "checks": {
      "type": "array",
      "items": {"$ref": "#/$defs/RiskCheck"}
    },
    "soft_checks": {
      "type": "array",
      "description": "LLM 추론 위험 (텍스트 기반). hard checks와 분리. confidence ≥ 0.5만 포함. risk_level/blockers_failed에 영향 없음.",
      "items": {"$ref": "#/$defs/SoftCheck"}
    },
    "task_risk_levels": {
      "type": "array",
      "description": "Task별 risk_level (UI 빨강/노랑/초록 표시용)",
      "items": {
        "type": "object",
        "required": ["task_id", "level", "reasons"],
        "properties": {
          "task_id": {"type": "string"},
          "level": {"enum": ["ok", "watch", "at_risk", "overdue"]},
          "reasons": {"type": "array", "items": {"type": "string"}}
        }
      }
    },
    "member_workload": {
      "type": "array",
      "description": "담당자별 주간 부하",
      "items": {
        "type": "object",
        "required": ["member_id", "scheduled_hours_next_7d", "capacity_hours", "utilization", "is_overloaded"],
        "properties": {
          "member_id": {"type": "string"},
          "scheduled_hours_next_7d": {"type": "number"},
          "capacity_hours": {"type": "number"},
          "utilization": {"type": "number", "description": "scheduled / capacity"},
          "is_overloaded": {"type": "boolean", "description": "utilization > 1.0"}
        }
      }
    },
    "blockers_failed": {
      "type": "array",
      "items": {"type": "string"},
      "description": "실패한 blocker check ID 목록 (예: ['deadline_feasibility', 'dependency_correctness'])"
    },
    "suggestions": {
      "type": "array",
      "maxItems": 5,
      "items": {"$ref": "#/$defs/RiskSuggestion"}
    },
    "summary": {
      "type": "string",
      "maxLength": 400,
      "description": "LLM Narrator의 프로젝트 전체 리스크 요약. facts만 인용."
    }
  },
  "$defs": {
    "RiskCheck": {
      "type": "object",
      "required": ["id", "group", "label", "result", "applicable", "is_blocker", "evidence_facts"],
      "properties": {
        "id": {"type": "string", "pattern": "^[a-z][a-z0-9_]*$"},
        "group": {"enum": ["deadline", "dependency", "workload"]},
        "label": {"type": "string", "description": "사용자 표시용 한글 라벨"},
        "result": {"enum": ["pass", "fail", "not_applicable"]},
        "applicable": {"type": "boolean"},
        "is_blocker": {"type": "boolean"},
        "evidence_facts": {"type": "array", "items": {"type": "string"}, "minItems": 1}
      }
    },
    "SoftCheck": {
      "type": "object",
      "required": ["id", "trigger_label", "confidence", "involved_task_ids", "supporting_facts"],
      "properties": {
        "id": {"type": "string", "pattern": "^S[1-9][0-9]*$", "description": "S1~S5 등"},
        "trigger_label": {
          "enum": [
            "implicit_dependency_suspected",
            "repeated_delay_root_cause",
            "milestone_task_mismatch",
            "task_definition_too_vague",
            "duplicate_task_suspected"
          ]
        },
        "confidence": {"type": "number", "minimum": 0.5, "maximum": 1.0, "description": "verify가 0.5 미만은 폐기"},
        "involved_task_ids": {
          "type": "array",
          "items": {"type": "string"},
          "minItems": 1,
          "description": "verify가 환각 task_id를 차단"
        },
        "supporting_facts": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "suggested_action": {
          "type": ["object", "null"],
          "description": "정보성이면 null, action이 있으면 RiskSuggestion.action과 동일 schema",
          "properties": {
            "type": {"enum": ["reschedule", "reassign", "split_task", "raise_importance", "lower_importance", "add_predecessor", "remove_predecessor"]},
            "target_task_id": {"type": "string"},
            "from": {"type": "string"},
            "to": {"type": "string"}
          }
        },
        "user_facing_text": {"type": "string", "maxLength": 200, "description": "한국어, 금지 단어 필터 통과 보장"}
      }
    },
    "RiskSuggestion": {
      "type": "object",
      "required": ["id", "fixes_check_ids", "action", "rationale_facts", "removes_blocker"],
      "properties": {
        "id": {"type": "string", "pattern": "^rs_[A-Za-z0-9]{6,}$"},
        "fixes_check_ids": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "action": {
          "type": "object",
          "required": ["type"],
          "properties": {
            "type": {"enum": [
              "reschedule", "reassign", "split_task",
              "raise_importance", "lower_importance",
              "add_predecessor", "remove_predecessor"
            ]},
            "target_task_id": {"type": "string"},
            "from": {"type": "string", "description": "현재 값 (사람이 읽기용)"},
            "to":   {"type": "string", "description": "제안 값"}
          }
        },
        "rationale_facts": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "removes_blocker": {"type": "boolean"},
        "user_facing_text": {
          "type": "string", "maxLength": 200,
          "description": "LLM Narrator의 한국어 출력. 금지 단어 필터 통과 보장."
        }
      }
    }
  }
}
```

## 6. Backend API 계약

### 6.1 `POST /v1/projects` — 프로젝트 생성
**Request:** `Project` (project_id 없음, 서버가 발급)
**Response 201:** `Project` (project_id 포함)

### 6.2 `POST /v1/projects/{project_id}/milestones:suggest`
**Request:**
```json
{ "snapshot": "ProjectSnapshot", "max_milestones": 8 }
```
**Response 200:**
```json
{
  "project_id": "...",
  "proposed_milestones": [
    {"name": "...", "due_date": "...", "ai_rationale": "..."}
  ],
  "agent_meta": {"latency_ms": 2400, "tokens": 850}
}
```
> 응답의 마일스톤은 모두 `status="proposed"`. 실제 저장은 6.3 호출로.

### 6.3 `POST /v1/projects/{project_id}/milestones:approve` [G1 게이트]
**Request:**
```json
{
  "approved": [
    {"name": "...", "due_date": "...", "ai_rationale": "..."}
  ],
  "rejected_count": 2
}
```
**Response 200:**
```json
{ "milestones": [ "Milestone (status=approved)" ] }
```

### 6.4 `POST /v1/projects/{project_id}/analyze` — **메인 엔드포인트**
Priority + Schedule + Risk 3개 sub-graph를 super-graph로 실행.

**Request:**
```json
{
  "snapshot": "ProjectSnapshot",
  "options": {
    "request_decomposition_for": ["task_id", "..."],
    "schedule_horizon_days": 14,
    "include_unscheduled_in_response": true
  }
}
```

**Response 200 — AnalyzeResponse:**
```json
{
  "project_id": "string",
  "snapshot_hash": "sha256 of snapshot — used as idempotency key",
  "priority":   "PriorityResponse",
  "schedule":   "ScheduleResponse",
  "risk":       "RiskResponse",
  "meta": {
    "latency_ms": 5200,
    "agent_latencies_ms": {
      "priority": 1800, "schedule": 3000, "risk": 4500
    },
    "cache_hit": false,
    "llm_calls": {
      "priority_decompose":   0,
      "priority_narrate":     1,
      "schedule_rerank":      1,
      "risk_soft_checks":     1,
      "risk_narrate":         1,
      "total":                4
    },
    "llm_fallbacks": {
      "schedule_rerank_violation":  false,
      "risk_soft_checks_timeout":   false,
      "narrator_fallback_template": false
    }
  }
}
```

`llm_calls.total` 평균 4회 (분해 요청 시 +N). fallback 발생 시 사용자에게 작은 배지로 표시 가능 (선택).

**캐싱:** 동일 `snapshot_hash` 재요청 시 LLM 미호출 캐시 응답. TTL 1시간.

### 6.5 `POST /v1/projects/{project_id}/schedule:approve` [G2 게이트]
**Request:**
```json
{
  "snapshot_hash": "...",
  "approvals": [
    {"task_id": "task_xxx", "candidate_slot_index": 0},
    {"task_id": "task_yyy", "candidate_slot_index": 2, "override_starts_at": "2026-05-08T14:00:00+09:00", "override_ends_at": "..."}
  ]
}
```

**Response 200:**
```json
{
  "events_created": [ "InternalCalendarEvent (approved=true)" ],
  "events_rejected": [
    {"task_id": "...", "reason": "snapshot_hash_stale"}
  ]
}
```

**409 Conflict** — 응답 분석 시점 이후 Task가 변경된 경우 (snapshot_hash mismatch). PM에게 재분석 안내.

### 6.6 `POST /v1/projects/{project_id}/risk:simulate`
사용자가 RiskSuggestion 적용을 미리 보고 싶을 때.
**Request:** `{ "snapshot": "...", "applied_suggestion_ids": ["rs_xxx"] }`
**Response 200:** 원래 risk + 적용 후 시뮬 risk + 변경된 체크 ID
LLM 미사용. < 100ms.

### 6.7 `GET /v1/health`
의존성 헬스체크 (`upstage_api`).

### 6.8 에러 응답 (공통)
```json
{
  "error": {
    "code": "string",
    "message": "string (한국어)",
    "details": { /* 선택 */ }
  }
}
```

| code | HTTP | 의미 |
|---|---|---|
| `validation_error` | 422 | Pydantic 검증 실패 (필드 메시지 details에 포함) |
| `task_info_insufficient` | 422 | 마감/소요시간/중요도 누락 (기획서 §4) |
| `circular_dependency` | legacy 422 | 과거 DAG 차단 코드. 현재 `/analyze`는 Risk `dependency_correctness` fail로 순환 경로를 반환 |
| `snapshot_hash_stale` | 409 | 분석 응답 후 snapshot 변경 → 재분석 필요 |
| `unschedulable_task` | 200 | 에러 아님, ScheduleResponse.unschedulable에 포함 |
| `agent_failed` | 502 | LLM/내부 실패 |
| `rate_limited` | 429 | 레이트 리밋 |

## 7. 변경 관리 규칙

1. 본 문서가 schema 단일 진실 소스다.
2. Backend는 Pydantic v2 모델, Frontend는 Zod 스키마로 본 문서 기반 자동 생성을 유지한다 (수기 동기화 금지).
3. 필드 추가는 backward-compatible 하게 (선택 필드).
4. enum 변경은 모든 담당자에게 PR 리뷰 강제.
5. 5요소 가중치(`PriorityScore.factors`) 변경은 `02-agent-priority-spec.md`의 가중치 표 + 골든 셋 회귀 테스트 + Frontend 라벨 표를 동일 PR에 포함해야 한다.
6. 새 RiskCheck 추가는 `04-agent-risk-spec.md`의 체크 표 + `backend/app/scoring/risk_checks/` 새 클래스 + 단위테스트 4 케이스 + 골든 5케이스 회귀 검증을 동일 PR에 포함해야 한다 (`08-roles-and-handoffs.md §3.5`).
