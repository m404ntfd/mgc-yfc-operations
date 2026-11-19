# CoastYouth Retail Round-Up Checkout — v0.60.0

When a cashier selects Pay now, DESK asks whether the customer would like to round up to the next dollar to support Youth for Christ. The cashier sees the exact donation and resulting total, with a prominent Yes, round up button on the left and No on the right. A coordinated customer-display overlay explains the ministry's mission on the Gulf Coast. Both screens follow the signed-in cashier's current theme, including glass palettes and dark themes.

## Checkout behavior

- Uses the existing donation setting in OFFICE. Enable donation prompts there to use the new flow; saved settings are retained.
- The donation is optional, added only after Yes, and recorded as a separate nontaxable receipt line. No leaves the sale unchanged and continues to payment. Closing the prompt returns to the sale.
- Whole-dollar totals and sales that already contain a donation skip the round-up question. A declined question is not repeated for the unchanged sale.
- Existing merchandise discounts, loyalty rewards and taxes are preserved. Retrying an interrupted save cannot duplicate the donation.
- The customer overlay clears when the cashier answers, cancels, changes the sale or disconnects. Training notices remain visible.
- Includes all previously published STORE OPS photo, checkout, credit/advance, printer, customer-display and update-policy improvements.

## Installation and data preservation

Versions: Server / Computer Setup **0.60.0**, DESK **1.20.0**. OFFICE **1.16.2** and STORE OPS desktop **1.5.2** remain compatible and are included in Computer Setup without a separate feature-version change.

Verify a current server backup, let staff finish/save their work, and update the shared server first. The server supplies the new checkout and customer-display screens. Then update/reopen DESK. Install over the existing applications and retain their data folders, server addresses and terminal registrations.

This release adds only a separate table for short-lived customer-display prompts. Existing timecards, punches, breaks, reservations, sales, photos, users, prices, account balances and settings are not reset or rewritten. Publishing does not itself install or restart the live server; its configured update policy remains in effect. The web app remains available.

## Verification

Checks cover 20 rendered theme/mode combinations, touch targets at 1920 × 1080, customer-display pairing and terminal isolation, consent/cancellation, discounts and rewards, whole-dollar totals, receipt output and interrupted-save retries.

Publication requires the application suites, Windows installer checks, repeat-install preservation, and a populated **0.59.2** upgrade with backup and rollback verification. All checks use isolated sample records, never the live store database.
