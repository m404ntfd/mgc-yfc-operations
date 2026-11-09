# CoastYouth Retail STORE OPS 0.48.0 / DESK 1.10.0 / OFFICE 1.7.0

- DESK adds thrift checkout tools: color-tag discounts, donated-item barcode entry, voluntary round-ups/custom donations, customer rewards and sold-item pickup slips.
- OFFICE adds color schedules and category exclusions, donation and loyalty rules, customer profiles with separate marketing consent, assistance vouchers, fulfillment tracking and thrift reports.
- Donation intake creates individually tracked catalog items with printable Code 39 price tags and inventory age. Checkout prevents duplicate sales; returned items require inspected restocking.
- Assistance vouchers reuse the existing store-credit ledger with category and expiry restrictions. Returns restore the original account. Loyalty balances are checked at payment and corrected on partial returns.
- Donation lines remain separate from merchandise metrics and cash-change rounding. The customer display shows an optional donation invitation. Merchandise returns cannot reverse donations.
- Sold slips retain receipt references, storage locations, due dates and fulfillment history. Delivery scheduling remains in STORE OPS; enter its appointment reference on the slip.
- Reports include tag performance, donations, voucher redemptions/balances, issued rewards and outstanding pickups, with Print / Save PDF.

Update the existing server first, then DESK and OFFICE. All programs continue using the same server and existing data. New programs are disabled until configured in OFFICE. Barcode scanner and label-printer hardware selection/setup will be reviewed separately; no device drivers or printer assignments are changed. Credit cards remain planned for a future update.

Existing installation IDs, data locations, users, timecards, reservations, sales, settings and credit histories are retained. Schema changes are additive; historical sales remain immutable. Release checks exercise populated upgrade, backup, repeated startup, rollback, attachments, open punches/breaks, refunds, permissions, retries, duplicate-sale protection and actual Windows installer upgrades.

Create and verify a current backup before installing. Keep the existing installation and data folders. Publishing makes downloads available; it does not install updates on store computers.
