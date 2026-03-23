from pathlib import Path

from agentbus.models import AgentName, RouteMode, TaskFrontmatter, TaskStatus
from agentbus.repo import AgentBusRepo
from agentbus.routing import report_to_json, route_comment, route_event, route_task


def test_route_task_uses_route_mode() -> None:
    task = TaskFrontmatter(
        task_id="TASK-1",
        title="Test",
        project="AgentBus",
        from_agent=AgentName.codex,
        to_agent=AgentName.openclaw,
        owner="tester",
        created_at="2026-03-22T00:00:00Z",
        updated_at="2026-03-22T00:00:00Z",
        status=TaskStatus.ready,
        route_mode=RouteMode.review,
        objective="Check routing",
    )

    decision = route_task(task, source_ref="agent_bus/tasks/openclaw/TASK-1.md")

    assert decision.target_agent == "openclaw"
    assert decision.route_mode == "review"
    assert decision.action == "review"


def test_route_comment_detects_codex_request() -> None:
    decisions = route_comment("@codex please review this change", source_ref="issue#12", trace_id="TRACE-1")

    assert len(decisions) == 1
    assert decisions[0].target_agent == "codex"
    assert decisions[0].action == "review"
    assert decisions[0].trace_id == "TRACE-1"


def test_route_event_routes_changed_task_file(tmp_path: Path) -> None:
    bus_task_dir = tmp_path / "agent_bus" / "tasks" / "codex"
    bus_task_dir.mkdir(parents=True)
    task_path = bus_task_dir / "TASK-20260322-002.md"
    task_path.write_text(
        """---
task_id: TASK-20260322-002
title: "Route me"
project: "AgentBus"
from_agent: "codex"
to_agent: "codex"
owner: "tester"
created_at: "2026-03-22T00:00:00Z"
updated_at: "2026-03-22T00:00:00Z"
status: "ready"
route_mode: "act"
trace_id: "TRACE-20260322-002"
priority: "P2"
objective: "Confirm push routing"
success_criteria: []
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

    repo = AgentBusRepo(root=tmp_path)
    payload = {"commits": [{"modified": ["agent_bus/tasks/codex/TASK-20260322-002.md"]}]}

    report = route_event(repo, event_name="push", event_payload=payload)

    assert len(report.decisions) == 1
    assert report.decisions[0].trace_id == "TRACE-20260322-002"
    assert report.decisions[0].action == "act"
    assert "TASK-20260322-002" in report_to_json(report)
