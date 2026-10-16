# Home Explorer — Changelog

All notable changes to Home Explorer are documented here. Home Assistant device access remains read-only; only user-confirmed relationship mappings are saved locally.

## [0.22.3] — 2026-10-16
- Paginate Find equipment search/filter results eight per page with Previous/Next and accurate filtered range.
- Reset to first page when a search or device-kind filter changes, clamp page when scan result counts change, and preserve device expansion while browsing pages.
- No changes to backend permissions, discovery, privacy filtering, or homeowner-confirmed mappings.

## [0.22.2] — 2026-10-16
- Paginate Automation Modernization Review at five candidates per page with previous/next controls, visible range and total.
- Include all review candidates rather than silently truncating after eight. Selection bounds clamp after data refresh; no changes to scanning or analysis.

## [0.22.1] — 2026-10-16
- Fix section-selector startup ordering so element lookups are initialized before first use. Restores client-side scan startup and single-section display.
- Add startup ordering regression coverage; no backend discovery, mapping, or permission changes.

## [0.22.0] — 2026-10-16
- Replace eight stacked intelligence and equipment panels with a single section selector below Home Overview.
- Show one existing panel at a time, selected by an accessible native dropdown; Find equipment selected by default.
- Keep all existing section DOM nodes, controls, result renderers, mapped relationships and scan data, with no backend changes beyond version metadata.
- Add synthetic layout regression checks; no new HA reads, writes, or telemetry.

## [0.21.2] — 2026-10-16
- Give Find equipment a matching section header and collapsible device browser while retaining search and view filters.
- Keep the matching equipment count visible in the section header. Default expanded for continuity.
- UI only; no change to Home Assistant permissions, discovery, or saved relationships.

## [0.21.1] — 2026-10-16
- Restore consistent review-section card, heading alignment, and compact right-aligned candidate count for Automation Modernization Review.
- Presentation-only fix; no changes to discovery, privacy, automation logic, or saved relationships.

## [0.21.0] — 2026-10-16
- Add read-only Automation Modernization Review, a bounded device-specific shortlist built from sanitized exact action references and flow branching evidence.
- Provide a Home Assistant investigation checklist without asserting genuine conflicts, duplicated intent or safe consolidation. No new HA reads or permissions, no changes to mapping storage.
- Document the Ecobee modernization case study as a real-world reference, and add synthetic regression tests for modernization candidates. The homeowner must separately verify the new review section on HA Green.

## [0.20.0] — 2026-10-16
- Stabilization release: declare amd64 alongside aarch64 with architecture-specific CI builds; verify an amd64 container starts and restricts ingress.
- Document installed-host acceptance and the difference between build, container smoke test, and Home Assistant deployment.
- Keep experimental status, privacy safeguards, read-only behavior and persistent /data relationships unchanged.
- Configuration of privacy preferences and actionable HA navigation are deferred until separately tested.

## [0.19.0] — 2026-10-15
- Begin Phase 5 with compact, read-only Dependency Intelligence over existing homeowner-confirmed power mappings.
- Relate confirmed physical links to reported outlet state, available electrical observations, and device-level automation role summaries while explicitly stating evidence limits.
- No new Home Assistant queries or permissions; preserve private /data mappings and existing Power Intelligence.
- Defer speculative conflict and opportunity analysis to later versioned releases.

## [0.15.4] — 2026-10-15
- Add per-device Automation Flow Intelligence: group structured trigger, condition and action stages from each individual fetched automation configuration rather than mixing references across automations.
- Explain which phases are present, sanitized trigger/condition types, and the roles a device directly plays; do not assert causality, runtime order or actual operations.
- Flag conditional/parallel/repeat structures and templates for manual review without exporting raw configuration, names, times, thresholds or commands.
- Preserve application-level security, live Power Intelligence and saved relationships.

