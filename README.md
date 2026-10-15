# Home Explorer v0.13.5 — Explore Your Connected Home

**Home Explorer** is a read-only device and capability explorer for Home Assistant, running locally through authenticated Home Assistant Ingress. It helps you understand what Home Assistant can see without issuing commands or modifying devices and automations.

## Current features (v0.13.5)

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
- Supervisor access remains server-side and should be protected. Entity identifiers and filtered state values are shown only to authenticated users of the local application.
- Automation definitions are inspected only in memory for exact entity/device references, without exposing raw configurations; suggestions are not verified automations.

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

Current version: **0.13.2** (October 14, 2026).

See the [complete changelog](home_explorer/CHANGELOG.md) for release-by-release details. Release history is maintained there rather than appended to this README.

## Developer checks

From the repository root with dependencies installed:

```bash
python -m py_compile home_explorer/server.py
node --check home_explorer/web/app.js
PYTHONPATH=home_explorer python -m unittest discover -s home_explorer/tests
```

GitHub Actions also runs validation on pushes. A green workflow is required before considering a release validated; successful installation alone does not replace test results.
