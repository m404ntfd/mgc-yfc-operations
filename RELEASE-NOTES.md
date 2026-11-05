# MGC YFC Operations 0.22.0

- Renames the Windows Server, Console, Remote Manager, installer and shortcuts to MGC YFC Operations. The scheduling section remains Thrift Mart Dispatch.
- Prompts each employee to choose a permitted starting page once per server calendar day.
- Verifies full pickup/delivery backups, including photos and history. Archives eligible completed/canceled records after 30 days into Dispatch Journal beneath the configured backup folder. Reports and complete restores include archived history.
- Preserves installation identity, data paths, accounts, settings, instance locks and update ZIP compatibility.

Run the new Windows installer over the existing installation to update desktop programs and shortcuts; the in-app code updater alone does not replace desktop executables. Existing startup and shortcut targets remain supported. Do not uninstall or move the data directory.

The repository is now m404ntfd/mgc-yfc-operations. Release and update links use the new name; GitHub redirects existing repository links. OneDrive must finish syncing; Files On-Demand is needed to reclaim space occupied by synced archives.
