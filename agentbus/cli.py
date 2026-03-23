from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agentbus.repo import AgentBusRepo
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


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "validate":
        return cmd_validate(args.root)

    parser.error(f"unsupported command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
