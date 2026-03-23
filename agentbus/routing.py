from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field, replace
from enum import Enum
from typing import Any

from agentbus.agents import AgentRegistry, default_registry, load_agent_registry, normalize_handle
from agentbus.inbox import write_inbox_marker
from agentbus.frontmatter import load_task
from agentbus.memory import build_memory_query_from_task, build_memory_query_from_text, search_memory
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
    context_notes: list[dict[str, Any]] = field(default_factory=list)
    inbox_markers: list[dict[str, Any]] = field(default_factory=list)
    thread_snapshots: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_name": self.event_name,
            "decision_count": len(self.decisions),
            "comment_body": self.comment_body,
            "context_notes": self.context_notes,
            "inbox_markers": self.inbox_markers,
            "thread_snapshots": self.thread_snapshots,
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


def route_task(task: TaskFrontmatter, source_ref: str = "", repo: AgentBusRepo | None = None) -> RoutingDecision:
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
        preferred_mode = explicit_mode or (definition.default_route_mode if definition else RouteMode.review)
        mode = definition.supported_mode(preferred_mode) if definition else preferred_mode
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


def route_labels(
    labels: list[str],
    registry: AgentRegistry | None = None,
    source_ref: str = "",
    trace_id: str = "",
    surface: RoutingSurface = RoutingSurface.issue_comment,
    explicit_mode: RouteMode | None = None,
    seen_handles: set[str] | None = None,
) -> list[RoutingDecision]:
    active_registry = registry or default_registry()
    active_seen = seen_handles or set()
    decisions: list[RoutingDecision] = []

    for label in labels:
        handle, mode = _parse_label(label, active_registry, explicit_mode)
        if handle is None or handle in active_seen:
            continue
        active_seen.add(handle)
        definition = active_registry.definition(handle)
        if definition is None:
            continue
        chosen_mode = definition.supported_mode(mode or definition.default_route_mode)
        decisions.append(
            RoutingDecision(
                target_agent=handle,
                route_mode=chosen_mode.value,
                action=_action_for_mode(chosen_mode).value,
                surface=surface.value,
                reason=f"label requested {handle} attention using {chosen_mode.value} mode",
                source_ref=source_ref,
                trace_id=trace_id,
            )
        )

    return decisions


def compose_comment(report: RoutingReport, registry: AgentRegistry | None = None) -> str:
    active_registry = registry or default_registry()
    visible_decisions = [
        decision
        for decision in report.decisions
        if _can_post_comment(active_registry, decision.target_agent)
    ]
    if not visible_decisions:
        return ""

    lines = [
        "<!-- agentbus-routed -->",
        "AgentBus routing update.",
        "",
        f"Event: `{report.event_name}`",
    ]

    for decision in visible_decisions:
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

    if report.context_notes:
        lines.extend(["", "Relevant memory context:"])
        for note in report.context_notes[:5]:
            title = note.get("title", "Untitled")
            memory_id = note.get("memory_id", "")
            source_path = note.get("source_path", "")
            summary = note.get("summary", "")
            lines.append(f"- {title} [{memory_id}] ({source_path})")
            if summary:
                lines.append(f"  - {summary}")

    return "\n".join(lines).strip()


