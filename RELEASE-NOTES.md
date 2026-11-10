# CoastYouth Retail catalog setup and reporting hierarchy

Server 0.52.0 / DESK 1.14.0 / OFFICE 1.11.0 / STORE OPS desktop 1.2.0

- Separates Revenue Centers, Departments, Sub Departments, printing categories and taxes into their own OFFICE setup screens.
- Replaces item category labels with Sub Department. Each Sub Department selects a Department, and each Department selects its reporting Revenue Center.
- Adds a complete-entry form with an Add button, a highlighted saved-entry list, and delete, x2 copy and pencil edit controls. The same controls are used for printer routes and color-tag rules.
- Saves each added, edited or deleted setup entry to the shared server. Copies receive a new identity after review and Add. Interrupted saves can be retried without creating duplicates.
- Protects setup entries that are still assigned to products, child Departments, printing routes, assistance vouchers or priced inventory. Unsaved details require confirmation before discarding.
- Adds sales reports by Sub Department, Department and Revenue Center. New sale lines record their reporting assignment; returns use the original assignment. Older sales without the hierarchy remain separate and are not reassigned retroactively.
- Retains existing product and discount-rule links when a Sub Department is renamed. Existing categories appear as Sub Departments until their parent Departments are assigned.
- Keeps the new lists readable in light, dark and glass palettes, including the selected row and action buttons.

## Installation

Create a verified server backup and finish current work. Update the existing server in place to 0.52.0 first, retaining its current data folder. Then use Computer Setup or the individual installers to update OFFICE, DESK and STORE OPS. Keep each application connected to the same existing server. Existing terminal registrations and device settings are retained.

In OFFICE, configure Revenue Centers first, then Departments, then assign Sub Departments. Products retain their current Sub Department until an authorized user changes it. Taxes and printer destinations are configured separately.

The STORE OPS web application remains available at its existing address. Publishing makes the installers available; it does not restart the live server or install software on store computers.

## Data preservation and verification

This release does not reset or replace operational tables. Timecards, open punches and breaks, reservations and attachments, sales, refunds, store-credit ledgers, users, HR records and settings remain on the existing server. Completed receipts retain their recorded prices, taxes and reporting assignments.

Release checks exercise a populated 0.51.0 upgrade, verified backup, repeated startup and rollback using isolated sample data. Installer checks retain existing data and device settings. Catalog checks cover permissions, conflicting edits, linked-entry deletion protection, tax removal followed by an original-sale refund, and interrupted-save retries. Browser checks exercise setup actions, checkout, receipts, reports and theme readability.
