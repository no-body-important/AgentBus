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

    def memory_dir(self) -> Path:
        return self.bus_dir / "memory"

    def memory_notes_dir(self) -> Path:
        return self.memory_dir() / "notes"

    def memory_index_dir(self) -> Path:
        return self.memory_dir() / "index"

    def template_dir(self) -> Path:
        return self.bus_dir / "templates"

    def config_dir(self) -> Path:
        return self.bus_dir / "config"

    def agents_config_path(self) -> Path:
        return self.config_dir() / "agents.yaml"

    def routing_ledger_dir(self) -> Path:
        return self.result_dir("_routing")

    def all_task_files(self) -> list[Path]:
        return sorted(self.bus_dir.glob("tasks/*/TASK-*.md"))

    def all_result_files(self) -> list[Path]:
        return sorted(self.bus_dir.glob("results/*/RESULT-*.md"))

    def all_inbox_files(self) -> list[Path]:
        return sorted(self.bus_dir.glob("inbox/*/INBOX-*.md"))

    def all_memory_files(self) -> list[Path]:
        return sorted(self.bus_dir.glob("memory/notes/MEMORY-*.md"))
