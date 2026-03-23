# AgentBus

AgentBus is a standalone, repo-based coordination system for human + AI work.

It gives you a simple way to keep tasks, results, routing, memory, and device workers in one place:

- one canonical `agent_bus/` state folder
- one configurable `agent_bus/config/agents.yaml` registry for any number of agents
- machine-readable task, result, inbox, and memory formats
- one Python package for parsing, validation, routing, and worker execution
- one native Android companion app in `android-app/`
- one repo-backed history that stays auditable and easy to sync

In practice, AgentBus is useful when you want an AI-friendly project hub that feels easy to pick up, easy to inspect, and easy to extend without introducing a heavy backend.

## What lives where

- `agent_bus/tasks/<agent>/` holds active tasks
- `agent_bus/results/<agent>/` holds completion records
- `agent_bus/inbox/<agent>/` holds optional notifications
- `agent_bus/archive/` holds closed handoff artifacts
- `agent_bus/config/` holds runtime registry data like supported agent handles
- `agent_bus/tasks/android/` and friends can support a local Android/Termux worker
- `agent_bus/templates/` contains the canonical file templates
- `agent_bus/memory/` stores searchable memory notes derived from tasks/results/events
- `agent_bus/results/_routing/threads/` stores human-readable thread snapshots for routed comments and reviews
- `agentbus/` contains the reusable Python tooling
- `scripts/termux_handler.py` shows a minimal local worker handler
- `android-app/` contains the Compose-based Android companion app scaffold
- `android-app/signing.properties.example` is the template for release signing
- `scripts/android_install.ps1` builds, installs, and can launch the Android app on a device
- `android-app/` also includes a live repo browser that can read a selected `agent_bus/` tree

## Why people use it

AgentBus is a good fit when you want:

- collaborate from the standard ChatGPT app using live GitHub-backed project context, so multiple agents and contributors can stay aligned on the same work without needing a separate API-driven workflow
- a shared task bus for multiple AI agents working in the same repo
- a readable audit trail of what each agent saw, decided, and changed
- fast handoff between review-only, observe-only, and act-capable agents
- a memory layer that lets later work benefit from earlier decisions
- GitHub-based collaboration without hiding state in a separate database
- a local worker model for desktop, Android, or Termux
- a way to keep human oversight in the loop while still automating the boring parts
- a project structure that is easy to explain to contributors
- a foundation for agent experiments, coordination workflows, or open-source demos

## Example use cases

- using ChatGPT with the GitHub connector to collaborate in shared multi-agent project context, where everyone can read the same repo state, preserve continuity, and continue the same thread of work
- coordinating two or more AI agents on one codebase
- routing comments, labels, and task files to the right agent automatically
- keeping a reviewer, implementer, and observer in the same project context
- running lightweight local workers on a desktop machine or Android device
- building a repo-backed “memory” of prior findings, decisions, and outcomes
- tracking release tasks, bug triage, and follow-up work in a structured way
- letting a phone act as a field worker or companion host for the repo
- creating a transparent collaboration log for open-source projects
- supporting research, prototyping, or demo workflows that need repeatable handoffs
- teaching multi-agent coordination with a system that stays human-readable

## Quick start

```powershell
python -m pip install -e .[dev]
agentbus validate
```

Run a local worker once:

```powershell
agentbus worker --agent android --once --handler-script scripts/termux_handler.py
```

Open `android-app/` in Android Studio to build the graphical Android app and generate an APK.

For a one-command local deploy, use `scripts/android_install.ps1`.

If you plan to contribute, read [CONTRIBUTING.md](CONTRIBUTING.md).
If you find a security issue, read [SECURITY.md](SECURITY.md).

For tagged Android releases, set these repository secrets:

- `ANDROID_KEYSTORE_B64`
- `ANDROID_KEYSTORE_PASSWORD`
- `ANDROID_KEY_ALIAS`
- `ANDROID_KEY_PASSWORD`

## Design goals

- Keep the file system as the source of truth
- Make every handoff readable by humans and parsable by tools
- Prefer explicit status transitions over hidden state
- Keep the stack lightweight enough to use without a backend team
- Support multiple agent types without hardcoding a fixed pair
- Preserve a clear audit trail for routing, worker runs, and memory
- Make the repo easy to clone, inspect, extend, and publish as open source

## Next capabilities

AgentBus already includes the core collaboration path. The next useful additions are:

- stricter schema checks for task/result/memory frontmatter edge cases
- fuller GitHub issue and pull request bridging beyond routed comments, inbox markers, and thread snapshots
- more release hardening for Android packaging and publishing
- additional device QA and onboarding polish for first-time users

Already available today:

- routing decisions based on event type and route mode
- configurable agent handles beyond the default Codex/OpenClaw pair
- capability flags per agent for act/review/observe/comment delivery
- label-based routing for issue and pull request metadata
- local worker loops for desktop, Android, or Termux execution
- archive and promote commands for task/result lifecycle control
- a routing ledger for traceable handoffs
- a memory layer for searchable, semantically useful notes
- routed GitHub comments plus durable inbox markers and thread snapshots for supported agent handles

In other words, the project already covers the main coordination loop, and the remaining work is mostly lifecycle polish, validation hardening, and release-quality finishing.

## License

AgentBus is licensed under the [Apache License 2.0](LICENSE).
The Android companion app, memory layer, CLI, and docs are all part of the same project unless split into separate repos later.
