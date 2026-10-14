# Home Explorer v0.3.0 — Plain-Language Discovery

Runs as a **local Home Assistant Green app** through authenticated Ingress. No external hosting or browser API token.

## What's new
- Distinguish Sense virtual energy-monitor detections from HA registered equipment. The new filter defaults to excluding Sense detections; they remain viewable.
- Identify related child components using Home Assistant's `via_device_id` parent relationship when available (for example, some robot vacuum docks).
- Explain entity categories in plain language; expand a card to view descriptions.
- Offer conditional, read-only automation ideas **not** represented as existing automations or guaranteed actions.
- Search by device, manufacturer, model, parent or exposed feature.
- Expanded name filtering for some personal names. Filtering is heuristic, NOT full anonymization.

## Safety and limitations
- Uses Home Assistant WebSocket through Supervisor inside Green; app has no direct host networking and no device-control endpoints.
- Supervisor token remains high privilege despite this app only issuing two registry read queries.
- Does not inspect automation definitions, current states, area assignments or vendor command details.
- No data export, analytics, external assets or background polling.
- Sense virtual detection classification is based on exactly matching the known manufacturer/model metadata and may miss other virtual detections.
- Multiple similar-looking physical devices are NOT automatically merged based on name alone.
- The user-facing privacy filter does not guarantee redaction of identifying names. Do not share screenshots as anonymized.

## Repository-based installation
Home Assistant can register this public GitHub repository as an app source. Read `REPOSITORY_UPDATES.md` before installing. The current user-confirmed deployment is a separate /local_apps installation; **do not remove or overwrite the working app without a migration plan**.

## v0.3.0 deployment status
Home Assistant Green: user-confirmed running, discovery and interface verified on October 14, 2026.

Tests: offline Python unit tests + syntax verification.
