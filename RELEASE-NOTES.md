# POS 1.2.0 + Operations 0.39.7

Adds customer and employee store-credit accounts with search, account history,
permission-controlled adjustments, required reasons, and store-credit checkout.
Credit can cover all or part of a sale, with cash for the remainder. Payments and
balance deductions are atomic and safe to retry after an interrupted connection.

The server window now groups Operations/server updates, POS updates, and full
server/controller installer downloads. POS retains its warning countdown and
unfinished-sale protection. Credit-card processing remains a future update.

Install the Operations update first, then update POS. To receive the updated
Windows server/controller buttons, run the Operations installer in the existing
installation folder. Data migrations only add account tables; existing timecards,
open punches/breaks, reservations, attachments, identifiers and audit history are
preserved. Existing backup and rollback safeguards remain in place.
