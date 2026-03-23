from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from pydantic import ValidationError

from agentbus.agents import load_agent_registry, normalize_handle
from agentbus.frontmatter import load_inbox, load_result, load_task
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

    registry = load_agent_registry(repo.agents_config_path())

    for path in repo.all_task_files():
        issues.extend(validate_task_file(path, repo, registry))

    for path in repo.all_result_files():
        issues.extend(validate_result_file(path, registry))

    for path in repo.all_inbox_files():
        issues.extend(validate_inbox_file(path, registry))

    return issues


def validate_task_file(path: Path, repo: AgentBusRepo | None = None, registry=None) -> list[Issue]:
    issues: list[Issue] = []
    try:
        task = load_task(path)
    except (OSError, ValidationError, ValueError) as exc:
        return [Issue(path, str(exc))]

    if not path.name.startswith("TASK-"):
        issues.append(Issue(path, "task file name must start with TASK-"))

    if registry is not None and registry.resolve(task.to_agent) is None:
        issues.append(Issue(path, f"unknown agent handle: {task.to_agent}"))

    if repo is not None:
        expected_dir = repo.task_dir(normalize_handle(task.to_agent))
        if path.parent.resolve() != expected_dir.resolve():
            issues.append(Issue(path, f"task should live in {expected_dir}"))

    return issues


def validate_result_file(path: Path, registry=None) -> list[Issue]:
    try:
        load_result(path)
    except (OSError, ValidationError, ValueError) as exc:
        return [Issue(path, str(exc))]
    if not path.name.startswith("RESULT-"):
        return [Issue(path, "result file name must start with RESULT-")]
    return []


def validate_inbox_file(path: Path, registry=None) -> list[Issue]:
    try:
        load_inbox(path)
    except (OSError, ValidationError, ValueError) as exc:
        return [Issue(path, str(exc))]
    if not path.name.startswith("INBOX-"):
        return [Issue(path, "inbox file name must start with INBOX-")]
    return []
