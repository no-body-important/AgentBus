from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field

from agentbus.models import RouteMode


class AgentDefinition(BaseModel):
    model_config = ConfigDict(extra="allow")

    handle: str
    label: str = ""
    aliases: list[str] = Field(default_factory=list)
    default_route_mode: RouteMode = RouteMode.review
    can_observe: bool = True
    can_review: bool = True
    can_act: bool = False
    can_post_comments: bool = True
    notes: str = ""

    def supports_mode(self, mode: RouteMode) -> bool:
        if mode == RouteMode.observe:
            return self.can_observe
        if mode == RouteMode.review:
            return self.can_review
        return self.can_act

    def supported_mode(self, preferred: RouteMode) -> RouteMode:
        if self.supports_mode(preferred):
            return preferred
        if preferred == RouteMode.act and self.can_review:
            return RouteMode.review
        if self.can_observe:
            return RouteMode.observe
        if self.can_review:
            return RouteMode.review
        if self.can_act:
            return RouteMode.act
        return preferred


class AgentRegistry(BaseModel):
    model_config = ConfigDict(extra="allow")

    agents: dict[str, AgentDefinition] = Field(default_factory=dict)

    def normalized_index(self) -> dict[str, str]:
        index: dict[str, str] = {}
        for handle, definition in self.agents.items():
            canonical = normalize_handle(handle)
            index[canonical] = canonical
            index[normalize_handle(definition.handle)] = canonical
            if definition.label:
                index[normalize_handle(definition.label)] = canonical
            for alias in definition.aliases:
                index[normalize_handle(alias)] = canonical
        return index

    def known_handles(self) -> list[str]:
        return sorted(self.agents.keys())

    def resolve(self, token: str) -> str | None:
        return self.normalized_index().get(normalize_handle(token))

    def definition(self, token: str) -> AgentDefinition | None:
        handle = self.resolve(token)
        if handle is None:
            return None
        return self.agents.get(handle)


def normalize_handle(token: str) -> str:
    return token.strip().lstrip("@").lower()


def default_registry() -> AgentRegistry:
    return AgentRegistry(
        agents={
            "codex": AgentDefinition(
                handle="codex",
                label="Codex",
                aliases=["codex"],
                default_route_mode=RouteMode.review,
                can_observe=True,
                can_review=True,
                can_act=True,
                can_post_comments=True,
            ),
            "openclaw": AgentDefinition(
                handle="openclaw",
                label="OpenClaw",
                aliases=["openclaw"],
                default_route_mode=RouteMode.review,
                can_observe=True,
                can_review=True,
                can_act=False,
                can_post_comments=True,
            ),
        }
    )


def load_agent_registry(path: str | Path | None) -> AgentRegistry:
    registry_path = Path(path) if path is not None else None
    if registry_path is None or not registry_path.exists():
        return default_registry()

    payload = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    if not isinstance(payload, dict):
        return default_registry()

    agents_section = payload.get("agents", payload)
    if not isinstance(agents_section, dict):
        return default_registry()

    agents: dict[str, AgentDefinition] = {}
    for handle, raw_definition in agents_section.items():
        if raw_definition is None:
            raw_definition = {}
        if not isinstance(raw_definition, dict):
            continue
        data = {"handle": handle, **raw_definition}
        agents[normalize_handle(handle)] = AgentDefinition.model_validate(data)

    return AgentRegistry(agents=agents) if agents else default_registry()
