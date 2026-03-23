# AgentBus

AgentBus is a standalone, repo-based handoff system for human + AI collaboration.

It turns the file-driven handoff setup into an independent project with:

- a canonical `agent_bus/` state folder
- a configurable `agent_bus/config/agents.yaml` registry for any number of agents
- machine-readable task, result, and inbox formats
- a small Python package for parsing and validation
- a CLI for validation, routing, and worker execution
- CI to catch broken handoff files early

## What lives where

- `agent_bus/tasks/<agent>/` holds active tasks
- `agent_bus/results/<agent>/` holds completion records
- `agent_bus/inbox/<agent>/` holds optional notifications
- `agent_bus/archive/` holds closed handoff artifacts
- `agent_bus/config/` holds runtime registry data like supported agent handles
- `agent_bus/tasks/android/` and friends can support a local Android/Termux worker
- `agent_bus/templates/` contains the canonical file templates
- `agentbus/` contains the reusable Python tooling
- `scripts/termux_handler.py` shows a minimal local worker handler

## Quick start

```powershell
python -m pip install -e .[dev]
agentbus validate
```

Run a local worker once:

```powershell
agentbus worker --agent android --once --handler-script scripts/termux_handler.py
```

## Design goals

- Keep the file system as the source of truth
- Make every handoff readable by humans and parsable by tools
- Prefer explicit status transitions over hidden state
- Make it easy to publish as an open-source GitHub repo

## Next capabilities

The current scaffold is intentionally small. The next useful additions are:

- routing decisions based on event type and route mode
- configurable agent handles beyond the default Codex/OpenClaw pair
- capability flags per agent for act/review/observe/comment delivery
- label-based routing for issue and pull request metadata
- local worker loops for desktop, Android, or Termux execution
- archive and promote commands
- stricter schema checks for task/result frontmatter
- a routing ledger for traceable handoffs
- optional GitHub issue and PR bridging
