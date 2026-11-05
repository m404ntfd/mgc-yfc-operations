# MGC YFC Operations 0.32.0

- Adds reusable permission Roles in Application Settings > Employees > Roles. Permissions are grouped into the same page/Application Settings categories as Settings. Assign a role in the employee's permission editor; role changes apply to assigned users on their next request.
- Adds Create and edit permission roles as a permission. Delegated role editors cannot add permissions they do not hold. Administrators retain all permissions, and existing individual employee permissions are preserved until a role is assigned.
- Return to Home follows the current starting page selected for that server calendar day, including changes made through Choose today's starting page.
- Separates the mobile receipt-reset buttons with full-width spacing and wrapped labels.
- Replaces the yellow disconnected banner with a transparent red overlay, the supplied animated Plug.gif, and centered NO INTERNET CONNECTION OR SERVER IS OFFLINE / PLEASE TRY AGAIN LATER text. It clears automatically after reconnecting and includes Try again.
- Adds the rings/building Apple touch icon and Android web-app manifest icons for home-screen shortcuts. Existing shortcuts may need to be removed and added again to refresh their cached icon.
- Embeds offline graphics and icons into the server during release packaging so the existing in-app updater delivers them too. Customer data and the legacy update file allowlist are preserved.

Use Check for Updates on the server, install and restart, then refresh browsers. The full Windows installer is also available for reinstalling over the existing location; do not uninstall first.

Windows applications remain unsigned; code signing is still deferred.
