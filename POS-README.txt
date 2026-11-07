MGC YFC Point of Sale 1.1.0

INSTALL
Back up Operations and let employees finish/save their work. Exit the server,
then install Operations 0.39.6 over the existing installation folder. Do not
uninstall or delete data. Close the old POS and install POS 1.1.0 under the same
Windows account on checkout computers. Existing exit passcodes and server
settings remain intact. WebView2 Runtime is required.

REGISTER
Large category and product buttons, right-side receipt, and checkout action rail.
Pay now expands cash payment. Catalog/manual items and server-saved carts remain
available. Credit cards will be added in future updates. Existing cash-only USD,
single-tax-rate and receipt behavior is retained; no refunds/voids are added.

UPDATES
Administrators: POS setup > POS application updates. The same controls are in
Operations settings and the server window's Update POS applications button.
Check for releases, choose one/all checkout computers, set warning seconds,
then Notify staff and update POS. Default warning: 120 seconds (30-3600 allowed).
Staff see a banner at the top. Finish or cancel the current sale and save all
entries, then acknowledge readiness after the countdown. The countdown cannot
force an unfinished transaction to close. New sales pause after the countdown.
The official installer is checksum-verified. POS closes only after the safety
check, then installs and reopens. Settings are backed up before replacement.
The administrator status list shows connected device versions and progress.
Cancel stops requests that have not yet entered installation.
POS 1.0.x requires this installer once; later updates can run from the application.

DATA AND EXIT PROTECTION
Timecards, reservations, attachments and audit records are preserved. No changes
to those records are required by this update. Do not delete the Operations data
folder or %APPDATA%\MGCYFCPOS\settings.json. That settings file holds this Windows
account's server address and salted exit-passcode hash. POS setup lets Operations
administrators change the exit passcode. Exit remains protected and blocks unsaved
work. Restricting Windows shortcuts requires separate Windows kiosk configuration.
If a sale response is interrupted, use Retry / check last action. Never clear app
storage to resolve an uncertain payment. Offline checkout is not provided.
