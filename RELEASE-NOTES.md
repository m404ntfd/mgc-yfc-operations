# CoastYouth Retail Checkout and Store Settings — v0.58.2

Selecting a product starts a sale and adds it to the receipt, including products with explicitly configured taxes when the store has no separate default rate. Open-price and weighed items ask for the required amount first; canceling leaves existing sale items unchanged.

## Checkout corrections

- Fixed the blanket receipt-and-tax setup warning that prevented imported products from starting a sale. Product tax selections, including non-taxable and zero-rate selections, are honored without inventing a store default rate.
- Taxable products or manual amounts without a configured tax remain blocked with instructions to select a product tax or confirm the store default in OFFICE.
- Fixed native DESK startup so the registered computer identity is resolved before loading the store catalog. Routine background connection checks no longer silently prevent a product tap.
- Price, quantity, discount, bundle and refund calculations retain the tax rates captured on each sale. Existing completed receipts are not recalculated.

- Standalone Server Admin reports 0.58.2 after installation so its startup update check recognizes that the current server package is already installed.

## Shared store setup

- Terminal setup shows the registered store and allows an administrator to select the store for a new checkout. Existing registered devices retain their assignment.
- Every checkout assigned to a store uses that store's catalog, taxes and receipt branding. OFFICE lists the store beside each terminal. Changing a terminal's store requires its open drawer and saved sales to be resolved first.
- Legacy receipt-only Thrift Mart profiles can read a previously confirmed shared tax rate without rewriting the saved profile.

## Install and preserve existing data

Update the existing Operations server to 0.58.2, then close and reopen DESK and OFFICE. These screens are delivered by the shared server; the native launchers remain DESK 1.18.0, OFFICE 1.15.0 and STORE OPS 1.4.0. Download the individual installers or Computer Setup for additional computers or reinstalling the clients.

Create and verify a fresh backup before installing. Finish transactions and save forms. Install over the existing application, retaining its data folder and connection settings. Do not uninstall or reset the database. Publishing this release does not restart or install anything on the live server.

No schema migration, catalog import, tax-rate assignment or operational-record rewrite is introduced by these checkout fixes. Timecards, open punches and breaks, reservations, attachments, completed sales, products, accounts, users, settings and terminal identities remain in the shared database. The Giving functionality and OFFICE status bar from the previous releases are retained.

Release verification includes product-tap and touch-screen flows, open-price and weight cancellation, multiple registers sharing a store, captured taxes and refunds, Windows/Linux tests, packaged assets, populated upgrade/backup/rollback, and Windows installer preservation checks.
