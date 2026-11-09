# CoastYouth Retail STORE OPS 0.49.0 / DESK 1.11.0 / OFFICE 1.8.0

- Thrift Mart and Binopoly have separate store profiles, terminal assignments, sales, item pricing, tax settings and receipt branding. Existing records remain associated with Thrift Mart without rewriting historical data.
- Sold-by-weight items prompt for manually entered pounds and calculate the pre-tax amount before Add to Sale. Digital scale integration remains a future hardware setup task.
- Optional cash-drawer reconciliation, gift certificates, scannable membership cards and birthday rewards are available in OFFICE and remain off by default. Loyalty can earn and redeem collectively or separately per store, with source tracking and refund protection.
- STORE OPS and OFFICE include donation performance and employee donation reports.
- OFFICE products can be marked “May require a pickup slip.” After successful payment, DESK offers the saved pickup/sold ticket set, then optional delivery scheduling. The split delivery window reuses the existing appointment form and calendar, starts with appointments minimized, and includes receipt/slip reprinting, loading pages and return to POS. Follow-ups can be resumed; retrying a saved delivery does not duplicate it.
- User and role administration is available within OFFICE, including shared role permissions, individual access, work assignments, profiles, PINs and login security. These configuration menus are removed from STORE OPS. Existing accounts and permissions remain shared; staff self-service stays available.
- Reports have branded headers with the configured store logo/name, report title, date range, scope, section bars and alternating detail rows. Print/PDF layout supports repeated table headings and wide reports. Combined reports identify All stores; labor reports identify the shared staff directory.

Update the existing server first, then DESK and OFFICE. The Computer Setup installer includes all three applications and lets you choose the computer's role. Existing installation IDs and data locations are unchanged. Credit cards will be added in future updates.

Existing timecards, open punches and breaks, reservations, attachments, sales, users, settings and account histories are retained. Database changes are additive and historical sales remain immutable. Release validation covers populated upgrade, backup, repeated startup, rollback and Windows installer preservation checks.

Create and verify a current backup before installing. Keep the existing installation and data folders. Publishing makes the downloads available; it does not install updates on store computers.
