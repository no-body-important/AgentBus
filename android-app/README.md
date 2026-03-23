# AgentBus Mobile

This is the native Android companion app scaffold for AgentBus.

It is intentionally lightweight:

- Jetpack Compose UI
- built-in tutorial screens
- agent registry overview
- local worker guidance for desktop and Android/Termux flows

## Open and build

Open `android-app/` in Android Studio as a Gradle project.

This scaffold now includes a Gradle wrapper, so you can build from the command line too.

From there you can:

- sync the project
- run it on an emulator or device
- build a debug APK
- later sign and release a production APK

## Build commands

From the repo root:

- debug APK: `cd android-app && .\gradlew.bat assembleDebug`
- release APK: `cd android-app && .\gradlew.bat assembleRelease`

Release builds require a local `android-app/signing.properties` file and a keystore. Copy `signing.properties.example` first, then fill in the values.

## One-command deploy

Use `scripts/android_install.ps1` to build, install, and optionally launch the app on a connected device.

## What this app is for

- understanding the AgentBus protocol visually
- reviewing agents, routes, and worker modes
- giving you a guided mobile front end for the same repo-backed system

## What it is not

- it is not a heavy backend
- it is not a replacement for the repo source of truth
- it is not a standalone data store

## Tutorial

See [TUTORIAL.md](TUTORIAL.md) for a more detailed walkthrough.
