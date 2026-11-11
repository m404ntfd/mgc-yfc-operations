# CoastYouth Retail touchscreen DESK

Server 0.55.0 / DESK 1.16.0 / OFFICE 1.13.0 / STORE OPS desktop 1.2.1

## Changes

- Optimizes DESK for a 27-inch monitor at 1920 x 1080 and 100% Windows scaling. Product tiles, text fields, menus and payment controls have larger touch targets. Compact desktop layouts remain supported.
- Adds large Up / Down buttons for products, groups and receipt lines, wider scrollbar styling and separate scrolling areas while keeping totals and payment controls visible.
- Adds receipt quantity minus / plus buttons. Changes are saved on the server using the sale's original price, tax and item choices. Weight-based items, individual donated items, gift certificates and donations retain their existing restrictions. Held sales and applied adjustments/rewards keep their safeguards.
- Adds touch keypads for open prices, weights, manual item quantities and cash/store-credit amounts. Cancel leaves the original entry unchanged. An open keypad is treated as work in progress during update coordination.
- Starts a sale automatically when the cashier taps the first product. Open-priced items and weighed items prompt for the required information before a new sale is created. Existing saved sales are reused.
- Explains when an item was not added because the cashier canceled without entering a price or weight. Items already on the receipt remain unchanged. Interrupted saves can be retried without duplicating sales or items.
- Keeps touch controls readable across the existing color and liquid-glass themes, including the Exit POS button in the dark theme.

## Installation

Update the shared server to 0.55.0 first, then DESK to 1.16.0. DESK loads the register from the server, so the server update is required for these screens and quantity controls. OFFICE 1.13.0 and STORE OPS desktop 1.2.1 remain compatible; their installers are included in Computer Setup.

Use a verified server backup, finish active transactions and keep the existing server data folder. Existing desktop applications should remain connected to that same server. Publishing makes downloads available; it does not install them on store computers or restart the live server. STORE OPS remains available at its existing web address.

## Data preservation and verification

This release makes no database schema changes and does not import, replace or delete catalog data. Existing products, prices, taxes, departments, users, settings, terminal registrations, timecards, open punches and breaks, audit history, reservations, attachments, sales and account balances remain in the shared database. Quantity controls edit only the selected open sale when a cashier explicitly changes its quantity.

Checks cover mouse/touch checkout, price and weight cancellation, quantity/tax snapshots, bundles, refunds, interrupted-request retries, update coordination, printing and theme readability. The release workflow also checks a populated 0.54.0 upgrade, verified backup, repeated startup and rollback with isolated sample records, plus repeat installation over existing data and client settings.
