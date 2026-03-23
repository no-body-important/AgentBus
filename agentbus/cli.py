from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict
from pathlib import Path

from pydantic import ValidationError

from agentbus.frontmatter import load_task
from agentbus.repo import AgentBusRepo
from agentbus.routing import report_to_json, route_event, route_task
from agentbus.validator import validate_repo


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="agentbus", description="AgentBus repository tooling")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser("validate", help="validate the repository handoff files")
    validate_parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="repository root containing agent_bus/",
    )

    route_parser = subparsers.add_parser("route", help="route repo events or task files")
    route_parser.add_argument(
        "--root",
        type=Path,
        default=Path.cwd(),
        help="repository root containing agent_bus/",
    )
    route_parser.add_argument(
        "--event-name",
        type=str,
        default=os.getenv("GITHUB_EVENT_NAME", "manual"),
        help="event name to route, such as push, issue_comment, or pull_request_review",
    )
    route_parser.add_argument(
        "--event-file",
        type=Path,
        default=Path(os.getenv("GITHUB_EVENT_PATH", "")) if os.getenv("GITHUB_EVENT_PATH") else None,
        help="path to a GitHub event payload JSON file",
    )
    route_parser.add_argument(
        "--task",
        type=Path,
        default=None,
        help="optional direct task file to route instead of an event payload",
    )
    route_parser.add_argument(
        "--json",
        action="store_true",
        help="emit JSON output instead of human-readable text",
    )

    return parser


def cmd_validate(root: Path) -> int:
    repo = AgentBusRepo(root=root)
    issues = validate_repo(repo)
    if issues:
        for issue in issues:
            print(f"{issue.severity.upper()}: {issue.path}: {issue.message}")
        return 1

    print(f"OK: validated {repo.bus_dir}")
    return 0


def cmd_route(root: Path, event_name: str, event_file: Path | None, task: Path | None, json_output: bool) -> int:
    repo = AgentBusRepo(root=root)
    try:
        if task is not None:
            task_model = load_task(task)
            report = {
                "event_name": "manual",
                "decision_count": 1,
                "decisions": [asdict(route_task(task_model, source_ref=str(task)))],
            }
            if json_output:
                print(json.dumps(report, indent=2, sort_keys=True))
            else:
                print(
                    f"TARGET={report['decisions'][0]['target_agent']} MODE={report['decisions'][0]['route_mode']} "
                    f"ACTION={report['decisions'][0]['action']}"
                )
                print(f"SOURCE={report['decisions'][0]['source_ref']} TRACE={report['decisions'][0]['trace_id']}")
            return 0

        payload: dict[str, object] = {}
        if event_file is not None and event_file.exists():
            payload = json.loads(event_file.read_text(encoding="utf-8"))

        report = route_event(repo, event_name=event_name, event_payload=payload)
        if json_output:
            print(report_to_json(report))
        else:
            if not report.decisions:
                print(f"OK: no routing decisions for {event_name}")
            for decision in report.decisions:
                print(
                    f"TARGET={decision.target_agent} MODE={decision.route_mode} "
                    f"ACTION={decision.action} SOURCE={decision.source_ref} TRACE={decision.trace_id}"
                )
        return 0
    except (OSError, ValueError, ValidationError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "validate":
        return cmd_validate(args.root)
    if args.command == "route":
        return cmd_route(args.root, args.event_name, args.event_file, args.task, args.json)

    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
