# CoastYouth Retail cash advances and centralized updates

Server 0.53.0 / DESK 1.15.0 / OFFICE 1.12.0 / STORE OPS desktop 1.2.0

- Adds a Cash Advance button beside Store credit in DESK. Authorized staff select another employee, enter an amount and reason, and confirm the cash payment. Each advance records the store, registered terminal, recipient, issuing employee and payment time.
- Adds separate permissions to issue employee advances and view advance reports. Administrators have access by default; other roles must be assigned access. A user cannot issue their own advance.
- Records advances separately from sales and store credit. When reconciliation is enabled, an open drawer is required, available cash is checked, and the advance reduces expected drawer cash exactly once. Cash and drawer reports include advances even when reconciliation is disabled. Payroll recovery is handled separately.
- Adds OFFICE > Accounts > Employee cash advances, with store, date and employee filters, totals, printing and CSV export. Payment records retain their original names and cannot be silently changed or deleted. Retrying an interrupted request cannot create a duplicate advance.
- Makes OFFICE > System > Application updates the central location for DESK, OFFICE, STORE OPS desktop and the STORE OPS web app/shared server. Includes active-user checks, staff notifications, cancellation and a completion notice after the server restarts.
- Removes DESK and OFFICE update panels from the native server and standalone server administration applications. Server update and recovery controls remain available there.
- Adds permission-aware settings search to the OFFICE top bar, including keyboard navigation and protection for unfinished forms.

## Installation

Create a verified server backup and finish current work. Run the full Server/Administration 0.53.0 installer over the existing installation, retaining its current data folder. The full installer is required for the native server-window changes; the web-only update package cannot replace that Windows program.

Then update OFFICE to 1.12.0 and DESK to 1.15.0 using Computer Setup, the individual installers, or the registered-computer updater in OFFICE. Keep every application connected to the same existing server. STORE OPS desktop remains at 1.2.0 and receives its web screens from that server.

Configure issuing and reporting access in OFFICE > Security > Roles & permissions. Cash advances require a registered DESK terminal so the store and drawer are identified correctly.

Publishing makes these downloads available. It does not install software on store computers or restart the live server. The STORE OPS website remains at its existing address.

## Data preservation and verification

The new cash-advance ledger is additive. Existing timecards, open punches and breaks, audit history, reservations and attachments, sales, refunds, store-credit ledgers, users, HR records, settings and terminal registrations are preserved.

Release checks cover a populated 0.52.0 upgrade, verified backup, repeated startup and rollback using isolated sample data, plus installation over existing data and device settings. Feature checks cover permissions, store assignment, available drawer cash, concurrent requests, interrupted-response recovery, reports, checkout, staff update coordination, settings search and theme readability.

The inventory spreadsheet remains an import preview. This release does not import its items or change existing catalog prices or taxes.
