# Clover connection-only pilot

Prepared November 24, 2026. This adapter is **not deployed or enabled in DESK**.
It does not implement charges, refunds, orders, or payment cancellation. Existing
cash and store-credit checkout behavior is unchanged. The connection adapter never
opens a business database or writes credentials to disk. The new setup screen
stores only hardware configuration in an additive table, with audit entries;
it does not modify terminal registration or existing operational records.

## Current result

- Owner confirmed Thrift Mart on the Clover Mini C305, with the device on the same
  network as pos1. Owner's TCP test on pos1 succeeded on port 12346.
- A verified HTTPS preflight using the new adapter succeeded from the development
  computer, Jasmin. REST Pay Display returned HTTP 401, requiring authorization.
  This proves secure reachability from that computer, **not an authorized pos1
  connection**. No payment requests were made.
- The Clover sandbox draft app is prepared with Merchant Read only. Sandbox
  authorization must not be used against the live Clover.
- The owner confirmed submitting verification under office@coastyfc.com. The signed-in production dashboard
  still displayed Account Unverified and missing identity/contact details when
  checked. Account submission/approval has not been confirmed by the portal.
- Clover's published approval pause runs November 10, 2026 through January 3,
  2027. Account verification and app approval are separate prerequisites.

Device addresses and account identifiers are retained only in the ignored local
diagnostic folder `output/clover-pilot`, not in release assets or this guide.

## Implemented and tested

`clover_connection.py` provides:

- Clover v2 OAuth authorization-code flow with S256 PKCE, single-use state,
  ten-minute expiry, and binding to the initiating authenticated admin session.
- Explicit app, merchant, store, terminal, device, and environment binding.
  A changed binding requires a fresh authorization. A callback for another app
  or merchant is rejected before any code exchange.
- In-memory token handling with redacted representations and expiration checks.
  This pilot deliberately requires reauthorization after expiration. It does not
  persist or automatically refresh tokens; production persistence and refresh
  rotation are separate work before release.
- Read-only verification that the device serial belongs to the expected merchant,
  followed by `GET /connect/v1/device/ping`. Only a 200 response containing boolean
  `connected: true` counts as successful authorization and connectivity.
- Secure LAN connections using Clover's official production CA in a private SSL
  context, TLS 1.2, and the documented cipher suites needed by this Mini. Hostname
  and certificate verification remain enabled. Windows certificate stores are not
  changed. Local targets must be explicit RFC1918 IPv4 addresses.
- No redirects, proxy forwarding, HTTP fallback, automatic retries, payment API,
  or remote error-body logging. Network calls have timeouts and response limits.
- A manual unauthenticated preflight command. It cannot accept tokens or initiate
  authorization, and a reachable device is never labeled authorized.

`test_clover_connection.py` contains 24 tests, all passing. They cover callback
tampering, replay and parallel callbacks, expiry, wrong merchant/device/store,
sandbox isolation, endpoint restrictions, refusal/busy responses, and real TLS
connections with disposable certificates. Wrong-name, expired, and untrusted
certificates fail before any HTTP request. Redirects are not followed.

### Setup controls added while approval is pending

- OFFICE: **System → Payment devices → Clover connection setup**. Also available
  from a terminal's printer/customer-display settings. Administrator-only access
  is enforced on the server, independently of what the browser displays.
- DESK: **MORE → Clover connection setup**. Shows only the current native
  registered device, and offers **Check connection · no charge**.
- Store/terminal identity, local IP address, serial number, and an optional
  confirmed merchant ID are saved in `retail_clover_pilot`. A store reassignment
  requires the administrator to reconfirm the configuration. A stale revision
  cannot overwrite newer settings. Duplicate serial assignments are rejected.
- The desktop check requires a one-use administrator approval bound to its
  native device ID and per-launch nonce. Approvals expire after 60 seconds and
  are invalidated by configuration changes, registration changes, logout, or
  revoked administrator status. The browser cannot pass an arbitrary network
  target to the native bridge. Approval tickets are held in memory, never written
  into the business database or audit logs.
