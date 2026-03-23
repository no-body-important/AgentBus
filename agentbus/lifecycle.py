from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import shutil
from pathlib import Path

from agentbus.frontmatter import load_result, load_task, update_document_frontmatter
from agentbus.agents import normalize_handle
from agentbus.models import TaskFrontmatter, TaskStatus
from agentbus.repo import AgentBusRepo


@dataclass(frozen=True)
class LifecycleMove:
    source: Path
    target: Path


@dataclass(frozen=True)
class LifecycleOperation:
    action: str
    task: LifecycleMove
    result: LifecycleMove | None
    archive_root: Path
    task_id: str


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def archive_task_pair(
    repo: AgentBusRepo,
    task_path: Path,
    result_path: Path | None = None,
    dry_run: bool = False,
) -> LifecycleOperation:
    task = load_task(task_path)
    archive_root = _archive_root(repo, task)
    task_target = archive_root / task_path.name
    result_source = result_path or _find_result_for_task(repo, task)
    result_target = archive_root / result_source.name if result_source is not None else None

    if not dry_run:
        archive_root.mkdir(parents=True, exist_ok=True)
        archived_task = task.model_copy(update={"status": TaskStatus.archived, "updated_at": now_utc()})
        update_document_frontmatter(task_path, archived_task.model_dump(mode="json"))
        _move_path(task_path, task_target)
        if result_source is not None and result_target is not None:
            _move_path(result_source, result_target)

    return LifecycleOperation(
        action="archive",
        task=LifecycleMove(source=task_path, target=task_target),
        result=LifecycleMove(source=result_source, target=result_target) if result_source and result_target else None,
        archive_root=archive_root,
        task_id=task.task_id,
    )


def promote_task_pair(
    repo: AgentBusRepo,
    archived_task_path: Path,
    archived_result_path: Path | None = None,
    dry_run: bool = False,
) -> LifecycleOperation:
    task = load_task(archived_task_path)
    archive_root = archived_task_path.parent
    task_target_dir = repo.task_dir(normalize_handle(task.to_agent))
    task_target = task_target_dir / archived_task_path.name
    result_source = archived_result_path or _find_archived_result_for_task(archive_root, task)
    result_target = None
    if result_source is not None:
        result = load_result(result_source)
        result_target = repo.result_dir(normalize_handle(result.reporting_agent)) / result_source.name

    if not dry_run:
        task_target_dir.mkdir(parents=True, exist_ok=True)
        promoted_task = task.model_copy(update={"status": TaskStatus.ready, "updated_at": now_utc()})
        update_document_frontmatter(archived_task_path, promoted_task.model_dump(mode="json"))
        _move_path(archived_task_path, task_target)
        if result_source is not None and result_target is not None:
            result_target.parent.mkdir(parents=True, exist_ok=True)
            _move_path(result_source, result_target)

    return LifecycleOperation(
        action="promote",
        task=LifecycleMove(source=archived_task_path, target=task_target),
        result=LifecycleMove(source=result_source, target=result_target) if result_source and result_target else None,
        archive_root=archive_root,
        task_id=task.task_id,
    )


def _archive_root(repo: AgentBusRepo, task: TaskFrontmatter) -> Path:
    stamp = task.updated_at.astimezone(timezone.utc).strftime("%Y/%m/%d")
    return repo.archive_dir() / stamp / task.task_id


def _find_result_for_task(repo: AgentBusRepo, task: TaskFrontmatter) -> Path | None:
    for path in repo.all_result_files():
        try:
            result = load_result(path)
        except (OSError, ValueError):
            continue
        if result.task_id == task.task_id or result.trace_id == task.trace_id:
            return path
    return None


def _find_archived_result_for_task(archive_root: Path, task: TaskFrontmatter) -> Path | None:
    for path in sorted(archive_root.glob("RESULT-*.md")):
        try:
            result = load_result(path)
        except (OSError, ValueError):
            continue
        if result.task_id == task.task_id or result.trace_id == task.trace_id:
            return path
    return None


def _move_path(source: Path, target: Path) -> None:
    if target.exists():
        raise ValueError(f"destination already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(target))
