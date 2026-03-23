from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import subprocess
import sys
from pathlib import Path
from typing import Any

from agentbus.frontmatter import load_document, load_result, update_document_frontmatter, write_document
from agentbus.memory import build_memory_query_from_task, capture_memory_from_result, format_memory_context, search_memory
from agentbus.models import ResultFrontmatter, ResultStatus, TaskFrontmatter, TaskStatus
from agentbus.repo import AgentBusRepo


@dataclass(frozen=True)
class WorkerConfig:
    root: Path
    agent: str
    handler_script: Path | None = None
    dry_run: bool = False


@dataclass(frozen=True)
class WorkerRunResult:
    processed: int
    result_paths: list[Path]
    task_paths: list[Path]
    messages: list[str]


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def run_worker_once(config: WorkerConfig) -> WorkerRunResult:
    repo = AgentBusRepo(root=config.root)
    task_dir = repo.task_dir(config.agent)
    result_dir = repo.result_dir(config.agent)
    task_dir.mkdir(parents=True, exist_ok=True)
    result_dir.mkdir(parents=True, exist_ok=True)

    processed = 0
    result_paths: list[Path] = []
    task_paths: list[Path] = []
    messages: list[str] = []

    for task_path in sorted(task_dir.glob("TASK-*.md")):
        task = TaskFrontmatter.model_validate(load_document(task_path).frontmatter)
        if task.status != TaskStatus.ready:
            continue

        task_paths.append(task_path)
        processed += 1
        task_frontmatter = task.model_copy(update={"status": TaskStatus.claimed, "updated_at": now_utc()})
        if not config.dry_run:
            update_document_frontmatter(task_path, task_frontmatter.model_dump(mode="json"))

        memory_hits = search_memory(repo, build_memory_query_from_task(task_frontmatter), limit=3)
        run_output = execute_task(config, repo, task_path, task_frontmatter)
        if memory_hits:
            run_output["memory_context"] = format_memory_context(memory_hits)
        result_path = write_result(repo, config.agent, task_frontmatter, task_path, run_output, config.dry_run)
        result_paths.append(result_path)
        messages.append(run_output["summary"])

        if not config.dry_run:
            capture_memory_from_result(repo, load_result(result_path), result_path, task_path, dry_run=False)

        final_status = TaskStatus.completed if run_output["status"] == ResultStatus.completed else TaskStatus.blocked
        if not config.dry_run:
            update_document_frontmatter(
                task_path,
                task_frontmatter.model_copy(update={"status": final_status, "updated_at": now_utc()}).model_dump(mode="json"),
            )

    return WorkerRunResult(processed=processed, result_paths=result_paths, task_paths=task_paths, messages=messages)


def execute_task(
    config: WorkerConfig,
    repo: AgentBusRepo,
    task_path: Path,
    task: TaskFrontmatter,
) -> dict[str, Any]:
    if config.handler_script is None:
        return {
            "status": ResultStatus.completed,
            "summary": f"No handler script configured for {config.agent}; recorded task as completed.",
            "actions": ["claim task", "write result"],
            "findings": [],
            "notes": "dry-run handler not configured",
        }

    if config.handler_script.suffix.lower() == ".py":
        command = [sys.executable, str(config.handler_script), str(task_path), str(repo.root), config.agent]
    else:
        command = [str(config.handler_script), str(task_path), str(repo.root), config.agent]
    completed = subprocess.run(command, capture_output=True, text=True, check=False)
    summary = completed.stdout.strip() or completed.stderr.strip() or "Handler script completed without output."
    status = ResultStatus.completed if completed.returncode == 0 else ResultStatus.blocked
    findings = [line for line in completed.stderr.splitlines() if line.strip()] if completed.stderr else []
    actions = ["claim task", f"run handler script: {config.handler_script}"]
    return {
        "status": status,
        "summary": summary,
        "actions": actions,
        "findings": findings,
        "notes": f"returncode={completed.returncode}",
    }


def write_result(
    repo: AgentBusRepo,
    agent: str,
    task: TaskFrontmatter,
    task_path: Path,
    run_output: dict[str, Any],
    dry_run: bool,
) -> Path:
    result_dir = repo.result_dir(agent)
    result_dir.mkdir(parents=True, exist_ok=True)
    result_id = f"RESULT-{now_utc().strftime('%Y%m%d-%H%M%S')}-{task.task_id.lower()}"
    result_path = result_dir / f"{result_id}.md"
    payload = ResultFrontmatter(
        result_id=result_id,
        task_id=task.task_id,
        reporting_agent=agent,
        completion_status=run_output["status"],
        started_at=now_utc(),
        finished_at=now_utc(),
        summary=run_output["summary"],
        trace_id=task.trace_id or task.task_id,
        exact_actions_taken=list(run_output.get("actions", [])),
        findings=list(run_output.get("findings", [])),
        recommended_next_owner="codex",
        recommended_next_action="Review the result and schedule the next task.",
        related_artifacts=[str(task_path.relative_to(repo.root))],
        blockers=[],
        risks=[],
        confidence="high" if run_output["status"] == ResultStatus.completed else "medium",
        notes=str(run_output.get("notes", "")),
    )
    if not dry_run:
        body_lines = ["## Human-readable Report", "", "Auto-generated by AgentBus worker."]
        memory_context = str(run_output.get("memory_context", "")).strip()
        if memory_context:
            body_lines.extend(["", "## Relevant Memory", memory_context])
        write_document(
            result_path,
            payload.model_dump(mode="json"),
            "\n".join(body_lines),
        )
    return result_path
