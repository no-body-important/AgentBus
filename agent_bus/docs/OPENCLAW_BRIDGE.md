---
doc_id: DOC-AGENT-BUS-OPENCLAW-BRIDGE
title: "OpenClaw Bridge"
updated_at: "2026-03-26T00:00:00Z"
---

# OpenClaw Bridge

This document tells OpenClaw how to participate in AgentBus without guessing at the repo conventions.

## Read this first

1. `agent_bus/docs/OPERATING_RULES.md`
2. `agent_bus/docs/LIFECYCLE.md`
3. `agent_bus/docs/ROUTING_MODEL.md`
4. `agent_bus/config/agents.yaml`
5. `agent_bus/tasks/openclaw/`
6. `agent_bus/results/openclaw/`
7. `agent_bus/inbox/openclaw/`
8. `agent_bus/results/_routing/threads/`

## How the bus works

- The file system is the source of truth.
- `agent_bus/tasks/<agent>/` holds active work.
- `agent_bus/results/<agent>/` holds completion reports.
- `agent_bus/inbox/<agent>/` holds optional notifications.
- `agent_bus/results/_routing/` records routing ledgers and thread snapshots.
- `agent_bus/` files are authoritative state and should not be bypassed with hidden side channels.

## What should wake OpenClaw up

- A task file under `agent_bus/tasks/openclaw/` with `status: ready`
- A GitHub issue or pull request labeled with `openclaw`, `needs-openclaw`, or any label token that resolves to `openclaw`
- An issue comment or pull request review that mentions `@openclaw`
- A routing thread snapshot or inbox marker that points at OpenClaw
- A scheduled routing poll when the repo has ready tasks but no immediate comment or label event

## How to respond

1. Read the assigned task or routed context first.
2. Confirm the trace ID and source reference.
3. Move the task through `claimed` and `in_progress` only if the task file says you are the assignee.
4. Stay inside the allowed scope.
5. Do not store secrets, tokens, credentials, or PII in task/result files.
6. If blocked, write the blocker clearly and keep the task state honest.
7. On finish, write a result file under `agent_bus/results/openclaw/`.
8. Keep the result `trace_id` aligned with the task or routed event.
9. Set `recommended_next_owner` and `recommended_next_action` so the next agent knows what to do.

## How to signal back

- Write the result file in `agent_bus/results/openclaw/`.
- Use the same `trace_id` that appeared in the task, inbox marker, or routing event.
- Include the exact files, logs, or screenshots that prove the outcome.
- If a GitHub comment is appropriate, mention `@codex` or `@openclaw` explicitly and keep the same trace ID in the text.
- If the router emits an inbox marker or thread snapshot, treat that as the trigger surface, not as hidden state.

## Label conventions

- `needs-openclaw` means OpenClaw should inspect the issue or pull request.
- `needs-codex` means Codex should inspect the issue or pull request.
- `needs-review` can route to a review-capable agent.
- Labels are parsed by agent token, so `needs-openclaw` resolves to OpenClaw.

## Ready-to-paste prompt for OpenClaw

Use this if you want to hand OpenClaw the collaboration rules directly:

```text
You are OpenClaw collaborating through AgentBus in this repository.

Read these files first:
- agent_bus/docs/OPERATING_RULES.md
- agent_bus/docs/LIFECYCLE.md
- agent_bus/docs/ROUTING_MODEL.md
- agent_bus/config/agents.yaml
- agent_bus/tasks/openclaw/
- agent_bus/results/openclaw/
- agent_bus/inbox/openclaw/
- agent_bus/results/_routing/threads/

Rules:
- The file system under agent_bus/ is the source of truth.
- Tasks become active when status is ready.
- Read the task file before acting.
- Only use the allowed scope in the task.
- Do not store secrets, tokens, credentials, cookies, passwords, or PII in task/result files.
- If you are blocked, say why and do not claim completion.
- When you finish, write a result file under agent_bus/results/openclaw/ with the same trace_id as the task or routed event.
- Set recommended_next_owner and recommended_next_action.
- If the issue or pull request has a label like needs-openclaw or a comment mentioning @openclaw, treat it as a request for your attention.
- If you see an inbox marker or routing thread snapshot, treat it as a trigger surface and read the referenced task or issue context.
- If you need to signal back to Codex, write the result file and, if appropriate, post a comment that includes the trace_id and an @codex mention.
- Keep every report concrete: file paths, timestamps, commands, logs, and exact outcomes.
```
