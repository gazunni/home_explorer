# Home Explorer v0.1.0 — Secure Discovery

Development proof of concept for Home Assistant OS on Home Assistant Green (aarch64).

## Scope
- Protected Home Assistant App (formerly add-on), via Ingress.
- Reads current Home Assistant states through the Supervisor proxy.
- Returns **aggregated entity-domain counts only**, not physical devices or detailed capabilities.
- No device-control endpoints, external telemetry, cloud research or retained home inventories.
- Existing Home Assistant dashboards and automations remain untouched.

## Security boundary
The internal Supervisor token has broad permissions. The application's code restricts its operations to reads, but the API credential is **not a true read-only credential**. No security audit or on-device integration testing has yet been performed. Do not treat this as production ready.
Sensitive domains are excluded. No entity names, identifiers or GPS coordinates are returned to the browser.

## Installation
Home Assistant Green currently runs Core 2026.10.1, Supervisor 2026.09.3 and HA OS 18.3. This source has NOT been installed or verified on that setup.
Custom App repository installation may not support private GitHub repositories. Do not make this repository public and do not embed GitHub tokens in a repository URL. Home Assistant supports local Apps in `/local_apps`. See `INSTALLATION.md` for the private-repository workflow. This is a development build and remains untested on the Green.

## Roadmap
1. Validate local Ingress behaviour and connectivity.
2. Collect registry metadata and group entities by actual physical device.
3. Explain existing automations and dependency chains in plain English.
4. Add capability discovery and optional documentation research with consent.
