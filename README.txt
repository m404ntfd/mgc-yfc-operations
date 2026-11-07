THRIFT MART DISPATCH SERVER — 0.7.0

Use MGC-YFC-Operations-Setup-v0.7.0.exe for a normal installation. Choose Server,
Remote Manager or Both. The installer includes the required Python runtime.
Open MGC YFC Operations Server from the Start menu. Minimize or click X to keep it running in the system tray.
First setup: http://localhost:8080 on the server PC. Create the administrator,
then add vehicles and employees. Phones use the staff-network address printed
in the server window. Allow the server on a trusted PRIVATE Windows network.

ONE DRIVE
Sign into OneDrive on the server. Settings > OneDrive backups & recovery lets
an administrator select a full LOCAL OneDrive folder path on the SERVER PC.
Enable hourly backups, save, and click Back up now to test. Latest 90 complete
ZIPs are retained. Backup includes schedule, accounts, vehicles, audit history,
GitHub repository setting and backup settings. Password hashes are included.
The program confirms a local save only. Confirm OneDrive has synced the file.
Failures and last-save information appear in Settings. Automatic backups run
only while the server is running; offline OneDrive uploads later when connected.
Do not place the live data folder itself in OneDrive.

RESTORE
On a replacement PC install Server, download a backup ZIP from OneDrive, and
choose Exit server from the truck tray menu. Open Restore MGC YFC Operations Server from the
Start menu. Select the ZIP. Existing data is preserved in data/restore-safety.
Start the server, sign in using an account from the backup, then reconnect and
enable the new OneDrive backup folder. Restore disables automatic cloud backup
until you reconnect the folder to avoid writing to an old PC's path.

DATA AND UPDATES
Current data: data/schedule.db. Other settings: data/updates.json and
 data/backup-settings.json. Do not delete these during a program upgrade.
Administrator Settings > Program updates installs GitHub server updates.
Remote Manager can also initiate updates. Everyone signs in again after restart.
Use the unified installer again to update the Remote Manager or launcher.
Built-in code updates preserve installed launcher files and all customer data.

LOCAL NETWORK ONLY
Local HTTP is unencrypted. Use a trusted staff network, not guest Wi-Fi or the
Internet. Do not port-forward 8080. Server must remain powered on and awake.
Optional startup occurs after Windows sign-in; this is not a Windows service.
Remote Manager cannot power on the server or launch a stopped server.

SOURCE USERS
Python 3.11+ with the standard library can run launcher.py directly. The Windows
installer bundles Python, so installed users do not need to set that up.
The legacy Start-Store-Dispatch.bat remains an alias for the renamed launcher.

PASSWORDS
Administrators can change passwords in Settings > Employee accounts, or using
Change a user's password in Remote Manager. Both password entries must match.
The selected user is signed out everywhere. No password is recorded in the log.

UPDATE BUTTON
Use Update server in the administrator navigation, or open Manage or Update
MGC YFC Operations Server from the Start menu for local administration.

TRAY
Double-click the white truck tray icon to show the server window. Right-click for
Open schedule, Manage / update server, and Exit server. X only hides the window.
Exit server stops scheduling after confirmation. The installer must be run once
to install this desktop host; code-only updates do not add executable files.

COMMAND WINDOW
Use MGC YFC Operations Server Console from the Start menu or a startup .bat.
The real command window uses the truck icon. Minimize sends it to the tray;
double-click the tray icon to restore. Its X is disabled; use tray Exit server.
The normal graphical Server shortcut is still available as an alternative.


PHONE / MOBILE SCHEDULE
After updating the running server to 0.8.0 or later, connect phones to the same staff Wi-Fi and open http://SERVER-IP:8080/mobile (use the network address shown in the server window). Sign in with an existing employee account. Create the first administrator locally on the server if needed, then add vehicles and employee accounts in Settings.
The phone view shares the same live schedule: add Pickup or Delivery, choose date/time and vehicle, enter customer/address/items, edit or remove appointments, search, and filter by vehicle/status. Call and map buttons open the phone's dialer/maps website. Maps require internet access. Updates refresh every 10 seconds and when returning to the browser. Unsaved form entries are not shared. If connection is lost, a warning appears; no offline saving is supported.
Bookmark /mobile or use the phone browser's Add to Home Screen option. No phone app or Remote Manager installation is required. The Windows server must stay awake and running. Use staff Wi-Fi with local device access (guest networks may block it). Allow the server's TCP port through Windows Firewall on the private store network if needed; do not expose it to the public internet. This is for local-network access; road access is not configured.

Version 0.8.1 appointment forms require a phone number and split addresses into street/city/state/ZIP. Select one or several employees from the checkbox dropdown. Existing free-text addresses and assignments remain intact; older addresses need their city/state/ZIP completed when edited. Remote Manager → Manage employees adds/removes employee accounts; removing an employee revokes their sessions but preserves appointment history. Install the 0.8.1 unified installer on Remote Manager PCs for that native feature; server update alone updates the browser and backend.

Email reports: In Reports, select filters and choose Email report. Review the preview and open your email app to choose recipients and send. For long reports, download the full text report and attach it manually. Email is sent by your own email app, not the dispatch server.

Cloudflare Tunnel: run cloudflared on the dispatch server and route operations.coastyfc.com to http://localhost:8080 (or the configured port). Preserve the original Host header. Only loopback connectors may supply X-Forwarded-Proto: https; HTTPS cookies are Secure and requests must match the exact external origin. Keep the hostname protected with Cloudflare Access staff policies. Do initial administrator setup locally before publishing. Install server updates through the local address if external login reports Invalid origin.


STORE-CREDIT ACCOUNTS (POS 1.2.0 / Operations 0.39.7)
Open Accounts from the POS action buttons. Search customer and employee accounts,
filter by type, and select an account to view its balance and full paginated history.
Create accounts at zero balance, then add credit with an adjustment reason/reference.
Employee accounts use existing stable employee identifiers; payroll and timecards
are not changed. One store-credit account is allowed per employee.
The role permissions "Look up accounts and redeem store credit" and "Create
store-credit accounts and adjust balances" control access separately.
Payments may use store credit alone or store credit plus cash. Change is paid only
from the cash portion. Negative balances are rejected. Adjustments and payment
history cannot be rewritten or deleted; corrections use a new offsetting adjustment.
If a connection interrupts a payment, use Retry / check last action. Do not start a
second payment: the original request is retained to prevent duplicate deductions.
New account tables are additive. No production records are bundled or modified.
Unfinished sales remain saved carts, separate from customer/employee credit.
Credit-card processing remains reserved for future updates.

SERVER SOFTWARE UPDATES
The server window groups Operations/server updates, POS updates, and the full
server/controller installer download. The in-app Operations update refreshes
server web software; use the full installer in the existing installation folder
to update the Windows server/controller executables. Update Operations before
POS when installing this accounts release. POS updates retain the configurable
warning countdown and block installation while a sale or unsaved form remains.
