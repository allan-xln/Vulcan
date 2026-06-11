# macOS Agent

## Current Status

macOS is not production-ready. It is represented in the demo as simulated/placeholder device data so the product narrative can show cross-platform intent.

## Intended Architecture

- LaunchAgent for user-session signals.
- LaunchDaemon only for privileged service needs.
- explicit accessibility permission flow for app/window metadata.
- signed/notarized package for production.
- queue, heartbeat and enrollment behavior aligned with Linux/Windows.

## Privacy Requirements

macOS collection must stay opt-in and transparent. The agent must not collect passwords, keystrokes, audio, webcam, private message contents or continuous screenshots.

## Roadmap

1. Create native collector skeleton.
2. Implement enrollment and heartbeat.
3. Add offline queue.
4. Add app/window metadata with permission checks.
5. Add installer/uninstaller.
6. Add signing and notarization.
7. Validate on real macOS hardware.
