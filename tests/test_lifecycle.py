from __future__ import annotations

from pathlib import Path

from agentbus.frontmatter import load_result, load_task, write_document
from agentbus.lifecycle import archive_task_pair, promote_task_pair
from agentbus.models import ResultStatus, TaskStatus
from agentbus.repo import AgentBusRepo


def _write_task(repo_root: Path) -> Path:
    task_dir = repo_root / "agent_bus" / "tasks" / "codex"
    task_dir.mkdir(parents=True, exist_ok=True)
    task_path = task_dir / "TASK-20260322-200.md"
    write_document(
        task_path,
        {
            "task_id": "TASK-20260322-200",
            "title": "Archive lifecycle",
            "project": "AgentBus",
            "from_agent": "codex",
            "to_agent": "codex",
            "owner": "tester",
            "created_at": "2026-03-22T00:00:00Z",
            "updated_at": "2026-03-22T00:00:00Z",
            "status": TaskStatus.ready.value,
            "route_mode": "act",
            "trace_id": "TRACE-20260322-200",
            "priority": "P2",
            "objective": "Verify archive/promote",
            "success_criteria": ["Archive and restore the pair"],
            "background": "",
            "allowed_actions": [],
            "forbidden_actions": [],
            "dependencies": [],
            "depends_on_results": [],
            "required_output_format": "RESULT_TEMPLATE.md",
            "related_artifacts": [],
            "superseded_by": "",
            "notes": "",
        },
        "## Request\nArchive lifecycle test.\n",
    )
    return task_path


def _write_result(repo_root: Path) -> Path:
    result_dir = repo_root / "agent_bus" / "results" / "codex"
    result_dir.mkdir(parents=True, exist_ok=True)
    result_path = result_dir / "RESULT-20260322-200.md"
    write_document(
        result_path,
        {
            "result_id": "RESULT-20260322-200",
            "task_id": "TASK-20260322-200",
            "reporting_agent": "codex",
            "completion_status": ResultStatus.completed.value,
            "started_at": "2026-03-22T00:00:00Z",
            "finished_at": "2026-03-22T00:01:00Z",
            "summary": "Archive lifecycle completed",
            "trace_id": "TRACE-20260322-200",
            "exact_actions_taken": ["wrote result"],
            "findings": [],
            "recommended_next_owner": "codex",
            "recommended_next_action": "Archive the pair.",
            "related_artifacts": ["agent_bus/tasks/codex/TASK-20260322-200.md"],
            "blockers": [],
            "risks": [],
            "confidence": "high",
            "notes": "",
        },
        "## Human-readable Report\n\nArchive lifecycle test.\n",
    )
    return result_path


def test_archive_and_promote_roundtrip(tmp_path: Path) -> None:
    repo = AgentBusRepo(root=tmp_path)
    task_path = _write_task(tmp_path)
    result_path = _write_result(tmp_path)

    archived = archive_task_pair(repo, task_path, result_path)

    assert archived.task.target.exists()
    assert archived.result is not None
    assert archived.result.target is not None
    assert not task_path.exists()
    assert not result_path.exists()

    archived_task = load_task(archived.task.target)
    assert archived_task.status == TaskStatus.archived

    promoted = promote_task_pair(repo, archived.task.target, archived_result_path=archived.result.target)

    assert promoted.task.target.exists()
    assert promoted.result is not None
    assert promoted.result.target is not None
    assert load_task(promoted.task.target).status == TaskStatus.ready
    assert load_result(promoted.result.target).completion_status == ResultStatus.completed
