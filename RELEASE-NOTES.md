# CoastYouth Retail 0.43.0

DESK 1.6.0 and OFFICE 1.3.0 add receipt customization, reservation messages and a customer checkout display.

- OFFICE receipt design supports a PNG/JPEG logo, contact details, return policy and footer with a live preview. New completed sales retain a receipt-design snapshot for reprints; historical sales remain unchanged.
- OFFICE reservation emails supports Google Workspace/Gmail confirmation and reminder templates, per-reservation enrollment, configurable reminder timing, previews and delivery history. Delivery is disabled by default and requires a server-side Gmail app password. No customers are automatically enrolled. Canceled and past reservations suppress pending messages. Uncertain delivery requires review before retrying.
- DESK can pair a customer-facing browser display showing current items, totals and a thank-you screen. Pairing is scoped to the cashier connection, and disconnected screens clear transaction details.
- Existing open pricing, themes, store credit, refunds, cash rounding, terminal setup and layout editing remain included. Credit-card processing remains a future update.

All database changes are additive. Existing timecards, punches, breaks, audit history, reservations, identifiers and attachments are preserved. Release gates exercise populated upgrade, backup and rollback behavior, plus installer preservation checks.

Before installing, verify a current backup and have staff finish their work. Update the existing Operations server first using its current data location, then DESK and OFFICE with the same server address. Do not create a replacement server or restore an older database. Publishing does not install the update on store computers.

Gmail delivery remains off until configured. Set COASTYOUTH_GMAIL_APP_PASSWORD for the Windows account running the server, restart that server process, and configure the matching sender in OFFICE > Sales > Reservation emails. Review enrolled reservations before enabling delivery. Live email delivery depends on your Google account policy and has not been tested with customer credentials.
