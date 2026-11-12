# CoastYouth Retail Checkout Update — v0.58.4

This release brings the approved touchscreen checkout screens to DESK and the checkout-button editor to OFFICE. Existing STORE OPS, Giving and Retail features remain included.

## DESK checkout

- Open-price products open the keypad automatically. Okay adds the item directly, including required item options. Cancel explains that the item was not added and keeps all existing sale lines.
- Discounts/ Surcharges uses four sections: item discounts, transaction discounts, item surcharges and transaction surcharges. Choices come from OFFICE and retain existing approval requirements and policy limits. Each manual adjustment replaces the previous manual adjustment.
- Pay now opens a receipt preview alongside amount due, amount tendered, change, quick tenders and a large keypad. Cash is selected first; entering 1000 on the keypad means $10.00.
- Store credit can cover part or all of a sale. Cash rounding applies to the remaining cash amount only, and appears on the screen and printed receipt. Full store-credit payments use the calculated total. Existing saved carts and completed receipts retain their recorded rounding rules.
- Pay later saves the transaction. Find lets the cashier select and reopen a saved transaction. Product selection starts new sales; the New sale and Manual amount buttons are removed.
- Print receipts lists today's completed transactions for the store, with a receipt preview and print/email options. Email delivery requires enabled Gmail settings; credit-card processing remains marked for a future update.
- Cancel sale uses the store's configured cancellation reasons and retains transaction history.
- Thrift store tools opens barcode, tag, donation, reward and pickup-slip tools. Barcode and gift-certificate entry can start a transaction without a New sale button.
- Exit no longer treats dismissed forms as unfinished work. Unconfirmed payments remain protected, with safe status checking and recovery after reopening DESK.

## OFFICE configuration

Under Sales → Taxes & payment rules, open Checkout buttons & cancellation reasons. Administrators with Manage POS permission can add, copy, edit and delete per-store choices. Existing discount limits, surcharge limits, return rules and manager approvals remain enforced.

## Installation and data preservation

Update the existing Operations server to **0.58.4 first**, then close and reopen DESK and OFFICE. Their screens come from the shared server. The launcher versions remain DESK **1.18.0**, OFFICE **1.15.0** and STORE OPS **1.4.0**; this release includes fresh installer copies for new computers or reinstalls. Computer Setup and standalone Server Admin are **0.58.4**.

Create and verify a fresh backup and finish transactions before installing. Install over the existing application, retaining its data folder and connection settings. Do not reset or replace the database. Publishing does not install or restart the live server.

The database change adds a checkout-configuration table. Existing timecards, punches, breaks, audit history, reservations, attachments, sales, products, prices, taxes, users, donor records, accounts, settings and terminal identities are preserved. No existing operational records are rewritten to apply this screen update.

Release verification includes payment and refund accounting, duplicate-payment protection, payment recovery, store permissions, touch controls at 1920×1080, theme contrast, printed receipts, Windows/Linux tests, a populated upgrade from v0.58.3, backup/rollback and actual Windows installer data preservation.
