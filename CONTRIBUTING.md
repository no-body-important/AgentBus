# Contributing to AgentBus

Thanks for taking part in the project.

## Principles

- keep the repo file-backed and auditable
- prefer small, focused changes
- avoid introducing heavy services unless they materially improve the bus
- preserve compatibility with the existing task/result/memory formats when possible

## Development loop

1. Run the Python checks: `pytest -q` and `python -m agentbus validate`
2. Run the Android debug build if you touched `android-app/`: `cd android-app && .\gradlew.bat assembleDebug`
3. Add or update tests for behavior changes
4. Keep documentation in sync with any new flows or file formats

## Branching

- use short feature branches
- keep commits focused
- do not rewrite history on shared branches unless explicitly agreed

## Safety

- do not commit secrets, keystores, or private tokens
- do not change unrelated repos or workflows when working on AgentBus
- prefer explicit file-based state over hidden side effects

