# Standing data-integrity requirement

The owner requires this and every future update to preserve the integrity of timecard and reservation data.

- Preserve existing timecards, clock punches, breaks, audit history, reservations/dispatch appointments, identifiers, account relationships, timestamps, statuses, notes, and attachments during upgrades.
- Use additive, backward-compatible migrations. Never reset, replace, truncate, or silently rewrite operational data to implement a UI change or resolve a migration problem.
- Before a release, test upgrades against an isolated populated database, verify that existing records and relationships survive, and verify backup/rollback behavior. Include checks for open punches and breaks, historical records, audit entries, and reservation attachments.
- Keep production databases, customer records, backups, credentials, and environment settings out of Git and release assets. Tests must use isolated data and backup destinations.
- If a requested change actually requires modifying existing operational records, make that change explicit, preserve an appropriate backup and audit trail, and resolve any ambiguity with the owner before the destructive step.

These requirements apply to future releases as well as the scheduling redesign.
