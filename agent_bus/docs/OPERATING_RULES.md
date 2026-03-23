---
doc_id: DOC-AGENT-BUS-OPERATING-RULES
title: "Operating Rules"
updated_at: "2026-03-22T00:00:00Z"
---

# Operating Rules

## Shared rules

- `agent_bus/` files are authoritative state.
- Do not store secrets, credentials, tokens, private keys, or PII in task/result files.
- Do not mark work successful unless objective and success criteria are actually met.
- No irreversible external actions without explicit human supervisor approval recorded in the task.

## Trigger convention

- A task becomes active when its frontmatter has `status: ready`.
- The assignee is determined by `to_agent`.
- The task file itself is the trigger.
- Inbox markers and thread snapshots are optional and must never replace the task file.

## Codex protocol

1. Read the task file under `agent_bus/tasks/codex/`.
2. Move status through `claimed` then `in_progress`.
3. Execute only the allowed actions.
4. If blocked, set `status: blocked` and document the blocker.
5. On finish, write a result under `agent_bus/results/codex/` and set a terminal task status.

## OpenClaw protocol

1. Read the task file under `agent_bus/tasks/openclaw/`.
2. Move status through `claimed` then `in_progress`.
3. Execute only the scoped browser, dashboard, or external UI checks.
4. If blocked, set `status: blocked` and report the blocker with evidence.
5. On finish, write a result under `agent_bus/results/openclaw/` and set a terminal task status.
