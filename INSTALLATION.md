# Home Explorer — Private local installation (development only)

Target: Home Assistant Green / Home Assistant OS 18.3 / Core 2026.10.1.
This has **not** yet been installed or tested on the target device.

## Why local Apps?
The GitHub repository is private. Home Assistant's supported local Apps development directory is `/local_apps` (older documents may call it `/addons`). Use your existing Studio Code Server or Terminal & SSH App to access it. **Do not** use the Git Pull App against `/config` or paste GitHub access tokens into App repository URLs.

## Transfer plan (no public repository or tokens in HA)
1. On your iPad, sign in to GitHub and open the private repository's branch `home-explorer-install-validation`.
2. Download the source ZIP using GitHub's Code > Download ZIP.
3. Using your installed Studio Code Server's file upload feature, transfer the ZIP to a temporary non-configuration location within its accessible workspace.
4. In the Terminal & SSH App, extract **only** the repository's `home_explorer/` directory into `/local_apps/home_explorer/`. Check the folder contains `config.yaml`, `Dockerfile`, `server.py` and `web/`, with no extra nested repository wrapper. Do not extract anything over `/config`.
5. In Home Assistant: Settings > Apps > Install app > menu > Check for updates (or reload), then inspect the Local Apps section.
6. Confirm the App configuration and permissions before installing; leave automatic startup disabled. Do not start until the code and compatibility checks are complete.

The exact upload and extraction commands depend on which paths the installed editor exposes and should be confirmed on your system before running shell commands. Never send repository credentials or Home Assistant backups in chat.

## First smoke test (after approval)
- Start Home Explorer, inspect the App log, then open its sidebar entry.
- Scan should report only counts grouped by entity domain.
- Verify the normal Home Assistant dashboard remains available.
- Stop and uninstall Home Explorer if there are unexpected network permissions, failure logs or resource usage.

## Security
The App's Supervisor-issued API token is not genuinely read-only. This first build merely avoids write operations in application code. Do not consider it security-audited or suitable for public distribution.
