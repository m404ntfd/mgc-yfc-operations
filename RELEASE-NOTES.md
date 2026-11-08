# CoastYouth Retail 0.44.0

DESK 1.7.0 and OFFICE 1.4.0 add reporting, shared user administration and coordinated updates. Publishing does not install updates on store computers.

- Operations Dashboard replaces Print with a Purpose with sales metrics, prior-period comparisons, item/category/employee breakdowns and permission-controlled clocked-in staff information.
- OFFICE adds sales, cash, product, account, tax and labor reports with printing and CSV export. Unsupported bowling, competition, gratuity, ingredient and payment-card reports are omitted. Labor cost percentage remains unavailable until wage history is recorded.
- OFFICE user editing adds Properties, Role, Personal and User View tabs, shared contact details, staff PIN and password controls. Login security and account unlocking move from the server to OFFICE.
- DESK logs out to a six-digit staff PIN screen. Protected Exit POS remains available. PIN sign-in requires HTTPS or localhost; password sign-in remains available.
- Server Updates has separate server, DESK and OFFICE sections. Native server/controller replacement uses the installer download option. Administration removes the old schedule/settings and user-management shortcuts.
- Backup shows progress and verified destination confirmation with an Okay button. Local verification does not confirm OneDrive cloud upload.
- Connections idle over 15 minutes are hidden. Server settings show the PC name and available client connection addresses.
- Combo server setup offers recognized legacy Remote Manager program-file cleanup on first launch. Shared data and uninstallers are retained.
- Web pickup/delivery, receipts, time clock and scheduling remain available. Managers can print employee schedules.

Additive changes preserve existing records and identifiers. Release checks cover populated upgrade from 0.43.0, backup, repeat startup and rollback, including timecards, punches, breaks, reservations, attachments, sales, catalog prices and store credit. Testing uses isolated sample data; live store data has not been changed.

Gmail delivery remains disabled until separately configured. Before installing, verify a current backup and let staff finish their work. Update the existing server first, then DESK and OFFICE using the same server address and data location. Do not create a replacement database.
