# CoastYouth Retail theme readability update

STORE OPS desktop 1.0.1 / DESK 1.12.1 / OFFICE 1.9.1 / Server 0.50.2

- Fixes dark text on dark buttons when glass themes and dark mode are combined.
- Pairs readable text and backgrounds for menus, form fields, dropdowns, hover, keyboard focus and disabled controls.
- Fixes contrast in communications, settings, receipt headings, connection badges and the Midnight manual-item form.
- Preserves the five glass color choices and colored product tiles.
- Keeps mobile STORE OPS menus fully on screen.
- Adds rendered contrast checks covering 244 screen/theme/mode combinations to the release workflow.

## Installation

Create a verified server backup, then update the existing server in place to 0.50.2. The shared theme styles are delivered by the server, so updating only a desktop launcher will not apply these fixes. Update the desired Windows clients using the individual installers or Computer Setup. Keep each client's existing server address and the server's existing data folder. Reopen clients or refresh browser pages after installation.

The STORE OPS web application remains available at its existing address. Publishing this release does not install it on store computers or restart the live server.

## Existing data

This is a presentation-only update with no database schema changes or business-record rewrites. Timecards, open punches and breaks, reservations, attachments, sales, users, HR records, encryption keys, account histories and settings remain on the existing server. Release gates verify populated upgrade, backup and rollback behavior using isolated sample data.
