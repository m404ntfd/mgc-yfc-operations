# CoastYouth Retail DESK 1.3.0, OFFICE 1.0.0, Operations 0.40.0

Install Operations/server 0.40.0 first in its existing installation folder. Then update DESK using its existing installation folder and install the separate OFFICE application. Connect both clients to the same existing Operations server.

- Separate DESK checkout and OFFICE configuration applications, each with its approved blue or orange icon.
- Products/groups, receipts/taxes, account administration, shared users/roles, and update controls are managed in OFFICE. DESK retains checkout, protected Exit, time clock, reservations, and paging.
- Users created in OFFICE or Operations share one directory and permissions; no duplicate employee database.
- First-time DESK admin passcode setup is retained. Administrators can change the local checkout passcode in OFFICE on that same Windows login and server; running DESK reads the updated protection before exiting.
- The server tray icon now uses three red rings and a computer.
- Credit cards will be added in future updates.

Existing timecards, open punches/breaks, reservations, attachments, audits and store-credit accounts stay in the existing server data directory. No reset or data relocation is required. The release includes upgrade, backup/rollback, checkout, native client and installer preservation checks. Before installing, finish active transactions and create a current server backup. Do not uninstall or delete the existing data folder.
