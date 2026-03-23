from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import re
from pathlib import Path
from agentbus.frontmatter import load_document, load_result, load_task, write_document
from agentbus.models import MemoryFrontmatter, ResultFrontmatter, TaskFrontmatter
from agentbus.repo import AgentBusRepo


STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "have",
    "in",
    "is",
    "it",
    "of",
    "on",
    "or",
    "the",
    "this",
    "to",
    "with",
    "that",
    "when",
    "what",
    "which",
    "will",
}


@dataclass(frozen=True)
class MemoryHit:
    path: Path
    score: float
    note: MemoryFrontmatter
    snippet: str


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def slugify(text: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return slug or "note"


def memory_notes_dir(repo: AgentBusRepo) -> Path:
    path = repo.memory_notes_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def memory_index_dir(repo: AgentBusRepo) -> Path:
    path = repo.memory_index_dir()
    path.mkdir(parents=True, exist_ok=True)
    return path


def build_memory_id(prefix: str, title: str, created_at: datetime | None = None) -> str:
    stamp = (created_at or now_utc()).strftime("%Y%m%d-%H%M%S")
    return f"MEMORY-{stamp}-{slugify(prefix + '-' + title)[:48]}"


def load_memory(path: str | Path) -> MemoryFrontmatter:
    document = load_document(path)
    return MemoryFrontmatter.model_validate(document.frontmatter)


def write_memory_entry(
    repo: AgentBusRepo,
    note: MemoryFrontmatter,
    body: str,
    dry_run: bool = False,
) -> Path:
    notes_dir = memory_notes_dir(repo)
    note_path = notes_dir / f"{note.memory_id}.md"
    if not dry_run:
        write_document(note_path, note.model_dump(mode="json"), body)
    return note_path


def capture_memory_from_task(
    repo: AgentBusRepo,
    task: TaskFrontmatter,
    task_path: Path,
    author_agent: str,
    source_type: str = "task",
    dry_run: bool = False,
) -> Path:
    created = now_utc()
    note = MemoryFrontmatter(
        memory_id=build_memory_id(author_agent, task.task_id, created),
        title=task.title,
        memory_type="task",
        author_agent=author_agent,
        created_at=created,
        updated_at=created,
        source_type=source_type,
        source_path=str(task_path.relative_to(repo.root)),
        source_trace_id=task.trace_id or task.task_id,
        importance=task.priority.lower() if task.priority else "normal",
        tags=[author_agent, task.to_agent, task.status.value, "task"],
        related_artifacts=[str(task_path.relative_to(repo.root))],
        summary=task.objective,
        body_hint="task",
    )
    body = "\n".join(
        [
            "## Summary",
            task.objective,
            "",
            "## Success Criteria",
            *bullet_lines(task.success_criteria),
            "",
            "## Context",
            f"- From: `{task.from_agent}`",
            f"- To: `{task.to_agent}`",
            f"- Status: `{task.status.value}`",
            f"- Route mode: `{task.route_mode.value}`",
            f"- Trace: `{task.trace_id or task.task_id}`",
        ],
    )
    return write_memory_entry(repo, note, body, dry_run=dry_run)


def capture_memory_from_result(
    repo: AgentBusRepo,
    result: ResultFrontmatter,
    result_path: Path,
    task_path: Path | None,
    dry_run: bool = False,
) -> Path:
    created = now_utc()
    source_ref = str(result_path.relative_to(repo.root))
    related = [source_ref]
    if task_path is not None:
        related.append(str(task_path.relative_to(repo.root)))

    note = MemoryFrontmatter(
        memory_id=build_memory_id(result.reporting_agent, result.result_id, created),
        title=result.summary[:80] or result.result_id,
        memory_type="result",
        author_agent=result.reporting_agent,
        created_at=created,
        updated_at=created,
        source_type="result",
        source_path=source_ref,
        source_trace_id=result.trace_id or result.task_id,
        importance="high" if result.completion_status.value == "completed" else "normal",
        tags=[result.reporting_agent, result.completion_status.value, "result"],
        related_artifacts=related + list(result.related_artifacts),
        summary=result.summary,
        body_hint="result",
    )

    body_lines = [
        "## Summary",
        result.summary,
        "",
        "## Actions Taken",
        *bullet_lines(result.exact_actions_taken),
        "",
        "## Findings",
        *bullet_lines(result.findings),
        "",
        "## Risks",
        *bullet_lines(result.risks),
        "",
        "## Blockers",
        *bullet_lines(result.blockers),
        "",
        "## Follow-up",
        f"- Recommended next owner: `{result.recommended_next_owner}`",
        f"- Recommended next action: {result.recommended_next_action or 'None'}",
        f"- Confidence: `{result.confidence}`",
    ]
    if result.notes:
        body_lines.extend(["", "## Notes", result.notes])

    return write_memory_entry(repo, note, "\n".join(body_lines), dry_run=dry_run)


def capture_memory_from_document(
    repo: AgentBusRepo,
    source_path: Path,
    source_kind: str,
    author_agent: str,
    dry_run: bool = False,
) -> Path:
    if source_kind == "task":
        task = load_task(source_path)
        return capture_memory_from_task(repo, task, source_path, author_agent=author_agent, source_type="task", dry_run=dry_run)
    if source_kind == "result":
        result = load_result(source_path)
        task_path = _find_related_task(repo, result.task_id)
        return capture_memory_from_result(repo, result, source_path, task_path, dry_run=dry_run)

    document = load_document(source_path)
    created = now_utc()
    title = document.frontmatter.get("title") or source_path.stem
    note = MemoryFrontmatter(
        memory_id=build_memory_id(author_agent, str(title), created),
        title=str(title),
        memory_type="observation",
        author_agent=author_agent,
        created_at=created,
        updated_at=created,
        source_type=source_kind,
        source_path=str(source_path.relative_to(repo.root)),
        source_trace_id=str(document.frontmatter.get("trace_id", "") or title),
        importance="normal",
        tags=[author_agent, source_kind],
        related_artifacts=[str(source_path.relative_to(repo.root))],
        summary=str(document.frontmatter.get("summary", "") or ""),
        body_hint="observation",
    )
    body = document.body or str(document.frontmatter)
    return write_memory_entry(repo, note, body, dry_run=dry_run)


def search_memory(repo: AgentBusRepo, query: str, limit: int = 5) -> list[MemoryHit]:
    query_tokens = tokenize(query)
    hits: list[MemoryHit] = []
    for path in repo.all_memory_files():
        try:
            note = load_memory(path)
            document = load_document(path)
        except (OSError, ValueError):
            continue
        score = score_memory(note, document.body, query_tokens)
        if score <= 0:
            continue
        hits.append(MemoryHit(path=path, score=score, note=note, snippet=build_snippet(document.body, query_tokens)))

    hits.sort(key=lambda hit: (-hit.score, hit.note.updated_at, hit.note.memory_id))
    return hits[: max(limit, 0)]


def render_search_results(hits: list[MemoryHit]) -> str:
    if not hits:
        return "No memory matches found."

    lines = []
    for hit in hits:
        lines.append(
            f"- {hit.note.memory_id} [{hit.score:.2f}] {hit.note.title} "
            f"({hit.note.source_type}: {hit.note.source_path})"
        )
        if hit.note.tags:
            lines.append(f"  tags: {', '.join(hit.note.tags)}")
        if hit.snippet:
            lines.append(f"  {hit.snippet}")
    return "\n".join(lines)


def tokenize(text: str) -> list[str]:
    tokens = re.findall(r"[a-z0-9]+", text.lower())
    return [token for token in tokens if token and token not in STOPWORDS]


def score_memory(note: MemoryFrontmatter, body: str, query_tokens: list[str]) -> float:
    if not query_tokens:
        return 0.0

    haystack = " ".join(
        [
            note.memory_id,
            note.title,
            note.memory_type,
            note.author_agent,
            note.source_type,
            note.source_path,
            note.source_trace_id,
            note.summary,
            " ".join(note.tags),
            " ".join(note.related_artifacts),
            body,
        ]
    ).lower()

    score = 0.0
    token_set = set(tokenize(haystack))
    query_set = set(query_tokens)
    overlap = len(token_set & query_set)
    score += overlap * 3.0

    if note.title.lower() in " ".join(query_tokens) or " ".join(query_tokens) in note.title.lower():
        score += 4.0
    if note.summary and any(token in note.summary.lower() for token in query_tokens):
        score += 2.0
    if note.source_trace_id and note.source_trace_id.lower() in " ".join(query_tokens):
        score += 5.0
    for tag in note.tags:
        if tag.lower() in query_set:
            score += 2.5
    if note.source_path and any(token in note.source_path.lower() for token in query_tokens):
        score += 1.5
    if any(token in haystack for token in query_tokens):
        score += 1.0
    return score


def build_snippet(body: str, query_tokens: list[str], width: int = 160) -> str:
    compact = re.sub(r"\s+", " ", body).strip()
    if not compact:
        return ""
    lowered = compact.lower()
    for token in query_tokens:
        idx = lowered.find(token)
        if idx >= 0:
            start = max(0, idx - width // 2)
            end = min(len(compact), start + width)
            snippet = compact[start:end].strip()
            return f"... {snippet} ..."
    return compact[:width].rstrip() + ("..." if len(compact) > width else "")


def bullet_lines(values: list[str]) -> list[str]:
    if not values:
        return ["- None"]
    return [f"- {value}" for value in values]


def _find_related_task(repo: AgentBusRepo, task_id: str) -> Path | None:
    for path in repo.all_task_files():
        try:
            task = load_task(path)
        except (OSError, ValueError):
            continue
        if task.task_id == task_id:
            return path
    return None
