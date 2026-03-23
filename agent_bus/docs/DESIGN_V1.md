---
doc_id: DOC-AGENT-BUS-DESIGN-V1
title: "Design v1"
updated_at: "2026-03-22T00:00:00Z"
---

# Agent Bus Design v1

## Purpose

Agent Bus is the repo-based handoff layer for humans and AI collaborators.

## Canonical state

- `agent_bus/` is authoritative.
- Tasks under `agent_bus/tasks/<agent>/` are the active queue.
- Results under `agent_bus/results/<agent>/` are the completion records.
- Inbox markers under `agent_bus/inbox/<agent>/` are optional notification aids.

## Trigger model

- `@Codex (...)` and `@OpenClaw (...)` are human-facing cues.
- The real trigger is a task file with `status: ready` in the correct agent folder.
- The file contents are the authoritative handoff payload.

## Compatibility rule

- Root-level docs may exist for convenience, but `agent_bus/docs/` is canonical.