- The new native bridge uses the saved, approved target and reports the actual
  source PC name. OFFICE directs the administrator to run the check on the
  intended DESK computer. Older DESK versions receive an update-needed message.
- Settings and progress screens explicitly keep card payments disabled and do
  not provide a payment function, token-entry field, or bypass for Clover approval.

Validation: **37 backend/native/security/data-integrity tests passed**, plus the
Clover UI checks. The UI was checked in all ten themes in both light and dark
modes. A simulated device check preserved an active sample cart. Populated
database checks preserved a completed sample cash sale, held cart, open and closed
timecards and breaks, timecard audit, reservation, and attachment, including
backup verification. No production database was opened by these tests.

Preview artifacts use clearly labeled sample terminals and a **simulated** native
device response. They are not evidence of authorization on the actual pos1:

- `output/preview/clover-pilot/office-setup.png`
- `output/preview/clover-pilot/desk-connection.png`

## Remaining work before live authorization

1. Wait for the production developer/app access Clover requires. The owner has
   confirmed which account was submitted. Do not use sandbox or
   manually generated merchant API tokens as substitutes for REST Pay OAuth.
2. Confirm the production Thrift Mart merchant ID from the owner's Clover
   dashboard. Store the expected merchant ID against the Thrift Mart configuration;
   do not trust an unsolicited OAuth callback to choose the store or merchant.
3. Add and review the HTTPS OAuth callback and authorization controls on the
   Operations server. The connection-settings screen above is implemented, but
   the browser authorization callback is not yet deployed. Require a fresh authenticated administrator session when
   starting and finishing authorization. Keep attempt state server-side; never
   return the verifier or tokens to ordinary browser scripts. Disable URL/query
   logging for the callback and use a no-referrer policy and no-store responses.
4. Configure the real, implemented Site URL and Alternate Launch Path in Clover.
   No placeholder URL has been saved in the developer portal.
5. Connect the authorization controls to the OAuth adapter. The native network
   check is already connected to it. Keep any retained credentials
   encrypted separately from store operational data and out of logs/backups intended
   for distribution. Add tested refresh-token rotation with serialized updates and
   recovery behavior before persistent use. This session-only pilot has no refresh
   retry or persistence behavior to depend on.
6. Bind the pilot to the existing pos1 registration and approved Clover serial.
   Run the authorized merchant/device check **on pos1**, not just on the Operations
   server or development computer. The device needs REST Pay Display running.
7. Verify the resulting successful authorized ping with no sale/order/payment
   created. Live payment capability is a later task requiring separate approval
   and payment/reconciliation testing.

## Developer checks

Run isolated tests:

```powershell
python -m unittest test_clover_connection test_clover_setup test_data_integrity test_pos_kiosk -v
python test_clover_setup_ui.py
```

The preflight can be run on the actual terminal using the address and serial
shown in REST Pay Display (replace the placeholders; do not supply credentials):

```powershell
python clover_connection.py --address <private-ip> --terminal <terminal-id> --serial <device-serial>
```

The output includes the actual source computer so a server-side check cannot be
mistaken for a check originating on pos1. No automatic release or updater changes
are part of this pilot.

## Official references

- [REST Pay development basics](https://docs.clover.com/dev/docs/rest-pay-development-basics)
- [Clover OAuth flow and state](https://docs.clover.com/dev/docs/oauth-flows-in-clover)
- [PKCE authorization](https://docs.clover.com/dev/docs/oauth-flow-for-low-trust-apps-pkce)
- [Local connection configuration](https://docs.clover.com/dev/docs/configuring-a-local-connection)
- [Merchant device lookup](https://docs.clover.com/dev/reference/devicegetmerchantdevices)
- [Read-only device ping](https://docs.clover.com/dev/reference/ping_device_get)
- [TLS cipher guidance](https://docs.clover.com/dev/docs/faqs)
- [Refresh-token lifecycle](https://docs.clover.com/dev/docs/use-refresh-token-to-generate-new-expiring-token)
- [Clover 2026 approval pause](https://docs.clover.com/dev/docs/announcing-2026-clover-code-freeze)
