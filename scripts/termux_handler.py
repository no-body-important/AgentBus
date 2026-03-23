from __future__ import annotations

import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) < 4:
        print("usage: termux_handler.py TASK_FILE REPO_ROOT AGENT", file=sys.stderr)
        return 2

    task_file = Path(sys.argv[1])
    repo_root = Path(sys.argv[2])
    agent = sys.argv[3]

    print(f"termux handler ready for {agent}")
    print(f"task={task_file}")
    print(f"repo={repo_root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
