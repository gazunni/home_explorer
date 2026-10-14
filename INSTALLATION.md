# Home Explorer v0.6.0

Source: https://github.com/gazunni/home_explorer

1. In Home Assistant Terminal run `ha store reload` to refresh the GitHub repository if the new version is not yet offered.
2. Settings → Apps → GitHub-managed Home Explorer → Update to 0.6.0. Keep backup option enabled.
3. Verify state Running, Open Web UI, Explore my devices, and confirm rows expand and collapse using the chevrons.
4. Test device-only and energy-monitor filters; test search with multiple expanded rows.
5. Keep Auto update disabled during active development.

Do not reinstall the removed local app. Existing backup files under /share remain unchanged.

Verify the expanded device entities and displayed states. No device commands are executed.
