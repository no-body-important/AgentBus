---
doc_id: DOC-AGENT-BUS-ANDROID-TERMUX
title: "Android / Termux Worker"
updated_at: "2026-03-22T00:00:00Z"
---

# Android / Termux Worker

AgentBus can run on an Android device through Termux as a local worker host.

## What it does

- watches `agent_bus/tasks/android/` for ready tasks
- claims and completes tasks locally
- writes results into `agent_bus/results/android/`
- optionally pushes changes back to GitHub

## Intended use

- lightweight local automation
- device-specific tasks
- review or act jobs that should run near the Android device

## Safety model

- `observe` and `review` are preferred for first-pass device support
- `act` should be limited to approved commands or a trusted handler script
- do not give the worker unrestricted shell access unless you deliberately want that risk

## Running it

Use the CLI worker command with `--agent android` and a local handler script if needed.

Example:

```powershell
agentbus worker --agent android --once --handler-script scripts/termux_handler.py
```

For repeated polling, omit `--once`.
