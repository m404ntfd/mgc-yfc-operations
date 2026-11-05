# MGC YFC Operations

[Download the single Windows installer](https://github.com/m404ntfd/mgc-yfc-operations/releases/latest)

The installer offers **Server**, **Remote Manager**, or **Both**, with the required runtime bundled. Windows x64; no separate Python installation needed. It installs for the current Windows user.

## Store computer: Server

Choose **MGC YFC Operations Server**, then open its white-truck Start-menu shortcut. The server runs in a desktop window and can be minimized to the system tray. On that PC visit `http://localhost:8080` to create the first administrator. Add vehicles and employees in Settings. Phones use the staff-network address printed in the server window.

## Communications Hub

After signing in, open **Communications Hub** in the section menu. Use **New message** to find someone on the team, or **Create group** to start a conversation with several people. Messages, saved items, and files stay on the store server. Only conversation members can view its messages and download its files (up to 3 MB per attachment).

New messages show an unread indicator and an alert inside the signed-in app. Mobile notifications are on by default. At first sign-in on a supported phone, tap **Allow notifications** to open the device permission prompt. You can turn mobile notifications off in **Communications Hub → Preferences** or use **Enable notifications on this device** there if you skipped setup. On desktop, enable notifications from the same Preferences screen. Keep **Show new message alerts** checked. Repeat on each computer or phone. Use the HTTPS staff address on remote devices. On iPhone or iPad (iOS/iPadOS 16.4 or later), add the site to the Home Screen and open it from its icon before enabling notifications. Supported desktop and Android browsers can also receive notifications after the app tab closes.

Servers upgrading from an installation without Web Push need the full Windows installer. The server needs outbound HTTPS to the browser's push provider. Notifications contain a generic alert, and opening one takes staff to Communications Hub after sign-in. Signing out turns off push for that browser. For a source checkout, install the server dependency with `python -m pip install -r requirements-push.txt`.

Manage staff accounts and reusable permission sets in **Settings → Application Settings → Users**. Use the **Users** tab for accounts or the **Roles** tab for permission sets.

## Other computer: Remote Manager

Run the same installer and select **MGC YFC Operations Remote Manager**. Enter the server IP/computer name and port (for example `192.168.1.50:8080`), test the connection, and sign in with a server administrator account. The native panel manages status, complete backups, restart and GitHub server updates. Schedule/account editing opens in the default browser and requires a separate browser sign-in.

## OneDrive backup

On the server, sign into OneDrive. In **Settings → OneDrive backups & recovery**, enter a folder inside that computer's OneDrive (a suggested path appears if Windows provides one), enable hourly backups, save, and click **Back up to OneDrive now**.

Each ZIP contains the schedule database (appointments, accounts, vehicles and audit history), GitHub updater settings and backup settings. The latest 90 archives are kept. Backups run hourly while the server is running. Failures and the last local save appear in Settings. A local save does not prove cloud sync: confirm OneDrive shows the file synced. Copying live database files into OneDrive is not used.

## Recovery on a replacement PC

1. Install the Server with the same installer and sign into OneDrive.
2. Download a complete backup ZIP locally from OneDrive.
3. Choose **Exit server** from the truck tray menu. Open **Restore MGC YFC Operations Server** in the Start menu.
4. Select the ZIP and confirm replacement. Current data is kept in a local safety folder first.
5. Start the server and sign in using an account from the backup. Reconnect and enable the new PC's OneDrive folder in Settings.

## Existing 0.2 users

Use **Exit server** (or close the old console) and keep a separate copy of `data/`. Install the Server into the existing program folder, or copy `data/` into the new installation folder while the server is stopped. This one-time installer upgrade adds the launcher, renamed shortcuts and restore tool. Later server code updates can use Settings or Remote Manager; updating the Remote Manager/installer requires rerunning the latest unified installer.

The legacy update asset remains named `Store-Dispatch-Update.zip` for compatibility. Program code updates do not overwrite customer data. The uninstaller leaves runtime-generated data and external backups in place.

## Operating limits

Use trusted staff networking only; local HTTP is unencrypted. Do not forward the port to the Internet. Remote Manager cannot turn on a PC or start a stopped server. Keep the server awake; optional automatic startup occurs after Windows sign-in, not before. The installer is unsigned. OneDrive must be running and signed in to sync the backup folder.

Run `python -m unittest test_server test_updater test_remote` for API, update, access-control and backup/restore tests. CI also builds the Windows executable/installer, checks GUI startup and tests an installed server with bundled Python.

## Administrator password changes and server updates

Server interface: **Settings → Employee accounts → Change password**. Remote Manager: **Change a user’s password**. Select the user and enter/confirm the new password. This signs the affected user out on all devices; administrators changing their own password sign in again too. Passwords are never shown in the activity log.

The server navigation includes **Update server**, which checks GitHub and offers installation when a newer release is available. The Server install also adds a **Manage or Update MGC YFC Operations Server** Start-menu shortcut with native update controls pointed at localhost. If using a custom port, edit the address before connecting.

Use the unified installer to update Remote Manager itself; the server-update action updates server code only.

## Server tray behavior (0.6)

The white box-truck icon identifies the server on the desktop/taskbar and in the tray. Minimize, X, or **Minimize to tray** hides its window without stopping scheduling. Double-click the tray icon to reopen; right-click for schedule, management/update controls, or **Exit server**. Exit asks before stopping the server. If the icon is hidden, expand the taskbar's hidden icons.

Install the full 0.6 installer once to add the tray executable. The code-only updater does not replace desktop executables. Logs are under `data/server-console.log`. Tray operation still requires the Windows user to remain signed in and the PC to stay awake.

## Command-window tray support (0.7)

Use **MGC YFC Operations Server Console** in the Start menu, or the existing startup batch file. This opens a dedicated command window with the white truck icon. Minimizing it sends it to the system tray without stopping the server; double-click the tray icon to restore it. The console X is disabled; use the tray's **Exit server** command for safe shutdown.

The graphical **MGC YFC Operations Server** shortcut remains an alternative. Only one server mode can run at a time. The Console shortcut uses classic Windows Console Host without changing the system-wide Windows Terminal preference. A raw developer command such as `python server.py` does not use the tray host.


PHONE / MOBILE SCHEDULE
After updating the running server to 0.8.0 or later, connect phones to the same staff Wi-Fi and open http://SERVER-IP:8080/mobile (use the network address shown in the server window). Sign in with an existing employee account. Create the first administrator locally on the server if needed, then add vehicles and employee accounts in Settings.
The phone view shares the same live schedule: add Pickup or Delivery, choose date/time and vehicle, enter customer/address/items, edit or remove appointments, search, and filter by vehicle/status. Call and map buttons open the phone's dialer/maps website. Maps require internet access. Updates refresh every 10 seconds and when returning to the browser. Unsaved form entries are not shared. If connection is lost, a warning appears; no offline saving is supported.
Bookmark /mobile or use the phone browser's Add to Home Screen option. No phone app or Remote Manager installation is required. The Windows server must stay awake and running. Use staff Wi-Fi with local device access (guest networks may block it). Allow the server's TCP port through Windows Firewall on the private store network if needed; do not expose it to the public internet. This is for local-network access; road access is not configured.

Version 0.8.1 appointment forms require a phone number and split addresses into street/city/state/ZIP. Select one or several employees from the checkbox dropdown. Existing free-text addresses and assignments remain intact; older addresses need their city/state/ZIP completed when edited. Remote Manager → Manage employees adds/removes employee accounts; removing an employee revokes their sessions but preserves appointment history. Install the 0.8.1 unified installer on Remote Manager PCs for that native feature; server update alone updates the browser and backend.
