# Home Explorer — Changelog

All notable changes to Home Explorer are documented here. Home Assistant device access remains read-only; only user-confirmed relationship mappings are saved locally.

## [0.13.3] — 2026-10-15
- Improve switch selector labels using Home Assistant friendly names and show exact switch entity IDs.
- Explain ambiguous duplicate appliance registrations instead of silently omitting them from the picker.
- Preserve local-only relationship saves and read-only Home Assistant access.

## [0.13.2] — 2026-10-15
- Add read-only Registry Intelligence classifications for disabled registrations, possible Tuya scenes, infrastructure, missing entities, and excluded entities.
- Explain entity-registry counts and disabled or unsupported entities without disclosing private entity names.
- Filter review entries by classification; all scene classifications remain provisional and no deletion is inferred.

## [0.13.1] — 2026-10-14
- Add read-only Registry review of disabled registrations and records with no eligible visible entities; exclude disabled registrations from normal browsing.
- Display disabled and empty registration counts separately; preserve privacy-name filtering and never expose internal registry IDs.
- Remove redundant device reading-health paragraph.

## [0.13.0] — 2026-10-14
- Add device-level reading intelligence with conservative status indicators and explanatory panels.
- Distinguish confirmed upstream power off from unavailable readings while avoiding unsupported hardware-fault conclusions.
- Explain unknown, unavailable, and fully reporting entity states; preserve read-only behavior.

## [0.12.4] — 2026-10-14
- Remove redundant discovery details and explanatory paragraphs already represented by the dashboard metrics.
- Show a conditional notice only for failed scans or incomplete automation configuration checks.
- Keep compact metrics, collapsed relationship editor, and read-only HA access unchanged.

## [0.12.3] — 2026-10-15
- Replace discovery paragraphs and large statistic cards with a compact two-row Home Overview.
- Display registered, shown, Sense, automation, checked, and privacy counts in matching inline boxes.
- Keep detailed discovery information expandable and relationship editor collapsed by default.
- Preserve read-only device access and locally saved relationships.

## [0.12.2] — 2026-10-14
- Show the current application version beside the READ ONLY badge in the header.
- Collapse the introductory guidance by default while keeping its title visible.
- Move Refresh devices outside the introductory panel for quick access.
- Preserve automatic discovery, read-only behavior, and local saved connections.

## [0.12.1] — 2026-10-14
- Move Find equipment and Show controls directly above device results, below Connected device relationships.
- Keep the relationship editor and its saved connections together without separating them from the list search.

## [0.12.0] — Development candidate
- Show confirmed upstream outlet state directly in the appliance row.
- Explain combinations of outlet state and appliance readings without claiming operating status, automation intent, or faults.
- Load local confirmed mappings once per scan; no Home Assistant commands are issued.

## [0.11.7] — 2026-10-14
- Corrected the add-on update notes to show recent releases in order.
- Aligned the version displayed in the web interface with the add-on version.

## [0.11.6] — 2026-10-14
- Recovered add-on startup after the 0.11.5 permission-switch regression.
- Added a Docker container startup smoke test to CI.

## [0.11.5] — 2026-10-14
- Attempted to repair local mapping storage permissions; this introduced a startup regression, fixed in 0.11.6.

## [0.11.4] — 2026-10-14
- Added side-by-side identity details for power source and appliance.
- Preserved mapping selections while filtering.

## [0.11.3] — 2026-10-14
- Automatic discovery on open, with a manual refresh button.
- Natural alphabetical ordering and separate outlet/appliance search.
- Expanded the relationship editor by default.

## [0.11.2] — 2026-10-14
- Replaced the oversized device-tile mapper with compact, searchable selectors.
- Added confirmation and locally saved connections.

## [0.11.1] — 2026-10-14
- Improved relationship mapping layout and interaction.

## [0.11.0] — 2026-10-14
- Touch-friendly tap-to-connect and desktop drag/drop mapper for upstream smart outlets.
- Confirmed relationships are stored in add-on /data, not in the public repository.
- Strictly scoped relationship writes; Home Assistant access remains read-only.
- Separate device reading health from electrical supply and actual operation.
- Per-device counts of reporting, unavailable, and unknown entities; never infer a device fault from one sensor.
- Optional explicit, local upstream outlet dependency mapping; supply states are displayed separately from appliance health.
- No automatic wiring inference or scheduled-off classification. Relationships must be manually confirmed.


## [0.10.0] — Development candidate
- Read-only exact automation-to-device reference counts, separated into triggers, conditions and actions; no automation names or raw definitions returned.
- Coverage indicator for configurations checked, with explicit handling for partial coverage.
- Regression tests for templates, private identifiers, structured references, and redaction.
- Read-only automation on/off status totals; no names or configurations exposed.
- Domain-wide service inventory and reported feature flags, without command execution.
- Privacy-safe reported select options and regression tests.

## [0.9.0] — Included in combined candidate
- Capability metadata discovery; does not prove entity-level service availability.

## [0.8.0] — Development candidate
- Added read-only at-a-glance device summaries based on existing exposed, non-private states.
- Prioritized meaningful known readings and excluded unknown/unavailable values from summaries.
- Added privacy and summary regression tests.

## [0.7.0] — 2026-10-14
### Changed
- Display readable interpretations of common Home Assistant states.
- Place raw entity IDs, raw states and control descriptions inside expandable technical details.
- Reduce repeated generic capability text in expanded device rows.
### Clarified
- Potential service families are described from entity domains only; no commands or permissions have been verified.
- Unknown and unavailable readings remain distinctly identified.
### Added
- Regression tests for entity-domain metadata, state values and sensitive entity filtering.

## [0.6.0] — 2026-10-14
### Added
- Actual entity names, IDs and latest read-only state values under each device capability group.
- Search by registered entity name/ID.
- Entity-level sensitive-name filtering.
### Changed
- Replaced the repeated manufacturer caveat with a single explanation in the header.
### Limitations
- States are observations, not verified command availability.

## [0.5.0] — 2026-10-14
### Changed
- Replaced the large device card grid with compact, one-device-per-row entries.
- Added an expandable chevron on the right of each device row.
- Allow multiple device rows to stay expanded.
- Moved capability explanations, device relationships, and automation ideas into expandable details.
- Retained search and device/energy-monitor filters.
- Preserve expanded rows when changing search or filter; clear expansions on a fresh scan.

### Security
- Continued using read-only discovery with existing privacy filtering and no device commands.

## [0.4.0] — 2026-10-14
### Added
- Separately identified information-only categories and potential-control categories.
- Added a device-only view and a Sense energy-monitor detection view.
### Clarified
- Potential controls are not verified executable commands.
- Manufacturer-app-only functionality cannot be determined from Home Assistant registry data.

## [0.3.0] — 2026-10-14
### Added
- Improved device explanations and exploration suggestions using registered device/entity categories.
- Device relationships and expandable capability information.

## [0.2.0] — 2026-10-14
### Added
- Read-only device discovery based on the Home Assistant device and entity registries.
- Manufacturer/model information where registered; privacy-conscious filtering.

## [0.1.0] — 2026-10-14
### Added
- Initial read-only entity inventory grouped by Home Assistant entity domain.
- Home Assistant Ingress interface with on-demand local discovery.

---
Release summaries for earlier versions are retrospective descriptions, not a complete record of individual commits.
