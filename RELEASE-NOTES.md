# MGC YFC Operations 0.31.0

- Requires a current eligible user to be selected when uploading a receipt without signing in. Guest submissions are assigned to that user's profile and are searchable in their receipt history and authorized all-user reports.
- Clearly labels guest assignments so they are distinct from authenticated user submissions. Selecting a user does not sign in or expose receipt files.
- Adds Reimbursement Required to both guest and signed-in receipt forms. The flag is saved and displayed in receipt history, receipt reports and administrative receipt review.
- Adds Submit receipts and appear in guest receipt assignment to employee permissions. Existing users retain receipt submission by default; administrators can disable it for individual employees. Administrators can always submit.
- Validates selected users and reimbursement values on the server, rejects stale selections, and keeps the existing receipt storage compatible with older server versions.

Use Check for Updates on the server, install and restart, then refresh browsers. The full Windows installer is also available for reinstalling over the existing location; do not uninstall first.

Windows applications remain unsigned; code signing is still deferred.
