# MGC YFC Point of Sale 1.0.0 + Operations 0.39.4

Introduces a separate Point of Sale application and installer, backed by the existing Operations server. Operations remains version 0.39.4; POS is version 1.0.0.

- Separate POS sign-in and checkout window, with its own Windows shortcut.
- Permission-controlled access to Time Clock, Reservations (pickup/delivery scheduling), and Paging in Operations. Saved carts remain in POS.
- Catalog and manual items, saved carts, cash tender/change, printable receipts, immutable sales history, and manager setup.
- Credit card areas display: **Credit cards will be added in future updates.** No card processor is enabled.
- Duplicate-request protection, cart revision checks, and safe-update acknowledgement in POS.
- Additive POS tables preserve existing timecards, reservations, attachments, and audit history.

## Install
Update the existing Operations server to 0.39.4 first. Back up, exit the server, and install the Operations setup over the existing folder; do not uninstall or delete data. The verified in-app server update is also supported. Then install **MGC-YFC-POS-Setup-v1.0.0.exe** on checkout computers and enter the Operations server address. Use existing accounts; grant staff Point of Sale permissions. Configure the receipt name and actual tax rate before checkout.

This first release supports USD cash sales with one tax rate and per-line rounding. It does not yet include refunds/voids, discounts, inventory tracking, Clover catalog import, cash-drawer hardware integration, or offline checkout. Card payments are deferred. The latest 100 permitted sales are displayed; older records are retained.

Validated with browser checkout/retry tests, Operations navigation, update acknowledgement, permission checks, and populated upgrade/backup/rollback checks covering historical and open timecards, breaks, reservation attachments, and audit records. No production database is included in release assets.
