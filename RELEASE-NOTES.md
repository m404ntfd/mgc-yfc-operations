# MGC YFC POS 1.1.0 + Operations 0.39.6

The POS register now has large color-coded category/product buttons, a right-hand receipt with visible totals, and a vertical checkout action menu. Bowling-lane tiles are not included. Cash checkout, saved carts, manual items, receipt printing, and administrator exit protection are retained.

## POS updates from the application
- Administrators can open **POS setup > POS application updates** to check releases, set the employee warning time, and request an update for one checkout computer or all connected POS computers.
- Operations settings includes **POS application updates**. The Windows server window has an **Update POS applications** button that opens the same administrator controls.
- The warning defaults to **120 seconds**, configurable from 30 to 3600 seconds. Each computer gets the full warning period when it receives the request.
- A top banner asks staff to finish their transaction. Expiring the countdown never forces a sale to close. Staff must finish or cancel the current sale, save unfinished entries, then acknowledge that they are ready. New sales are blocked after the countdown ends until the request is canceled or the update is completed.
- The native updater downloads the official stable POS installer and verifies its SHA-256 checksum, then rechecks authorization and unfinished work. A separate helper waits for POS to exit, backs up device settings, installs into the same folder, and reopens POS. Administrators can monitor connected device versions/status and cancel outstanding requests.
- An update canceled after an installer has already started cannot undo that installation. Disconnected devices are not reported as completed. Failed downloads do not close POS.

## First installation of this release
Existing POS 1.0.x installations need the **POS 1.1.0 installer once** to gain the native self-update capability. Later POS releases can use the new application update controls.

1. Make a complete Operations backup and let staff finish/save their work.
2. Exit the server and install **MGC-YFC-Operations-Setup-v0.39.6.exe** over its existing folder. This also adds the Windows server's new POS update button. Do not uninstall or delete the data folder. The in-app Operations update also delivers the web controls, but does not replace older native server buttons.
3. Close the existing POS and install **MGC-YFC-POS-Setup-v1.1.0.exe** under the same Windows account on each checkout computer. Keep existing connection/passcode settings.
4. Open POS. Existing exit passcodes are retained; first-time devices require administrator passcode setup.

No timecard or reservation migration is required. Operational records and attachments remain in the existing Operations database. POS update control settings are separate from that database. Credit cards will be added in future updates.

Microsoft Edge WebView2 Runtime is required. Windows-level kiosk restrictions remain separate from full-screen application protection.

Validated with browser/native POS tests, countdown/authorization/checksum and unfinished-sale tests, populated upgrade/backup/rollback checks, and Windows installer/data-preservation tests. Release assets contain no production data.
