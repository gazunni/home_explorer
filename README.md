# Home Explorer v0.4.0 — Capability Clarity

Home Explorer runs locally on Home Assistant Green through authenticated Ingress. It reads device and entity registries when requested, without operating devices.

## v0.4.0
- Each card distinguishes **Information only** categories (sensors and binary sensors) from **Potential control** entity categories.
- Possible controls are explicitly **not verified** against live services, permissions, feature flags or device states.
- Manufacturer-app-only functions are marked **unknown**. Home Assistant registry data alone cannot reveal a manufacturer's full feature catalogue.
- Existing Sense detections, parent relationships, search and read-only suggestions remain.

## Security and accuracy limitations
- No manufacturer research/API calls, no command execution, no cloud uploads.
- No current states, entity service capabilities, vendor app features, existing automation code or device-specific permission checks.
- A switch, light or vacuum entity may be a potential control but its real available actions are not guaranteed.
- A device feature not represented in HA cannot automatically be classified as vendor-only.
- Name filtering is heuristic and **does not anonymize screenshots**.
- Supervisor credentials stay server-side but are high privilege. The code makes only registry read requests.

## Updating Green
Your GitHub-managed Home Explorer installation is the repository app (not /local_apps). After Home Assistant refreshes the app repository, v0.4.0 should be offered as an update. Leave Auto update off during development, review release notes, and make sure a backup exists before updating.

## Verification
Run `python -m unittest discover -s home_explorer/tests` with the `home_explorer` directory on PYTHONPATH and websockets installed. Run `python -m py_compile home_explorer/server.py` and `node --check home_explorer/web/app.js`.

## v0.5.0 — Compact device rows
The device grid has been replaced with a single-column list. Tap a device row or the right-side chevron to expand its capabilities, parent relationship, explanations and suggested uses. Multiple devices may be open simultaneously. Search and device-type filtering remain intact. Expansion state is retained while filtering and reset on a fresh scan. All operations remain read-only.