## [0.15.3] — 2026-10-15
- Explicitly whitelist only approved Home Assistant read queries, rejecting service calls, registry mutation and all unexpected query parameters within the app.
- Serialize discovery scans to avoid concurrent Supervisor WebSocket session amplification; return 429 on overlapping requests.
- Reject unsupported transfer-encoded relationship changes and restrict mutation to the existing local JSON mapping endpoint.
- Add security regression tests for disallowed HA requests, incorrect automation IDs, parallel scans, and forbidden HTTP routes.
- Clarify that Home Assistant Ingress authorizes callers and the Supervisor token itself remains capable of broader operations; this is application-level defense in depth, not token-level least privilege.
- Preserve saved `/data` relationships and previous discovery behavior.

## [0.15.2] — 2026-10-15
- Start Python as an unprivileged explorer user, including persistent `/data` ownership migration.
- Remove hardcoded personal-name privacy keywords from the public repository; apply token-boundary filtering to reduce false positives.
- Add sanitized error logging and tests for gateway restrictions, relationship-update headers, and request-size limits.
- Align release metadata and add CI version consistency checks.
- Existing device/automation discovery and locally stored relationships remain unchanged.

## [0.15.1] — 2026-10-15
- Explain allowed structural trigger and condition categories on directly referenced devices; label action targets without asserting an executed command.
- Provide expandable per-device explanations in Automation Intelligence and within the device view.
- Preserve exact-reference-only analysis and avoid exposing automation labels, rule values, service calls, schedules, templates or secret values.
- Remain read-only and retain existing electrical relationships.

## [0.15.0] — 2026-10-15
- Introduce a compact, collapsed-by-default Automation Intelligence panel with exact-reference coverage metrics and device role filters.
- Explain verified trigger, condition and action references by device without exposing automation names or configuration rules.
- Highlight multiple-role devices and devices with no *exact* found reference, without treating absence as proof of non-use.
- Explicitly warn when configuration retrieval is incomplete, and exclude private entity references.
- All Home Assistant data remains read-only and six saved electrical relationships remain unaffected.

## [0.14.0] — 2026-10-15
- Complete Power Intelligence presentation: distinguish commanded on/off, electrical load observations, and appliance operation.
- Compare sensor last_updated with switch last_changed to identify measurements recorded before the current switch state.
- Classify measurements as recent (up to 15 min), aging (15–60 min), and older (over 60 min), without declaring integration failure merely because a reading is old.
- Label historical readings as Last and distinguish no observed load from unavailable or unverified load.
- Preserve exact, privacy-conscious per-outlet correlations and all locally saved relationships; no Home Assistant commands.

## [0.13.8] — 2026-10-15
- Match HS300 switches to registered child socket devices using Home Assistant via_device_id plus exact unique normalized socket name.
- Expose measurements owned by the child socket to that specific parent switch as explicitly provisional socket-registry matches, with no guessed values or device commands.
- Keep unmatched and ambiguous sockets uncorrelated; test Sony TV connection and invalid parent cases.

## [0.13.7] — 2026-10-15
- Add compact switch-state and timestamped electrical badges directly to saved connections.
- Find *candidate* HS300 outlet readings only when unique same-device sensor IDs share an entire outlet stem and a recognized measurement suffix; mark these unverified, never assert the physical load from identifiers.
- Keep shared strip readings unassigned and all Home Assistant access read-only.

## [0.13.6] — 2026-10-15
- Correct single-outlet electrical monitoring when an EP25 also exposes a configuration switch such as its LED.
- Distinguish outlet switches from configuration/diagnostic switches using Home Assistant entity categories.
- Keep shared multi-outlet measurements unassigned and show the reason when readings cannot be correlated.
- Add EP25 regression tests for power, current, voltage and entity-category fallbacks.

## [0.13.5] — 2026-10-15
- Show concise saved outlet-to-appliance relationship labels; move technical IDs into expandable details.
- Prevent Remove controls from wrapping on tablets and phones.
- Display read-only on/off observations and cautiously attributed voltage, current or power measurements on single-switch registry devices, including last-update timestamps.
- Avoid assigning shared multi-outlet-strip sensor measurements to the wrong outlet.

## [0.13.4] — 2026-10-15
- Resolve identical friendly-name devices by opaque unique device keys, not names.
- Show actual TP-Link source manufacturer and LG ThinQ appliance independently.
- Preserve legacy name-keyed mappings for unambiguous device names.


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
