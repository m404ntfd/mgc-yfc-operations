# CoastYouth Retail terminal registration and computer updates

Server 0.51.0 / DESK 1.13.0 / OFFICE 1.10.0 / STORE OPS desktop 1.1.0

- Adds visible selection checkboxes beside computers in OFFICE updates, plus Select all, Clear selection and a selected count. Nothing is selected by default.
- Requires an administrator to complete first-time desktop registration after connecting to the shared server.
- Displays the saved computer name and Registered status in DESK, OFFICE and STORE OPS terminal setup.
- Keeps computer registration when the application restarts, is updated or changes IP address. Existing checkout assignments, layouts and store selections are retained.
- Preserves OFFICE's device configuration when changing its server connection.
- Includes STORE OPS in registered-computer application updates, with staff warnings, a countdown, verified installers and protection for unfinished work.

## Installation

Create a verified server backup and finish current work. Update the existing server in place to 0.51.0 first, keeping its existing data folder. Then update DESK, OFFICE and STORE OPS on each computer using Computer Setup or the individual installers. Older STORE OPS installations need this installer once before receiving coordinated desktop updates.

Open each desktop application against the same server. If registration is required, sign in with an administrator account, confirm the computer name and role, and select Register terminal. DESK can use an existing unassigned checkout or create one; existing assigned checkouts are retained. Registration is shared by applications on the same Windows computer. In OFFICE, select computers under View updates before sending an update request. Closed applications and offline computers receive pending requests when they reopen and sign in.

The STORE OPS web application remains available at its existing address. Publishing does not install updates on store computers or restart the live server.

## Existing data

No business records or database tables are reset or replaced. Timecards, open punches and breaks, reservations, attachments, sales, users, HR records, account histories and settings remain on the existing server. Release checks cover populated upgrades from 0.50.2, verified backups, repeat startup, rollback, installer data preservation and retained computer/checkout registrations using isolated sample data.
