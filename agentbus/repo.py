from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class AgentBusRepo:
    root: Path

    @property
    def bus_dir(self) -> Path:
        return self.root / "agent_bus"

    def task_dir(self, agent: str) -> Path:
        return self.bus_dir / "tasks" / agent

    def result_dir(self, agent: str) -> Path:
        return self.bus_dir / "results" / agent

    def inbox_dir(self, agent: str) -> Path:
        return self.bus_dir / "inbox" / agent

    def archive_dir(self) -> Path:
        return self.bus_dir / "archive"

    def template_dir(self) -> Path:
        return self.bus_dir / "templates"

    def config_dir(self) -> Path:
        return self.bus_dir / "config"

    def agents_config_path(self) -> Path:
        return self.config_dir() / "agents.yaml"

    def all_task_files(self) -> list[Path]:
        return sorted(self.bus_dir.glob("tasks/*/TASK-*.md"))

    def all_result_files(self) -> list[Path]:
        return sorted(self.bus_dir.glob("results/*/RESULT-*.md"))

    def all_inbox_files(self) -> list[Path]:
        return sorted(self.bus_dir.glob("inbox/*/INBOX-*.md"))
