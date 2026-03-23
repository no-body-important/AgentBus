# AgentBus Mobile Tutorial

## 1. What you are looking at

AgentBus Mobile is a native Android companion app for the AgentBus repo protocol.

Its job is to make the system easier to understand and use on a phone:

- what an agent is
- how tasks move
- how comments and labels trigger routing
- how a local worker can run on Android or Termux

## 2. How it fits into the system

The Android app does not replace the repo.

The repo remains the source of truth:

- `agent_bus/tasks/` for active work
- `agent_bus/results/` for results
- `agent_bus/inbox/` for notifications
- `agent_bus/memory/` for shared memory notes and the index
- `agent_bus/config/agents.yaml` for the agent registry

The app is a visual companion that helps you inspect and understand that shared state.

## 3. What it can do

- show a dashboard with the current AgentBus structure
- explain the protocol with step-by-step screens
- list agents and capabilities
- open a live repo tree and read `agent_bus/` files directly
- surface the indexed memory trail from `agent_bus/memory/index/memory-index.json`
- search memory notes and save a new note back into the selected repo tree
- tap an indexed memory note to load it into the editor and update it in place
- show local worker guidance for desktop and Android/Termux
- it can be expanded further to read live data from a sync service or a remote API

## 4. How to use it

1. Open `android-app/` in Android Studio.
2. Let Gradle sync.
3. Run the app on an emulator or connected device.
4. Use the tutorial screen to understand the workflow.
5. Use the worker screen to see how Android/Termux fits in.

## 5. How the Android/Termux worker fits

The worker mode is for a device that participates in the repo workflow locally.

It can:

- watch for tasks
- claim work
- run a handler script
- write results back to the repo
- contribute memory notes that become part of the shared context layer

That makes the Android device another local agent host rather than a separate silo.

## 6. Safe usage rules

- start with `observe` and `review`
- keep `act` limited to trusted handlers
- do not grant broader shell access than necessary
- keep secrets out of task and result files

## 7. Suggested next steps

- connect the app to live repository data
- add authentication or local device approval
- add task import/export support
- add an activity log for route decisions and worker runs

## 8. Release signing

To build and publish a signed Android release, provide these secrets in GitHub:

- `ANDROID_KEYSTORE_B64`
- `ANDROID_KEYSTORE_PASSWORD`
- `ANDROID_KEY_ALIAS`
- `ANDROID_KEY_PASSWORD`

The release workflow will use them to build an APK when you push a `v*` tag.
