from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from pydantic import ValidationError

from agentbus.frontmatter import load_task
from agentbus.lifecycle import archive_task_pair, promote_task_pair
from agentbus.memory import (
    capture_memory_from_document,
    build_memory_id,
    now_utc,
    render_search_results,
    search_memory,
    write_memory_entry,
)
from agentbus.models import MemoryFrontmatter
from agentbus.repo import AgentBusRepo
from agentbus.routing import RoutingReport, report_to_json, route_event, route_task, write_routing_ledger
from agentbus.validator import validate_repo
from agentbus.worker import WorkerConfig, run_worker_once


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
        help="event name to route, such as push, issue_comment, issues, pull_request, or pull_request_review",
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
    route_parser.add_argument(
        "--ledger-dir",
        type=Path,
        default=None,
        help="optional directory where a routing ledger JSON file should be written",
    )
    route_parser.add_argument(
        "--emit-inbox-markers",
        action="store_true",
        help="write durable inbox markers for routed issue and PR events",
    )
    route_parser.add_argument(
        "--emit-thread-markers",
        action="store_true",
        help="write durable thread snapshot files for routed issue and PR events",
    )

    worker_parser = subparsers.add_parser("worker", help="run a local worker loop for one agent")
    worker_parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root containing agent_bus/")
    worker_parser.add_argument("--agent", required=True, help="agent handle to process, such as android or codex")
    worker_parser.add_argument("--handler-script", type=Path, default=None, help="optional local script to execute per task")
    worker_parser.add_argument("--once", action="store_true", help="process one cycle and exit")
    worker_parser.add_argument("--interval", type=int, default=30, help="seconds between cycles in loop mode")
    worker_parser.add_argument("--dry-run", action="store_true", help="simulate worker actions without writing files")

    memory_parser = subparsers.add_parser("memory", help="write or search shared memory notes")
    memory_subparsers = memory_parser.add_subparsers(dest="memory_command", required=True)

    memory_add_parser = memory_subparsers.add_parser("add", help="add a new memory note")
    memory_add_parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root containing agent_bus/")
    memory_add_parser.add_argument("--title", required=True, help="memory note title")
    memory_add_parser.add_argument("--summary", required=True, help="short summary for retrieval")
    memory_add_parser.add_argument("--body", default="", help="full markdown body for the note")
    memory_add_parser.add_argument("--author", default="codex", help="authoring agent handle")
    memory_add_parser.add_argument("--type", default="observation", help="memory type such as observation or decision")
    memory_add_parser.add_argument("--source-type", default="manual", help="source kind such as manual, task, or result")
    memory_add_parser.add_argument("--source-path", default="", help="source path inside the repo")
    memory_add_parser.add_argument("--trace-id", default="", help="trace identifier for the memory note")
    memory_add_parser.add_argument("--importance", default="normal", help="importance classification")
    memory_add_parser.add_argument("--tag", action="append", default=[], help="additional tags; repeat to add more")
    memory_add_parser.add_argument("--artifact", action="append", default=[], help="related artifact paths; repeat to add more")
    memory_add_parser.add_argument("--dry-run", action="store_true", help="print the note path without writing")

    memory_capture_parser = memory_subparsers.add_parser("capture", help="capture memory from a task, result, or markdown file")
    memory_capture_parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root containing agent_bus/")
    memory_capture_parser.add_argument("--source-file", type=Path, required=True, help="file to capture from")
    memory_capture_parser.add_argument(
        "--source-kind",
        choices=["task", "result", "document"],
        default="document",
        help="type of source file to capture",
    )
    memory_capture_parser.add_argument("--author", default="codex", help="authoring agent handle")
    memory_capture_parser.add_argument("--dry-run", action="store_true", help="print the note path without writing")

    memory_search_parser = memory_subparsers.add_parser("search", help="search shared memory notes")
    memory_search_parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root containing agent_bus/")
    memory_search_parser.add_argument("--query", required=True, help="search terms or a phrase")
    memory_search_parser.add_argument("--limit", type=int, default=5, help="maximum results to return")
    memory_search_parser.add_argument("--json", action="store_true", help="emit JSON output instead of text")

    archive_parser = subparsers.add_parser("archive", help="archive a completed task and matching result")
    archive_parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root containing agent_bus/")
    archive_parser.add_argument("--task", type=Path, required=True, help="task file to archive")
    archive_parser.add_argument("--result", type=Path, default=None, help="optional matching result file to archive")
    archive_parser.add_argument("--dry-run", action="store_true", help="print the archive target without writing")

    promote_parser = subparsers.add_parser("promote", help="restore an archived task and matching result")
    promote_parser.add_argument("--root", type=Path, default=Path.cwd(), help="repository root containing agent_bus/")
    promote_parser.add_argument("--task", type=Path, required=True, help="archived task file to restore")
    promote_parser.add_argument("--result", type=Path, default=None, help="optional archived result file to restore")
    promote_parser.add_argument("--dry-run", action="store_true", help="print the restore target without writing")

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


