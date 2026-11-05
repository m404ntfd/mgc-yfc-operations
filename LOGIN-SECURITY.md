# Login security

In the browser, open Settings > Login Security. Administrators can set 1–100 failed attempts before lockout; the default is 5. Consecutive failures are counted per account regardless of device or tunnel address. Successful sign-in resets the count. Locked accounts stay locked across server restarts. Changing the limit applies to subsequent failed attempts and does not unlock accounts.

Use Refresh locked accounts, then Unlock user. Unlocking resets the failed-attempt counter without changing the password. The permission “Unlock employee accounts after failed logins” can be assigned under Employees > Edit user / permissions. Delegated employees cannot change the attempt limit or reset passwords unless separately authorized. The application currently assigns permissions to individual employees, not named roles. Assign this permission to at least one other trusted employee for administrator recovery.

The native manager changes and local recovery script require the full Windows installer update; the in-app server update delivers the web/API controls.

On the Windows server, Manage / update server > Login security / unlock opens the same settings in the native administration window. The Remote Manager has this button too; native manager sign-in remains administrator-only. Delegated employees use the web settings. Locks, settings, and audit records are stored in schedule.db and included in backups. Existing signed-in sessions are retained; lockout blocks new sign-ins.

If no authorized person can sign in, run the following from a command prompt in the installation folder on the host computer (substitute the actual employee name and data folder):

```
runtime\python.exe unlock_local.py "Employee Name" --data "C:\path\to\data"
```

This recovery requires local access to the server database and writes an audit entry. It does not expose a network recovery endpoint.

# Turn off Cloudflare's extra verification

Install and verify the server update before changing Access. These steps bypass Cloudflare's sign-in only; the Operations employee login remains required.

1. Open Cloudflare Zero Trust / Cloudflare One and go to Access > Applications (the newer navigation may say Access controls > Applications).
2. Edit the `operations` application for `operations.coastyfc.com`.
3. In Policies, add a policy named `Operations — application login` with Action `Bypass`.
4. Under Include, choose `Everyone`. Attach this policy only to the operations application. Leave the original staff Allow policy available so bypass can be undone easily.
5. Save the policy and application. Keep the tunnel, published hostname route, and proxied DNS record in place.
6. In a private/incognito browser window, open https://operations.coastyfc.com. You should reach the application's own login without the Cloudflare email-code prompt.

To restore Cloudflare verification, detach/remove the Bypass policy and keep the original staff Allow policy attached. Bypass removes the Access authentication gate and Access request logging for matching requests; anyone can reach the application login. Cloudflare recommends against permanent bypass for internal applications. Do not confuse Bypass with Allow Everyone, which can still require authentication.

Official documentation: https://developers.cloudflare.com/cloudflare-one/access-controls/policies/
