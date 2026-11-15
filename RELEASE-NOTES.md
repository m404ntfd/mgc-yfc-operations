# CoastYouth Retail Training & Checkout — v0.59.0

This release includes the reviewed training, checkout, printer, customer-display and update-policy changes. Publishing these installers does not install or restart the live store server.

## Updates

- DESK, OFFICE and STORE OPS desktop check at startup and every hour. Available updates show a restart notice; there is no staff countdown, forced restart or background client installation. Restarting opens the verified installer offer, which the user can accept or defer.
- OFFICE keeps computer registration and installed-version inventory. Remote update controls are removed, and old rollout requests cannot start a client update.
- The shared server checks daily at 04:00 AM America/Chicago. A verified update is staged, committed writes are drained, and the launcher backs up and checks the database before applying the update and restarting. A failed check does not restart the server. The check window ends at 04:05; a server starting later waits until the next day.
- Open applications display the requested warning from 03:50 through 04:01 Central, including the instruction to remain out until 04:05. The warning does not acknowledge work or close forms automatically.

## DESK

- Staff PIN receives focus on sign-in; Enter submits it.
- Open-price input uses automatic cents: 1000 enters $10.00. Okay adds the item; Cancel keeps existing sale lines and explains that the new item was not added.
- Cancellation reasons appear as directly selectable buttons.
- The top receipt shortcut becomes the training-mode control. Active training has fading red status text and a red warning bar with a red/yellow indicator. Reduced-motion preferences are respected.
- Practice payments, customers and cash advances are recorded separately. They do not enter live sales, cash drawer events, account balances, inventory movements, loyalty points, pickup fulfillment or credit-card processing. Practice receipts are marked as training. OFFICE provides a separate training transaction report; cashiers can reprint their own practice receipts.
- Complete, save with Pay later, or cancel the current transaction before switching modes. Live and training saved carts cannot be mixed.
- Pay now stays red at the bottom right, beneath Pay later, receipt controls and Find. Credit/ Advances is a green menu containing store credit and employee advances, and closes when the user taps elsewhere.
- Appearance and permission-protected terminal setup move into Settings. Product groups, product lists and receipt lines retain scrollbars and support touch panning.
- Add customer opens a form and can send it to the assigned customer touchscreen. Submitted details return to the cashier for review and saving; the customer display receives no staff credentials or access to employee screens.

## Printers and customer displays

- Terminal setup in DESK and OFFICE stores the exact Windows receipt-printer name and a persistent, revocable customer-display link for each register.
- Display logos and store names use that location's receipt branding; welcome and thank-you messages are configurable per store.
- A completed payment automatically prints through the desktop's configured receipt printer. Viewing a historical receipt does not automatically print it. Duplicate automatic printing is suppressed, including uncertain delivery; deliberate manual reprinting remains available.
- Printer errors leave the recorded transaction intact and show a reprint message. A physical receipt-printer test is still required on the chosen hardware.

## Installation and preservation

Versions: shared server and Computer Setup **0.59.0**, DESK **1.19.0**, OFFICE **1.16.0**, STORE OPS desktop **1.5.0**. Update the shared server first, then the desktop applications, to enable the full behavior. Existing installation identifiers, data paths and terminal identities remain in place. Verify a current server backup before installation and install over the existing applications; do not delete their data folders.

Migrations add separate training, terminal-printing, customer-display and temporary-entry tables. Existing timecards, punches, breaks, reservations, attachments, sales, account ledgers, products, taxes, users and settings are not reset or replaced. Practice activity creates only practice records, related draft carts, idempotent request results and audit entries.

Checks use synthetic data. They cover checkout, training isolation, permission checks, payment replay, store credit, cash advances, receipt error recovery, customer-display isolation, touch layout/theme contrast and startup notices. The populated upgrade test from 0.58.4 verifies exact preservation, backup integrity, repeated startup and rollback. Publication is gated on Windows installer builds, installation and reinstall preservation checks, and the application regression suites. Physical receipt printing must be checked with the selected Windows printer and driver after installation.
