# CoastYouth Retail Register Shifts — v0.65.0

DESK now uses **MORE → End Shift** to close the register for every cashier on that terminal. It displays completed transactions, open transactions and amounts due. Manual closing is blocked until all live open/saved transactions on that terminal are completed or canceled. Employee timecards are separate and are not clocked out.

The server automatically closes register shifts at the configured end of business day, default **23:59:59 Central time**. Unpaid open/saved transactions become **$0.00 voids with no payment collected**, retained with their original items, amounts, cashier and terminal in the closing business day's shift report. Paid receipts, inventory deductions, credit balances and loyalty awards are never fabricated for those voids. Closing catches up after a server restart; retrying a close or a payment does not duplicate it. Training transactions remain separate.

In **OFFICE → Sales → Register closing → Register shifts & business day**, configure the per-store closing time and default report paper. Open shifts keep the closing time captured when they started; changed settings apply to the next shift. Business dates are the dates of scheduled closing times in America/Chicago, including daylight saving changes.

**OFFICE → Reports → Sales analysis → Register shift reports** provides retained terminal shift summaries and transaction detail. Reports show store branding, cash and store-credit receipts, refunds processed at the terminal, employee cash advances, cash rounding and unpaid void history. Print to Letter (8.5 × 11) using the print dialog, or from DESK to its configured receipt printer. Cash counts and opening floats remain in the existing optional cash-drawer reconciliation feature. New shift tracking begins with this update; historical paid receipts remain in their existing reports.

The Register navigation icon is now a verified connection indicator. Defaults: check every **10 seconds**, yellow after **20 seconds** without a successful check, red after **30 seconds**, or immediately when Windows reports disconnection. OFFICE can change these timings under **System → Computers & versions → Register connection indicator**. Checks do not replay transactions or count as staff activity. DESK's header buttons are also aligned and equally tall.

## Installation and automatic updates

- Server / Server Admin / Computer Setup: **0.65.0**
- DESK: **1.23.0**
- OFFICE: **1.20.0**
- STORE OPS desktop: **1.6.1** (unchanged launcher; server supplies current screens)

Update the shared server first, then DESK and OFFICE. This release is offered through the existing update checks, server update schedule, and OFFICE computer-update controls. Publishing does not immediately force an installation or change the current update-consent rules. Older clients with a certificate error may require the browser-downloaded installer once; certificate and checksum verification remain enabled.

The all-in-one installer retains application identity, terminal registration, server address and settings. Install over the existing version; do not uninstall or remove application data.

## Data integrity and checks

Migrations add shift/settings/audit tables. Existing sales, timecards, open punches and breaks, reservation records and attachments, users, store credit and other operational data are retained. The requested automatic close changes only unpaid carts to discarded status, retains their original body, and writes an immutable $0 void snapshot and audit record. Existing paid receipts are never rewritten. Terminal removal retains historical reports.

Checks cover all-cashier manual blocking, idempotency, exact closing-boundary payment retries, restart catch-up, store/terminal isolation, terminal transfers, training separation, immutable void history, daylight saving transitions, settings permissions, print routing, Letter/receipt layouts, theme contrast, connection failures/recovery and preserved carts. Populated 0.64.1 upgrade, backup, repeated startup and rollback checks verify retained records and attachments. Receipt print routing is tested with a printer stub; no physical receipt printer is attached to the test computer.
