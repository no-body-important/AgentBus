from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

from agentbus.agents import AgentRegistry, default_registry, load_agent_registry, normalize_handle
from agentbus.frontmatter import load_task
from agentbus.models import RouteMode, TaskFrontmatter, TaskStatus
from agentbus.repo import AgentBusRepo


class RoutingSurface(str, Enum):
    task_file = "task_file"
    inbox_marker = "inbox_marker"
    issue_comment = "issue_comment"
    pull_request_review = "pull_request_review"
    push = "push"
    manual = "manual"


class RoutingAction(str, Enum):
    notify = "notify"
    review = "review"
    act = "act"
    observe = "observe"


@dataclass(frozen=True)
class RoutingDecision:
    target_agent: str
    route_mode: str
    action: str
    surface: str
    reason: str
    source_ref: str = ""
    trace_id: str = ""


@dataclass(frozen=True)
class RoutingReport:
    event_name: str
    decisions: list[RoutingDecision] = field(default_factory=list)
    comment_body: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_name": self.event_name,
            "decision_count": len(self.decisions),
            "comment_body": self.comment_body,
            "decisions": [asdict(decision) for decision in self.decisions],
        }


COMMENT_MODE_PATTERN = re.compile(r"\b(?P<mode>observe|review|act)\b", re.IGNORECASE)
MENTION_PATTERN = re.compile(r"@(?P<agent>[A-Za-z][A-Za-z0-9_-]*)")


def _action_for_mode(mode: RouteMode) -> RoutingAction:
    if mode == RouteMode.observe:
        return RoutingAction.observe
    if mode == RouteMode.review:
        return RoutingAction.review
    return RoutingAction.act


def route_task(task: TaskFrontmatter, source_ref: str = "") -> RoutingDecision:
    mode = task.route_mode
    return RoutingDecision(
        target_agent=normalize_handle(task.to_agent),
        route_mode=mode.value,
        action=_action_for_mode(mode).value,
        surface=RoutingSurface.task_file.value,
        reason=f"task {task.task_id} is {task.status.value} with route_mode {mode.value}",
        source_ref=source_ref,
        trace_id=task.trace_id or task.task_id,
    )


def route_comment(
    comment_body: str,
    registry: AgentRegistry | None = None,
    source_ref: str = "",
    trace_id: str = "",
    surface: RoutingSurface = RoutingSurface.issue_comment,
) -> list[RoutingDecision]:
    active_registry = registry or default_registry()
    explicit_mode = _extract_mode(comment_body)
    decisions: list[RoutingDecision] = []
    seen_handles: set[str] = set()

    for match in MENTION_PATTERN.finditer(comment_body or ""):
        token = match.group("agent")
        handle = active_registry.resolve(token)
        if handle is None or handle in seen_handles:
            continue

        seen_handles.add(handle)
        definition = active_registry.definition(handle)
        mode = explicit_mode or (definition.default_route_mode if definition else RouteMode.review)
        decisions.append(
            RoutingDecision(
                target_agent=handle,
                route_mode=mode.value,
                action=_action_for_mode(mode).value,
                surface=surface.value,
                reason=f"comment requested {handle} attention using {mode.value} mode",
                source_ref=source_ref,
                trace_id=trace_id,
            )
        )

    return decisions


def compose_comment(report: RoutingReport, registry: AgentRegistry | None = None) -> str:
    active_registry = registry or default_registry()
    if not report.decisions:
        return ""

    lines = [
        "<!-- agentbus-routed -->",
        "AgentBus routing update.",
        "",
        f"Event: `{report.event_name}`",
    ]

    for decision in report.decisions:
        definition = active_registry.definition(decision.target_agent)
        label = definition.label if definition and definition.label else decision.target_agent
        mention = f"@{decision.target_agent}"
        lines.append(
            f"- {mention} ({label}): {decision.action} in `{decision.route_mode}` mode "
            f"from `{decision.surface}`"
        )
        if decision.trace_id:
            lines[-1] += f" trace `{decision.trace_id}`"
        if decision.reason:
            lines.append(f"  - {decision.reason}")

    return "\n".join(lines).strip()


def route_event(
    repo: AgentBusRepo,
    event_name: str,
    event_payload: dict[str, Any] | None = None,
) -> RoutingReport:
    payload = event_payload or {}
    registry = load_agent_registry(repo.agents_config_path())
    decisions: list[RoutingDecision] = []

    if event_name in {"issue_comment", "pull_request_review"}:
        body = _extract_comment_body(event_name, payload)
        source_ref = _extract_comment_ref(event_name, payload)
        trace_id = _extract_trace_id(payload)
        surface = RoutingSurface.issue_comment if event_name == "issue_comment" else RoutingSurface.pull_request_review
        decisions.extend(route_comment(body, registry=registry, source_ref=source_ref, trace_id=trace_id, surface=surface))
        report = RoutingReport(event_name=event_name, decisions=decisions)
        return RoutingReport(event_name=event_name, decisions=decisions, comment_body=compose_comment(report, registry))

    if event_name == "push":
        for path in _extract_changed_paths(payload):
            if not path.startswith("agent_bus/tasks/") or not path.endswith(".md"):
                continue
            task_path = repo.root / path
            if not task_path.exists():
                continue
            task = load_task(task_path)
            decisions.append(route_task(task, source_ref=path))
        return RoutingReport(event_name=event_name, decisions=decisions)

    if event_name == "workflow_dispatch":
        for task_path in repo.all_task_files():
            task = load_task(task_path)
            if task.status == TaskStatus.ready:
                decisions.append(route_task(task, source_ref=str(task_path.relative_to(repo.root))))
        return RoutingReport(event_name=event_name, decisions=decisions)

    for task_path in repo.all_task_files():
        task = load_task(task_path)
        if task.status == TaskStatus.ready:
            decisions.append(route_task(task, source_ref=str(task_path.relative_to(repo.root))))

    return RoutingReport(event_name=event_name, decisions=decisions)


def report_to_json(report: RoutingReport) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True)


def _extract_mode(comment_body: str) -> RouteMode | None:
    match = COMMENT_MODE_PATTERN.search(comment_body or "")
    if not match:
        return None
    return RouteMode(match.group("mode").lower())


def _extract_comment_body(event_name: str, payload: dict[str, Any]) -> str:
    if event_name == "issue_comment":
        return str(payload.get("comment", {}).get("body", ""))
    if event_name == "pull_request_review":
        return str(payload.get("review", {}).get("body", ""))
    return ""


def _extract_comment_ref(event_name: str, payload: dict[str, Any]) -> str:
    if event_name == "issue_comment":
        issue = payload.get("issue", {})
        number = issue.get("number")
        return f"issue#{number}" if number is not None else ""
    if event_name == "pull_request_review":
        pr = payload.get("pull_request", {})
        number = pr.get("number")
        return f"pr#{number}" if number is not None else ""
    return ""


def _extract_trace_id(payload: dict[str, Any]) -> str:
    return str(payload.get("trace_id", "") or payload.get("comment", {}).get("node_id", "") or "")


def _extract_changed_paths(payload: dict[str, Any]) -> list[str]:
    paths: list[str] = []
    for commit in payload.get("commits", []) or []:
        for key in ("added", "modified", "removed"):
            for path in commit.get(key, []) or []:
                if path not in paths:
                    paths.append(path)
    return paths
