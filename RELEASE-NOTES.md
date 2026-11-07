# MGC YFC POS 1.0.1 + Operations 0.39.5

POS now opens in a full-screen Windows window without standard minimize or close buttons. Exit POS requires the checkout computer's administrator passcode and refuses to close while work is unfinished.

- First-use setup requires an Operations administrator to set a 6–12 digit exit passcode before checkout is available.
- Administrators can change the passcode under POS setup / Checkout computer. Approval is verified by Operations; only a salted hash is stored locally.
- Time Clock, Reservations, and Paging stay inside the protected window, with Return to POS and Exit POS controls.
- Cash checkout, saved carts, sales history, and existing employee permissions are retained. Credit cards will be added in future updates.
- No timecard or reservation migration is required. Existing records, attachments, open punches/breaks, and audit history are preserved.

## Install in this order
1. Make a complete backup of the existing Operations server. Allow staff to finish and save their work.
2. Update Operations to **0.39.5** using its in-app updater, or exit the server and run **MGC-YFC-Operations-Setup-v0.39.5.exe** over its existing installation folder. Do not uninstall the server or delete its data folder.
3. Close the old POS and install **MGC-YFC-POS-Setup-v1.0.1.exe** on each checkout computer using the same Windows account. Existing server connection settings are retained.
4. Open POS and sign in as an Operations administrator to set the exit passcode.

Microsoft Edge WebView2 Runtime is required on checkout computers. This release provides application-level full-screen protection; restricting Windows shortcuts and switching to other programs requires separate Windows kiosk configuration.

Passcode settings are stored under `%APPDATA%\MGCYFCPOS\settings.json`, separately from the Operations database. Preserve this file during future POS upgrades. Setup is per Windows account on each checkout computer.

Validation includes native WebView2 setup/exit/navigation tests, browser checkout and retry tests, administrator authorization and lockout checks, installer checks, and populated upgrade/backup/rollback checks for historical/open timecards, breaks, reservations, attachments, and audits. Release packages contain no production data.
