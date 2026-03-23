from pathlib import Path

from agentbus.agents import AgentDefinition, AgentRegistry
from agentbus.frontmatter import load_inbox, write_document
from agentbus.memory import capture_memory_from_result
from agentbus.models import RouteMode, TaskFrontmatter, TaskStatus
from agentbus.models import ResultFrontmatter, ResultStatus
from agentbus.repo import AgentBusRepo
from agentbus.routing import compose_comment, report_to_json, route_comment, route_event, route_task, write_routing_ledger
from agentbus.worker import WorkerConfig, run_worker_once


def test_route_task_uses_route_mode() -> None:
    task = TaskFrontmatter(
        task_id="TASK-1",
        title="Test",
        project="AgentBus",
        from_agent="codex",
        to_agent="openclaw",
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


def test_route_comment_supports_custom_agent_registry() -> None:
    registry = AgentRegistry(
        agents={
            "claude": AgentDefinition(
                handle="claude",
                label="Claude",
                aliases=["claude"],
                default_route_mode=RouteMode.act,
                can_observe=True,
                can_review=True,
                can_act=True,
            ),
            "grok": AgentDefinition(handle="grok", label="Grok", aliases=["grok"], default_route_mode=RouteMode.observe),
        }
    )

    decisions = route_comment("@Claude and @grok take a look", registry=registry, source_ref="issue#22")

    assert [decision.target_agent for decision in decisions] == ["claude", "grok"]
    assert [decision.action for decision in decisions] == ["act", "observe"]


def test_route_comment_respects_capability_flags() -> None:
    registry = AgentRegistry(
        agents={
            "openclaw": AgentDefinition(
                handle="openclaw",
                label="OpenClaw",
                aliases=["openclaw"],
                default_route_mode=RouteMode.act,
                can_observe=True,
                can_review=True,
                can_act=False,
            )
        }
    )

    decisions = route_comment("@openclaw build this", registry=registry, source_ref="issue#7")

    assert decisions[0].route_mode == "review"
    assert decisions[0].action == "review"


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


def test_compose_comment_includes_sentinel_and_mentions() -> None:
    report = route_event(
        AgentBusRepo(root=Path(".")),
        event_name="issue_comment",
        event_payload={
            "comment": {"body": "@codex please review"},
            "issue": {"number": 12},
        },
    )

    body = compose_comment(report)

    assert "<!-- agentbus-routed -->" in body
    assert "@codex" in body


def test_route_event_routes_labels(tmp_path: Path) -> None:
    repo = AgentBusRepo(root=tmp_path)
    payload = {
        "comment": {"body": "Please review"},
        "issue": {
            "number": 44,
            "labels": [{"name": "needs-codex"}, {"name": "triage"}],
        },
    }

    report = route_event(repo, event_name="issue_comment", event_payload=payload)

    assert any(decision.target_agent == "codex" for decision in report.decisions)


def test_route_event_writes_inbox_markers_for_issue_comments(tmp_path: Path) -> None:
    repo = AgentBusRepo(root=tmp_path)
    payload = {
        "comment": {"body": "@codex please review this"},
        "issue": {"number": 88, "labels": [{"name": "needs-codex"}]},
        "trace_id": "TRACE-INBOX-88",
    }

    report = route_event(repo, event_name="issue_comment", event_payload=payload, emit_inbox_markers=True)

    assert report.inbox_markers
    marker = report.inbox_markers[0]
    assert marker["target_agent"] == "codex"
    assert marker["trace_id"] == "TRACE-INBOX-88"

    inbox_files = list((tmp_path / "agent_bus" / "inbox" / "codex").glob("INBOX-*.md"))
    assert len(inbox_files) == 1
    inbox = load_inbox(inbox_files[0])
    assert inbox.to_agent == "codex"
    assert inbox.trace_id == "TRACE-INBOX-88"
    assert inbox.source_ref == "issue#88"


def test_route_event_writes_thread_snapshot_for_issue_comments(tmp_path: Path) -> None:
    repo = AgentBusRepo(root=tmp_path)
    payload = {
        "comment": {"body": "@codex please review this"},
        "issue": {"number": 89, "labels": [{"name": "needs-codex"}]},
        "trace_id": "TRACE-THREAD-89",
    }

    report = route_event(
        repo,
        event_name="issue_comment",
        event_payload=payload,
        emit_inbox_markers=True,
        emit_thread_markers=True,
    )

    assert report.thread_snapshots
    thread = report.thread_snapshots[0]
    assert thread["trace_id"] == "TRACE-THREAD-89"

    thread_files = list((tmp_path / "agent_bus" / "results" / "_routing" / "threads").glob("THREAD-*.md"))
    assert len(thread_files) == 1
    thread_text = thread_files[0].read_text(encoding="utf-8")
    assert "Bridge Thread Snapshot" in thread_text
    assert "Routing Decisions" in thread_text
    assert "Inbox Markers" in thread_text
    assert "@codex" in thread_text


def test_route_event_includes_memory_context(tmp_path: Path) -> None:
    repo = AgentBusRepo(root=tmp_path)
    task_path = tmp_path / "agent_bus" / "tasks" / "codex" / "TASK-20260322-050.md"
    task_path.parent.mkdir(parents=True, exist_ok=True)
    write_document(
        task_path,
        {
            "task_id": "TASK-20260322-050",
            "title": "Memory routing test",
            "project": "AgentBus",
            "from_agent": "codex",
            "to_agent": "codex",
            "owner": "tester",
            "created_at": "2026-03-22T00:00:00Z",
            "updated_at": "2026-03-22T00:00:00Z",
            "status": "completed",
            "route_mode": "act",
            "trace_id": "TRACE-ROUTE-050",
            "priority": "P2",
            "objective": "Seed memory for routing",
            "success_criteria": [],
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
        "## Request\nSeed the memory layer.\n",
    )
    result_path = tmp_path / "agent_bus" / "results" / "codex" / "RESULT-20260322-050.md"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    write_document(
        result_path,
        {
            "result_id": "RESULT-20260322-050",
            "task_id": "TASK-20260322-050",
            "reporting_agent": "codex",
            "completion_status": ResultStatus.completed.value,
            "started_at": "2026-03-22T00:00:00Z",
            "finished_at": "2026-03-22T00:01:00Z",
            "summary": "Captured routing ledger memory",
            "trace_id": "TRACE-ROUTE-050",
            "exact_actions_taken": ["seeded memory"],
            "findings": [],
            "recommended_next_owner": "codex",
            "recommended_next_action": "Review routing context",
            "related_artifacts": [str(task_path.relative_to(tmp_path))],
            "blockers": [],
            "risks": [],
            "confidence": "high",
            "notes": "",
        },
        "## Human-readable Report\n\nSeed memory.\n",
    )
    capture_memory_from_result(
        repo,
        ResultFrontmatter.model_validate(
            {
                "result_id": "RESULT-20260322-050",
                "task_id": "TASK-20260322-050",
                "reporting_agent": "codex",
                "completion_status": "completed",
                "started_at": "2026-03-22T00:00:00Z",
                "finished_at": "2026-03-22T00:01:00Z",
                "summary": "Captured routing ledger memory",
                "trace_id": "TRACE-ROUTE-050",
                "exact_actions_taken": ["seeded memory"],
                "findings": [],
                "recommended_next_owner": "codex",
                "recommended_next_action": "Review routing context",
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

    report = route_event(
        repo,
        event_name="issue_comment",
        event_payload={
            "comment": {"body": "@codex please review the routing ledger memory"},
            "issue": {"number": 50},
            "trace_id": "TRACE-ROUTE-050",
        },
    )

    assert report.context_notes
    assert report.context_notes[0]["source_type"] == "result"
    assert report.context_notes[0]["summary"] == "Captured routing ledger memory"
    assert "Relevant memory context" in report.comment_body


def test_write_routing_ledger_creates_json_file(tmp_path: Path) -> None:
    report = route_event(
        AgentBusRepo(root=Path(".")),
        event_name="issue_comment",
        event_payload={
            "comment": {"body": "@codex please review"},
            "issue": {"number": 12},
        },
    )

    ledger_path = write_routing_ledger(report, tmp_path, "issue_comment")

    assert ledger_path.exists()
    assert ledger_path.name.startswith("ROUTING-")


def test_worker_claims_and_completes_task(tmp_path: Path) -> None:
    task_dir = tmp_path / "agent_bus" / "tasks" / "android"
    task_dir.mkdir(parents=True)
    task_path = task_dir / "TASK-20260322-003.md"
    task_path.write_text(
        """---
task_id: TASK-20260322-003
title: "Worker test"
project: "AgentBus"
from_agent: "codex"
to_agent: "android"
owner: "tester"
created_at: "2026-03-22T00:00:00Z"
updated_at: "2026-03-22T00:00:00Z"
status: "ready"
route_mode: "act"
trace_id: "TRACE-20260322-003"
priority: "P2"
objective: "Confirm worker execution"
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

    handler = tmp_path / "handler.py"
    handler.write_text(
        "import sys\n"
        "print('handled ' + sys.argv[1])\n",
        encoding="utf-8",
    )

    result = run_worker_once(WorkerConfig(root=tmp_path, agent="android", handler_script=handler))

    assert result.processed == 1
    assert result.result_paths[0].exists()
    assert "handled" in result.messages[0]
    updated_task = task_path.read_text(encoding="utf-8")
    assert "status: completed" in updated_task
