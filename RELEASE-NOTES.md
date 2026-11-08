# CoastYouth Retail 0.41.0 release

DESK 1.4.0 and OFFICE 1.1.0 add shared terminal layouts and the retail workflows reviewed with the owner. Computer Setup offers Server, OFFICE, POS and Custom installation choices while retaining existing component installation IDs and paths.

- OFFICE layout editor, shared terminal registration and server terminal-administration shortcut.
- Required item choices, priced add-ons, fixed-price bundles with component tax allocation, scheduled availability and promotions.
- Held-sale search and permission-controlled transfer; manager-approved fixed/percentage adjustments and cancellation reasons.
- Receipt-based full/partial refunds with a configurable 30-day default window, original cash/store-credit allocation and duplicate-return protection.
- Optional nearest-five-cent rounding of cash change; OFF by default. Prices, tax and store-credit amounts remain exact. Receipts and reports show rounding separately.
- Catalog CSV preview/import/export, common product changes, printing categories and sales/refund reports. Printing uses the staff-selected destination in the print dialog.
- Separate permissions for adjustment approval, held-sale transfer and refunds. Initial discount/surcharge limits are 20%/10%, editable in OFFICE; promotional stacking is excluded by default.

Existing timecards, open punches/breaks, reservations, identifiers, attachments, credit balances and original receipts are retained. Migrations are additive. Isolated populated upgrade, backup, repeated-startup and rollback checks are included in release validation.

Update the existing server first, then DESK and OFFICE. Keep the current server folder/data location and use the same server address in each client. Make and verify a current backup before updating the live server. Publishing this release does not install it automatically on store computers.

Credit-card processing remains a future update. Optional Windows computer renaming requires administrator approval and a later restart; it is never performed automatically. Renaming a server may require updating saved client addresses.
