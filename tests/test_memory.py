from __future__ import annotations

from pathlib import Path

from agentbus.frontmatter import write_document
from agentbus.memory import capture_memory_from_result, load_memory_index, search_memory
from agentbus.models import ResultFrontmatter, ResultStatus, TaskFrontmatter, TaskStatus
from agentbus.repo import AgentBusRepo
from agentbus.worker import WorkerConfig, run_worker_once


def _write_task(repo_root: Path, agent: str = "codex") -> Path:
    task_dir = repo_root / "agent_bus" / "tasks" / agent
    task_dir.mkdir(parents=True, exist_ok=True)
    task_path = task_dir / "TASK-20260322-100.md"
    write_document(
        task_path,
        {
            "task_id": "TASK-20260322-100",
            "title": "Capture memory test",
            "project": "AgentBus",
            "from_agent": "codex",
            "to_agent": agent,
            "owner": "tester",
            "created_at": "2026-03-22T00:00:00Z",
            "updated_at": "2026-03-22T00:00:00Z",
            "status": TaskStatus.ready.value,
            "route_mode": "act",
            "trace_id": "TRACE-20260322-100",
            "priority": "P2",
            "objective": "Test memory capture",
            "success_criteria": ["Create a memory note"],
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
        "## Request\nTest body.\n",
    )
    return task_path


def test_capture_memory_from_result_and_search(tmp_path: Path) -> None:
    repo = AgentBusRepo(root=tmp_path)
    task_path = _write_task(tmp_path)
    result_path = tmp_path / "agent_bus" / "results" / "codex" / "RESULT-20260322-100.md"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    write_document(
        result_path,
        {
            "result_id": "RESULT-20260322-100",
            "task_id": "TASK-20260322-100",
            "reporting_agent": "codex",
            "completion_status": ResultStatus.completed.value,
            "started_at": "2026-03-22T00:00:00Z",
            "finished_at": "2026-03-22T00:01:00Z",
            "summary": "Added routing ledger and memory capture",
            "trace_id": "TRACE-20260322-100",
            "exact_actions_taken": ["wrote ledger", "captured memory"],
            "findings": ["none"],
            "recommended_next_owner": "codex",
            "recommended_next_action": "Review the memory note",
            "related_artifacts": [str(task_path.relative_to(tmp_path))],
            "blockers": [],
            "risks": [],
            "confidence": "high",
            "notes": "",
        },
        "## Human-readable Report\n\nMemory test.\n",
    )

    note_path = capture_memory_from_result(
        repo,
        ResultFrontmatter.model_validate(
            {
                "result_id": "RESULT-20260322-100",
                "task_id": "TASK-20260322-100",
                "reporting_agent": "codex",
                "completion_status": "completed",
                "started_at": "2026-03-22T00:00:00Z",
                "finished_at": "2026-03-22T00:01:00Z",
                "summary": "Added routing ledger and memory capture",
                "trace_id": "TRACE-20260322-100",
                "exact_actions_taken": ["wrote ledger", "captured memory"],
                "findings": ["none"],
                "recommended_next_owner": "codex",
                "recommended_next_action": "Review the memory note",
                "related_artifacts": [str(task_path.relative_to(tmp_path))],
                "blockers": [],
                "risks": [],
                "confidence": "high",
                "notes": "",
            }
        ),
        result_path,
        task_path,
    )

    assert note_path.exists()
    hits = search_memory(repo, "routing ledger memory", limit=5)
    assert hits
    assert hits[0].note.source_type == "result"
    assert "routing ledger" in hits[0].note.summary.lower()


def test_capture_memory_from_result_is_idempotent(tmp_path: Path) -> None:
    repo = AgentBusRepo(root=tmp_path)
    task_path = _write_task(tmp_path)
    result_path = tmp_path / "agent_bus" / "results" / "codex" / "RESULT-20260322-101.md"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    write_document(
        result_path,
        {
            "result_id": "RESULT-20260322-101",
            "task_id": "TASK-20260322-100",
            "reporting_agent": "codex",
            "completion_status": ResultStatus.completed.value,
            "started_at": "2026-03-22T00:00:00Z",
            "finished_at": "2026-03-22T00:01:00Z",
            "summary": "Idempotent memory capture",
            "trace_id": "TRACE-20260322-100",
            "exact_actions_taken": ["wrote note"],
            "findings": [],
            "recommended_next_owner": "codex",
            "recommended_next_action": "Keep dedupe stable",
            "related_artifacts": [str(task_path.relative_to(tmp_path))],
            "blockers": [],
            "risks": [],
            "confidence": "high",
            "notes": "",
        },
        "## Human-readable Report\n\nIdempotent memory.\n",
    )
    result_frontmatter = ResultFrontmatter.model_validate(
        {
            "result_id": "RESULT-20260322-101",
            "task_id": "TASK-20260322-100",
            "reporting_agent": "codex",
            "completion_status": "completed",
            "started_at": "2026-03-22T00:00:00Z",
            "finished_at": "2026-03-22T00:01:00Z",
            "summary": "Idempotent memory capture",
            "trace_id": "TRACE-20260322-100",
            "exact_actions_taken": ["wrote note"],
            "findings": [],
            "recommended_next_owner": "codex",
            "recommended_next_action": "Keep dedupe stable",
            "related_artifacts": [str(task_path.relative_to(tmp_path))],
            "blockers": [],
            "risks": [],
            "confidence": "high",
            "notes": "",
        }
    )

    first_path = capture_memory_from_result(repo, result_frontmatter, result_path, task_path)
    second_path = capture_memory_from_result(repo, result_frontmatter, result_path, task_path)

    assert first_path == second_path
    assert len(list((tmp_path / "agent_bus" / "memory" / "notes").glob("MEMORY-*.md"))) == 1
    assert len(load_memory_index(repo)["entries"]) == 1


def test_worker_writes_memory_note(tmp_path: Path) -> None:
    task_path = _write_task(tmp_path, agent="android")

    seeded_result_path = tmp_path / "agent_bus" / "results" / "codex" / "RESULT-20260322-099.md"
    seeded_result_path.parent.mkdir(parents=True, exist_ok=True)
    write_document(
        seeded_result_path,
        {
            "result_id": "RESULT-20260322-099",
            "task_id": "TASK-20260322-100",
            "reporting_agent": "codex",
            "completion_status": ResultStatus.completed.value,
            "started_at": "2026-03-22T00:00:00Z",
            "finished_at": "2026-03-22T00:01:00Z",
            "summary": "Test memory capture for worker routing",
            "trace_id": "TRACE-20260322-100",
            "exact_actions_taken": ["seeded memory context"],
            "findings": [],
            "recommended_next_owner": "android",
            "recommended_next_action": "Run the worker and attach memory context.",
            "related_artifacts": [str(task_path.relative_to(tmp_path))],
            "blockers": [],
            "risks": [],
            "confidence": "high",
            "notes": "",
        },
        "## Human-readable Report\n\nSeeded memory.\n",
    )
    capture_memory_from_result(
        AgentBusRepo(root=tmp_path),
        ResultFrontmatter.model_validate(
            {
                "result_id": "RESULT-20260322-099",
                "task_id": "TASK-20260322-100",
                "reporting_agent": "codex",
                "completion_status": "completed",
                "started_at": "2026-03-22T00:00:00Z",
                "finished_at": "2026-03-22T00:01:00Z",
                "summary": "Test memory capture for worker routing",
                "trace_id": "TRACE-20260322-100",
                "exact_actions_taken": ["seeded memory context"],
                "findings": [],
                "recommended_next_owner": "android",
                "recommended_next_action": "Run the worker and attach memory context.",
                "related_artifacts": [str(task_path.relative_to(tmp_path))],
                "blockers": [],
                "risks": [],
                "confidence": "high",
                "notes": "",
            }
        ),
        seeded_result_path,
        task_path,
    )

    handler = tmp_path / "handler.py"
    handler.write_text("print('worker handled')\n", encoding="utf-8")

    result = run_worker_once(WorkerConfig(root=tmp_path, agent="android", handler_script=handler))

    assert result.processed == 1
    memory_files = list((tmp_path / "agent_bus" / "memory" / "notes").glob("MEMORY-*.md"))
    assert memory_files
    result_files = list((tmp_path / "agent_bus" / "results" / "android").glob("RESULT-*.md"))
    assert result_files
    result_text = result_files[0].read_text(encoding="utf-8")
    assert "## Relevant Memory" in result_text
    hits = search_memory(AgentBusRepo(root=tmp_path), "worker handled", limit=5)
    assert hits
