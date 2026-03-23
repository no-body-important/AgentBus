from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AgentName(str, Enum):
    codex = "codex"
    openclaw = "openclaw"


class TaskStatus(str, Enum):
    drafted = "drafted"
    ready = "ready"
    claimed = "claimed"
    in_progress = "in_progress"
    blocked = "blocked"
    completed = "completed"
    cancelled = "cancelled"
    archived = "archived"


class ResultStatus(str, Enum):
    completed = "completed"
    blocked = "blocked"
    cancelled = "cancelled"
    failed = "failed"


class TaskFrontmatter(BaseModel):
    model_config = ConfigDict(extra="allow")

    task_id: str
    title: str
    project: str = "AgentBus"
    from_agent: AgentName
    to_agent: AgentName
    owner: str = ""
    created_at: datetime
    updated_at: datetime
    status: TaskStatus
    priority: str = "P2"
    objective: str
    success_criteria: list[str] = Field(default_factory=list)
    background: str = ""
    allowed_actions: list[str] = Field(default_factory=list)
    forbidden_actions: list[str] = Field(default_factory=list)
    dependencies: list[str] = Field(default_factory=list)
    depends_on_results: list[str] = Field(default_factory=list)
    required_output_format: str = "RESULT_TEMPLATE.md"
    related_artifacts: list[str] = Field(default_factory=list)
    superseded_by: str = ""
    notes: str = ""


class ResultFrontmatter(BaseModel):
    model_config = ConfigDict(extra="allow")

    result_id: str
    task_id: str
    reporting_agent: AgentName
    completion_status: ResultStatus
    started_at: datetime
    finished_at: datetime
    summary: str
    exact_actions_taken: list[str] = Field(default_factory=list)
    findings: list[str] = Field(default_factory=list)
    recommended_next_owner: AgentName | str = "codex"
    recommended_next_action: str = ""
    related_artifacts: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    risks: list[str] = Field(default_factory=list)
    confidence: str = "high"
    notes: str = ""


class InboxFrontmatter(BaseModel):
    model_config = ConfigDict(extra="allow")

    inbox_id: str
    task_id: str
    to_agent: AgentName
    task_path: str
    published_at: datetime
    status: TaskStatus = TaskStatus.ready
    summary: str = ""


class Document(BaseModel):
    model_config = ConfigDict(extra="allow")

    frontmatter: dict[str, Any]
    body: str
