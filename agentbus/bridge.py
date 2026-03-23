from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from agentbus.frontmatter import write_document
from agentbus.models import ThreadFrontmatter
from agentbus.repo import AgentBusRepo
from agentbus.routing import RoutingReport


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def build_thread_id(event_name: str, source_ref: str, created_at: datetime | None = None) -> str:
    stamp = (created_at or now_utc()).strftime("%Y%m%d-%H%M%S")
    safe_source = source_ref.replace("/", "-").replace("#", "-").replace(" ", "-").strip("-").lower()
    safe_event = event_name.replace("/", "-").replace("#", "-").replace(" ", "-").strip("-").lower() or "event"
    return f"THREAD-{stamp}-{safe_event}-{safe_source[:36] or 'bridge'}"


def build_thread_body(report: RoutingReport) -> str:
    lines = [
        "# Bridge Thread Snapshot",
        "",
        f"Event: `{report.event_name}`",
        f"Decisions: {len(report.decisions)}",
        f"Inbox markers: {len(report.inbox_markers)}",
    ]

    if report.decisions:
        lines.extend(["", "## Routing Decisions"])
        for decision in report.decisions:
            lines.append(
                f"- @{decision.target_agent}: {decision.action} in `{decision.route_mode}` "
                f"from `{decision.surface}`"
            )
            if decision.trace_id:
                lines[-1] += f" trace `{decision.trace_id}`"
            if decision.reason:
                lines.append(f"  - {decision.reason}")

    if report.inbox_markers:
        lines.extend(["", "## Inbox Markers"])
        for marker in report.inbox_markers:
            path = marker.get("path", "")
            target_agent = marker.get("target_agent", "")
            source_ref = marker.get("source_ref", "")
            trace_id = marker.get("trace_id", "")
            lines.append(f"- {target_agent}: {path}")
            if source_ref or trace_id:
                details = []
                if source_ref:
                    details.append(f"source `{source_ref}`")
                if trace_id:
                    details.append(f"trace `{trace_id}`")
                lines.append(f"  - {'; '.join(details)}")

    if report.context_notes:
        lines.extend(["", "## Memory Context"])
        for note in report.context_notes[:5]:
            title = note.get("title", "Untitled")
            memory_id = note.get("memory_id", "")
            source_path = note.get("source_path", "")
            summary = note.get("summary", "")
            lines.append(f"- {title} [{memory_id}] ({source_path})")
            if summary:
                lines.append(f"  - {summary}")

    if report.comment_body:
        lines.extend(["", "## Comment Body", "", report.comment_body])

    return "\n".join(lines).strip() + "\n"


def write_thread_snapshot(
    repo: AgentBusRepo,
    report: RoutingReport,
    source_ref: str,
    comment_path: str = "",
    dry_run: bool = False,
) -> Path:
    created = now_utc()
    thread_dir = repo.routing_ledger_dir() / "threads"
    thread_dir.mkdir(parents=True, exist_ok=True)
    thread_id = build_thread_id(report.event_name, source_ref, created)
    path = thread_dir / f"{thread_id}.md"
    frontmatter = ThreadFrontmatter(
        thread_id=thread_id,
        event_name=report.event_name,
        source_ref=source_ref,
        trace_id=_pick_trace_id(report),
        decision_count=len(report.decisions),
        inbox_count=len(report.inbox_markers),
        published_at=created,
        summary=_pick_summary(report),
        target_agents=[decision.target_agent for decision in report.decisions],
        comment_path=comment_path,
    )
    if not dry_run:
        write_document(path, frontmatter.model_dump(mode="json"), build_thread_body(report))
    return path


def _pick_trace_id(report: RoutingReport) -> str:
    for decision in report.decisions:
        if decision.trace_id:
            return decision.trace_id
    for marker in report.inbox_markers:
        trace_id = marker.get("trace_id", "")
        if trace_id:
            return str(trace_id)
    return ""


def _pick_summary(report: RoutingReport) -> str:
    if report.comment_body:
        first_line = report.comment_body.strip().splitlines()[0]
        return first_line[:160]
    if report.decisions:
        decision = report.decisions[0]
        return f"{decision.target_agent} -> {decision.action} ({decision.route_mode})"
    return "Bridge thread snapshot"
