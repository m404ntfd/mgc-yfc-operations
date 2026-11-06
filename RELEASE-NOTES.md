# MGC YFC Operations 0.39.3

- Adds live active/inactive connections to the native server Administration panel. Excludes the always-running local server controller from user counts.
- Defines activity by user interaction, with a five-minute default timeout configurable in Application Settings → Connection Activity. Background polling does not keep a user active. Inactive connections no longer block updates.
- Adds coordinated update notifications to both browser and native-controller entry points. Users can finish work, minimize the notice, and acknowledge when leaving their page. Completion is reported after restart.
- Adds a trusted local-server administrator override for stuck updates, with a warning about unsaved work and an audit entry. Remote/browser callers cannot use it. Verification, backup, and rollback still apply.
- Automatically saves valid shift edits and safely retries lost responses without duplicate shifts. Fixes saved forms incorrectly remaining marked unfinished.
- Preserves existing timecards, reservations, attachments, audit history, accounts, and roles. Changes to storage are additive metadata/settings tables.

Use the full Windows installer for this release to update the server program and its embedded controller. Exit the server using its tray menu, run the installer over the existing installation, and restart. Do not uninstall or remove the data folder. Inactive sessions and forced updates may lose unsaved work; save or coordinate with users first when possible.
