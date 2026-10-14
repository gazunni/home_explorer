# Home Explorer — Changelog

All notable changes to Home Explorer are documented here. Home Explorer remains read-only; capability descriptions do not verify executable Home Assistant commands.

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
