MGC YFC Point of Sale 1.0.1

INSTALLATION
1. Make a complete Operations backup and let staff finish/save their work.
2. Update Operations to 0.39.5 first, using the in-app updater or installing over
   the existing server folder after exiting the server. Do not uninstall or
   delete the data folder. Existing timecards and reservations remain intact.
3. Close the previous POS, then run MGC-YFC-POS-Setup-v1.0.1.exe on each checkout
   computer using the same Windows account. Microsoft Edge WebView2 Runtime
   must be installed. The existing server address is retained.
4. Open Point of Sale. On first use, enter the Operations server address if needed,
   sign in as an Operations administrator, and set a 6-12 digit exit passcode.
5. Grant staff Use Point of Sale through Operations permissions. Configure the
   receipt name and actual tax rate in POS setup before the first sale.

FULL-SCREEN AND EXIT
The installed POS has no normal minimize/close controls. Exit POS requires the
admin exit passcode and blocks exit while work is unsaved. Ordinary close requests
open the protected Exit dialog. Administrators can change the passcode under
POS setup / Checkout computer. The passcode hash and server address are stored
in %APPDATA%\MGCYFCPOS\settings.json. Preserve that file during upgrades.
Setup is per Windows account on each checkout computer. Windows kiosk policies
are needed to restrict Windows shortcuts and switching to other applications.

OPERATIONS AND SALES
Time Clock, Reservations, and Paging open inside the protected window with
Return to POS and Exit POS controls. Permissions remain enforced by Operations.
Reservations means the existing pickup/delivery scheduling screen.
Catalog and manual items, server-saved carts, cash tender/change, printable
receipts, and sales history are available. Credit cards will be added in future
updates. No card payments can be charged or recorded as completed.
Cash sales use USD with one configured tax rate and per-line rounding. Saved
carts retain their original tax rate. Refunds/voids, discounts, inventory counts,
cash-drawer hardware, and Clover catalog import are not included. Sales history
shows the latest 100 accessible sales; older records are retained.

SAFE SAVING AND UPDATES
If an action is interrupted, use Retry / check last action before another action.
Do not clear application/browser storage to resolve an uncertain sale; inspect
Sales history first. POS participates in Operations update notifications.
Save/finish open fields before acknowledging. Saved carts remain on the server.
The server must be available for checkout; offline checkout is not provided.
No operational records are stored in the POS settings file. This update does not
reset, replace, or migrate timecards or reservations.
