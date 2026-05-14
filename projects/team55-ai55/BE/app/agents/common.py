from __future__ import annotations

from collections import defaultdict, deque
from datetime import datetime

from app.schemas import Task, TaskStatus


ACTIVE_STATUSES = {TaskStatus.todo, TaskStatus.in_progress, TaskStatus.blocked, TaskStatus.review}


def clamp(value: float, lower: float = 0, upper: float = 1) -> float:
    return max(lower, min(upper, value))


def find_cycle(tasks: list[Task]) -> list[str] | None:
    task_ids = {task.task_id for task in tasks}
    graph = {task.task_id: [pid for pid in task.predecessor_ids if pid in task_ids] for task in tasks}
    visiting: set[str] = set()
    visited: set[str] = set()
    stack: list[str] = []

    def dfs(node: str) -> list[str] | None:
        if node in visiting:
            idx = stack.index(node)
            return stack[idx:] + [node]
        if node in visited:
            return None
        visiting.add(node)
        stack.append(node)
        for nxt in graph[node]:
            cycle = dfs(nxt)
            if cycle:
                return cycle
        stack.pop()
        visiting.remove(node)
        visited.add(node)
        return None

    for task_id in graph:
        cycle = dfs(task_id)
        if cycle:
            return cycle
    return None


def topo_sort(tasks: list[Task]) -> list[Task]:
    by_id = {task.task_id: task for task in tasks}
    indegree = {task.task_id: 0 for task in tasks}
    successors: dict[str, list[str]] = defaultdict(list)
    for task in tasks:
        for pred in task.predecessor_ids:
            if pred in by_id:
                indegree[task.task_id] += 1
                successors[pred].append(task.task_id)
    queue = deque([task_id for task_id, degree in indegree.items() if degree == 0])
    ordered: list[Task] = []
    while queue:
        task_id = queue.popleft()
        ordered.append(by_id[task_id])
        for nxt in successors[task_id]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0:
                queue.append(nxt)
    return ordered if len(ordered) == len(tasks) else tasks


def hours_between(start: datetime, end: datetime) -> float:
    return max(0, (end - start).total_seconds() / 3600)

