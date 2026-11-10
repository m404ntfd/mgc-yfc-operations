# CoastYouth Retail STORE OPS Desktop 1.0.0 / Server 0.50.1

- Adds the installable STORE OPS Windows application with the green cart icon, shared server connection setup, existing sign-in and permissions, and the complete STORE OPS web interface.
- Keeps operations.coastyfc.com available for mobile and remote browser use. Desktop and web use the same server records; the desktop client does not create a second business database.
- Adds STORE OPS to Computer Setup as an optional component, selected for office computers and available through Custom selection on POS computers.
- Protects unfinished work when closing the desktop window. Supports document downloads and desktop pickup-slip printing.
- Improves glass-theme header and report-title contrast.

## Installation

Install CoastYouth-Retail-STORE-OPS-Setup-v1.0.0.exe on the office or POS computer. Keep the default https://operations.coastyfc.com connection, or enter the existing store server address. Sign in with the existing account. The application requires access to that server and Microsoft Edge WebView2 Runtime.

Server 0.50.1 includes the matching desktop controls and printing adjustments. Update the existing server installation in place after creating a verified backup. Do not create a replacement server or change its data folder. DESK remains 1.12.0 and OFFICE remains 1.9.0.

## Data preservation

No database schema changes or business-record rewrites are introduced by this release. Existing timecards, open punches and breaks, reservations, attachments, sales, users, account histories, HR records, encryption keys and settings remain on the existing server. Release checks include populated upgrade, backup and rollback verification. Publishing installers does not install them on store computers or interrupt the running website.
