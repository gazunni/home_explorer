# Home Explorer — repository updates

This repository is intended to be a Home Assistant app repository.

## Current release synchronization
Before adding this repository to Home Assistant, ensure `home_explorer/config.yaml` and the corresponding app source have BOTH been updated to the same verified release. Do not simply edit the version string.

## Add the repository to Home Assistant
1. Confirm this GitHub repository is **Public** (Settings → General → Danger Zone → Change repository visibility).
2. In Home Assistant, navigate to **Settings → Apps → Install app**.
3. Open the top-right menu (⋮), choose **Repositories**, enter `https://github.com/gazunni/home_explorer` and save.
4. Refresh the app store. Home Explorer should appear as a repository-managed app.

## Local install vs repository-managed install
An app installed from `/local_apps/home_explorer` has a different Supervisor identity from an app installed from GitHub, even when its internal slug is the same. Do not assume adding the GitHub repository upgrades an existing local installation.

Plan the migration separately: preserve the working local app and its backup, validate the repository build, then intentionally switch installations. Never enable automatic updates until the upgrade and shutdown paths have been tested.

## New releases
Commit the complete release source and change `home_explorer/config.yaml` to the new version in the same release. Refreshing the repository lets Home Assistant detect it. Keep **Auto update** off initially.
