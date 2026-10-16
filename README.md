# Home Explorer v0.21.1 — Explore Your Connected Home

## Version 0.21.1 — Automation Modernization Review

A new read-only review section lists up to eight devices with multiple **distinct checked configurations** directly referencing them as action targets. It provides evidence and an explicit Home Assistant investigation step, with branch-presence context from previously sanitized device flow outlines. It never calls these conflicts or recommends automatic deletion. The Ecobee case study (`docs/case-studies/ecobee-modernization-2026-10-16.md`) grounds future work; this release does **not** infer automation purpose, timing, thresholds or runtime causality, and cannot perform a full Ecobee-style consolidation automatically.


**Home Explorer** is an application designed for read-only device and capability explorer for Home Assistant, running locally through authenticated Home Assistant Ingress. It helps you understand what Home Assistant can see without issuing commands or modifying devices and automations.

## Current features (v0.19.0)

- Relationship selections use unique opaque device keys, distinguishing same-name TP-Link and LG ThinQ registrations. Existing name-keyed relationships remain readable for unambiguous device names.


- Relationship picker prioritizes user-facing switch names, shows exact switch entity IDs, and labels ambiguous duplicate appliance registrations rather than silently omitting them.


- On-demand discovery of registered devices and their exposed Home Assistant entities.
- Compact, expandable device rows with manufacturer/model and parent-device information where available.
- Automation status counts and exact structured device-reference counts; automation names, configuration bodies and IDs remain excluded. Some automations may be unavailable for analysis; coverage is reported.
- Domain-wide service catalogue and reported feature flags; neither proves a service can be called for an individual entity.
- Read-only at-a-glance status summaries where real readings are available.\n- Optional, explicitly confirmed upstream smart-outlet relationships using the in-app mapper, saved in add-on `/data/power_dependencies.json`; outlet power is not proof that an appliance is operating.
- Device-specific entity names and readable Home Assistant states, with technical entity IDs and raw values available on demand.
- Separate categories for information-only entities and **potential** controls. A potential control is not a verified working command.
- Separate device and Sense energy-monitor detection views.
- Search by device, manufacturer, capability, entity name or entity ID.
- Read-only suggestions for further investigation.

## Important limitations and privacy

- No device commands, automation modifications or cloud uploads.
- States are read-only observations; an entity's existence does not prove a command will succeed.
- Manufacturer-app-only functionality **cannot** be established from Home Assistant registries.
- Unknown or unavailable states should not be interpreted as device faults.
- Private-name filtering is heuristic, not guaranteed anonymization. Review screenshots before sharing.
- Supervisor access remains server-side and has broader Home Assistant capabilities than the application's deliberately limited operations. A strict application-level read-query allowlist rejects write operations in the websocket request builder; it does not change the token's underlying permissions. Ingress access must still be protected by Home Assistant authentication. An admin-only panel setting should not be treated as a separately verified per-user access check. The read-only designation describes application behavior, not a token-level read-only permission. Entity identifiers and filtered state values are shown only to authenticated users of the local application.
- Automation definitions are inspected only in memory for exact entity/device references, without exposing raw configurations; suggestions are not verified automations.

## Dependency Intelligence (v0.19.0)

The Phase 5 first increment correlates only homeowner-confirmed local power relationships with sanitized current outlet state and exact device-level automation roles. It does not infer wiring, targeting of a specific outlet from a device-level reference, causation, or appliance operation. More advanced conflict and opportunity analysis remains future work.

## Phase 5: potential automation overlaps (v0.19.0)

Shows devices exactly referenced as action targets in two or more separately fetched automation configurations. Counts are per configuration rather than repeated steps. These are investigation candidates, **not proven contradictory commands, schedules or actual execution**. Read-only and fully sanitized; no raw automation details are sent to the browser.

## Evidence-Based Opportunity Intelligence (v0.19.0)

The new compact investigation panel highlights multiple exact action references, ambiguous saved appliance identity, unknown mapped outlet states and incomplete automation retrieval. It does not infer that similar registrations are duplicates, propose deleting integration entries, interpret actual automation execution, or change Home Assistant.

## Home Intelligence Review (v0.19.0)

Uses named, bounded evidence-based findings: ambiguous saved appliance registrations, unavailable mapped outlet states, and up to three of the most frequently referenced automation action targets. Each includes a factual evidence label, explicit uncertainty and a homeowner review step. This is not defect detection or instruction to remove integrations. No new HA commands.

## Release qualification and support boundaries (v0.20.0)

Home Explorer remains **experimental**. Declared architectures are **aarch64** (Home Assistant Green) and **amd64**. GitHub CI builds ARM64 and builds/starts amd64 in a Linux runner, checks access controls and runs regression tests. CI does **not** establish that the add-on installs and behaves correctly on every host or Home Assistant release.

Known deployment evidence: the homeowner has exercised v0.19.0 on Home Assistant Green with an iPad; the new v0.20.0 release requires its own installed acceptance verification. No Home Assistant amd64 installation has been acceptance-tested yet.

See [RELEASE_QUALIFICATION.md](RELEASE_QUALIFICATION.md) for the test matrix, acceptance checklist, limitations and issue reporting template.

## Installation and updates

Repository: https://github.com/gazunni/home_explorer

Use the **GitHub-managed Home Explorer** app in Home Assistant. Do not reinstall the retired local copy.

1. In Home Assistant, open **Settings → Apps → Home Explorer**.
2. When a new version appears, review the changelog and choose **Update**.
3. If the repository has not refreshed yet, run `ha store reload` in Terminal & SSH and check again.
4. Keep a backup before updating. During active development, leave **Auto update** off.
5. Verify the app starts, run **Explore my devices**, and test expansion, searching and filters.

Full instructions: [INSTALLATION.md](INSTALLATION.md).

## Version history

Current version: **0.21.1** (October 16, 2026).

See the [complete changelog](home_explorer/CHANGELOG.md) for release-by-release details. Release history is maintained there rather than appended to this README.

## Developer checks

From the repository root with dependencies installed:

```bash
python -m py_compile home_explorer/server.py
node --check home_explorer/web/app.js
PYTHONPATH=home_explorer python -m unittest discover -s home_explorer/tests
```

GitHub Actions also runs validation on pushes. A green workflow is required before considering a release validated; successful installation alone does not replace test results.
