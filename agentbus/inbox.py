from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from agentbus.frontmatter import write_document
from agentbus.models import InboxFrontmatter, TaskStatus
from agentbus.repo import AgentBusRepo


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def build_inbox_id(agent: str, source_ref: str, created_at: datetime | None = None) -> str:
    stamp = (created_at or now_utc()).strftime("%Y%m%d-%H%M%S")
    safe_source = source_ref.replace("/", "-").replace("#", "-").replace(" ", "-").strip("-").lower()
    return f"INBOX-{stamp}-{agent.lower()}-{safe_source[:36] or 'bridge'}"


def write_inbox_marker(
    repo: AgentBusRepo,
    agent: str,
    source_ref: str,
    summary: str,
    body: str,
    trace_id: str = "",
    task_id: str = "",
    dry_run: bool = False,
) -> Path:
    created = now_utc()
    inbox_dir = repo.inbox_dir(agent)
    inbox_dir.mkdir(parents=True, exist_ok=True)
    inbox_id = build_inbox_id(agent, source_ref, created)
    path = inbox_dir / f"{inbox_id}.md"
    frontmatter = InboxFrontmatter(
        inbox_id=inbox_id,
        task_id=task_id or trace_id or source_ref or inbox_id,
        to_agent=agent,
        task_path=source_ref or task_id or inbox_id,
        published_at=created,
        status=TaskStatus.ready,
        trace_id=trace_id or source_ref or inbox_id,
        summary=summary,
        source_ref=source_ref,
    )
    if not dry_run:
        write_document(
            path,
            frontmatter.model_dump(mode="json"),
            body.strip() or "This inbox marker was created automatically by AgentBus.",
        )
    return path
