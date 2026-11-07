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
