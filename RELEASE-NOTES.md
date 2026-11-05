# MGC YFC Operations 0.28.0

- Gives the standalone Remote Manager a YFC rings and TV-remote icon. The server keeps its rings and building icon; the web interface now uses that building artwork as its favicon.
- Organizes Settings into Application Settings and page-name categories. The subcategory row starts blank, fills when a category is selected, and shows only controls the signed-in user may access.
- Groups appearance, mobile layout, backups, updates, employees, login security and audit history under Application Settings; vehicles under Thrift Mart Dispatch; receipt codes and receipt review under Receipts & Accounting. Paging and Print with a Purpose have categories ready for future controls.
- Keeps automatic responsive mobile detection and adds Mobile View on/off overrides under Application Settings > Mobile View. The choice is remembered for the current browser/device.
- Shows Attempts Remaining Until Account Lock beneath failed-login errors, using the actual account limit. A successful login resets the count. Native administration also shows the remaining count.
- Combines local administration and offline restore with the server executable. The Administration tab requires administrator sign-in and connects only to this computer's server. Other computers keep the standalone Remote Manager.
- After an upgrade, the running combined server offers to remove obsolete standalone-manager executables and shortcuts. It never launches the shared suite uninstaller, and retains server files, databases and account configuration. Declining keeps the old manager.

INSTALL THE FULL WINDOWS INSTALLER on the server to receive the combined desktop application and native icons. Exit the existing server from its tray menu, run this installer over the same installation, select Server, then start MGC YFC Operations Server. Accept the optional standalone-manager removal prompt only when ready. Do not uninstall the server first. Refresh web browsers after installation.

The in-app update ZIP delivers the web and server API changes but cannot replace native desktop executables. Windows applications remain unsigned; code signing is still deferred.
