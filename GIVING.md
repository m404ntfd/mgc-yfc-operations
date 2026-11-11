# OFFICE Giving preview

The Giving section uses the existing Operations database. It is separate from retail sales, inventory donation intake, store credit, and cash drawers.

Implemented: donor profiles and statement preferences; an immutable ledger of gifts already received; audited correction voids with visible reason, staff name and timestamp; monthly commitment drafts; monthly and calendar-year printable statement previews; permanent saved statement copies and per-donor history; organization and statement-message settings. Amounts use integer cents. Retries use unique request identifiers and edits check record revisions. Voiding a record does not issue a refund.

Saving a statement captures the current donor, organization, message, gifts and totals in one transaction. Later edits and gift voids do not alter saved copies. Staff can reopen or print them from history. Saved copies are explicitly marked not sent; this does not claim delivery or issue a tax receipt automatically. Multiple copies for the same period are allowed for corrections; unique request IDs prevent accidental duplicates on retry.

Permissions: `view_giving` plus the applicable `manage_donors`, `record_gifts`, `adjust_gifts`, `manage_giving_plans`, `giving_statements`, or `giving_settings` grant. OFFICE access also uses its existing `use_pos` permission. Administrators retain access. All endpoints enforce permissions on the server.

This is a development preview. Clover payments, secure payment-method enrollment, recurring billing, donor self-service, automatic monthly/January emails, statement delivery history, and processor reconciliation are not connected. Draft monthly commitments cannot be activated. Never put payment credentials, card numbers, or security codes in donor fields. Statements are previews, not delivery confirmations. Configure the organization identity and review wording and goods/services details before issuing statements.

Next integration: confirm Clover ecommerce/recurring eligibility and rates; add hosted card capture and token storage, consent records, signed webhook reconciliation and duplicate-charge prevention; then implement scheduled delivery, retry history, and approved monthly/annual templates.

Validation: `python prepare_web_assets.py`, `python -m unittest test_giving test_giving_storage test_data_integrity test_startup_updates`, `python test_giving_ui.py`, and `python test_office_navigation_ui.py`. The Giving pull-request workflow runs these checks and the populated upgrade/backup/rollback test against the 0.56.0 baseline, and saves synthetic preview screenshots. Tests use isolated temporary databases and synthetic donors. The migration only adds giving tables/indexes/triggers. This branch does not change the version or install an update.

Printed previews and saved copies retain their status labels and saved reference. Received gifts show original recording details and correction history without changing the original ledger entry.
