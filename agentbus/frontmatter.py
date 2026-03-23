from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from agentbus.models import Document, InboxFrontmatter, ResultFrontmatter, TaskFrontmatter


def load_document(path: str | Path) -> Document:
    document_path = Path(path)
    text = document_path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError(f"{document_path} is missing YAML frontmatter")

    parts = text.split("\n---\n", 1)
    if len(parts) != 2:
        raise ValueError(f"{document_path} has invalid frontmatter delimiters")

    frontmatter_text = parts[0].removeprefix("---\n")
    body = parts[1]
    parsed = yaml.safe_load(frontmatter_text) or {}
    if not isinstance(parsed, dict):
        raise ValueError(f"{document_path} frontmatter must be a mapping")

    return Document(frontmatter=parsed, body=body)


def load_task(path: str | Path) -> TaskFrontmatter:
    document = load_document(path)
    return TaskFrontmatter.model_validate(document.frontmatter)


def load_result(path: str | Path) -> ResultFrontmatter:
    document = load_document(path)
    return ResultFrontmatter.model_validate(document.frontmatter)


def load_inbox(path: str | Path) -> InboxFrontmatter:
    document = load_document(path)
    return InboxFrontmatter.model_validate(document.frontmatter)


def dump_frontmatter_lines(frontmatter: dict[str, Any]) -> str:
    return yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=False).rstrip()


def write_document(path: str | Path, frontmatter: dict[str, Any], body: str) -> None:
    document_path = Path(path)
    payload = "---\n"
    payload += dump_frontmatter_lines(frontmatter)
    payload += "\n---\n"
    payload += body.lstrip("\n")
    document_path.write_text(payload, encoding="utf-8")


def update_document_frontmatter(path: str | Path, frontmatter: dict[str, Any]) -> None:
    document = load_document(path)
    write_document(path, frontmatter=frontmatter, body=document.body)
