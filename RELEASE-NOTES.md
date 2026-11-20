# CoastYouth Retail Cash Entry — v0.62.1

After either **Yes, round up** or **No**, DESK puts the cursor in **Amount tendered** for cash payment. Cashiers can immediately type the amount received without clicking the field. Entering `2000` produces `$20.00`.

- The on-screen keypad returns focus to Amount tendered, so cashiers can alternate between touch and a physical keyboard.
- Quick-tender buttons and switching back to Cash leave the amount selected for replacement by the next typed amount.
- Tab navigation and selecting a store-credit account retain normal focus. Opening the payment window does not interrupt a cashier who has already started navigating or typing.
- Donation choices, cash rounding, payment totals, store-credit calculations and receipt contents retain their existing behavior.

## Installation

Versions: Server / Computer Setup **0.62.1**, DESK **1.21.1**. The compatible OFFICE **1.18.0** and STORE OPS desktop **1.5.2** remain included without a version change.

Verify a current server backup and let staff finish/save their work. **Update the shared server first, then restart DESK.** The shared server supplies the checkout screen; updating only the DESK launcher will not apply this screen change. The DESK installer is also provided for installations and reinstalls.

Install over the existing applications and retain their data folders and connection settings. This update changes no database schema or operational records. Sales, reports, timecards, reservations, users, settings and attachments remain in the existing shared data source. Publishing does not itself install or restart the live server; its configured update policy remains in effect.

## Verification

Release checks cover immediate physical-keyboard entry after both round-up choices on mouse and touch displays, mixed keypad/keyboard entry, method switching, Tab navigation, completed cash payments and receipt totals. Existing checkout checks cover partial store credit, interrupted-payment recovery, receipts and exit behavior.

The populated **0.62.0 → 0.62.1** upgrade check verifies backup, repeated startup and rollback while retaining original records, identifiers, historical and open timecards/breaks, reservations and attachments. Windows installer checks verify installation and reinstallation without replacing existing data or settings.
