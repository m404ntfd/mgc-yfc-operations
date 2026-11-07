MGC YFC Point of Sale 1.0.0

INSTALLATION
1. Back up the Operations server before updating. Use its complete backup option,
   then Exit server and keep a separate copy of the existing data folder.
2. Install Operations 0.39.4 over the existing server folder, or use its verified
   in-app update. Never uninstall the server or delete its data folder.
3. Run MGC-YFC-POS-Setup-v1.0.0.exe on each checkout computer.
4. Open the separate MGC YFC Point of Sale shortcut. Enter the same Operations
   server address used by the browser, for example http://192.168.1.20:8080.
5. Sign in with an existing Operations account. Administrators have POS access.
   Grant staff "Use Point of Sale" through Operations role/permission settings.
6. An administrator or permitted manager must set the receipt store name and
   confirm the store tax rate in POS setup before the first sale.

The POS launcher also has a "Change POS server connection" Start-menu shortcut.
The POS uses Edge or Chrome in an application window when installed, otherwise
the default browser. It has a separate installer and shortcut; it uses the shared
Operations server for authentication and records, not a second store database.

VERSION 1.0.0
- Catalog items and manually entered descriptions, categories, prices and quantities.
- Server-saved carts, cash tender/change, receipt printing, recent sales history.
- Time Clock, Reservations and Paging open Operations in another window using
  the existing permissions. The POS cart stays saved. Reservations currently
  means the existing pickup/delivery scheduling screen.
- Sales are stored separately from timecards/reservations. Existing records are
  retained. Catalog contents are not automatically imported from Clover.
- Credit cards will be added in future updates. No card terminal is connected,
  and no card payments can be charged or recorded as completed in this release.
- USD only, one configured tax rate, rounded per line. Settings changes apply to
  new carts; saved carts retain their original rate. Configure actual store tax
  requirements before use. Complex tax rules, discounts, inventory quantities,
  cash-drawer hardware, refunds and voids are not included in this first release.
- Sales history displays the latest 100 sales accessible to the signed-in employee.
  The underlying records are retained. Managers can be granted all-sales access.

SAFE SAVING
An interrupted action retains its unique request in the checkout browser session.
Use "Retry / check last action" before attempting another action. Do not clear
browser storage to resolve an uncertain sale; inspect Sales history first.
Avoid signing out while an action is pending. Shared browser windows use the
same Operations sign-in; signing out affects those windows as well.

UPDATES
The POS takes part in Operations update notifications and acknowledgement.
Save/finish open fields before acknowledging. Saved carts remain on the server.
The configured inactivity timeout and native administrator override still apply.
The server must be available for checkout; offline cash checkout is not provided.
