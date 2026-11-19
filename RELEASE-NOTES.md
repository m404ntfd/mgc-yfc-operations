# CoastYouth Retail Terminal Management — v0.61.0

OFFICE can remove a terminal from active use without deleting any of its history. The voluntary Youth for Christ donation round-up prompt now defaults to on for settings that have not been configured.

## Terminal removal and retained reporting

- Open OFFICE → System → Checkout & printing → Terminals and select Remove beside the terminal. A confirmation explains what changes and which records are retained.
- Removing a terminal disables its checkout and customer display and removes it from active terminal choices. Complete or cancel its open/saved sales and reconcile its open drawer first.
- All sales, receipts, cash advances, drawer activity, audit logs and report totals remain available under their original recorded terminal names. Timecards, reservations, attachments, users, product prices and other operational records remain intact.
- Authorized users can restore the terminal from Removed terminals with its previous store, layout, printer and device registration. Reconnecting or restarting the removed computer does not silently restore its checkout registration.
- Permission checks, revision checks and safe request retries protect terminal changes. Removal and restoration are recorded in the audit log.

## Donation round-up default

- At Pay now, DESK offers voluntary rounding up to the next dollar for Youth for Christ. The cashier and customer-display prompt match the cashier's current theme.
- Unconfigured donation settings default to on. An existing saved off preference remains off; it can be changed in OFFICE → Customers → Rewards & programs → Color tags, donations & loyalty → Donations.
- A donation is added only after the customer agrees. No leaves the sale unchanged. Donations remain separate, nontaxable receipt lines. Cash-change rounding is a separate setting and is unchanged.

## Installation and data preservation

Versions: Server / Computer Setup **0.61.0**, DESK **1.20.1**, OFFICE **1.17.0**. STORE OPS desktop **1.5.2** remains compatible and is included in Computer Setup.

Verify a current server backup, let staff finish/save their work, and update the shared server first. The server supplies these screens and settings to the applications. Then update or reopen OFFICE and DESK. Install over the existing applications and retain their data folders and connection settings.

The update adds a separate terminal-removal status table. It does not reset, delete or rewrite historical business data. Publishing does not itself install or restart the live server; its configured update policy remains in effect. The operations web app remains available.

## Verification

Checks cover before/after reporting equality, preserved sales and original audit entries, open and held sale guards, open drawer guards, permissions, outdated requests, safe retries, terminal restoration, native registration status, and the default round-up prompt. Existing checkout workflows and 20 rendered theme/mode combinations are also checked.

Release checks include a populated upgrade from **0.60.0**, verified backup, repeated startup and rollback, with historical records, open punches and breaks, reservation attachments and original identifiers preserved. Windows installer checks cover install/reinstall behavior without changing existing data files.
