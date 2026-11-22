# CoastYouth Retail Readability — v0.63.1

The Assigned employees selector in request reviews and appointment editing now uses matching text and background colors in light, dark and glass themes. Dark mode no longer shows pale employee names on a white background.

- Selected employees have a clear row highlight, and keyboard focus on the selector remains visible.
- Nearby request-screen totals, the older-address notice and the pending-request summary retain readable contrast in dark and glass themes.
- Employee selections, saved assignments, permissions and request approval behavior are unchanged.

## Installation

Server / Computer Setup **0.63.1** includes the compatible DESK **1.22.0**, OFFICE **1.19.0** and STORE OPS desktop **1.6.0** installers. Those desktop versions remain unchanged because the shared server supplies the updated screens.

Verify a current backup and let staff finish or save their work. **Update the Operations server first**, using the existing installation and data folders. Then refresh the web page or close and reopen the desktop application. Computer Setup retains the verified server connection and administrator registration workflow introduced in 0.63.0.

This release changes screen styling and release metadata; it makes no database schema or operational-record changes. Sales, timecards, reservations, reports, users, settings, attachments and computer registrations remain in the existing shared data source. Publishing does not itself install or restart the live server; its configured update policy remains in effect.

## Verification

The rendered contrast check covers **268 theme/layout combinations**, including request review with a selected employee on desktop and mobile. The populated **0.63.0 → 0.63.1** release check verifies upgrade, backup, repeated startup and rollback while retaining original rows, open and historical timecards and breaks, sales, accounts, registrations, reservations and attachments. Windows installer checks verify repeated installation without replacing existing data or client settings.
