# CoastYouth Retail organized OFFICE settings

Server 0.54.0 / DESK 1.15.1 / OFFICE 1.13.0 / STORE OPS desktop 1.2.1

## Changes

- Organizes OFFICE into Products, Sales, Customers, Staff, Reports and System. Each category has focused groups with no more than five tools, reducing the number of choices shown at once.
- Adds location breadcrumbs and a return button for each settings group. Settings search opens the same tools and shows their new locations. Existing role permissions still control access.
- Preserves unfinished-item warnings when using the new navigation. Settings remain readable in light, dark and liquid-glass themes and on smaller desktop screens.
- Shows Open price in the bulk catalog, import preview and DESK layout editor for items that prompt the cashier for a price. This changes the label only; it does not change saved prices, tax rules or checkout behavior.
- Improves Computer Setup diagnostics. If a component installer stops, the message names the application, reports its exit code, lists completed applications and identifies the saved logs. Remaining applications are not started after a failure. Individual installers also write setup logs.
- Keeps the existing update size limit by losslessly compressing the embedded web assets in the update package. Application behavior and updater compatibility are preserved.

## Installation

Create a verified server backup and finish active work before installing. Keep the existing server data folder and connect all desktop applications to that same server. Update the shared server/web application to receive the new OFFICE screens. Computer Setup or the individual installers provide the updated desktop versions and installation logging.

Publishing makes these downloads available; it does not install them on store computers or restart the live server. STORE OPS remains available at its existing web address.

The installer diagnostics improve error reporting. They do not establish that an antivirus alert or an installation failure on a particular computer has been resolved. That computer can be investigated separately.

## Data preservation and verification

This release makes no database schema changes and does not import, replace or delete catalog data. Existing imported products, prices, taxes, departments, users, settings, terminal registrations, timecards, open punches and breaks, audit history, reservations and attachments, sales and account balances remain in the shared server database.

Checks cover navigation, search, permissions, unsaved forms, theme readability, open-priced item labels and existing OFFICE/DESK workflows. Release checks include a populated 0.53.0 upgrade, verified backup, repeated startup and rollback using isolated sample data, plus installation over existing data and device settings. Installer failure tests use harmless sample installers and verify that data files remain unchanged.
