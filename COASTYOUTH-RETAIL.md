CoastYouth Retail DESK and OFFICE — development preview

DESK keeps checkout, grouped product buttons, receipt, cash/store-credit payment,
saved sales, and Operations links. Catalog, receipt/tax setup, and account
adjustments are in OFFICE. This-register controls retain the native DESK admin
exit passcode and update controls.

OFFICE has Home, Sales, Accounts, Security and System navigation. Its Users screen
uses the exact same /api/user, /api/admin/users, /api/roles and /api/admin/user-role
services as Operations. There is no second user table or synchronization copy.
The existing manage_users permission controls creation and role assignment;
existing server rules prevent granting permissions beyond the acting user's
access. User-management staff can enter OFFICE without checkout permission.
Roles editing still opens the existing Operations role editor.

The standalone OFFICE Windows launcher uses /office on the existing Operations
server. Its local settings contain only the server address, and its close guard
prevents discarding unfinished forms. DESK keeps its existing installation ID,
settings path, update asset naming and executable filename for compatibility;
window titles and shortcuts use CoastYouth Retail DESK. Temporary CY lettering
is used until the owner supplies application icons.

Reference analysis:
https://support.bowlingvision.com/article/378-sync-office-creating-new-user
https://support.bowlingvision.com/article/274-managing-roles-permissions-in-sync
https://support.bowlingvision.com/article/233-sync-office---accounts
https://support.bowlingvision.com/article/219-sync-desk-lane-sales-group-area
https://support.bowlingvision.com/article/220-sync-desk-lane-sales-package-area

Borrowed patterns: task-based Office sections, separate Desk checkout, product
groups, shared role-based user administration, and account history. Bowling-lane
controls and package-selling behavior were not introduced into this retail app.

Validation: shared-user creation in both directions, duplicate-name prevention,
shared role assignments, restricted OFFICE access, shared catalog, cash/credit
checkout and retry, update warnings, native DESK protection, native OFFICE close
guard, and existing timecard/reservation preservation. All use isolated data.

Not published. Existing live stores remain on POS 1.2.0 / Operations 0.39.7.


## Icon review — November 7, 2026
Saved the approved DESK/OFFICE and OPERATIONS original artwork from POS Name Ideas under assets/coastyouth-*-original.png. These are original presentation sheets, retained without alteration. Updated assets/create_icon.py to replace the server building with a computer while retaining all three red rings; dispatch.png and dispatch.ico are used by the existing server tray and packaging. Updated server tray help text accordingly. Icon preview only; not published. Separate DESK/OFFICE/OPERATIONS application-size extraction and wiring remain for the branding integration after review. No operational data was accessed or modified.

## Separate DESK / OFFICE build
DESK no longer exposes setup, catalog editing, receipt/tax settings, register settings, or update administration. Retail configuration belongs to OFFICE. DESK retains checkout, manual amounts, sales lookup, store-credit payment, Operations shortcuts, update warnings, and protected Exit. Mandatory initial exit-passcode setup remains in DESK; later changes are in OFFICE on the same checkout computer/Windows login/server, using server administrator approval. DESK rereads local protection before exit so OFFICE passcode changes take effect. Separate desk.ico and office.ico are exported from the approved original presentation sheet and wired to each executable and installer; embedded app branding uses those same separate marks. Existing installer IDs and database paths remain unchanged.
Validation: shared users/catalog browser test, native OFFICE unsaved-work close guard, native full-screen DESK and protected exit test, OFFICE-to-running-DESK passcode regression, data-integrity and embedded-asset tests passed. Separate Windows executable builds succeeded. Not published.
# Thrift workflows — unpublished preview

DESK's **Thrift store tools** button offers donated-item barcode entry, color-tag
assignment, voluntary donations, customer selection and loyalty redemption.
OFFICE's Sales section holds color/donation/loyalty rules, donation intake and
price tags, fulfillment and thrift reports. Its Accounts section holds customer
profiles and assistance-voucher issuance. Existing role permissions govern these
tools; voucher issuance requires Manage store credit and reporting/fulfillment
requires View POS sales.

- New programs are off until configured. Tag dates use the server's local date;
  weekday selection uses Monday–Sunday. Discounts are calculated on assignment
  and saved with the cart. Tag names remain visible on receipts. Promotional
  prices and bundles are excluded from tag discounts. Manual discounts/rewards
  on tag-discounted merchandise require the stacking setting.
- Optional round-ups/custom donations are separate receipt lines and excluded
  from merchandise dashboard metrics and loyalty earnings. The customer display
  invites the customer to tell the cashier. Donations cannot be reversed using
  merchandise returns; they need a separately reviewed accounting adjustment.
- Vouchers reuse the immutable store-credit ledger. Issue with recipient,
  funding reference, expiration and eligible categories; redeem by AC code using
  DESK Store credit. Ineligible items/donations require a separate transaction.
  Returns restore the original voucher account. Ordinary credit adjustments
  cannot bypass voucher issuance rules.
- Customer rewards earn on cash merchandise spend, excluding tax/donations.
  Credit/voucher purchases do not earn points. One reward per sale, capped at
  eligible merchandise value, with no manual-discount combination. Partial
  returns adjust earned/redeemed points cumulatively. Previously spent points
  can leave a negative balance recoverable through future earnings. Marketing
  consent is independent of membership and editable; no campaigns are sent.
- Sold slips reference completed receipts and record storage location, due
  date, contact and fulfillment status. Dispatch scheduling remains in STORE
  OPS; its appointment reference is entered on the slip. Slip edits never alter
  reservations. Print the saved slip from its editor.
- Intake creates a one-of-a-kind catalog item and Code 39 price label. Scan in
  DESK or select the item from the catalog. Quantity is one; checkout prevents
  duplicate sales across tills. Returns require explicit inspected restocking.
  Inventory age is shown in the latest-200-item intake list. Test actual scanner
  and printer/label stock before production use.
- Thrift reports provide net tag sales/markdowns, donations, net voucher
  redemptions, issued reward discounts, current voucher balances and current
  outstanding pickups. Print / Save PDF uses the system print dialog.

All new tables are additive. Existing sales remain immutable; no production
records were accessed during development. Tests cover request retries, stale
revisions, permissions, voucher restrictions, partial returns, duplicate intake
sales, reward balance conflicts and isolated browser workflows. A populated
v0.47.0 upgrade rehearsal preserved every existing row and attachment through
upgrade, backup, repeated startup and code rollback. This release does not enable credit-card processing.