def route_event(
    repo: AgentBusRepo,
    event_name: str,
    event_payload: dict[str, Any] | None = None,
    emit_inbox_markers: bool = False,
    emit_thread_markers: bool = False,
) -> RoutingReport:
    payload = event_payload or {}
    registry = load_agent_registry(repo.agents_config_path())
    decisions: list[RoutingDecision] = []
    context_notes: list[dict[str, Any]] = []

    if event_name in {"issue_comment", "pull_request_review"}:
        body = _extract_comment_body(event_name, payload)
        source_ref = _extract_comment_ref(event_name, payload)
        trace_id = _extract_trace_id(payload)
        surface = RoutingSurface.issue_comment if event_name == "issue_comment" else RoutingSurface.pull_request_review
        explicit_mode = _extract_mode(body)
        comment_decisions = route_comment(body, registry=registry, source_ref=source_ref, trace_id=trace_id, surface=surface)
        decisions.extend(comment_decisions)
        decisions.extend(
            route_labels(
                _extract_labels(payload),
                registry=registry,
                source_ref=source_ref,
                trace_id=trace_id,
                surface=surface,
                explicit_mode=explicit_mode,
                seen_handles={decision.target_agent for decision in comment_decisions},
            )
        )
        context_hits = search_memory(repo, build_memory_query_from_text(body, source_ref=source_ref, trace_id=trace_id), limit=3)
        context_notes = [
            {
                "memory_id": hit.note.memory_id,
                "title": hit.note.title,
                "source_type": hit.note.source_type,
                "source_path": hit.note.source_path,
                "summary": hit.note.summary,
                "score": hit.score,
                "tags": hit.note.tags,
            }
            for hit in context_hits
        ]
        inbox_markers: list[dict[str, Any]] = []
        if emit_inbox_markers:
            for decision in decisions:
                marker_path = write_inbox_marker(
                    repo,
                    decision.target_agent,
                    source_ref=source_ref or decision.source_ref or decision.trace_id or event_name,
                    summary=decision.reason or f"Routing update for {decision.target_agent}",
                    body=body or decision.reason,
                    trace_id=trace_id or decision.trace_id,
                    task_id=trace_id or source_ref or decision.trace_id or event_name,
                )
                inbox_markers.append(
                    {
                        "path": str(marker_path.relative_to(repo.root)),
                        "target_agent": decision.target_agent,
                        "source_ref": source_ref or decision.source_ref or decision.trace_id or event_name,
                        "trace_id": trace_id or decision.trace_id,
                    }
                )
        base_report = RoutingReport(
            event_name=event_name,
            decisions=decisions,
            context_notes=context_notes,
            inbox_markers=inbox_markers,
        )
        comment_body = compose_comment(base_report, registry)
        thread_snapshots: list[dict[str, Any]] = []
        if emit_thread_markers:
            from agentbus.bridge import write_thread_snapshot

            thread_path = write_thread_snapshot(
                repo,
                replace(base_report, comment_body=comment_body),
                source_ref=source_ref or trace_id or event_name,
            )
            thread_snapshots.append(
                {
                    "path": str(thread_path.relative_to(repo.root)),
                    "source_ref": source_ref or trace_id or event_name,
                    "trace_id": trace_id,
                }
            )
        return replace(base_report, comment_body=comment_body, thread_snapshots=thread_snapshots)

    if event_name == "push":
        for path in _extract_changed_paths(payload):
            if not path.startswith("agent_bus/tasks/") or not path.endswith(".md"):
                continue
            task_path = repo.root / path
            if not task_path.exists():
                continue
            task = load_task(task_path)
            decisions.append(route_task(task, source_ref=path, repo=repo))
            context_hits = search_memory(repo, build_memory_query_from_task(task), limit=2)
            for hit in context_hits:
                context_notes.append(
                    {
                        "memory_id": hit.note.memory_id,
                        "title": hit.note.title,
                        "source_type": hit.note.source_type,
                        "source_path": hit.note.source_path,
                        "summary": hit.note.summary,
                        "score": hit.score,
                        "tags": hit.note.tags,
                    }
                )
        return RoutingReport(event_name=event_name, decisions=decisions, context_notes=context_notes)

    if event_name == "workflow_dispatch":
        for task_path in repo.all_task_files():
            task = load_task(task_path)
            if task.status == TaskStatus.ready:
                decisions.append(route_task(task, source_ref=str(task_path.relative_to(repo.root)), repo=repo))
                context_hits = search_memory(repo, build_memory_query_from_task(task), limit=2)
                for hit in context_hits:
                    context_notes.append(
                        {
                            "memory_id": hit.note.memory_id,
                            "title": hit.note.title,
                            "source_type": hit.note.source_type,
                            "source_path": hit.note.source_path,
                            "summary": hit.note.summary,
                            "score": hit.score,
                            "tags": hit.note.tags,
                        }
                    )
        return RoutingReport(event_name=event_name, decisions=decisions, context_notes=context_notes)

    for task_path in repo.all_task_files():
        task = load_task(task_path)
        if task.status == TaskStatus.ready:
            decisions.append(route_task(task, source_ref=str(task_path.relative_to(repo.root)), repo=repo))
            context_hits = search_memory(repo, build_memory_query_from_task(task), limit=2)
            for hit in context_hits:
                context_notes.append(
                    {
                        "memory_id": hit.note.memory_id,
                        "title": hit.note.title,
                        "source_type": hit.note.source_type,
                        "source_path": hit.note.source_path,
                        "summary": hit.note.summary,
                        "score": hit.score,
                        "tags": hit.note.tags,
                    }
                )

    return RoutingReport(event_name=event_name, decisions=decisions, context_notes=context_notes)


def report_to_json(report: RoutingReport) -> str:
    return json.dumps(report.to_dict(), indent=2, sort_keys=True)


def _can_post_comment(registry: AgentRegistry, handle: str) -> bool:
    definition = registry.definition(handle)
    if definition is None:
        definition = default_registry().definition(handle)
    return bool(definition and definition.can_post_comments)


def build_routing_ledger_path(ledger_dir: Path, event_name: str) -> Path:
    from datetime import datetime, timezone

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    safe_event = re.sub(r"[^a-zA-Z0-9_-]+", "-", event_name).strip("-").lower() or "event"
    return ledger_dir / f"ROUTING-{timestamp}-{safe_event}.json"


def write_routing_ledger(report: RoutingReport, ledger_dir: Path, event_name: str) -> Path:
    ledger_dir.mkdir(parents=True, exist_ok=True)
    ledger_path = build_routing_ledger_path(ledger_dir, event_name)
    ledger_path.write_text(report_to_json(report), encoding="utf-8")
    return ledger_path


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


def _extract_labels(payload: dict[str, Any]) -> list[str]:
    raw_labels: list[Any] = []
    issue = payload.get("issue", {})
    pull_request = payload.get("pull_request", {})
    if isinstance(issue, dict):
        raw_labels.extend(issue.get("labels", []) or [])
    if isinstance(pull_request, dict):
        raw_labels.extend(pull_request.get("labels", []) or [])

    labels: list[str] = []
    for entry in raw_labels:
        if isinstance(entry, dict):
            name = entry.get("name")
            if name:
                labels.append(str(name))
        elif entry:
            labels.append(str(entry))
    return labels


def _parse_label(label: str, registry: AgentRegistry, explicit_mode: RouteMode | None) -> tuple[str | None, RouteMode | None]:
    normalized = label.strip().lower()
    if not normalized:
        return None, None

    mode = explicit_mode
    if "act" in normalized:
        mode = RouteMode.act
    elif "observe" in normalized:
        mode = RouteMode.observe
    elif "review" in normalized:
        mode = RouteMode.review

    for token in re.split(r"[-: ]+", normalized):
        handle = registry.resolve(token)
        if handle:
            return handle, mode

    handle = registry.resolve(normalized)
    if handle:
        return handle, mode

    return None, None


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
