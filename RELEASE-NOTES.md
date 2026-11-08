# CoastYouth Retail / Operations 0.45.0

Approved icon update for Operations Server, standalone Server Admin (Remote Manager), and the Operations web app.

- Server: three red rings with a server tower and green status light.
- Standalone administration: three red rings with a monitor and gear.
- Operations web: three red rings with a globe and dashboard, used for browser and home-screen icons.
- Windows installers, shortcuts, window icons and system-tray icons use the approved artwork.
- DESK remains 1.7.0 and OFFICE remains 1.4.0; their application icons and behavior are unchanged. Their installers remain included for complete computer setup.

This release changes branding assets and version information only. No database migrations or business-record changes are introduced. Release gates verify populated upgrade from 0.44.0, backup and rollback, as well as installer preservation of existing server data and client settings.

Verify a current backup before installing. Update the existing Operations installation using the same folder and data location. Use the full Operations installer to update native server/admin icons; the in-app server ZIP updates the web icon. Publishing does not install updates on store computers.
