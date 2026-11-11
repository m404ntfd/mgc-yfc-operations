# CoastYouth Retail OFFICE Status Bar — v0.58.1

Adds a compact bottom bar in OFFICE showing the loaded web application version, installed OFFICE launcher version when available, Operations connection status, signed-in user, and local date and live time.

The bar reserves space below the workspace, uses a two-row layout on narrow screens, and is hidden when printing. Connection status follows existing server checks and waits for confirmation after the network reconnects.

Install the Operations server update and reopen OFFICE to load the new bar. The native OFFICE launcher remains 1.15.0; the web application shows 0.58.1. DESK remains 1.18.0 and STORE OPS remains 1.4.0.

Retains the initial staff Giving features from v0.58.0. Clover payments, recurring charges, donor self-service and automatic emails remain disabled. No database migration or operational data changes are introduced by the status bar.

Publication is gated on Windows/Linux application tests, browser and packaging checks, Giving checks, and populated upgrade/backup/rollback and installer verification.
