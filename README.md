# Home Explorer v0.2.0 — Registered Device Discovery

**Status:** Development branch only. Not installed on the Home Assistant Green.

## Features
- Runs as a protected Home Assistant App with authenticated Ingress.
- Reads the Home Assistant device registry and entity registry on demand through the internal WebSocket proxy.
- Lists registered devices, manufacturer and model, grouped exposed entity categories and entity counts.
- Search/filter devices without any cloud services.
- Filters sensitive entity domains and devices with security/location-related names. This is a heuristic, **not a guarantee of complete anonymization**.
- No device control commands, automation editing, history access or background polling.
- Does not upload any household inventory or persist discoveries to disk.

## Important limitations
- "Capabilities" are exposed entity types, **not** a complete inventory of actual supported commands or manufacturer features.
- Not all entities belong to registered devices.
- Child devices may appear as separate entries and will need parent relationship display improvements.
- The Supervisor token is highly privileged: our code only sends read commands but the credential itself is **not scoped read-only**.
- The app and dependencies have **not** yet been validated or tested on real Green hardware.

## Installation process
Do not overwrite the running v0.1.0 prototype until a backup of its local app folder is made and v0.2.0 tests pass. The private repository stays private. Use the established local Apps directory /local_apps.

## Next development steps
1. Validate Python and JavaScript syntax, configuration schema, dependency versions and safe responses.
2. Verify WebSocket registry availability with HA Core 2026.10.1.
3. Add parent-child grouping and richer feature explanations.
4. Read-only automation relationship discovery in a later release.
