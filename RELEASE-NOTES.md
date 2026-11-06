# MGC YFC Operations 0.39.2

- Reorganizes user setup into Properties, Role, Personal, and User view tabs using the existing application style.
- Adds a responsive settings tile menu with descriptions and permission-aware navigation.
- Separates role editing into Properties and Permissions, with category filters, search, and Enable shown / Disable shown actions.
- Keeps existing individual permissions and shared-role assignments intact. Individual access is edited separately by administrators; hidden permissions are preserved when filtered role changes are saved.
- Adds browser checks for permission preservation, restricted role managers, personal details, mobile/dark layouts, and unchanged operational records.

No database migrations or changes to timecard or reservation storage. Existing records, attachments, and account relationships are preserved. The administrator connection checks introduced in 0.39.1 remain included.

Install using Update server → Check for server updates → Install update & restart. Save work and sign out of other application connections before installing.
