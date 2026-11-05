# MGC YFC Operations 0.27.0

- Adds Print with a Purpose to the page menu and daily starting-page choices, with a cyan (#00ffff) header and a placeholder for its future design.
- Removes Phone Access from Settings and renames the dropdown's Settings / Appearance entry to Settings. Appearance remains available within Settings.
- Adds confirmation before manually resetting a receipt. Cancel and Escape preserve the entered category and attachment and confirm that no changes were made.
- Replaces My password / passcode with Return to Home. Home is the first starting page selected for the user that server calendar day; later page selections do not replace it. Navigation actions are available across signed-in pages.
- Ends inactive sessions at the next server-local midnight. Deliberate user activity within five minutes keeps an overnight session active until it becomes inactive; background refreshes do not count. Every session has an absolute 24-hour limit.
- Adds mobile/desktop regression checks and session-expiry checks.

On the host server, use Check for Updates, install and restart, then refresh browsers. The full Windows installer is also available for reinstalling over the existing installation. Keep the existing installation location and do not uninstall first.

The Windows installer and applications remain unsigned; code signing is still deferred.
