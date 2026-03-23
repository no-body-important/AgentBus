from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from agentbus.frontmatter import load_inbox, load_result, load_task
from agentbus.models import AgentName
from agentbus.repo import AgentBusRepo


@dataclass(frozen=True)
class Issue:
    path: Path
    message: str
    severity: str = "error"


def validate_repo(repo: AgentBusRepo) -> list[Issue]:
    issues: list[Issue] = []
    if not repo.bus_dir.exists():
        issues.append(Issue(repo.bus_dir, "missing agent_bus directory"))
        return issues

    for path in repo.all_task_files():
        issues.extend(validate_task_file(path, repo))

    for path in repo.all_result_files():
        issues.extend(validate_result_file(path))

    for path in repo.all_inbox_files():
        issues.extend(validate_inbox_file(path))

    return issues


def validate_task_file(path: Path, repo: AgentBusRepo | None = None) -> list[Issue]:
    issues: list[Issue] = []
    try:
        task = load_task(path)
    except (OSError, ValidationError, ValueError) as exc:
        return [Issue(path, str(exc))]

    if not path.name.startswith("TASK-"):
        issues.append(Issue(path, "task file name must start with TASK-"))

    if task.to_agent not in {AgentName.codex, AgentName.openclaw}:
        issues.append(Issue(path, "task to_agent must be codex or openclaw"))

    if repo is not None:
        expected_dir = repo.task_dir(task.to_agent.value)
        if path.parent.resolve() != expected_dir.resolve():
            issues.append(Issue(path, f"task should live in {expected_dir}"))

    return issues


def validate_result_file(path: Path) -> list[Issue]:
    try:
        load_result(path)
    except (OSError, ValidationError, ValueError) as exc:
        return [Issue(path, str(exc))]
    if not path.name.startswith("RESULT-"):
        return [Issue(path, "result file name must start with RESULT-")]
    return []


def validate_inbox_file(path: Path) -> list[Issue]:
    try:
        load_inbox(path)
    except (OSError, ValidationError, ValueError) as exc:
        return [Issue(path, str(exc))]
    if not path.name.startswith("INBOX-"):
        return [Issue(path, "inbox file name must start with INBOX-")]
    return []
