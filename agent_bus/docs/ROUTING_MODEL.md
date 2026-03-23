---
doc_id: DOC-AGENT-BUS-ROUTING-MODEL
title: "Routing Model"
updated_at: "2026-03-22T00:00:00Z"
---

# Routing Model

## Goal

AgentBus should route work by intent, not by guesswork, and it should do so through a configurable agent registry.

The router decides:

- who should receive the signal
- whether the signal is awareness, review, or action
- which surface emitted the signal
- what trace ID ties the exchange together

## Event types

### Repository events

- `push`
- `workflow_dispatch`

### Collaboration events

- `issue_comment`
- `pull_request_review`

### File-driven events

- task file created or updated under `agent_bus/tasks/<agent>/`
- result file created or updated under `agent_bus/results/<agent>/`
- inbox marker published under `agent_bus/inbox/<agent>/`

## Routing modes

- `observe`: keep context, do not act
- `review`: inspect and comment, but do not change code unless asked
- `act`: make a change or produce a concrete artifact

## Trigger surfaces

- task files
- inbox markers
- issue comments
- pull request review comments
- GitHub Action logs and artifacts

## Agent registry

Supported agent handles are defined in `agent_bus/config/agents.yaml`.

That registry is what lets the bus expand beyond Codex and OpenClaw without rewriting the router.

Each agent can define:

- a canonical handle
- a display label
- aliases for mention detection
- a default route mode
- whether it should be included in routed comments

## Schema additions

These fields make routing more explicit and traceable:

- `route_mode` on task frontmatter
- `trace_id` on task, result, and inbox frontmatter
- `RoutingDecision` output from the CLI
- JSON output from `agentbus route`

## Workflow behavior

The GitHub Action should:

1. inspect the event payload
2. detect the relevant task or comment
3. classify the request as observe, review, or act
4. emit a routing report
5. optionally post or publish the routing report as the trigger surface

## Recommended upgrades

These are the highest-value additions for efficiency and capability:

1. Add `route_mode` and `trace_id` to every handoff artifact so all work is correlatable.
2. Add `agentbus route` so GitHub Actions can make routing decisions without custom scripting.
3. Add a dedicated routing workflow so repo events and comments are handled consistently.
4. Add a routing ledger artifact, such as `agent_bus/results/_routing/`, to record every decision.
5. Add a manual approval gate for destructive or external actions so automation stays safe.
