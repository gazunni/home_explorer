# Home Explorer — Release Qualification Matrix

## Release 0.20.0 — Stabilization (2026-10-16)

**Status: experimental.** Test evidence is specific to an architecture, environment, version and verification level. Passing CI must not be described as installed Home Assistant compatibility.

| Environment | Build | Container smoke | Home Assistant installed acceptance |
| --- | --- | --- | --- |
| Linux amd64 CI runner | GitHub Actions Docker build | Start non-root server, writable private /data, deny unauthenticated API | **Not tested** on actual HA host |
| Linux aarch64 via CI emulation | GitHub Actions Docker Buildx + QEMU | Not run on ARM64 in this workflow | **Not tested for v0.20.0** |
| Home Assistant Green / aarch64 | CI architecture build only | CI is not HA Green | **Pending homeowner validation for v0.20.0** |
| Other HA machines | Not tested beyond architecture-specific CI | Not tested | Not tested |

## Automated release gate

- Python syntax and unittest discovery; Node JavaScript syntax plus synthetic UI tests
- Consistent add-on, server, page, README, changelog and container-label version
- Build Linux/arm64 using Buildx and QEMU; build Linux/amd64 separately
- Container startup on Linux/amd64 under non-root user
- Local /data writable by application identity, external unauthenticated /api/devices denied
- No new outbound telemetry, API write permissions, or mapping migration

## Homeowner acceptance on Home Assistant Green

1. Update the existing GitHub-managed add-on to version 0.20.0. Do not reinstall or remove data.
2. Confirm version header and successful on-demand scan.
3. Confirm automation inspection completes: compare checked/attempted counts; do not assume automation number is constant while cleaning.
4. Confirm all six homeowner-confirmed outlet-to-appliance mappings survived the update.
5. Expand Home Intelligence Review and a device. Confirm normal text display and no unexpected behavior.
6. Review logs for failures, crashes, or permission denials involving /data.
7. Report screenshots of the version + Home Overview and the six-saved relationship count, plus any errors.

Acceptance status stays **pending** until the homeowner reports the result.

## amd64 acceptance gate (not yet met)

An independent amd64 Home Assistant installation must perform the same steps. Docker CI alone does not verify Supervisor add-on installation, ingress, permissions, or integrations.

## Privacy and permission boundaries

All Home Assistant discovery is application-level read-only. The permitted write remains explicit homeowner-confirmed relationship mapping to the app's own /data. The Home Assistant Supervisor token has broader permissions than this application and is *not* claimed token-level read-only. Keyword privacy filtering is heuristic, not guaranteed anonymization. Configurable filters are out of scope for this release.

## Issue report template

Provide release number, host architecture, Home Assistant version, deployment method, precise steps, expected vs observed behavior, and **redacted** logs. Do not include raw automation contents, credentials, backup archives, private entity IDs, precise schedules or unfiltered environment variables.
