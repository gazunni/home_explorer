# Home Explorer v0.3.0 — repository setup

This public repository can be added to Home Assistant's app store:
Settings > Apps > Install app > ⋮ > Repositories
https://github.com/gazunni/home_explorer

**Do not install/migrate yet without checking the separate local installation.**
The working Green app is installed as local_home_explorer under /local_apps/home_explorer; the repository installation has a different Supervisor slug. Adding the repository does not automatically convert the existing installation. Keep the existing v0.3.0 app working and retain the v0.2.0 rollback backup while evaluating migration.

See REPOSITORY_UPDATES.md for the detailed update workflow. Auto update should remain off until migration and shutdown behavior are verified.
