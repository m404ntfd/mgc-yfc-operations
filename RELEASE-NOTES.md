# CoastYouth Retail DESK Checkout — v0.64.0

DESK now opens Thrift store tools as large green popup buttons, matching Credit/Advances. The menu gives access to customer lookup and creation, donated-item scans, color tags, donations, rewards, sold-item pickup slips, and the existing STORE OPS pickup/delivery area. Existing feature settings and user permissions still apply.

- An active sale shows **Loyalty customer** immediately below **Cancel sale**. Cashiers can select an existing customer or add a profile without opening Thrift store tools.
- Staff with **Manage store credit** permission can create customer/employee credit accounts and add or subtract credit through DESK’s green **Store credit** button. Adjustments require a reason and retain the existing account history, revision checks and audit records.
- Operations opened inside DESK has a red **Return to DESK / Exit POS** bar. It is absent from ordinary browser and standalone STORE OPS sessions. Saved-cart navigation and the protected exit remain in effect.
- Completed sales print automatically to the register’s configured printer. If automatic printing has no configured printer, an **Okay** notice lets the cashier continue without paper; the paid transaction and receipt remain saved.
- After printing or acknowledging that notice, DESK returns to a blank receipt area. The default is **5 seconds**. Configure **OFFICE → Sales → Checkout buttons → Receipt printing & next sale** for each store (1–300 seconds).
- The countdown pauses during open tasks, printing and pickup/delivery follow-up. It stops when another sale starts or a different receipt opens. Printer failures retain the receipt and show an error for deliberate reprinting. Print last receipt and Print receipts retain access to saved sales.

## Installation

Server / Computer Setup **0.64.0** includes DESK **1.22.0**, OFFICE **1.19.0**, and STORE OPS desktop **1.6.0**. The desktop launcher versions are unchanged; the shared server supplies these screens and checkout changes.

Verify a current backup and allow staff to finish or save their work. **Update the Operations server first**, using its existing installation and data folders. Close and reopen DESK, OFFICE and STORE OPS, or refresh browser tabs. Existing clients do not need reinstallation for these changes.

No database schema changes, resets or replacement of operational records are involved. The new store-specific timing setting defaults to five seconds without rewriting old records, and older settings clients preserve a previously configured delay. Existing sales, timecards, breaks, reservations, reports, users, credit balances, attachments, settings and terminal registrations remain in the shared data source. Publishing does not itself install or restart the live server.

## Verification

Isolated browser checks cover touch targets at 1920×1080, 1366×768 and 1024×768 in Classic Gray, Midnight and Glass Blue; customer assignment; permitted credit management and restricted-user controls; missing-printer acknowledgement; automatic printing; receipt timing; open-task pauses; preservation of a newly started sale; and the DESK-only return bar. Existing checkout, training, pickup/delivery and credit workflows are rechecked.

The release process verifies populated **0.63.1 → 0.64.0** upgrades, backups, repeated startup and rollback, plus repeated Windows installation without replacing operational data or client settings.