def cmd_route(
    root: Path,
    event_name: str,
    event_file: Path | None,
    task: Path | None,
    json_output: bool,
    ledger_dir: Path | None,
    emit_inbox_markers: bool,
    emit_thread_markers: bool,
) -> int:
    repo = AgentBusRepo(root=root)
    try:
        if task is not None:
            task_model = load_task(task)
            report = RoutingReport(event_name="manual", decisions=[route_task(task_model, source_ref=str(task))])
            if ledger_dir is not None:
                write_routing_ledger(report, ledger_dir, "manual")
            if json_output:
                print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
            else:
                decision = report.decisions[0]
                print(
                    f"TARGET={decision.target_agent} MODE={decision.route_mode} ACTION={decision.action}"
                )
                print(f"SOURCE={decision.source_ref} TRACE={decision.trace_id}")
            return 0
        payload: dict[str, object] = {}
        if event_file is not None and event_file.exists():
            payload = json.loads(event_file.read_text(encoding="utf-8"))

        report = route_event(
            repo,
            event_name=event_name,
            event_payload=payload,
            emit_inbox_markers=emit_inbox_markers,
            emit_thread_markers=emit_thread_markers,
        )
        if ledger_dir is not None:
            write_routing_ledger(report, ledger_dir, event_name)
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
            for marker in report.inbox_markers:
                print(f"INBOX={marker.get('path', '')} TARGET={marker.get('target_agent', '')}")
            for thread in report.thread_snapshots:
                print(f"THREAD={thread.get('path', '')} TRACE={thread.get('trace_id', '')}")
            if report.comment_body:
                print(report.comment_body)
        return 0
    except (OSError, ValueError, ValidationError, json.JSONDecodeError) as exc:
        print(f"ERROR: {exc}")
        return 1


def cmd_worker(root: Path, agent: str, handler_script: Path | None, once: bool, interval: int, dry_run: bool) -> int:
    config = WorkerConfig(root=root, agent=agent, handler_script=handler_script, dry_run=dry_run)
    while True:
        result = run_worker_once(config)
        print(
            f"OK: processed={result.processed} agent={agent} "
            f"tasks={len(result.task_paths)} results={len(result.result_paths)}"
        )
        for message in result.messages:
            if message:
                print(message)
        if once:
            return 0
        time.sleep(max(5, interval))


def cmd_memory_add(
    root: Path,
    title: str,
    summary: str,
    body: str,
    author: str,
    memory_type: str,
    source_type: str,
    source_path: str,
    trace_id: str,
    importance: str,
    tags: list[str],
    artifacts: list[str],
    dry_run: bool,
) -> int:
    repo = AgentBusRepo(root=root)
    created = now_utc()
    note = MemoryFrontmatter(
        memory_id=build_memory_id(author, title, created),
        title=title,
        memory_type=memory_type,
        author_agent=author,
        created_at=created,
        updated_at=created,
        source_type=source_type,
        source_path=source_path,
        source_trace_id=trace_id,
        importance=importance,
        tags=tags or [author, memory_type],
        related_artifacts=artifacts,
        summary=summary,
        body_hint="manual",
    )
    path = write_memory_entry(repo, note, body or summary, dry_run=dry_run)
    print(str(path))
    return 0


def cmd_memory_capture(
    root: Path,
    source_file: Path,
    source_kind: str,
    author: str,
    dry_run: bool,
) -> int:
    repo = AgentBusRepo(root=root)
    path = capture_memory_from_document(repo, source_file, source_kind, author, dry_run=dry_run)
    print(str(path))
    return 0


def cmd_memory_search(root: Path, query: str, limit: int, json_output: bool) -> int:
    repo = AgentBusRepo(root=root)
    hits = search_memory(repo, query, limit=limit)
    if json_output:
        print(
            json.dumps(
                [
                    {
                        "path": str(hit.path.relative_to(repo.root)),
                        "score": hit.score,
                        "memory_id": hit.note.memory_id,
                        "title": hit.note.title,
                        "source_type": hit.note.source_type,
                        "source_path": hit.note.source_path,
                        "tags": hit.note.tags,
                        "snippet": hit.snippet,
                    }
                    for hit in hits
                ],
                indent=2,
                sort_keys=True,
            )
        )
    else:
        print(render_search_results(hits))
    return 0


def cmd_archive(root: Path, task: Path, result: Path | None, dry_run: bool) -> int:
    repo = AgentBusRepo(root=root)
    operation = archive_task_pair(repo, task, result_path=result, dry_run=dry_run)
    print(f"OK: {operation.action} task {operation.task.source} -> {operation.task.target}")
    if operation.result is not None:
        print(f"OK: {operation.action} result {operation.result.source} -> {operation.result.target}")
    print(f"ARCHIVE_ROOT={operation.archive_root}")
    return 0


def cmd_promote(root: Path, task: Path, result: Path | None, dry_run: bool) -> int:
    repo = AgentBusRepo(root=root)
    operation = promote_task_pair(repo, task, archived_result_path=result, dry_run=dry_run)
    print(f"OK: {operation.action} task {operation.task.source} -> {operation.task.target}")
    if operation.result is not None:
        print(f"OK: {operation.action} result {operation.result.source} -> {operation.result.target}")
    print(f"ARCHIVE_ROOT={operation.archive_root}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "validate":
        return cmd_validate(args.root)
    if args.command == "route":
        return cmd_route(
            args.root,
            args.event_name,
            args.event_file,
            args.task,
            args.json,
            args.ledger_dir,
            args.emit_inbox_markers,
            args.emit_thread_markers,
        )
    if args.command == "worker":
        return cmd_worker(args.root, args.agent, args.handler_script, args.once, args.interval, args.dry_run)
    if args.command == "memory":
        if args.memory_command == "add":
            return cmd_memory_add(
                args.root,
                args.title,
                args.summary,
                args.body,
                args.author,
                args.type,
                args.source_type,
                args.source_path,
                args.trace_id,
                args.importance,
                args.tag,
                args.artifact,
                args.dry_run,
            )
        if args.memory_command == "capture":
            return cmd_memory_capture(args.root, args.source_file, args.source_kind, args.author, args.dry_run)
        if args.memory_command == "search":
            return cmd_memory_search(args.root, args.query, args.limit, args.json)
    if args.command == "archive":
        return cmd_archive(args.root, args.task, args.result, args.dry_run)
    if args.command == "promote":
        return cmd_promote(args.root, args.task, args.result, args.dry_run)

    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
