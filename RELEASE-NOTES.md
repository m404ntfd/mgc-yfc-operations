# MGC YFC Operations 0.34.0

- Fixes the once-per-tab intro flag that prevented mobile playback on subsequent page loads and after logout.
- Serves the existing mobile MP4/WebM through same-origin video URLs with Safari-compatible byte ranges, HEAD responses, content lengths and strong ETags, instead of playing embedded data URLs with media fragments.
- Explicitly configures muted inline mobile autoplay and keeps the Youth for Christ title/tagline cutoff and fade to login.
- If the browser refuses autoplay, keeps login accessible and offers Tap to play intro. Manual replay also works when reduced-motion preferences suppress automatic playback.
- Adds Chromium and WebKit regression coverage for initial load, reload, logout, replay and blocked-autoplay recovery, plus media byte-range tests.

Use Check for Updates on the server, install and restart. Refresh the browser or fully close and reopen the home-screen application to load the fix. The full Windows installer is also available for reinstalling over the existing location; do not uninstall first.

Windows applications remain unsigned; code signing is still deferred.
