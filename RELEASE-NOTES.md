# CoastYouth Retail Initial Staff Giving — v0.58.0

Adds the initial staff Giving workspace in OFFICE, backed by the existing Operations database. Includes donor profiles and audited changes; received gifts with voids and linked corrections; filtered donor giving history; monthly commitment drafts and change history; monthly/yearly statement previews, saved copies and printing; and delivery preparation/cancellation history.

Saved statements display their original donor details and period separately from new preview criteria. Print and save actions appear above the document. Missing organization identity details show a setup notice.

Initial setup: update the Operations server, open OFFICE → Giving → Settings, and enter the organization EIN, mailing address and statement messages. Review staff Giving permissions before entering donor records. Review a statement preview before issuing statements. Existing saved copies retain their original details; save a new copy after correcting settings.

Clover payments, recurring charges, donor self-service and automatic email delivery are not enabled. Monthly commitments are drafts. Delivery preparation does not send email. Do not enter card numbers or security codes.

Preserves v0.57.0 connection and recovery improvements. Uses additive Giving tables with existing operational records retained. Release publication requires Giving endpoint/browser checks, populated upgrade/backup/rollback checks, the existing suite tests and Windows installer verification.

Versions: Operations server, Server Admin and Computer Setup 0.58.0; DESK 1.18.0; OFFICE 1.15.0; STORE OPS 1.4.0. Giving is supplied by the updated Operations server; existing client versions remain compatible.
