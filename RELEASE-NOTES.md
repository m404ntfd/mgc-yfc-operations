# MGC YFC Operations 0.23.0

- Adds a Receipt Upload page from the login button and Receipts & Accounting.
- Supports mobile camera/photo selection and desktop file upload, with Settings-managed categories/codes.
- Adds Submit, Submit & Start New, Reset and Return to Dashboard. Signed-in users return to their chosen starting page; guests return to sign-in. Public uploads do not grant dashboard access.
- Stores receipts and categories in the server database, included in existing database backups. Administrators can review submitted files in Settings > Receipts.
- Email delivery remains pending the requested recipient list and email layout; confirmations explicitly report server storage, not sent mail.

Use Check for Updates on the host server, install and restart, then reload browsers. The Windows installer is also provided for desktop installations. Existing data paths and installation identity are preserved.
