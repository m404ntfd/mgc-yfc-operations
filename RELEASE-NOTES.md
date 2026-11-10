# CoastYouth Retail STORE OPS 0.50.0 / DESK 1.12.0 / OFFICE 1.9.0

- STORE OPS sign-in uses the green cart-and-wave icon and CoastYouth Retail STORE OPS wordmark on desktop and mobile.
- OFFICE catalog setup includes configured category and printing-category lists, multiple taxes, open-price behavior, and a save/discard prompt when leaving an unfinished item. Discounts and surcharges have separate configuration areas; card processing remains a future update.
- Glass appearance themes include color choices and improved dashboard contrast. OFFICE sign-in identifies CoastYouth Office.
- Invitation-only employee onboarding is available through STORE OPS, with administrator-only HR permissions by default, configurable HR email, help messages, progress tracking, completion notifications and printable employee packets in OFFICE.
- Browser completion uses original W-4 (2026), Mississippi withholding (Rev. 10/24), I-9 (01/20/25), and uploaded background-check pages. HR reviews and enables form versions. Existing signed versions are retained. Initial I-9 Sections 1 and 2 are supported; preparer/translator supplements require a separate signer workflow and are not enabled for browser signing in this release.
- Employee details require an area code and SAVE & CONTINUE advances the workflow. Phone numbers use (XXX) XXX-XXXX; SSNs mask their first five digits after leaving a field; date fields have calendar controls and MM/DD/YYYY formatting. Signed documents retain the complete required information. One final whole-document acknowledgment replaces per-page checkboxes.
- Encrypted form drafts, password-authenticated signatures, separate employer completion, immutable signature evidence, final completed-document downloads and HR review preserve the submitted record. Onboarding does not itself run a background check or replace required I-9 document examination.

## Installation and data preservation

Use the full Server or Computer Setup installer for this release: browser forms require the included PDF runtime components. Install over the existing application using its existing data folder, then update DESK and OFFICE. The legacy in-app update contains application code but cannot add those runtime components to older installations.

Existing timecards, open punches and breaks, reservations, attachments, sales, users, settings and account histories are retained through additive migrations. HR encryption keys are included in verified backups and must be retained with the database. No production records or credentials are included in release assets.

Create and verify a current backup before installation. Publishing provides downloads; it does not install updates on store computers or send employee invitations. Review HR form templates and employer settings before sending real invitations.
