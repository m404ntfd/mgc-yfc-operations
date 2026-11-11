# OFFICE Giving preview

The Giving section uses the existing Operations database. It is separate from retail sales, inventory donation intake, store credit, and cash drawers.

Implemented: donor profiles and statement preferences; an immutable ledger of gifts already received; audited correction voids with visible reason, staff name and timestamp; monthly commitment drafts; monthly and calendar-year printable statement previews; permanent saved statement copies and per-donor history; organization and statement-message settings. Amounts use integer cents. Retries use unique request identifiers and edits check record revisions. Voiding a record does not issue a refund.

Saving a statement captures the current donor, organization, message, gifts and totals in one transaction. Later edits and gift voids do not alter saved copies. Staff can reopen or print them from history. Saved copies are explicitly marked not sent; this does not claim delivery or issue a tax receipt automatically. Multiple copies for the same period are allowed for corrections; unique request IDs prevent accidental duplicates on retry.

Permissions: `view_giving` plus the applicable `manage_donors`, `record_gifts`, `adjust_gifts`, `manage_giving_plans`, `giving_statements`, or `giving_settings` grant. OFFICE access also uses its existing `use_pos` permission. Administrators retain access. All endpoints enforce permissions on the server.

This is a development preview. Clover payments, secure payment-method enrollment, recurring billing, donor self-service, automatic monthly/January emails, statement delivery history, and processor reconciliation are not connected. Draft monthly commitments cannot be activated. Never put payment credentials, card numbers, or security codes in donor fields. Statements are previews, not delivery confirmations. Configure the organization identity and review wording and goods/services details before issuing statements.

Next integration: confirm Clover ecommerce/recurring eligibility and rates; add hosted card capture and token storage, consent records, signed webhook reconciliation and duplicate-charge prevention; then implement scheduled delivery, retry history, and approved monthly/annual templates.

Validation: `python prepare_web_assets.py`, `python -m unittest test_giving test_giving_storage test_data_integrity test_startup_updates`, `python test_giving_ui.py`, and `python test_office_navigation_ui.py`. The Giving pull-request workflow runs these checks and the populated upgrade/backup/rollback test against the 0.56.0 baseline, and saves synthetic preview screenshots. Tests use isolated temporary databases and synthetic donors. The migration only adds giving tables/indexes/triggers. This branch does not change the version or install an update.

Printed previews and saved copies retain their status labels and saved reference. Received gifts show original recording details and correction history without changing the original ledger entry.

## Donor backend

`GET /api/giving/donor?id=...` retrieves a profile; `GET /api/giving/donors?search=...&limit=50&offset=0` searches name, email and address without loading gifts or plans. Search is case-insensitive and treats wildcard characters literally. Pages have a maximum of 100 records and stable name/ID ordering. The current implementation scans donor profiles in memory; database-indexed search remains future work for larger directories. Shared household emails are allowed and do not merge profiles.

`GET /api/giving/donor_history?donor=...` requires both view_giving and manage_donors. Each successful new profile or edit records immutable before/after values, staff name, timestamp and revision in the same transaction as the profile and retry receipt. A retry does not add history twice. Invalid revisions and unknown edit IDs are rejected. Concurrent donor saves are serialized before checking the revision. Existing donors are unchanged during migration; their first subsequent edit captures the prior profile, without inventing earlier history. No profile deletion or merge is introduced.

These endpoints are backend groundwork; the OFFICE interface does not yet display the directory or change history. The existing profile editor remains compatible. Validate with `python -m unittest test_giving_donors` in addition to the checks above.

## Gift ledger corrections

`POST /api/giving/replace_gift` takes the same fields as a received gift plus the original gift ID (`gift`) and a correction `reason`. It requires `view_giving`, `record_gifts`, and `adjust_gifts`. The original entry, its void, the replacement and the link between them are preserved in the ledger. The void, replacement, audit entry and retry receipt commit together. A repeated request returns the same replacement ID. An original that is already voided returns a conflict. Use `POST /api/giving/void` for a correction that requires no replacement.

The overview includes `replaces` and `replacement` gift IDs when linked. Current statements include the replacement according to its donor and gift date. Saved statement copies retain the original entries and totals. The replacement endpoint is ready for an OFFICE correction form.

## Monthly commitment backend

`POST /api/giving/plan` records each draft creation, edit or cancellation with its before and after values, revision, staff name and timestamp. The draft, history and retry receipt commit together. Retrying a save returns the original result. Edits require an existing draft ID and its current revision. Existing drafts keep their saved values and revisions, and the first subsequent edit captures the prior values.

`GET /api/giving/plan_history?id=...` returns newest changes first and requires both `view_giving` and `manage_giving_plans`. The existing OFFICE editor can continue creating, editing and cancelling drafts. OFFICE monthly drafts include a View history action for staff with plan-management permission. It shows newest changes first with before/after values, revision, staff and timestamp. Donor names reflect current profiles and IDs retain the recorded association. Older drafts with no history are labelled explicitly. History loading supports retry and ignores responses after navigation or closing. Run `python -m unittest test_giving_plan_history_ui -v` for isolated browser coverage; run `python prepare_web_assets.py` to regenerate bundled application assets before running or packaging the application. Drafts carry no payment authorization.
