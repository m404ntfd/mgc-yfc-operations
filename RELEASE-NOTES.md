# CoastYouth Retail Combined Update — v0.58.3

This release combines all completed Giving and Retail work with the DESK screen-fit correction. It is the current update for the shared Operations server, OFFICE, DESK and STORE OPS screens.

## DESK touchscreen correction

- Fits the register within 1920×1080 at 100% Windows scaling. The top menu is now included in the available screen height, so receipt controls, scroll arrows and the Cash Advance button stay visible.
- Keeps the existing large touch buttons, product tiles, quantity controls and keypads. Long product lists and receipts scroll inside their own panels.
- Adjusts the workspace for window/taskbar space and the update warning banner.

## Combined Giving and Retail features

- Retains the Giving workspace in OFFICE: donor management and profile history, received gifts and audited corrections, monthly giving drafts and change history, saved statements and printing, delivery preparation/cancellation, and filtered gift history.
- Retains the OFFICE status bar and its theme contrast correction.
- Includes first-product-tap checkout, open-price and weight prompts with safe cancellation, product-specific taxes, and shared store catalog/tax/receipt settings for registered terminals from v0.58.2.
- Giving card processing, automatic recurring charges, donor self-service and automatic statement emails remain future development. Prepared statement deliveries are not automatically sent.

## Installation and existing data

Update the existing Operations server to **0.58.3**, then close and reopen DESK, OFFICE and STORE OPS. These screens are delivered by the shared server. The native launcher versions remain DESK 1.18.0, OFFICE 1.15.0 and STORE OPS 1.4.0; new copies of their installers are included for additional computers or reinstalls. Standalone Server Admin reports 0.58.3.

Create and verify a fresh backup before installing. Finish transactions and save forms. Install over the existing application and retain its data folder and connection settings. Do not reset or replace the database. Publishing this release does not install or restart the live server.

No database migration or operational-record rewrite is introduced by this update. Timecards, punches, breaks, reservations, attachments, sales, products, prices, taxes, users, donor records, accounts, settings and terminal identities remain in the shared data source.

Release checks cover Giving and checkout workflows, touchscreen controls and themes, Windows/Linux tests, populated upgrade from v0.58.2, backup/rollback, native applications and actual Windows installer data preservation.
