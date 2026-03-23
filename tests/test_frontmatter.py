from pathlib import Path

from agentbus.frontmatter import load_task
from agentbus.repo import AgentBusRepo
from agentbus.validator import validate_repo


def write_task(path: Path) -> None:
    path.write_text(
        """---
task_id: TASK-20260322-001
title: "Validate handoff"
project: "AgentBus"
from_agent: "codex"
to_agent: "openclaw"
owner: "tester"
created_at: "2026-03-22T00:00:00Z"
updated_at: "2026-03-22T00:00:00Z"
status: "ready"
priority: "P1"
objective: "Confirm validation works"
success_criteria:
  - "Task parses"
background: ""
allowed_actions: []
forbidden_actions: []
dependencies: []
depends_on_results: []
required_output_format: "RESULT_TEMPLATE.md"
related_artifacts: []
superseded_by: ""
notes: ""
---

## Request

Test body.
""",
        encoding="utf-8",
    )


def test_load_task_parses_frontmatter(tmp_path: Path) -> None:
    task_path = tmp_path / "TASK-20260322-001.md"
    write_task(task_path)

    task = load_task(task_path)

    assert task.task_id == "TASK-20260322-001"
    assert task.to_agent == "openclaw"
    assert task.status.value == "ready"


def test_validate_repo_accepts_minimal_structure(tmp_path: Path) -> None:
    bus_dir = tmp_path / "agent_bus" / "tasks" / "openclaw"
    bus_dir.mkdir(parents=True)
    write_task(bus_dir / "TASK-20260322-001.md")

    repo = AgentBusRepo(root=tmp_path)
    issues = validate_repo(repo)

    assert issues == []
