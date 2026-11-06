# MGC YFC Operations 0.39.1

- Adds an administrator-only Connections before updating panel showing signed-in connections, recent activity, and whether the server is still seeing each connection.
- Blocks updates while other signed-in connections remain, including idle connections, unconfirmed connections, other tabs, and active Time Clock PIN sessions.
- Rechecks connections on the server immediately before staging an update. A new login after the screen was checked cannot bypass this protection.
- Disables installation when connection status cannot be confirmed. Connection status refreshes automatically and can be refreshed manually.
- Preserves existing timecard and reservation records. This release introduces no database schema changes; connection tracking is kept in memory.

Save work and sign out or close other application tabs before installing. The panel does not inspect unsaved form contents; check guest/kiosk activity separately. The administrator installing the update should save their own work first.

For this first upgrade from 0.39.0, coordinate with users before installing: the new connection protection becomes available after 0.39.1 is installed.
