# Daily starting page and Dispatch Journal

This change is staged under the existing program and repository names. Do not perform the rename until the host's current pickup/delivery backup is verified and OneDrive has finished syncing it.

## Verify the current host before renaming

1. Ask staff to pause edits, then use Settings → Backups → Back up to OneDrive now.
2. Save `verify_dispatch_backup.py` in the server application folder. From that folder, run:

   `runtime\python.exe verify_dispatch_backup.py --backup "C:\full\path\to\the\latest-backup.zip"`

   If DISPATCH_DATA points outside the normal application folder, add `--data "C:\actual\data\folder"`.
3. The tool opens the live database read-only, takes a consistent temporary snapshot, checks ZIP/SQLite integrity, and compares each live appointment, revision, photo, and audit entry with the backup. It prints counts without customer information. A mismatch stops verification; create a fresh backup and repeat while edits are paused.
4. Confirm OneDrive reports that exact backup file as synced. A local file write or matching checksum does not prove cloud upload. Keep the verified backup through the rename.

## Daily page choice

The server's local calendar date controls the daily choice. Each employee chooses once per day, shared across their devices. Existing undated preferences prompt again. The page dropdown and popup use the same permitted sections. Staff can reopen the chooser from the menu. A receipt shortcut preselects Receipts & Accounting but does not skip the first daily choice.

## Retention and reports

Automatic hourly backups must be enabled. The additional archive option can be disabled in Settings. Entries stay active for at least 30 days after both their appointment date and last recorded change. Only Completed and Canceled entries are eligible; scheduled/in-progress, future, undated, and recently edited records remain active.

Before local removal the server creates a complete verified backup, writes an immutable SQLite archive under `<configured backup folder>\Dispatch Journal`, reads it back, and compares every selected entry, revision, photo, and audit row. It commits the archive index and local removals together, then compacts the active database. Failures before that transaction leave the active records intact. Journal files are never automatically deleted.

Reports merge journal history with active entries. Missing/damaged journal files stop the report with an error rather than showing an incomplete result. Every complete backup merges archived history into its database, so it can be restored without the separate journal files. Restored backups disable automatic backup until the location is reconnected.

OneDrive Files On-Demand is required to reduce the space occupied by synced journal files and full backups on the host. The application verifies local writes; it cannot confirm the OneDrive service's cloud upload or force cloud-only storage. Keep OneDrive running. Historical reports may need to download online-only files. Local rolling backups remain limited to 30 daily copies and full backups to 90 archives.

Changing the configured backup folder is blocked once journal files exist, until a separate verified journal migration is implemented. Do not manually move/delete Dispatch Journal.

## Rename after verification

Target repository: `mgc-yfc-operations`. Target desktop names: MGC YFC Operations Server and MGC YFC Operations Remote Manager. Installer, tray labels and shortcuts use MGC YFC Operations. The scheduling section remains Thrift Mart Dispatch.

Preserve the existing installer AppId, existing install/data location, schedule.db, DISPATCH_DATA override, instance locks, legacy backup format recognition and legacy update asset during the transition. Update executable references, shortcuts, startup entries, release workflow and updater endpoints together. Do not change the repository URL in deployed updaters until the repository rename/redirect is verified. GitHub repository rename requires repository administration access, which the current GitHub connector does not expose.
